"""Sounds and timed speech: sources, edits, placement and soundtrack mixing."""

import dataclasses
import marshal
import math
import os
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from types import CodeType
from typing import TYPE_CHECKING, ClassVar, Self
from warnings import deprecated

import numpy as np

from manimgx.animation import clock
from manimgx.animation.easing import linear
from manimgx.animation.timeline import Animation, AnimationOptions
from manimgx.caches import Memo
from manimgx.mobject import Mobject

if TYPE_CHECKING:
    from manimgx.scene import Scene
import json
import re
from collections.abc import Sequence

RATE = 48_000
"""The soundtrack's sample rate: 48,000 samples a second, as video's sound has."""
CUT = 0.005
"""How long a sound cut short fades out, at least, in seconds: a cut mid-wave clicks."""
DUCK_ATTACK, DUCK_RELEASE = 0.15, 0.5
"""How long a ducking sound takes to dip before speech, and to come back after it (s)."""
BITRATE = 224_000
"""The soundtrack's bitrate per channel: AAC-LC at 224 kbps."""

type Source = str | os.PathLike[str] | bytes | np.ndarray
"""What a sound is made from: a file's path, a file's bytes (any common audio file: WAV, AIFF,
MP3, AAC/M4A, Opus, Vorbis, FLAC, ALAC; a video's sound too), or samples (float, -1 to 1: one
column per channel)."""

_DECODED: Memo[int, np.ndarray] = Memo(64)


@dataclass(frozen=True, slots=True)
class _Edit:
    """How a sound is made from its source: in the order applied."""

    start: float = 0.0  # the source trimmed to [start, end) seconds
    end: float | None = None
    speed: float = 1.0  # played faster (and higher) or slower (and lower)
    loop: float | None = None  # repeated to last this long (inf: until stopped)
    gain: float = 0.0  # in decibels
    fade_in: float = 0.0
    fade_out: float = 0.0
    pan: float = 0.0  # -1 left, 0 center, 1 right
    duck: float = 0.0  # decibels it dips by while anything speaks


class Sound(Animation[Mobject]):
    """A sound a film plays.

    Make one from a file, the bytes of one, or samples; edit it (each edit makes a new
    sound); place it in a scene: [`add_sound`][manimgx.Scene.add_sound] starts it now and
    takes no time, while [`play`][manimgx.Scene.play] plays it as a part of the play, which
    then lasts at least as long as the sound. In a composition it starts when its window
    opens: `LaggedStart(*(AnimationGroup(FadeIn(d), click) for d in dots))` clicks as each
    dot appears. It changes nothing on screen, and a play's `run_time` does not change it:
    a sound lasts its [`duration`][manimgx.audio.sound.Sound.duration].

    Args:
        source: A file's path, a file's bytes, or samples: floats from -1 to 1, one
            column per channel (a 1-D array is mono), copied as they are given.
        rate: The samples' rate, in samples a second; only for samples.
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": linear}
    speaks: ClassVar[bool] = False  # speech ducks what is set to duck

    def __init__(self, source: Source, *, rate: int | None = None) -> None:
        if isinstance(source, np.ndarray) != (rate is not None):
            raise ValueError("give a rate with samples, and only with samples")
        if rate is not None and (not math.isfinite(rate) or rate <= 0):
            raise ValueError("the sample rate must be finite and positive")
        if isinstance(source, str | os.PathLike) and not Path(source).is_file():
            raise FileNotFoundError(f"no sound file at {os.fspath(source)!r}")
        if isinstance(source, np.ndarray):  # its own: the samples as they were given
            source = np.array(source, copy=True, subok=True)
        self.source = source
        self.rate = rate
        self._edit = _Edit()
        super().__init__(None)

    # ── edits: each makes a new sound ─────────────────────────────────────────
    def _but(self, **changes: float | None) -> Self:
        other = object.__new__(type(self))
        other.__dict__.update(self.__dict__)
        other._edit = dataclasses.replace(self._edit, **changes)
        other.__dict__.pop("_made", None)
        return other

    def gain(self, decibels: float) -> Self:
        """This sound louder by `decibels` (quieter if negative: -6 halves it)."""
        return self._but(gain=self._edit.gain + decibels)

    def fade_in(self, seconds: float) -> Self:
        """This sound fading in from silence over its first `seconds`."""
        return self._but(fade_in=seconds)

    def fade_out(self, seconds: float) -> Self:
        """This sound fading out to silence over its last `seconds`."""
        return self._but(fade_out=seconds)

    def trim(self, start: float = 0.0, end: float | None = None) -> Self:
        """The part of this sound from `start` to `end` seconds (None: its end)."""
        return self._but(start=start, end=end)

    def loop(self, duration: float | None = None) -> Self:
        """This sound repeated to last `duration` seconds; None: until the film ends, or
        until its clip is [stopped][manimgx.audio.sound.Clip.stop]."""
        return self._but(loop=math.inf if duration is None else duration)

    def speed(self, factor: float) -> Self:
        """This sound played `factor` times as fast, as a tape is: higher and shorter.

        The resulting speed must be finite and positive.
        """
        speed = self._edit.speed * factor
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError("the resulting speed must be finite and positive")
        return self._but(speed=speed)

    def pan(self, position: float) -> Self:
        """This sound placed from -1 (left) through 0 (center) to 1 (right)."""
        return self._but(pan=position)

    def duck(self, decibels: float = 12) -> Self:
        """This sound dipping by `decibels` while anything speaks (while a
        [`Speech`][manimgx.audio.Speech] plays): music under a narration. It eases down
        `DUCK_ATTACK` seconds before the speech and back up over `DUCK_RELEASE` after.
        """
        return self._but(duck=decibels)

    @classmethod
    def of(
        cls, function: Callable[[np.ndarray], np.ndarray], duration: float
    ) -> "Sound":
        """A sound made by a function of time: `function(t)`, given the times of its
        samples (seconds, an array), returns their values (-1 to 1).

        Examples:
            `Sound.of(lambda t: 0.3 * np.sin(2 * np.pi * 440 * t), 1)`: a second of A.
        """
        t = np.arange(round(duration * RATE)) / RATE
        return cls(np.asarray(function(t), np.float32), rate=RATE)

    # ── what it is ──────────────────────────────────────────────────────────────
    @property
    def samples(self) -> np.ndarray:
        """Its samples at `RATE`: floats, one column per channel (1 or 2)."""
        made = self.__dict__.get("_made")
        if made is None:
            made = self.__dict__["_made"] = _make(self)
        return made

    @property
    def duration(self) -> float:
        """How long it lasts, in seconds (inf for a sound looped until stopped)."""
        if self._edit.loop is not None:
            return self._edit.loop
        return len(self.samples) / RATE

    @property
    def _duration(self) -> Fraction:
        return (
            Fraction(len(self.samples), RATE)
            if self._edit.loop is None
            else super()._duration
        )

    @property
    def run_time(self) -> float:
        """Its duration: a sound plays for as long as it lasts. An endless one (`loop()`)
        cannot be played: add it ([`add_sound`][manimgx.Scene.add_sound]), and stop it.
        """
        if self._edit.loop == math.inf:
            raise ValueError(
                "an endless sound (loop()) never ends: add it with add_sound, and stop"
                " its clip, instead of playing it"
            )
        return self.duration

    @run_time.setter
    def run_time(self, value: float) -> None:
        pass  # a play's run_time sets its animations', not its sounds'

    # ── as an animation: it changes nothing on screen ─────────────────────────
    def begin(self) -> None: ...
    def finish(self) -> None: ...
    def clean_up_from_scene(self, scene: "Scene") -> None: ...
    def advance(self, t: Fraction) -> None: ...
    def interpolate(self, alpha: float) -> None: ...


@dataclass(eq=False)
class Clip:
    """A sound as a film plays it: from `start`, in seconds of scene time, until it ends
    or is stopped. [`add_sound`][manimgx.Scene.add_sound] returns it."""

    sound: Sound
    start: Fraction
    end: Fraction | None = (
        None  # stopped: silent from here, having faded out over `fade`
    )
    fade: float = 0.0

    def stop(self, fade: float = 0.05) -> None:
        """Stop the sound: it fades out from now (the instant the scene is computing) over
        `fade` seconds, and is silent after."""
        self.end, self.fade = clock.now + clock.rational(fade), fade


def _source_samples(sound: Sound) -> np.ndarray:
    """Source samples at RATE (2-D), possibly borrowed; consumers must not mutate them."""
    source = sound.source
    if isinstance(source, np.ndarray):
        data = source.astype(np.float32, copy=False).reshape(
            len(source), math.prod(source.shape[1:])
        )
        rate = sound.rate
        assert rate is not None
        return data if rate == RATE else _resample(data, rate, RATE)
    raw = source if isinstance(source, bytes) else Path(source).read_bytes()
    from manimgx._engine import digest

    key = digest(raw)
    return _DECODED.recall(key, lambda: _decode(raw))


def _decode(raw: bytes) -> np.ndarray:
    from manimgx._engine import decode_audio

    samples, channels = decode_audio(raw, RATE)
    return np.frombuffer(samples, np.float32).reshape(-1, channels)


def _resample(data: np.ndarray, rate: float, to: float) -> np.ndarray:
    """Samples at `rate` resampled to `to`: band-limited (the engine's windowed sinc)."""
    from manimgx._engine import resample_audio

    channels = data.shape[1]
    out = resample_audio(np.ascontiguousarray(data).tobytes(), channels, rate, to)
    return np.frombuffer(out, np.float32).reshape(-1, channels)


def _make(sound: Sound) -> np.ndarray:
    """The sound's samples: its source trimmed, sped, looped, its gain, fades and pan. An
    endless loop is one round of it, without fades: the mix repeats it for as long as its
    clip plays, and fades it where the clip starts and ends."""
    e = sound._edit
    data = _source_samples(sound)
    data = data[round(e.start * RATE) : None if e.end is None else round(e.end * RATE)]
    if e.speed != 1:
        data = _resample(data, RATE * e.speed, RATE)
    if e.loop is not None and math.isfinite(e.loop) and len(data):
        n = round(e.loop * RATE)
        data = np.tile(data, (-(-n // len(data)), 1))[:n]
    data = data * np.float32(10 ** (e.gain / 20))
    if e.loop != math.inf:
        _ramp(data, e.fade_in, e.fade_out)
    if e.pan:
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        data[:, 0] *= min(1.0, 1 - e.pan)
        data[:, 1] *= min(1.0, 1 + e.pan)
    return data


def _ramp(data: np.ndarray, fade_in: float, fade_out: float) -> None:
    """Fade the ends of `data` in place: linear ramps of those lengths."""
    for seconds, head in ((fade_in, True), (fade_out, False)):
        n = min(len(data), round(seconds * RATE))
        if n:
            ramp = np.linspace(0, 1, n, endpoint=False, dtype=np.float32)[:, None]
            if head:
                data[:n] *= ramp
            else:
                data[len(data) - n :] *= ramp[::-1]


def mix(clips: list[Clip], duration: Fraction) -> np.ndarray | None:
    """The soundtrack of a film `duration` seconds long: its clips mixed, at RATE (one
    column per channel: mono when every clip is mono and centered); None if it has none.

    A clip plays from its start until its sound ends, it is stopped, or the film ends; a
    sound cut short fades out over its stop's fade, or `CUT` at least (a cut mid-wave
    clicks). An endless loop fades in where its clip starts and out where it ends.
    """
    if not clips:
        return None
    total = round(duration * RATE)
    channels = max(c.sound.samples.shape[1] for c in clips)
    out = np.zeros((total, channels), np.float32)
    for clip in clips:
        at = round(clip.start * RATE)
        if at >= total:
            continue
        e, data = clip.sound._edit, clip.sound.samples
        span = (total if clip.end is None else min(total, round(clip.end * RATE))) - at
        if span <= 0:
            continue
        stop = 0.0 if clip.end is None else clip.fade
        if e.loop == math.inf and len(data):
            data = np.tile(data, (-(-span // len(data)), 1))[:span]
            _ramp(data, e.fade_in, max(e.fade_out, stop, CUT))
        elif len(data) > span:
            data = data[:span].copy()
            _ramp(data, 0, max(stop, CUT))
        if e.duck:
            data = data * _ducked(clips, e.duck, at, len(data))[:, None]
        out[at : at + len(data)] += data  # mono into each channel of stereo
    return out


def _ducked(clips: list[Clip], decibels: float, at: int, length: int) -> np.ndarray:
    """The gain of a ducking sound placed at sample `at` for `length` samples: 1, dipping
    by `decibels` while any speech among `clips` plays (eased on a 10 ms grid)."""
    low, hop = 10 ** (-decibels / 20), RATE // 100
    grid = np.arange(at, at + length + hop, hop, dtype=np.float64) / RATE
    gain = np.ones(len(grid))
    for clip in clips:
        if clip.sound.speaks:
            a = float(clip.start)
            b = a + clip.sound.duration
            if clip.end is not None:
                b = min(b, float(clip.end))
            if b <= a:
                continue
            ease_in = np.clip((grid - (a - DUCK_ATTACK)) / DUCK_ATTACK, 0, 1)
            ease_out = np.clip(((b + DUCK_RELEASE) - grid) / DUCK_RELEASE, 0, 1)
            gain = np.minimum(gain, 1 - (1 - low) * np.minimum(ease_in, ease_out))
    return np.interp(np.arange(length) / hop, np.arange(len(grid)), gain).astype(
        np.float32
    )


@dataclass(frozen=True, slots=True)
class Word:
    """A word of a speech, and when it is said: from `start` to `end`, in seconds from the
    speech's start."""

    text: str
    start: float
    end: float


class Speech(Sound):
    """Speech: a sound that knows what it says and when it says each word.

    A voice returns one. It plays as any sound does; [`Scene.say`][manimgx.Scene.say]
    also times animations by its words.

    Args:
        source: The audio: a file's path, a file's bytes, or samples.
        text: What it says.
        words: Each word and when it is said, if the voice knows; otherwise they are
            estimated from the audio.
        rate: The samples' rate; only for samples.
    """

    speaks: ClassVar[bool] = True

    def __init__(
        self,
        source: Source,
        *,
        text: str,
        words: Sequence[Word] = (),
        rate: int | None = None,
    ) -> None:
        super().__init__(source, rate=rate)
        self.text = text
        self._words = tuple(words)  # the source's: before trims and speed

    @property
    def words(self) -> tuple[Word, ...]:
        """Its words, in order, with when each is said (in seconds from its start): the
        voice's, or estimated from the audio; a trim or a change of speed moves them with
        the audio."""
        if not self._words:
            self._words = estimate(self.text, _source_samples(self))
        e = self._edit
        if e.start == 0 and e.speed == 1 and e.end is None:
            return self._words
        end = math.inf if e.end is None else e.end
        return tuple(
            Word(w.text, (w.start - e.start) / e.speed, (w.end - e.start) / e.speed)
            for w in self._words
            if e.start <= w.start < end
        )


type Voice = Callable[[str], Speech]
"""Anything that speaks: a function from text to [`Speech`][manimgx.audio.Speech]. Bring any
text-to-speech: wrap its call in a function that returns `Speech(audio, text=text)`."""


# ── timing ───────────────────────────────────────────────────────────────────────────────


_WORD = re.compile(r"\S+")


def estimate(text: str, samples: np.ndarray) -> tuple[Word, ...]:
    """When each word of `text` is said in `samples`, estimated: the audio's voiced span
    shared among the words by their letters, with a share more for the pause after a comma or
    a full stop."""
    words = _WORD.findall(text)
    if not words:
        return ()
    level = np.abs(samples).max(axis=1) if samples.ndim > 1 else np.abs(samples)
    hop = RATE // 100  # 10 ms
    frames = len(level) // hop
    loud = level[: frames * hop].reshape(frames, hop).max(axis=1) > 0.02
    voiced = np.flatnonzero(loud)
    if not len(voiced):
        total = len(samples) / RATE
        return tuple(
            Word(w, total * i / len(words), total * (i + 1) / len(words))
            for i, w in enumerate(words)
        )
    first, last = voiced[0], voiced[-1] + 1
    # weight: letters, plus a pause after a comma or a full stop
    weights = []
    for w in words:
        weights.append(len(w) + (6 if w[-1] in ".!?:;" else 3 if w[-1] == "," else 1))
    total_weight = sum(weights)
    edges = np.concatenate([[0], np.cumsum(weights)]) / total_weight
    span = (last - first) / 100
    times = first / 100 + edges * span
    return tuple(
        Word(
            w,
            float(times[i]),
            float(times[i + 1] - (weights[i] - len(w)) / total_weight * span),
        )
        for i, w in enumerate(words)
    )


@deprecated("ManimGX's machinery: the captions call it", category=None)
def lines(speech: Speech, width: int = 42) -> list[tuple[float, float, str]]:
    """A speech as captions: its words in lines of at most `width` characters, a line ending
    at the end of a sentence, each shown from its first word's start until the next line's
    (or its last word's end), in seconds from the speech's start."""
    out: list[tuple[float, float, str]] = []
    line: list[Word] = []
    for word in speech.words:
        if line and len(" ".join(w.text for w in line)) + 1 + len(word.text) > width:
            out.append((line[0].start, word.start, " ".join(w.text for w in line)))
            line = []
        line.append(word)
        if word.text[-1] in ".!?":
            out.append((line[0].start, word.end, " ".join(w.text for w in line)))
            line = []
    if line:
        out.append((line[0].start, line[-1].end, " ".join(w.text for w in line)))
    return out


# ── the script: [spans] in the text ─────────────────────────────────────────────────────

_SPAN = re.compile(r"\[([^\[\]]*)\]")


@deprecated("ManimGX's machinery: say calls it", category=None)
def spans(script: str) -> tuple[str, list[tuple[int, int]]]:
    """The text of a script, its brackets taken out, and each bracketed span's characters
    in that text: `"Here is [a circle]."` is `("Here is a circle.", [(8, 16)])`."""
    text, found, at = [], [], 0
    shift = 0
    for m in _SPAN.finditer(script):
        text.append(script[at : m.start()])
        begin = m.start() - shift
        found.append((begin, begin + len(m.group(1))))
        text.append(m.group(1))
        at, shift = m.end(), shift + 2
    text.append(script[at:])
    return "".join(text), found


@deprecated("ManimGX's machinery: say calls it", category=None)
def times(speech: Speech, span: tuple[int, int]) -> tuple[float, float]:
    """When the characters `span` of a speech's text are said: from the start of its first
    word to the end of its last; an empty span, the start of the word it comes before.
    """
    begin, end = span
    words = speech.words
    located = [(m.start(), m.end()) for m in _WORD.finditer(speech.text)]
    inside = [i for i, (a, b) in enumerate(located) if a < end and b > begin] or [
        next((i for i, (a, _) in enumerate(located) if a >= begin), len(words) - 1)
    ]
    first, last = inside[0], inside[-1]
    if begin == end:
        return words[first].start, words[first].start
    return words[first].start, words[last].end


# ── the cache: what a voice said, kept ──────────────────────────────────────────────────


def cached(voice: Voice, text: str, folder: Path) -> Speech:
    """What `voice` says for `text`: spoken once, then kept in `folder` as its audio and a
    JSON of its words, named by the text and a digest of the voice and the text.

    The audio may be replaced (a recording of the same words, in any format the engine
    reads, under the same name): its words are then timed again, from it.
    """
    from manimgx._engine import digest

    identity = _identity(voice)
    key = f"{digest(identity.encode(), b'\0', text.encode()):016x}"
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]
    stem = folder / f"{slug}-{key[:10]}"
    meta = stem.with_suffix(".json")
    if meta.exists():
        record = json.loads(meta.read_text(encoding="utf-8"))
        audio = stem.with_suffix(record["suffix"]).read_bytes()
        same = record.get("audio") == f"{digest(audio):016x}"
        words = [Word(*w) for w in record["words"]] if same else []
        speech = Speech(audio, text=text, words=words)
        speech._edit = _Edit(**record.get("edit", {}))
        return speech
    speech = voice(text)
    folder.mkdir(parents=True, exist_ok=True)
    suffix, data = _stored(speech)
    stem.with_suffix(suffix).write_bytes(data)
    meta.write_text(
        json.dumps(
            {
                "text": text,
                "voice": identity,
                "suffix": suffix,
                "audio": f"{digest(data):016x}",
                "edit": dataclasses.asdict(speech._edit),
                "words": [[w.text, w.start, w.end] for w in speech._words],
            },
            indent=1,
        )
        + "\n",  # a text file, to commit
        encoding="utf-8",
    )
    return speech


def _identity(voice: Voice) -> str:
    """What names a voice in the cache: what decides what it says. A dataclass's repr (its
    settings; a key is left out of it); a function's name, its code and the plain values it
    holds (in its closure, its defaults, and the fields of the object a method is bound
    to); another callable's type and plain fields. A plain value is immutable: a string, a
    number, a boolean, None, or a tuple of them — a voice's settings, not its state (a
    client, a list it appends to)."""
    if hasattr(voice, "__dataclass_fields__"):
        return repr(voice)
    fn = getattr(
        voice, "__func__", voice
    )  # a bound method: its function, and its object
    code = getattr(fn, "__code__", None)
    if code is None:  # an object with __call__
        return f"{type(voice).__module__}.{type(voice).__qualname__}{_fields(voice)!r}"
    from manimgx._engine import digest

    body = digest(marshal.dumps(_code(code)))
    cells = tuple(c.cell_contents for c in getattr(fn, "__closure__", None) or ())
    defaults = getattr(fn, "__defaults__", None) or ()
    keywords = getattr(fn, "__kwdefaults__", None) or {}
    held = (
        _plain(cells),
        _plain(defaults),
        _plain(tuple(sorted(keywords.items()))),
        _fields(getattr(voice, "__self__", None)),
    )
    name = f"{getattr(fn, '__module__', '')}.{getattr(fn, '__qualname__', '')}"
    return f"{name}#{body:016x}{held!r}"


def _code(code: CodeType) -> CodeType:
    """A voice's code without source locations, including its nested functions."""
    return code.replace(
        co_filename="",
        co_firstlineno=0,
        co_linetable=b"",
        co_consts=tuple(
            _code(c) if isinstance(c, CodeType) else c for c in code.co_consts
        ),
    )


def _fields(owner: object) -> tuple[tuple[str, object], ...]:
    """An object's plain fields, in order of their names."""
    plain = ((k, _plain(v)) for k, v in sorted(getattr(owner, "__dict__", {}).items()))
    return tuple((k, v) for k, v in plain if v is not _OTHER)


def _plain(value: object) -> object:
    """`value` if it is plain (immutable: a string, number, boolean, None, or a tuple of
    them, whose other items are left out); else `_OTHER`."""
    if value is None or isinstance(value, str | int | float | bool | bytes):
        return value
    if isinstance(value, tuple):
        return tuple(v for v in map(_plain, value) if v is not _OTHER)
    return _OTHER


_OTHER = object()  # not a plain value: left out of a voice's name


def _stored(speech: Speech) -> tuple[str, bytes]:
    source = speech.source
    if isinstance(source, bytes):
        return _sniff(source), source
    if isinstance(source, np.ndarray):
        return ".wav", _wav(_source_samples(speech))
    path = Path(source)
    return path.suffix or ".bin", path.read_bytes()


def _sniff(data: bytes) -> str:
    if data[:4] == b"RIFF":
        return ".wav"
    if data[:4] == b"fLaC":
        return ".flac"
    if data[:4] == b"OggS":
        return ".ogg"
    if data[4:8] == b"ftyp":
        return ".m4a"
    return ".mp3"


def _wav(samples: np.ndarray) -> bytes:
    """Float samples at RATE as a 32-bit float WAV file."""
    data = np.ascontiguousarray(samples, np.float32)
    channels = data.shape[1] if data.ndim > 1 else 1
    body = data.tobytes()
    header = b"".join(
        [
            b"RIFF",
            (36 + len(body)).to_bytes(4, "little"),
            b"WAVEfmt ",
            (16).to_bytes(4, "little"),
            (3).to_bytes(2, "little"),  # IEEE float
            channels.to_bytes(2, "little"),
            RATE.to_bytes(4, "little"),
            (RATE * 4 * channels).to_bytes(4, "little"),
            (4 * channels).to_bytes(2, "little"),
            (32).to_bytes(2, "little"),
            b"data",
            len(body).to_bytes(4, "little"),
        ]
    )
    return header + body


def timed(text: str, pieces: Sequence[tuple[str, float, float]]) -> tuple[Word, ...]:
    """The words of `text`, timed by a voice's timed pieces of it, in order (its characters,
    or its tokens): each word from the start of the piece its first letter is in to the end
    of the piece its last letter is in. Empty if the pieces don't spell the text's letters
    (a voice that said "two" for "2"): its words are then estimated."""
    # each letter of the pieces: its piece's times
    owner: list[tuple[float, float]] = []
    for piece, a, b in pieces:
        owner += [(a, b)] * sum(c.isalnum() for c in piece)
    letters = [c.lower() for c in text if c.isalnum()]
    spelled = [c.lower() for piece, _, _ in pieces for c in piece if c.isalnum()]
    if not letters or letters != spelled:
        return ()
    words, k = [], 0
    for m in _WORD.finditer(text):
        n = sum(c.isalnum() for c in m.group())
        if n:
            words.append(Word(m.group(), owner[k][0], owner[k + n - 1][1]))
            k += n
        else:  # punctuation: beside the preceding word, or the first following word
            at = words[-1].end if words else owner[0][0]
            words.append(Word(m.group(), at, at))
    return tuple(words)

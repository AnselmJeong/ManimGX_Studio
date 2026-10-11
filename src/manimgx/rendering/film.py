"""Film: a scene's frames, as the player draws them — a view and one record per object (`feed`) —
and its plays, sounds, sections and captions. Shapes and brushes reach the player once, keyed by
content; a frame equal to the previous one lengthens it, unless it begins a section (a keyframe).
Frames go to a video, to a callback (which draws those it wants), or nowhere (their records are
still made); each play, as it ends, to a callback. The sounds are mixed as the video is written.
"""

import contextlib
import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Final, Literal, cast, get_args
from warnings import deprecated

from manimgx import _engine
from manimgx.animation import clock
from manimgx.config import config
from manimgx.rendering import feed
from manimgx.rendering.feed import CameraView, Feeder

if TYPE_CHECKING:
    import numpy as np

    from manimgx.animation.timeline import Animation
    from manimgx.audio.sound import Clip
    from manimgx.drawing.geometry import Path
    from manimgx.mobject import Mobject
    from manimgx.scene import Camera


X264Preset = Literal[
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
    "placebo",
]
"""The x264 presets, from fastest to slowest."""

DEFAULT_ENCODER_PRESET: Final[X264Preset] = cast(
    X264Preset, _engine.DEFAULT_ENCODER_PRESET
)
"""The native encoder's default preset, shared by Python and the command line."""
DEFAULT_ENCODER_CRF: Final[float] = _engine.DEFAULT_ENCODER_CRF
"""The native encoder's default constant rate factor."""


class Frame:
    """A frame of a film, as the film sends it: shown as frames `index` to
    `index + repeat - 1` of the video.

    A frame the world holds still for is sent once, shown `repeat` times. Its pixels are
    drawn only when asked for, by [`pixels`][manimgx.rendering.film.Frame.pixels].

    Args:
        index: Where it is in the film: the number of the first frame it is shown as.
        repeat: How many frames it is shown for.
        draw: The function that draws its pixels.
        key: Whether it begins a section of the film.
    """

    __slots__ = ("_draw", "index", "key", "repeat")

    def __init__(
        self, index: int, repeat: int, draw: Callable[[], bytes], key: bool = False
    ) -> None:
        self.index = index
        """Where it is in the film: the number of the first frame it is shown as, from
        0."""
        self.repeat = repeat
        """How many frames it is shown for: more than 1 for a hold."""
        self.key = key
        """Whether it begins a [section][manimgx.rendering.film.Section] of the film: the picture
        the section before it ends on."""
        self._draw = draw

    def pixels(self) -> bytes:
        """Draw the frame, now.

        Drawing is what a frame costs: ask only for the frames you keep, and before the
        film sends its next frame.

        Returns:
            Its pixels: RGBA, a byte a channel, row after row from the top.
        """
        return self._draw()


type FrameSink = Callable[[Frame], object]
"""A function handed each frame of a film as the film sends it, a
[`Frame`][manimgx.rendering.film.Frame] (see [`Scene.render`][manimgx.Scene.render]); what it returns
is ignored. It may raise [`Cut`][manimgx.rendering.film.Cut] to end the film there."""


@dataclass(frozen=True, slots=True)
class Play:
    """One play, or wait, of a scene, as its film keeps it: its number, when it began
    and ended, and where the scene's code played it."""

    index: int
    """Its number, from 0: plays and waits are counted together."""
    start: Fraction
    """When it began, in seconds of scene time, exactly."""
    end: Fraction
    """When it ended, in seconds of scene time, exactly."""
    where: tuple[str, int] | None
    """Where the scene's code played it: the file and line of the innermost call outside
    manimgx; None if there is none."""


type SectionType = Literal[
    "default.normal",
    "presentation.normal",
    "presentation.skip",
    "presentation.loop",
    "presentation.complete_loop",
]
"""How a presentation plays a section (Manim's section types): `normal` stops at its end
until the presenter goes on; `skip` goes on by itself; `loop` plays it again and again until
the presenter goes on; `complete_loop` too, finishing the round it is in first."""


@dataclass(frozen=True, slots=True)
class Section:
    """A section of a film, as [`next_section`][manimgx.Scene.next_section] begins one: it
    lasts until the next section begins, or the film ends."""

    name: str
    """Its name."""
    start: Fraction
    """When it begins, in seconds of scene time: a frame's time, exactly."""
    frame: int
    """Its first frame's number: a keyframe of the video, where a player can start."""
    type: SectionType
    """How a presentation plays it."""
    notes: str
    """What the presenter reads during it."""


@dataclass(frozen=True, slots=True)
class Caption:
    """A caption of a film: `text`, shown from `start` to `end`, in seconds of scene
    time."""

    start: float
    end: float
    text: str


def _wav(sound: "np.ndarray") -> bytes:
    """A soundtrack as a WAV file: 16-bit, which every browser plays."""
    import io
    import wave

    import numpy as np

    from manimgx.audio.sound import RATE

    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(sound.shape[1])
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(sound, -1, 1) * 32767).round().astype("<i2").tobytes())
    return out.getvalue()


type Take = Callable[[bytes], object]
"""A function handed a film's take as it is recorded (see [`Film`][manimgx.rendering.film.Film]):
bytes of the stream manimgx's player reads — uploads, frames and notes, then the film's
sound and captions — in order, frame by frame; what it returns is ignored. It may raise
[`Cut`][manimgx.rendering.film.Cut] to end the film there: it is then sent nothing more (a
[`Window`][manimgx.Window] closed by its viewer does)."""


type PlayHook = Callable[[Play, tuple[Animation, ...]], object]
"""A function called as each play or wait of a film ends (see
[`Scene.render`][manimgx.Scene.render]), with the [`Play`][manimgx.rendering.film.Play] and the
animations it played, the world as the play left it; what it returns is ignored. It may
raise [`Cut`][manimgx.rendering.film.Cut] to end the film there."""


class Cut(Exception):
    """An early end to a film: raised by a frame sink, a play hook or a take, it stops
    the scene there.

    The film closes as it is: its video, if any, is written up to the last frame sent.
    """


@dataclass(frozen=True, slots=True)
class Export:
    """How a film's video was made: what [`Film.export`][manimgx.Film.export] holds once
    the video is written."""

    seconds: float
    """How long the video took, in seconds: from its start, as the scene began
    rendering, to its file written."""
    x264: float
    """Of those, the seconds spent in x264, the H.264 encoder (on a thread of its
    own)."""
    converted: float
    """The share of the video's 16 × 16 pixel blocks converted for the encoder, from 0
    to 1: the others had not changed since the frame before, and were skipped."""
    bytes: int
    """The size of the file, in bytes."""


class Film:
    """A scene's film: its frames, as they are sent, its plays, and its sounds, sections
    and captions.

    [`Scene.render`][manimgx.Scene.render] makes one and returns it. Each frame is sent
    once: encoded into the video, if there is one, and handed to `frames`, if given; a
    frame equal to the one before is not sent again, but lengthens it. Each play, as it
    ends, is kept, and handed to `plays`, if given. The sounds the scene placed are mixed
    into the video's sound track as it is written.

    A film can instead be recorded as a take: the engine's work written down — each shape
    once, then each frame's view and records, and at the end its sound and captions — for
    ManimGX's player to play, at any moment: in a [`Window`][manimgx.Window], live as the
    scene runs (`manimgx preview`), or in the browser, where Python has no GPU (Pyodide).

    Args:
        video: The MP4 file the frames are encoded into as they come, if any.
        frames: A function handed each frame, a [`Frame`][manimgx.rendering.film.Frame] (see
            [`FrameSink`][manimgx.rendering.film.FrameSink]).
        plays: A function called as each play ends (see
            [`PlayHook`][manimgx.rendering.film.PlayHook]).
        take: A function handed the take's bytes as they are recorded, frame by frame,
            if the film is recorded as a take (see [`Take`][manimgx.rendering.film.Take]).
        preset: The x264 preset the video is encoded with: faster presets make larger
            files.
        crf: The video's quality, as x264's constant rate factor, from 0 to 51:
            lower is better, the default value is 18.
    """

    def __init__(
        self,
        video: str | os.PathLike[str] | None = None,
        *,
        frames: FrameSink | None = None,
        plays: PlayHook | None = None,
        take: Take | None = None,
        preset: X264Preset = DEFAULT_ENCODER_PRESET,
        crf: float = DEFAULT_ENCODER_CRF,
    ) -> None:
        if preset not in get_args(X264Preset):
            raise ValueError(f"unknown x264 preset {preset!r}")
        if not 0 <= crf <= 51:
            raise ValueError(
                f"x264 CRF must be a finite number from 0 to 51, not {crf}"
            )
        fps = config.frame_rate
        if video is not None and fps != int(fps):
            raise ValueError(
                f"a video needs a whole number of frames per second, not {fps}"
            )
        width, height = config.pixel_width, config.pixel_height
        if video is not None and (width % 2 or height % 2):  # H.264's 4:2:0 halves both
            raise ValueError(
                f"a video needs an even width and height, not {width}x{height}"
            )
        self.fps = clock.rational(fps)
        """How many frames a second the film has: the configuration's when it began."""
        # the GPU draws the film; or its take is recorded, to be drawn by ManimGX's player: by
        # choice, or where the engine has no GPU (in Pyodide)
        self._player: _engine.Player | None = None
        self._recorder: _engine.Recorder | None = None
        drawn: _engine.Player | _engine.Recorder
        if take is None and (gpu := feed.Player) is not None:
            if video is not None or frames is not None:
                _engine.start_gpu()  # the film draws: the GPU comes up as it begins
            self._player = drawn = gpu(width, height)
            if video is not None:
                drawn.begin_export(
                    os.fspath(video), fps=int(fps), preset=preset, crf=crf
                )
        elif video is None and frames is None:
            self._recorder = drawn = _engine.Recorder(width, height, fps)
        else:
            raise ValueError(
                "a film recorded as a take is drawn by ManimGX's player, not here: it"
                " has no video or pixels"
                + ("" if feed.Player else " (this Python has no GPU)")
            )
        self._take = take
        self.feeder = Feeder(width, height, drawn)
        self.video = None if video is None else os.fspath(video)
        """The path of the video being written; None once it is written, and if there is
        none."""
        self.frames = frames
        """The function each drawn frame is handed to, if any."""
        self.frame_count = 0
        """How many frames the film has so far, a hold counting every frame it lasts."""
        self.plays: list[Play] = []
        """The plays and waits the scene has run, in order: each a
        [`Play`][manimgx.rendering.film.Play]."""
        self.sections: list[Section] = [
            Section("unnamed", Fraction(0), 0, "default.normal", "")
        ]
        """The film's sections, in order: each a [`Section`][manimgx.rendering.film.Section],
        lasting until the next begins. The first begins with the film."""
        self.subcaptions: list[Caption] = []
        """The captions the scene added (see
        [`add_subcaption`][manimgx.Scene.add_subcaption]); [`captions`]
        [manimgx.Film.captions] adds those of its speech."""
        self.clips: list[Clip] = []
        """The sounds the scene placed, in the order it placed them: each a
        [`Clip`][manimgx.audio.sound.Clip], from its start in scene time."""
        self.export: Export | None = None
        """How the video was made, once it is written: an
        [`Export`][manimgx.rendering.film.Export]; None until then, and with no video."""
        self._hook = plays
        self._pending: tuple[bytes, bytes, list[CameraView], int] | None = (
            None  # sent once it ends
        )
        self._first = 0  # the index of the pending frame
        self._key = False  # the next frame begins a section: a keyframe of its own
        self._pending_key = False  # the pending frame is one

    def soundtrack(self) -> "np.ndarray | None":
        """The film's sound: its clips mixed over its length, at
        [`RATE`][manimgx.audio.sound.RATE] samples a second, one column per channel; None if
        the scene placed no sound."""
        from manimgx.audio.sound import mix

        return mix(self.clips, self.frame_count / self.fps)

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def section(
        self, name: str, start: Fraction, type: SectionType, notes: str
    ) -> None:
        """Begin a section at the next frame, which starts at `start`: the scene calls it
        (see [`next_section`][manimgx.Scene.next_section]). A section with no frame yet
        gives way to it.

        Args:
            name: Its name.
            start: When it begins: the next frame's time.
            type: How a presentation plays it.
            notes: What the presenter reads during it.
        """
        if self.sections[-1].frame == self.frame_count:
            self.sections.pop()
        self.sections.append(Section(name, start, self.frame_count, type, notes))
        self._key = True
        self._note({"section": asdict(self.sections[-1])})

    def cut(self) -> list[tuple["Clip", float]]:
        """The sounds the film's end cuts short: each clip, with the seconds it loses."""
        end = self.frame_count / self.fps
        out = []
        for clip in self.clips:
            if clip.end is None and clip.sound.duration != float("inf"):
                lost = float(clip.start) + clip.sound.duration - float(end)
                if lost > 1e-3:
                    out.append((clip, lost))
        return out

    def subtitles(self) -> str:
        """The film's [`captions`][manimgx.Film.captions] as subtitles, in SubRip (`.srt`)
        form: what players, editors and video sites read beside a video."""

        def stamp(t: float) -> str:
            ms = round(t * 1000)
            return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

        return "".join(
            f"{i}\n{stamp(c.start)} --> {stamp(c.end)}\n{c.text}\n\n"
            for i, c in enumerate(self.captions(), 1)
        )

    def captions(self) -> list[Caption]:
        """The film's captions, in order of their start: those the scene added, and its
        speech's, a line of a few words at a time as they are said."""
        from manimgx.audio import Speech, lines

        spoken = [
            Caption(float(clip.start) + a, float(clip.start) + b, text)
            for clip in self.clips
            if isinstance(clip.sound, Speech)
            for a, b, text in lines(clip.sound)
        ]
        return sorted(self.subcaptions + spoken, key=lambda c: c.start)

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def played(self, play: Play, animations: "tuple[Animation, ...]") -> None:
        """Keep a play that has ended, and hand it to the play hook with the animations
        it played: the scene calls it as each play ends, the world as the play left it.

        Args:
            animations: What it played.
        """
        # the film keeps the play, not the animations: they hold their objects' copies
        self.plays.append(play)
        if self._recorder is not None:
            self._note({"play": asdict(play)})
        if self._hook is not None:
            self._hook(play, animations)

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def picture(self, camera: "Camera", mobjects: "list[Mobject]") -> bytes:
        """Draw the world as `camera` sees it now: a picture, not a frame of the film.

        Args:
            camera: The camera it is seen through.
            mobjects: The mobjects drawn, in the order they are drawn.

        Returns:
            Its pixels: RGBA, a byte a channel, row after row from the top.
        """
        view, records, cameras = self.feeder.frame(camera, mobjects)
        if self._player is None:
            raise RuntimeError("a film recorded as a take is drawn by ManimGX's player")
        if self._player.pressured():
            self.feeder.sweep([records, *[c[4] for c in cameras]], pressed=True)
        return self._player.render(view, records, cameras)

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def record(
        self, camera: "Camera", mobjects: "list[Mobject]", repeat: int = 1
    ) -> None:
        """Record a frame: the mobjects as `camera` sees them, shown for `repeat`
        frames.

        The scene calls it for each frame it computes.

        Args:
            camera: The camera the frame is seen through.
            mobjects: The mobjects drawn, in the order they are drawn (see
                [`display_list`][manimgx.Scene.display_list]).
            repeat: How many frames it is shown for.
        """
        view, records, cameras = self.feeder.frame(camera, mobjects)
        self._add(view, records, cameras, repeat)

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def tween(
        self,
        camera: "Camera",
        mobjects: "list[Mobject]",
        leaves: "list[tuple[Mobject, list[Mobject], Path, np.ndarray, np.ndarray]]",
    ) -> None:
        """Record, at once, the frames of a play that only carries its leaves between
        keyframes: the scene calls it for such a play.

        Args:
            camera: The camera the frames are seen through.
            mobjects: The mobjects drawn, in the order they are drawn.
            leaves: For each moving leaf: the leaf, its keyframes, its path, and per
                frame the interval it is in and the time along it (-1 marking the frames
                the entry does not claim).
        """
        for view, records in self.feeder.tween(camera, mobjects, leaves):
            self._add(view, records, [], 1)

    def _add(
        self, view: bytes, records: bytes, cameras: list[CameraView], repeat: int
    ) -> None:
        pending = self._pending
        if (
            pending is not None
            and not self._key
            and pending[:3] == (view, records, cameras)
        ):
            self._pending = (view, records, cameras, pending[3] + repeat)
        else:
            self._send()
            self._pending = (view, records, cameras, repeat)
            self._first = self.frame_count
            self._pending_key, self._key = self._key, False
        self.frame_count += repeat

    def _send(self) -> None:
        pending, self._pending = self._pending, None
        if pending is None:
            return
        view, records, cameras, repeat = pending
        if self._recorder is not None:
            self._recorder.frame(view, records, repeat, cameras)
            self._flush()
        if (player := self._player) is None:
            return
        if (self.video is not None or self.frames is not None) and player.pressured():
            self.feeder.sweep([records, *[c[4] for c in cameras]], pressed=True)
        key = self._pending_key
        if self.frames is None:
            if self.video is not None:
                player.push(view, records, repeat, cameras, key)
            return
        sent = self.video is None

        def push() -> None:
            nonlocal sent
            if not sent:
                player.push(view, records, repeat, cameras, key)
                sent = True

        def draw() -> bytes:
            nonlocal sent
            if sent:
                return player.render(view, records, cameras)
            # A pixel consumer and the encoder share one completed GPU draw. Defer export
            # until the callback asks: metadata-only callbacks keep the asynchronous path.
            pixels = player.push(view, records, repeat, cameras, key, capture=True)
            sent = True
            assert pixels is not None
            return pixels

        try:
            self.frames(Frame(self._first, repeat, draw, key))
        except Cut:
            push()  # the frame that cuts a film still belongs to its video
            raise
        push()

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def close(self) -> None:
        """Close the film: send its last frame, and write its video, if any.

        [`Scene.render`][manimgx.Scene.render] calls it as the scene ends. A
        [`Cut`][manimgx.rendering.film.Cut] raised for the last frame ends the film all the same;
        any other error abandons the video.
        """
        try:
            with contextlib.suppress(Cut):
                self._send()
            with contextlib.suppress(Cut):  # its take cut it: it hears no more
                self._end()
        except BaseException:
            self.abort()
            raise

    def _end(self) -> None:
        """Write the closed film's video, if any, and tell its take how it ends."""
        if self.video is not None and self._player is not None:
            sound = self.soundtrack()
            if sound is None:
                self.export = Export(*self._player.end_export())
            else:
                from manimgx.audio.sound import BITRATE, RATE

                channels = sound.shape[1]
                self.export = Export(
                    *self._player.end_export(
                        sound.tobytes(), channels, RATE, BITRATE * channels
                    )
                )
            self.video = None
        if self._recorder is not None:
            # what the player plays and shows beside the frames; then the take's end
            if (sound := self.soundtrack()) is not None:
                self._recorder.sound(_wav(sound))
            if captions := self.captions():
                self._note({"captions": [asdict(c) for c in captions]})
            self._recorder.end()
            self._flush()

    @deprecated("ManimGX's machinery: the scene calls it", category=None)
    def abort(self) -> None:
        """Stop the film without writing its video; its take, if it is recorded as one, ends
        saying that its scene failed.

        [`Scene.render`][manimgx.Scene.render] calls it when the scene fails.
        """
        if self.video is not None and self._player is not None:
            self.video = None
            self._player.abort_export()
        if self._recorder is not None:
            # its take keeps what was made until the scene failed, and ends saying so: a player
            # drops it, unless it shows it already
            pending, self._pending = self._pending, None
            if pending is not None:
                view, records, cameras, repeat = pending
                self._recorder.frame(view, records, repeat, cameras)
            self._recorder.end(failed=True)
            with contextlib.suppress(Cut):  # cut already: it hears nothing more
                self._flush()

    def _note(self, note: dict[str, object]) -> None:
        """Tell whoever shows the take the film's own records, as JSON (an exact time as a
        float): a play that ended, a section, the captions."""
        if self._recorder is not None:
            self._recorder.note(json.dumps(note, default=float))
            self._flush()

    def _flush(self) -> None:
        """Hand the take what was recorded since (with nobody to hand it to, drop it); once
        it cuts the film, it is handed nothing more."""
        if self._recorder is not None:
            data = self._recorder.drain()
            if self._take is not None and data:
                try:
                    self._take(data)
                except Cut:
                    self._take = None
                    raise

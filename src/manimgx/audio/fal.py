"""fal.ai's text-to-speech models, as voices: `Fal(model, **settings)`.

[fal](https://fal.ai) runs text-to-speech models behind one API and one key. `Fal` supports
the models below:

| Model | Its settings | Words timed |
| --- | --- | --- |
| `fal-ai/elevenlabs/tts/eleven-v3` (the default) | [`ElevenV3`][manimgx.audio.fal.ElevenV3] | by the model |
| `fal-ai/minimax/speech-2.8-hd` | [`MiniMax`][manimgx.audio.fal.MiniMax] | estimated |
| `google/gemini-3.8-flash-tts` | [`Gemini`][manimgx.audio.fal.Gemini] | estimated |
| `fal-ai/inworld-tts` | [`Inworld`][manimgx.audio.fal.Inworld] | estimated |
| `fal-ai/qwen-3-tts/text-to-speech/1.7b` | [`Qwen`][manimgx.audio.fal.Qwen] | estimated |

A model takes settings of its own, typed per model: a type checker knows which settings a
model takes and which values (its voices, say), and `Fal` checks their names as it is made.
The key is `FAL_KEY`'s (fal's dashboard gives one), or `key=`; it never names the voice in the
cache.
"""

import json
import math
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Literal, Unpack, overload

from typing_extensions import TypedDict

from manimgx.audio.sound import Speech, timed

# ── the models' settings, as their schemas on fal have them ────────────────────────────────


class ElevenV3(TypedDict, total=False, closed=True):
    """The settings of ElevenLabs' Eleven v3 (`fal-ai/elevenlabs/tts/eleven-v3`), which times
    its words. Its text may carry audio tags: `[whispers]`, `[laughs]`, `[excited]`…"""

    voice: str
    """A voice's name or ID in ElevenLabs' library: Aria, Roger, Sarah, Laura, Charlie,
    George, Callum, River, Liam, Charlotte, Alice, Matilda, Will, Jessica, Eric, Chris, Brian,
    Daniel, Lily, Bill… (default "Rachel")."""
    stability: float
    """How steady the voice is, from 0 (expressive) to 1 (steady) (default 0.5)."""
    language_code: str | None
    """The language, as an ISO 639-1 code ("en", "de"…) (default: the text's)."""
    apply_text_normalization: Literal["auto", "on", "off"]
    """Whether numbers and the like are spelled out before they are said (default "auto":
    as the model sees fit)."""


class MiniMaxVoice(TypedDict, total=False):
    """A MiniMax voice and how it speaks."""

    voice_id: str
    """The voice: Wise_Woman, Friendly_Person, Inspirational_girl, Deep_Voice_Man, Calm_Woman,
    Casual_Guy, Lively_Girl, Patient_Man, Young_Knight, Determined_Man, Lovely_Girl,
    Decent_Boy, Imposing_Manner, Elegant_Man, Abbess, Sweet_Girl_2, Exuberant_Girl, or a
    cloned voice's ID (default "Wise_Woman")."""
    speed: float
    """How fast, from 0.5 to 2 (default 1)."""
    vol: float
    """How loud, from 0.01 to 10 (default 1)."""
    pitch: int
    """How high, in semitones from -12 to 12 (default 0)."""
    emotion: (
        Literal["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]
        | None
    )
    """The emotion it speaks with (default: as the text reads)."""
    english_normalization: bool
    """Whether English numbers are read more carefully, a little slower (default False)."""


class MiniMaxAudio(TypedDict, total=False):
    """The audio MiniMax makes."""

    sample_rate: Literal[8000, 16000, 22050, 24000, 32000, 44100]
    """Samples a second (default 32000)."""
    bitrate: Literal[32000, 64000, 128000, 256000]
    """Bits a second, for MP3 (default 128000)."""
    format: Literal["mp3", "flac"]
    """The file's format (default "mp3")."""
    channel: Literal[1, 2]
    """Channels: 1 (mono) or 2 (stereo) (default 1)."""


class MiniMaxLoudness(TypedDict, total=False):
    """How MiniMax evens out the audio's loudness."""

    enabled: bool
    """Whether it does (default True)."""
    target_loudness: float
    """The loudness it aims at, in LUFS, from -70 to -10 (default -18)."""
    target_range: float
    """The loudness range, in LU, from 0 to 20 (default 8)."""
    target_peak: float
    """The highest peak, in dBTP, from -3 to 0 (default -0.5)."""


class MiniMaxTimbre(TypedDict, total=False):
    """How MiniMax changes the voice itself."""

    pitch: int
    """Higher or lower, from -100 to 100 (default 0)."""
    intensity: int
    """More or less energetic, from -100 to 100 (default 0)."""
    timbre: int
    """Its tone's color, from -100 to 100 (default 0)."""


class MiniMaxPronunciation(TypedDict, total=False):
    """How MiniMax pronounces particular words."""

    tone_list: list[str]
    """Each word and its pronunciation: `"text/(pronunciation)"` (Chinese tones 1 to 5:
    `"燕少飞/(yan4)(shao3)(fei1)"`)."""


class MiniMax(TypedDict, total=False, closed=True):
    """The settings of MiniMax Speech 2.8 HD (`fal-ai/minimax/speech-2.8-hd`). Its text may
    carry pauses, `<#0.5#>` (in seconds), and interjections: `(laughs)`, `(sighs)`, `(coughs)`,
    `(clears throat)`, `(gasps)`, `(sniffs)`, `(groans)`, `(yawns)`."""

    voice_setting: MiniMaxVoice
    """The voice and how it speaks ([`MiniMaxVoice`][manimgx.audio.fal.MiniMaxVoice])."""
    audio_setting: MiniMaxAudio
    """The audio it makes ([`MiniMaxAudio`][manimgx.audio.fal.MiniMaxAudio])."""
    language_boost: (
        Literal[
            "Chinese",
            "Chinese,Yue",
            "English",
            "Arabic",
            "Russian",
            "Spanish",
            "French",
            "Portuguese",
            "German",
            "Turkish",
            "Dutch",
            "Ukrainian",
            "Vietnamese",
            "Indonesian",
            "Japanese",
            "Italian",
            "Korean",
            "Thai",
            "Polish",
            "Romanian",
            "Greek",
            "Czech",
            "Finnish",
            "Hindi",
            "Bulgarian",
            "Danish",
            "Hebrew",
            "Malay",
            "Slovak",
            "Swedish",
            "Croatian",
            "Hungarian",
            "Norwegian",
            "Slovenian",
            "Catalan",
            "Nynorsk",
            "Afrikaans",
            "auto",
        ]
        | None
    )
    """A language or dialect it listens for (default: none)."""
    normalization_setting: MiniMaxLoudness
    """How it evens out the loudness
    ([`MiniMaxLoudness`][manimgx.audio.fal.MiniMaxLoudness])."""
    voice_modify: MiniMaxTimbre | None
    """How it changes the voice itself ([`MiniMaxTimbre`][manimgx.audio.fal.MiniMaxTimbre])."""
    pronunciation_dict: MiniMaxPronunciation | None
    """How it pronounces particular words
    ([`MiniMaxPronunciation`][manimgx.audio.fal.MiniMaxPronunciation])."""


class Gemini(TypedDict, total=False, closed=True):
    """The settings of Google's Gemini 3.8 Flash TTS (`google/gemini-3.8-flash-tts`). Its text
    may carry vocal events: `<laugh>`, `<sigh>`."""

    voice: Literal[
        "Achernar",
        "Achird",
        "Algenib",
        "Algieba",
        "Alnilam",
        "Aoede",
        "Autonoe",
        "Callirrhoe",
        "Charon",
        "Despina",
        "Enceladus",
        "Erinome",
        "Fenrir",
        "Gacrux",
        "Iapetus",
        "Kore",
        "Laomedeia",
        "Leda",
        "Orus",
        "Pulcherrima",
        "Puck",
        "Rasalgethi",
        "Sadachbia",
        "Sadaltager",
        "Schedar",
        "Sulafat",
        "Umbriel",
        "Vindemiatrix",
        "Zephyr",
        "Zubenelgenubi",
    ]
    """The voice (default "Kore")."""
    style_instructions: str | None
    """How to say it, in words: "Warm and unhurried, like a patient teacher." (default:
    none)."""


class Inworld(TypedDict, total=False, closed=True):
    """The settings of Inworld TTS-1.5 Max (`fal-ai/inworld-tts`), which speaks up to 2,000
    characters a line."""

    voice: Literal[
        "Loretta (en)",
        "Darlene (en)",
        "Marlene (en)",
        "Hank (en)",
        "Evelyn (en)",
        "Celeste (en)",
        "Pippa (en)",
        "Tessa (en)",
        "Liam (en)",
        "Callum (en)",
        "Hamish (en)",
        "Abby (en)",
        "Graham (en)",
        "Rupert (en)",
        "Mortimer (en)",
        "Snik (en)",
        "Anjali (en)",
        "Saanvi (en)",
        "Arjun (en)",
        "Claire (en)",
        "Oliver (en)",
        "Simon (en)",
        "Elliot (en)",
        "James (en)",
        "Serena (en)",
        "Gareth (en)",
        "Vinny (en)",
        "Lauren (en)",
        "Jessica (en)",
        "Ethan (en)",
        "Tyler (en)",
        "Jason (en)",
        "Chloe (en)",
        "Veronica (en)",
        "Victoria (en)",
        "Miranda (en)",
        "Sebastian (en)",
        "Victor (en)",
        "Malcolm (en)",
        "Kayla (en)",
        "Nate (en)",
        "Jake (en)",
        "Brian (en)",
        "Amina (en)",
        "Kelsey (en)",
        "Derek (en)",
        "Grant (en)",
        "Evan (en)",
        "Alex (en)",
        "Ashley (en)",
        "Craig (en)",
        "Deborah (en)",
        "Dennis (en)",
        "Edward (en)",
        "Elizabeth (en)",
        "Hades (en)",
        "Julia (en)",
        "Pixie (en)",
        "Mark (en)",
        "Olivia (en)",
        "Priya (en)",
        "Ronald (en)",
        "Sarah (en)",
        "Shaun (en)",
        "Theodore (en)",
        "Timothy (en)",
        "Wendy (en)",
        "Dominus (en)",
        "Hana (en)",
        "Clive (en)",
        "Carter (en)",
        "Blake (en)",
        "Luna (en)",
        "Yichen (zh)",
        "Xiaoyin (zh)",
        "Xinyi (zh)",
        "Jing (zh)",
        "Erik (nl)",
        "Katrien (nl)",
        "Lennart (nl)",
        "Lore (nl)",
        "Alain (fr)",
        "Hélène (fr)",
        "Mathieu (fr)",
        "Étienne (fr)",
        "Johanna (de)",
        "Josef (de)",
        "Gianni (it)",
        "Orietta (it)",
        "Asuka (ja)",
        "Satoshi (ja)",
        "Hyunwoo (ko)",
        "Minji (ko)",
        "Seojun (ko)",
        "Yoona (ko)",
        "Szymon (pl)",
        "Wojciech (pl)",
        "Heitor (pt)",
        "Maitê (pt)",
        "Diego (es)",
        "Lupita (es)",
        "Miguel (es)",
        "Rafael (es)",
        "Svetlana (ru)",
        "Elena (ru)",
        "Dmitry (ru)",
        "Nikolai (ru)",
        "Riya (hi)",
        "Manoj (hi)",
        "Yael (he)",
        "Oren (he)",
        "Nour (ar)",
        "Omar (ar)",
    ]
    """The voice, with its language (default "Craig (en)")."""
    sample_rate_hertz: Literal[8000, 16000, 24000, 32000, 40000, 48000]
    """Samples a second (default 48000)."""


class Qwen(TypedDict, total=False, closed=True):
    """The settings of Alibaba's Qwen3-TTS 1.7B (`fal-ai/qwen-3-tts/text-to-speech/1.7b`)."""

    voice: (
        Literal[
            "Vivian",
            "Serena",
            "Uncle_Fu",
            "Dylan",
            "Eric",
            "Ryan",
            "Aiden",
            "Ono_Anna",
            "Sohee",
        ]
        | None
    )
    """The voice (default: the model's)."""
    language: Literal[
        "Auto",
        "English",
        "Chinese",
        "Spanish",
        "French",
        "German",
        "Italian",
        "Japanese",
        "Korean",
        "Portuguese",
        "Russian",
    ]
    """The language (default "Auto": the text's)."""
    prompt: str | None
    """How to say it, in words (not what to say) (default: none)."""
    speaker_voice_embedding_file_url: str | None
    """A cloned voice: the URL of the speaker embedding `fal-ai/qwen-3-tts/clone-voice`
    made; it overrides `voice` and `prompt` (default: none)."""
    reference_text: str | None
    """What the cloned voice's recording says, which helps it sound like it (default:
    none)."""
    temperature: float | None
    """How varied the delivery is, above 0 and up to 1 (default 0.9)."""
    top_k: int | None
    """Sampling: from the k likeliest sounds (default 50)."""
    top_p: float | None
    """Sampling: from the likeliest sounds that make up p of the chance, 0 to 1 (default 1)."""
    repetition_penalty: float | None
    """How strongly it avoids repeating itself (default 1.05)."""
    subtalker_dosample: bool | None
    """Whether its second stage samples (default True)."""
    subtalker_temperature: float | None
    """Its second stage's temperature, 0 to 1 (default 0.9)."""
    subtalker_top_k: int | None
    """Its second stage's top k (default 50)."""
    subtalker_top_p: float | None
    """Its second stage's top p, 0 to 1 (default 1)."""
    max_new_tokens: int | None
    """The most sound it makes, in its codec's tokens, 1 to 8192 (default 8192 here: fal's
    own, 200, can cut a long line short)."""


type Model = Literal[
    "fal-ai/elevenlabs/tts/eleven-v3",
    "fal-ai/minimax/speech-2.8-hd",
    "google/gemini-3.8-flash-tts",
    "fal-ai/inworld-tts",
    "fal-ai/qwen-3-tts/text-to-speech/1.7b",
]
"""The models `Fal` speaks through."""


@dataclass(frozen=True, slots=True)
class _Spec:
    """How a model is asked: the input its text goes in, its settings, what is sent unless a
    setting says otherwise, and what is always sent."""

    text: str
    settings: type
    defaults: tuple[tuple[str, object], ...] = ()
    fixed: tuple[tuple[str, object], ...] = ()


_MODELS: dict[str, _Spec] = {
    "fal-ai/elevenlabs/tts/eleven-v3": _Spec(
        "text", ElevenV3, fixed=(("timestamps", True),)
    ),
    "fal-ai/minimax/speech-2.8-hd": _Spec("prompt", MiniMax),
    "google/gemini-3.8-flash-tts": _Spec("prompt", Gemini),
    "fal-ai/inworld-tts": _Spec("text", Inworld),
    "fal-ai/qwen-3-tts/text-to-speech/1.7b": _Spec(
        "text", Qwen, defaults=(("max_new_tokens", 8192),)
    ),
}


# ── the voice ───────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True, init=False, repr=False)
class Fal:
    """A text-to-speech model on fal.ai, as a voice: `Fal(model, **settings)`, where the
    settings are the model's own ([`ElevenV3`][manimgx.audio.fal.ElevenV3] for the default).

    Args:
        model: The model's ID on fal.
        key: fal's API key; by default `FAL_KEY`.
        **settings: The model's settings.

    Examples:
        A scene's voice, in its class:

        ```py
        voice = m.voices.Fal(
            "fal-ai/minimax/speech-2.8-hd",
            voice_setting={"voice_id": "Calm_Woman", "speed": 1.1},
        )
        ```
    """

    model: Model
    """The model's ID on fal."""
    settings: dict[str, object]
    """The model's settings, as given."""
    key: str | None = field(default=None, compare=False)
    """fal's API key, if given; else `FAL_KEY` is read as the voice speaks."""

    @overload
    def __init__(
        self,
        model: Literal["fal-ai/elevenlabs/tts/eleven-v3"] = ...,
        /,
        *,
        key: str | None = None,
        **settings: Unpack[ElevenV3],
    ) -> None: ...
    @overload
    def __init__(
        self,
        model: Literal["fal-ai/minimax/speech-2.8-hd"],
        /,
        *,
        key: str | None = None,
        **settings: Unpack[MiniMax],
    ) -> None: ...
    @overload
    def __init__(
        self,
        model: Literal["google/gemini-3.8-flash-tts"],
        /,
        *,
        key: str | None = None,
        **settings: Unpack[Gemini],
    ) -> None: ...
    @overload
    def __init__(
        self,
        model: Literal["fal-ai/inworld-tts"],
        /,
        *,
        key: str | None = None,
        **settings: Unpack[Inworld],
    ) -> None: ...
    @overload
    def __init__(
        self,
        model: Literal["fal-ai/qwen-3-tts/text-to-speech/1.7b"],
        /,
        *,
        key: str | None = None,
        **settings: Unpack[Qwen],
    ) -> None: ...
    def __init__(
        self,
        model: Model = "fal-ai/elevenlabs/tts/eleven-v3",
        /,
        *,
        key: str | None = None,
        **settings: object,
    ) -> None:
        spec = _MODELS.get(model)
        if spec is None:
            raise ValueError(f"fal: no model {model!r} here: {', '.join(_MODELS)}")
        known = spec.settings.__annotations__
        if unknown := sorted(settings.keys() - known.keys()):
            raise TypeError(
                f"{model} takes {', '.join(known)}; not {', '.join(unknown)}"
            )
        object.__setattr__(self, "model", model)
        object.__setattr__(
            self, "settings", {k: _ordered(v) for k, v in sorted(settings.items())}
        )
        object.__setattr__(self, "key", key)

    def __repr__(self) -> str:
        """The call that makes it, without its key: what names it in the cache."""
        given = "".join(f", {k}={v!r}" for k, v in self.settings.items())
        return f"Fal({self.model!r}{given})"

    def __call__(self, text: str) -> Speech:
        key = self.key or os.environ.get("FAL_KEY")
        if not key:
            raise RuntimeError(
                "no key for fal.ai: set FAL_KEY (fal's dashboard gives one), or give"
                " `key=`"
            )
        spec = _MODELS[self.model]
        body = {
            **dict(spec.defaults),
            **self.settings,
            **dict(spec.fixed),
            spec.text: text,
        }
        reply = json.loads(
            _fetch(
                f"https://fal.run/{self.model}", body, {"Authorization": f"Key {key}"}
            )
        )
        audio = _fetch(reply["audio"]["url"])  # fal keeps it days, not forever: now
        return Speech(
            audio, text=text, words=timed(text, _pieces(reply.get("timestamps")))
        )


def _ordered(value: object) -> object:
    """`value` with every dict in it ordered by its keys: one voice, one name, however its
    settings were written."""
    if isinstance(value, dict):
        return {k: _ordered(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_ordered(v) for v in value]
    return value


def _pieces(stamps: object) -> list[tuple[str, float, float]]:
    """A model's timing of its text, as fal passes it on, as timed pieces of the text: items of
    a text, a start and an end (words or characters), or ElevenLabs' alignments (characters,
    with their starts and ends). Empty if there is none, or if it runs backwards: the words
    are then estimated."""
    pieces: list[tuple[str, float, float]] = []
    for item in stamps if isinstance(stamps, list) else ():
        if not isinstance(item, dict):
            continue
        if "characters" in item:
            pieces += [
                (str(c), float(a), float(b))
                for c, a, b in zip(
                    item["characters"],
                    item["character_start_times_seconds"],
                    item["character_end_times_seconds"],
                    strict=True,
                )
            ]
        elif {"text", "start", "end"} <= item.keys():
            pieces.append((str(item["text"]), float(item["start"]), float(item["end"])))
    starts = [a for _, a, _ in pieces]
    valid = all(0 <= a <= b and math.isfinite(b) for _, a, b in pieces)
    return pieces if valid and starts == sorted(starts) else []


def _fetch(
    url: str,
    body: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> bytes:
    """GET `url`, or POST `body` to it as JSON; the response's bytes (an HTTP error says what
    the service said)."""
    request = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="GET" if body is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:500]
        raise RuntimeError(f"{url}: HTTP {error.code}: {detail}") from None

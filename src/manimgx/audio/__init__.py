"""Audio: editable sounds, timed speech, and the voices that produce it.

A voice is any function from text to [`Speech`][manimgx.audio.Speech]: a sound that knows its
words and when each is said. [`Scene.say`][manimgx.Scene.say] speaks through the scene's voice
and plays animations during the words they belong to: `self.say("Here is [a circle].",
m.Create(circle))` draws the circle as "a circle" is said, and the film waits for the sentence.
What a voice says is kept (`cached`), so a scene renders again without speaking again.

The voices ManimGX brings are text-to-speech services', a module each: [`fal`][manimgx.audio.fal]
(fal.ai's models, [`Fal`][manimgx.audio.fal.Fal]). Any other is a few lines away (see
[`Voice`][manimgx.audio.Voice]).
"""

from manimgx.audio.fal import Fal
from manimgx.audio.sound import (
    Speech,
    Voice,
    Word,
    cached,
    estimate,
    lines,
    spans,
    timed,
    times,
)

__all__ = [
    "Fal",
    "Speech",
    "Voice",
    "Word",
    "cached",
    "estimate",
    "lines",
    "spans",
    "timed",
    "times",
]

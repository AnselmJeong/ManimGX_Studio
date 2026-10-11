---
title: "Voice"
description: "A voice that explains: say a line while animations play during its words, choose a voice, read captions, or make a voice of your own."
---

# Voice

```python fold title="The film's code"
import manimgx as m


class VoiceHero(m.Scene):
    def construct(self) -> None:
        square = m.MathTex("x^2", font_size=96).shift(2 * m.LEFT)
        derivative = m.MathTex("2x", font_size=96).shift(2 * m.RIGHT)
        arrow = m.Arrow(square.get_right(), derivative.get_left(), buff=0.4)
        script = m.Text(
            "The derivative of [x squared] is [two x].", font_size=32
        ).to_edge(m.DOWN)
        self.add(square, script)
        self.play(m.Indicate(square))
        self.play(m.GrowArrow(arrow), m.Write(derivative))
        self.wait()
```

[say][manimgx.Scene.say] speaks a line with the scene's voice, and plays animations while it
speaks. Put the words of each animation in brackets, and give the animations in the same
order: each starts with the first of its words. The scene waits until the line ends, so
lines don't overlap; change the words, and the animations follow the new words.

The scene's voice speaks through a text-to-speech service. ManimGX keeps what it says in a
folder named `voice/`, next to the scene's file, so the scene renders again without the
service, and only a changed line goes to it again. What the voice says becomes the video's
captions.

::: manimgx.Scene.say
    options:
      heading_level: 2

::: manimgx.Scene.speech
    options:
      heading_level: 2

::: manimgx.Scene.voice
    options:
      heading_level: 2

::: manimgx.Speech
    options:
      heading_level: 2

## Voices

The voices ManimGX brings are fal.ai's: `m.voices.Fal`, with the model you choose and its
settings. Your editor shows each model's settings.

::: manimgx.audio.fal.Fal
    options:
      heading_level: 3

### Models { #manimgx.audio.fal }

::: manimgx.audio.fal.ElevenV3
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMax
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMaxVoice
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMaxAudio
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMaxLoudness
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMaxTimbre
    options:
      heading_level: 4

::: manimgx.audio.fal.MiniMaxPronunciation
    options:
      heading_level: 4

::: manimgx.audio.fal.Gemini
    options:
      heading_level: 4

::: manimgx.audio.fal.Inworld
    options:
      heading_level: 4

::: manimgx.audio.fal.Qwen
    options:
      heading_level: 4

## Captions

::: manimgx.Scene.add_subcaption
    options:
      heading_level: 3

## A voice of your own

A voice is any function from a text to a [Speech][manimgx.Speech]: a sound that knows its
words, and when each is said. Any text-to-speech service can be one.

::: manimgx.audio.Voice
    options:
      heading_level: 3

::: manimgx.audio.Word
    options:
      heading_level: 3

::: manimgx.audio.timed
    options:
      heading_level: 3

::: manimgx.audio.estimate
    options:
      heading_level: 3

::: manimgx.audio.cached
    options:
      heading_level: 3

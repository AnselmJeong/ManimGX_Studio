# Sound and voice

A video can have sound: a sound with an animation, music under the whole video, or a
voice that explains. ManimGX puts each sound at its moment in the video, and mixes them
into one sound track.

## Play a sound with an animation

[`Sound`][manimgx.Sound] reads a sound from a file: WAV, MP3, AAC, FLAC and the other
usual formats. Give it to `self.play` with an animation, and it starts with the
animation:

```py
self.play(m.FadeIn(dot), m.Sound("click.wav"))
```

To start a sound at any moment, without an animation, use `self.add_sound`: the sound
plays while the scene continues.

```py
self.add_sound(m.Sound("theme.mp3"))
```

A sound plays to its end. In `self.play`, the play lasts until the sound ends;
`self.add_sound` doesn't wait. To stop a sound before its end, keep what `add_sound`
gives back: `music = self.add_sound(...)`, then `music.stop(fade=2)`.

## Change a sound

A sound's methods make a changed sound: here, music 18 decibels quieter, which fades in
for 2 seconds and plays until the video ends. A sound that loops never ends, so start it
with `add_sound`: `self.play` refuses it.

```py
music = self.add_sound(m.Sound("theme.mp3").gain(-18).fade_in(2).loop())
```

The [`Sound`][manimgx.Sound] reference shows every change.

## Say a line

[`say`][manimgx.Scene.say] speaks a line with the scene's voice, and plays animations
while it speaks. Put the words of each animation in brackets, and give the animations in
the same order. The voice doesn't say the brackets:

```python
import manimgx as m


class Derivative(m.Scene):
    def construct(self) -> None:
        square = m.MathTex("x^2", font_size=96).shift(2 * m.LEFT)
        derivative = m.MathTex("2x", font_size=96).shift(2 * m.RIGHT)
        self.add(square)
        self.say(
            "The derivative of [x squared] is [two x].",
            m.Indicate(square),
            m.Write(derivative),
        )
```

Each animation starts with the first of its words. The scene waits until the line ends,
so lines don't overlap. If you change the words, the animations follow the new words.

## Voices

The default voice is ElevenLabs' Eleven v3, on [fal.ai](https://fal.ai). It needs your
fal.ai key in the `FAL_KEY` environment variable. To choose a different voice, set
`voice` in the scene's class, next to `construct`:

```py
voice = m.voices.Fal(
    "fal-ai/minimax/speech-2.8-hd",
    voice_setting={"voice_id": "Calm_Woman", "emotion": "happy"},
)
```

[`Fal`][manimgx.audio.fal.Fal] speaks with [five models][manimgx.audio.fal], and your
editor shows the settings of each one. Any other text-to-speech service can be a voice
too: a voice is a function from text to a [`Speech`][manimgx.Speech]. For a dialogue,
give `say` a voice for one line: `self.say("Hello!", voice=other)`.

ManimGX keeps what the voice says in a folder named `voice/`, next to your scene's file.
So the scene renders again without the service, even offline, and only a changed line
goes to the service again. To use your own recording for a line, put it in place of
that line's audio, with the same name.

## Captions

What the voice says becomes the video's captions. `manimgx render` writes them next to
the video, as subtitles (`.srt`) that video players and video sites read.
[`add_subcaption`][manimgx.Scene.add_subcaption] adds captions of your own.

## Next

[Rendering and sharing](rendering.md) shows the ways to make your video, check it, and
share it.

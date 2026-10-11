---
title: "Sound"
description: "Sounds from files or from functions of time, changed and placed in the video: with an animation, at any moment, or under the whole video."
---

# Sound

```python fold title="The film's code"
import manimgx as m
import numpy as np


class SoundHero(m.Scene):
    def construct(self) -> None:
        def tone(t: np.ndarray) -> np.ndarray:
            return 0.3 * np.sin(2 * np.pi * 440 * t) * np.exp(-3 * t)

        dots = m.VGroup(
            *[m.Dot(radius=0.25, color=m.YELLOW) for _ in range(4)]
        ).arrange(buff=1)
        for dot in dots:
            self.play(
                m.FadeIn(dot, scale=2), m.Sound.of(tone, duration=0.5), run_time=0.5
            )
        self.wait()
```

A sound is read from a file (WAV, MP3, AAC, FLAC and the other usual kinds), or made by a
function of time. ManimGX places each sound at its moment in the video, and mixes them into
one sound track.

Give a sound to `play` with animations, and it starts with them. To start one at any moment,
add it: the scene goes on while it plays. A sound plays to its end, or until you stop the
clip that adding it gives back.

A sound's methods make a changed sound: quieter or louder, faded in or out, trimmed, looped,
faster, panned, or ducked under a voice.

::: manimgx.Sound
    options:
      heading_level: 2

::: manimgx.Scene.add_sound
    options:
      heading_level: 2

::: manimgx.audio.sound.Clip
    options:
      heading_level: 2

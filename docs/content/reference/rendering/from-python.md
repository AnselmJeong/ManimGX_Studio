---
title: "From Python"
description: "Render a scene from a program: its film, with its frames, plays, sounds, sections and captions, and a window that plays it."
---

# From Python

```python fold title="The film's code"
import manimgx as m


class FromPythonHero(m.Scene):
    def construct(self) -> None:
        code = m.Code(
            code_string='film = MyScene().render()\nfilm.export("video.mp4")\nprint(film.subtitles())',
            language="python",
            background="window",
        ).scale(1.1)
        self.play(m.FadeIn(code))
        self.wait()
```

A scene renders from Python as from the command line: `MyScene().render()` runs it and
records its film. The film keeps the frames, the plays, the sounds, the sections and the
captions, to write as a video or to read in a program. A window plays a film on the screen as
it is recorded.

::: manimgx.Scene.render
    options:
      heading_level: 2

::: manimgx.Film
    options:
      heading_level: 2

::: manimgx.Window
    options:
      heading_level: 2

## What a film holds

::: manimgx.rendering.film.Frame
    options:
      heading_level: 3

::: manimgx.rendering.film.Play
    options:
      heading_level: 3

::: manimgx.rendering.film.Section
    options:
      heading_level: 3

::: manimgx.rendering.film.Export
    options:
      heading_level: 3

::: manimgx.rendering.film.Cut
    options:
      heading_level: 3

::: manimgx.rendering.film.Take
    options:
      heading_level: 3

::: manimgx.rendering.film.FrameSink
    options:
      heading_level: 3

::: manimgx.rendering.film.PlayHook
    options:
      heading_level: 3

::: manimgx.audio.sound.RATE
    options:
      heading_level: 3

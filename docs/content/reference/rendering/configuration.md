---
title: "Configuration"
description: "The configuration every scene is made and rendered with: the video's size and frame rate, its background, and the frame's size in units."
---

# Configuration

```python fold title="The film's code"
import manimgx as m

m.config.pixel_width, m.config.pixel_height = 1080, 1920


class ConfigurationHero(m.Scene):
    def construct(self) -> None:
        frame = m.Rectangle(
            width=m.config.frame_width - 0.2,
            height=m.config.frame_height - 0.2,
            color=m.BLUE,
        )
        square = m.Square(side_length=8, color=m.YELLOW).scale(0.97)
        label = m.Text("1080 × 1920", font_size=56)
        self.play(m.Create(frame), m.Create(square), m.Write(label))
        self.wait()
```

`m.config` holds what every scene is made with: the video's size in pixels, its frame rate,
its background, and the frame's size in units. Set it after `import manimgx as m`, before
the scene is made; the command line's options set it too (`-r 1080x1920`, `--fps 30`).

The frame has the video's shape, and its short side is 8 units: a wide video shows about
14.2 × 8 units, a tall one 8 × 14.2, and the 8 × 8 square in the middle is in both.

::: manimgx.config.config
    options:
      heading_level: 2

::: manimgx.config.Config
    options:
      heading_level: 2

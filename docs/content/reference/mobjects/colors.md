---
title: "Colors"
description: "The named colors, the colors you mix, and the functions that blend, invert and choose them."
---

# Colors

```python fold title="The film's code"
import manimgx as m


class ColorsHero(m.Scene):
    def construct(self) -> None:
        rows = m.VGroup()
        for family in [
            "BLUE",
            "TEAL",
            "GREEN",
            "YELLOW",
            "GOLD",
            "RED",
            "MAROON",
            "PURPLE",
            "GREY",
        ]:
            row = m.VGroup(m.Text(family, font="monospace", font_size=24))
            for shade in "ABCDE":
                color = m.PALETTE[f"{family}_{shade}"]
                row.add(
                    m.Circle(radius=0.24, color=color, fill_opacity=1, stroke_width=0)
                )
            row.arrange(buff=0.16)
            rows.add(row)
        rows.arrange(m.DOWN, buff=0.16, aligned_edge=m.RIGHT)
        self.play(
            m.LaggedStart(
                *[m.FadeIn(row, shift=0.2 * m.RIGHT) for row in rows], lag_ratio=0.1
            )
        )
        self.wait()
```

A color is a name, such as `m.BLUE`; a hex code, such as `"#58C4DD"`; or numbers of red,
green and blue. Each takes the place of the others wherever a color goes:
`m.Circle(color="#58C4DD")` is `m.Circle(color=m.BLUE)`.

Most named colors come in a family of five shades, from A, the lightest, to E, the darkest;
the family's own name is its C. GRAY and GREY are two spellings of one color.

## The named colors

::: manimgx.drawing.paint
    options:
      show_root_heading: false
      extra:
        palette: true

::: manimgx.PALETTE
    options:
      heading_level: 3

## Make a color

::: manimgx.ManimColor
    options:
      heading_level: 3

::: manimgx.HSV
    options:
      heading_level: 3

## Blend colors

::: manimgx.interpolate_color
    options:
      heading_level: 3

::: manimgx.color_gradient
    options:
      heading_level: 3

::: manimgx.average_color
    options:
      heading_level: 3

::: manimgx.invert_color
    options:
      heading_level: 3

::: manimgx.colors_by_value
    options:
      heading_level: 3

## Choose colors at random

::: manimgx.random_color
    options:
      heading_level: 3

::: manimgx.random_bright_color
    options:
      heading_level: 3

::: manimgx.RandomColorGenerator
    options:
      heading_level: 3

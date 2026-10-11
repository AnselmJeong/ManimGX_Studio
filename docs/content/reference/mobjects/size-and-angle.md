---
title: "Size and angle"
description: "How large a mobject is and which way it turns, and the methods that scale, stretch, turn, flip and reshape it."
---

# Size and angle

```python fold title="The film's code"
import manimgx as m


class SizeAndAngleHero(m.Scene):
    def construct(self) -> None:
        shapes = m.VGroup(
            *[
                m.Square(side_length=1.6, color=m.BLUE, fill_opacity=0.5)
                for _ in range(4)
            ]
        )
        shapes.arrange(buff=1.2)
        names = m.VGroup(
            m.Text("scale(1.4)", font="monospace", font_size=30),
            m.Text("rotate(PI / 4)", font="monospace", font_size=30),
            m.Text("stretch(1.6, 0)", font="monospace", font_size=30),
            m.Text("flip()", font="monospace", font_size=30),
        )
        for shape, name in zip(shapes, names, strict=True):
            name.next_to(shape, m.DOWN, buff=1.1)
        marker = m.Dot(color=m.YELLOW).move_to(shapes[3].get_corner(m.UR))
        shapes[3].add(marker)
        self.add(shapes, names)
        self.play(
            shapes[0].animate.scale(1.4),
            shapes[1].animate.rotate(m.PI / 4),
            shapes[2].animate.stretch(1.6, 0),
            shapes[3].animate.flip(),
            run_time=2,
        )
        self.wait()
```

A mobject's size is its bounding box's: its [width][manimgx.Mobject.width] and its
[height][manimgx.Mobject.height]. Most shapes take their size when you make them (a
circle its `radius`, a text its `font_size`); these methods change it later, about the
mobject's center unless you give another point.

An angle is in radians: a whole turn is `m.TAU`, half a turn `m.PI`, and `30 * m.DEGREES`
is 30 degrees. A positive angle turns counterclockwise.

## Size

::: manimgx.Mobject.width
    options:
      heading_level: 3

::: manimgx.Mobject.height
    options:
      heading_level: 3

::: manimgx.Mobject.scale
    options:
      heading_level: 3

::: manimgx.Mobject.scale_to_fit_width
    options:
      heading_level: 3

::: manimgx.Mobject.scale_to_fit_height
    options:
      heading_level: 3

::: manimgx.Mobject.match_width
    options:
      heading_level: 3

::: manimgx.Mobject.match_height
    options:
      heading_level: 3

::: manimgx.Mobject.stretch
    options:
      heading_level: 3

::: manimgx.Mobject.stretch_to_fit_width
    options:
      heading_level: 3

::: manimgx.Mobject.stretch_to_fit_height
    options:
      heading_level: 3

::: manimgx.Mobject.replace
    options:
      heading_level: 3

## Angle

<div class="mx-constants" markdown>

::: manimgx.PI
    options:
      heading_level: 3

::: manimgx.TAU
    options:
      heading_level: 3

::: manimgx.DEGREES
    options:
      heading_level: 3

</div>

::: manimgx.Mobject.rotate
    options:
      heading_level: 3

::: manimgx.Mobject.flip
    options:
      heading_level: 3

::: manimgx.rotation_matrix
    options:
      heading_level: 3

## Any change

::: manimgx.Mobject.put_start_and_end_on
    options:
      heading_level: 3

::: manimgx.Mobject.apply_matrix
    options:
      heading_level: 3

::: manimgx.Mobject.apply_function
    options:
      heading_level: 3

::: manimgx.Mobject.apply_complex_function
    options:
      heading_level: 3

::: manimgx.Mobject.set
    options:
      heading_level: 3

---
title: "Style"
description: "A mobject's fill and stroke, their colors and opacities, gradients, and what covers what."
---

# Style

```python fold title="The film's code"
import manimgx as m


class StyleHero(m.Scene):
    def construct(self) -> None:
        stroked = m.Circle(color=m.BLUE, stroke_width=8)
        filled = m.Circle(color=m.GREEN, fill_opacity=0.6)
        gradient = m.Circle(fill_opacity=1, stroke_width=0).set_color(
            [m.BLUE, m.YELLOW]
        )
        faint = m.Circle(color=m.RED, fill_opacity=1).fade(0.7)
        circles = m.VGroup(stroked, filled, gradient, faint).arrange(buff=0.8)
        names = m.VGroup(
            m.Text("stroke", font="monospace", font_size=24),
            m.Text("fill", font="monospace", font_size=24),
            m.Text("gradient", font="monospace", font_size=24),
            m.Text("fade", font="monospace", font_size=24),
        )
        for circle, name in zip(circles, names, strict=True):
            name.next_to(circle, m.DOWN, buff=0.5)
        self.play(
            m.LaggedStart(*[m.Create(circle) for circle in circles], lag_ratio=0.2)
        )
        self.play(m.FadeIn(names))
        self.wait()
```

A shape has a stroke, its outline, and a fill, its inside. Each has a color and an
opacity, from 0 (unseen) to 1 (solid), and the stroke has a width, in hundredths of a unit.
Most shapes are made with a stroke and no fill: give `fill_opacity` to fill them.

Every mobject takes the same style keywords when you make it, and each kind sets its own
defaults (a circle is red, a dot is filled). The methods below change the style later,
for the mobject and all its parts.

::: manimgx.drawing.paint.Style
    options:
      heading_level: 2
      inherited_members: true
      members: [color, fill_color, fill_opacity, stroke_color, stroke_opacity, stroke_width, background_stroke_color, background_stroke_opacity, background_stroke_width, sheen_factor, sheen_direction, joint_type, cap_style, shade_in_3d, material, z_index, name, target]

## Color and opacity

::: manimgx.Mobject.set_color
    options:
      heading_level: 3

::: manimgx.Mobject.set_fill
    options:
      heading_level: 3

::: manimgx.Mobject.set_stroke
    options:
      heading_level: 3

::: manimgx.Mobject.set_opacity
    options:
      heading_level: 3

::: manimgx.Mobject.fade
    options:
      heading_level: 3

::: manimgx.Mobject.fade_to
    options:
      heading_level: 3

::: manimgx.Mobject.set_style
    options:
      heading_level: 3

::: manimgx.Mobject.match_style
    options:
      heading_level: 3

::: manimgx.Mobject.match_color
    options:
      heading_level: 3

::: manimgx.Mobject.color
    options:
      heading_level: 3

::: manimgx.Mobject.fill_color
    options:
      heading_level: 3

::: manimgx.Mobject.fill_opacity
    options:
      heading_level: 3

::: manimgx.Mobject.stroke_color
    options:
      heading_level: 3

::: manimgx.Mobject.stroke_opacity
    options:
      heading_level: 3

::: manimgx.Mobject.stroke_width
    options:
      heading_level: 3

## Over a source's colors

Text and SVG drawings come with colors of their own. These keywords paint over them.

::: manimgx.drawing.paint.Repaint
    options:
      heading_level: 3

## Gradients and sheen

A list of colors, given where one color goes, makes a gradient: `set_color([m.BLUE,
m.YELLOW])` blends one into the other across the mobject.

::: manimgx.Mobject.set_color_by_gradient
    options:
      heading_level: 3

::: manimgx.Mobject.set_colors_by_radial_gradient
    options:
      heading_level: 3

::: manimgx.Mobject.set_submobject_colors_by_radial_gradient
    options:
      heading_level: 3

::: manimgx.Mobject.set_sheen
    options:
      heading_level: 3

::: manimgx.Mobject.set_sheen_direction
    options:
      heading_level: 3

## Ends and corners of a stroke

::: manimgx.CapStyleType
    options:
      heading_level: 3

::: manimgx.LineJointType
    options:
      heading_level: 3

::: manimgx.VMobject.set_cap_style
    options:
      heading_level: 3

## What covers what

A mobject added later covers one added before. A higher z-index covers a lower one,
whatever the order.

::: manimgx.Mobject.set_z_index
    options:
      heading_level: 3

::: manimgx.Mobject.z_index
    options:
      heading_level: 3

::: manimgx.Mobject.add_background_rectangle
    options:
      heading_level: 3

::: manimgx.Mobject.background_rectangle
    options:
      heading_level: 3

## A class's defaults

::: manimgx.Mobject.set_default
    options:
      heading_level: 3

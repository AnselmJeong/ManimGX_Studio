---
title: "Lines and arrows"
description: "Lines between points, arrows that point, vectors from the origin, and the tips that end them."
---

# Lines and arrows

```python fold title="The film's code"
import manimgx as m


class LinesAndArrows(m.Scene):
    def construct(self) -> None:
        line = m.Line(m.LEFT, m.RIGHT)
        dashed = m.DashedLine(m.LEFT, m.RIGHT, color=m.BLUE)
        arrow = m.Arrow(m.LEFT, m.RIGHT, buff=0, color=m.YELLOW)
        double = m.DoubleArrow(m.LEFT, m.RIGHT, buff=0, color=m.GREEN)
        curved = m.CurvedArrow(m.LEFT, m.RIGHT, color=m.PINK)
        stealth = m.Line(m.LEFT, m.RIGHT, color=m.ORANGE).add_tip(
            tip_shape=m.StealthTip
        )
        shapes = m.VGroup(line, dashed, arrow, double, curved, stealth)
        names = m.VGroup(
            m.Text("Line", font="monospace", font_size=26),
            m.Text("DashedLine", font="monospace", font_size=26),
            m.Text("Arrow", font="monospace", font_size=26),
            m.Text("DoubleArrow", font="monospace", font_size=26),
            m.Text("CurvedArrow", font="monospace", font_size=26),
            m.Text("StealthTip", font="monospace", font_size=26),
        )
        cells = m.VGroup()
        for shape, name in zip(shapes, names, strict=True):
            name.next_to(shape, m.DOWN, buff=0.4)
            cells.add(m.VGroup(shape, name))
        cells.arrange_in_grid(rows=2, buff=(1.4, 1))
        self.play(m.LaggedStart(*[m.Create(shape) for shape in shapes], lag_ratio=0.2))
        self.play(m.FadeIn(names))
        self.wait()
```

A line joins two points. An arrow is a line with a tip at its end, which shows a direction;
a vector is an arrow from the origin. Lines, arrows and arcs can end in a tip, at either end,
in any of the shapes at the [end of this page](#tips).

An end of a line can also be a mobject: the line then runs from that mobject's edge, so that
it joins two shapes without crossing them.

::: manimgx.Line
    options:
      heading_level: 2

::: manimgx.DashedLine
    options:
      heading_level: 2

::: manimgx.Arrow
    options:
      heading_level: 2

::: manimgx.DoubleArrow
    options:
      heading_level: 2

::: manimgx.Vector
    options:
      heading_level: 2

::: manimgx.CurvedArrow
    options:
      heading_level: 2

::: manimgx.CurvedDoubleArrow
    options:
      heading_level: 2

::: manimgx.TangentLine
    options:
      heading_level: 2

## Tips

A tip is a small shape at the end of a line, an arc or an arrow. Arrows make theirs; any
other line or arc takes one with `add_tip`. `tip_shape` chooses its shape, and `tip_style`
its style.

::: manimgx.TipableVMobject
    options:
      heading_level: 3
      members: [add_tip, pop_tips, get_tip, get_tips, has_tip, has_start_tip, tip, start_tip, get_start, get_end, get_length]

::: manimgx.mobjects.shapes.TippedBase
    options:
      heading_level: 3
      inherited_members: [tip_length, normal_vector, tip_style]

### Tip shapes

::: manimgx.ArrowTriangleFilledTip
    options:
      heading_level: 4

::: manimgx.ArrowTriangleTip
    options:
      heading_level: 4

::: manimgx.StealthTip
    options:
      heading_level: 4

::: manimgx.ArrowCircleFilledTip
    options:
      heading_level: 4

::: manimgx.ArrowCircleTip
    options:
      heading_level: 4

::: manimgx.ArrowSquareFilledTip
    options:
      heading_level: 4

::: manimgx.ArrowSquareTip
    options:
      heading_level: 4

::: manimgx.ArrowTip
    options:
      heading_level: 4

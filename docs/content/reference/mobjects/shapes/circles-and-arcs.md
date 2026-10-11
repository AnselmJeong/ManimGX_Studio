---
title: "Circles and arcs"
description: "Circles, dots, ellipses and arcs, and the rings and slices made from them."
---

# Circles and arcs

```python fold title="The film's code"
import manimgx as m


class CirclesAndArcs(m.Scene):
    def construct(self) -> None:
        shapes = m.VGroup(
            m.Circle(color=m.BLUE),
            m.Dot(radius=0.3, color=m.YELLOW),
            m.Ellipse(width=2.6, height=1.4, color=m.GREEN),
            m.Arc(radius=1, start_angle=0, angle=3 * m.PI / 2, color=m.RED),
            m.Annulus(inner_radius=0.5, outer_radius=1, color=m.TEAL),
            m.Sector(radius=1.1, angle=2 * m.PI / 3, color=m.GOLD),
        )
        names = ["Circle", "Dot", "Ellipse", "Arc", "Annulus", "Sector"]
        cells = m.VGroup()
        for shape, name in zip(shapes, names, strict=True):
            label = m.Text(name, font="monospace", font_size=30)
            cells.add(m.VGroup(shape, label.next_to(shape, m.DOWN, buff=0.4)))
        cells.arrange_in_grid(rows=2, buff=(1.2, 0.8))
        self.play(m.LaggedStart(*[m.Create(cell[0]) for cell in cells], lag_ratio=0.15))
        self.play(m.FadeIn(m.VGroup(*[cell[1] for cell in cells])))
        self.wait()
```

A circle is an arc that goes all the way around. An arc is a part of a circle: from a start
angle, counterclockwise through an angle. A dot is a small filled circle, to mark a point.
A ring is the region between two circles, and a slice of it, or of a disc, is a sector.

Arcs end in tips as lines do: see [Lines and arrows](lines-and-arrows.md#tips).

::: manimgx.Circle
    options:
      heading_level: 2

::: manimgx.Dot
    options:
      heading_level: 2

::: manimgx.Ellipse
    options:
      heading_level: 2

::: manimgx.Arc
    options:
      heading_level: 2

::: manimgx.ArcBetweenPoints
    options:
      heading_level: 2

::: manimgx.Annulus
    options:
      heading_level: 2

::: manimgx.AnnularSector
    options:
      heading_level: 2

::: manimgx.Sector
    options:
      heading_level: 2

---
title: "Polygons"
description: "Shapes of straight sides, from triangles to stars, and the rectangles that frame the screen."
---

# Polygons

```python fold title="The film's code"
import manimgx as m


class PolygonsHero(m.Scene):
    def construct(self) -> None:
        shapes = m.VGroup(
            m.Triangle(color=m.BLUE),
            m.Square(side_length=1.8, color=m.GREEN),
            m.Rectangle(width=2.6, height=1.5, color=m.YELLOW),
            m.RoundedRectangle(width=2.6, height=1.5, corner_radius=0.4, color=m.TEAL),
            m.RegularPolygon(n=6, color=m.RED),
            m.Star(color=m.GOLD),
        )
        names = [
            "Triangle",
            "Square",
            "Rectangle",
            "RoundedRectangle",
            "RegularPolygon",
            "Star",
        ]
        cells = m.VGroup()
        for shape, name in zip(shapes, names, strict=True):
            label = m.Text(name, font="monospace", font_size=26)
            cells.add(m.VGroup(shape, label.next_to(shape, m.DOWN, buff=0.4)))
        cells.arrange_in_grid(rows=2, buff=(1, 0.8))
        self.play(m.LaggedStart(*[m.Create(cell[0]) for cell in cells], lag_ratio=0.15))
        self.play(m.FadeIn(m.VGroup(*[cell[1] for cell in cells])))
        self.wait()
```

A polygon is a shape of straight sides, from each corner to the next and from the last back
to the first. Give `m.Polygon` its corners, or take a ready-made one: a triangle, a square, a
rectangle, a regular polygon, a star. Every polygon can round its corners.

A polygram is several polygons in one shape; a polygon is a polygram of one.

::: manimgx.Polygon
    options:
      heading_level: 2

::: manimgx.Polygram
    options:
      heading_level: 2

::: manimgx.Triangle
    options:
      heading_level: 2

::: manimgx.Square
    options:
      heading_level: 2

::: manimgx.Rectangle
    options:
      heading_level: 2

::: manimgx.RoundedRectangle
    options:
      heading_level: 2

::: manimgx.RegularPolygon
    options:
      heading_level: 2

::: manimgx.RegularPolygram
    options:
      heading_level: 2

::: manimgx.Star
    options:
      heading_level: 2

::: manimgx.ArcPolygon
    options:
      heading_level: 2

::: manimgx.ArcPolygonFromArcs
    options:
      heading_level: 2

## The screen's shape

::: manimgx.ScreenRectangle
    options:
      heading_level: 3

::: manimgx.FullScreenRectangle
    options:
      heading_level: 3

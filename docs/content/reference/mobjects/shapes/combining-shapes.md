---
title: "Combining shapes"
description: "New shapes from old ones: their union, their intersection, their difference, a shape with holes, and the hull around points."
---

# Combining shapes

```python fold title="The film's code"
import manimgx as m


class CombiningShapes(m.Scene):
    def construct(self) -> None:
        def pair() -> m.VGroup:
            return m.VGroup(
                m.Circle(radius=0.9).shift(0.45 * m.LEFT),
                m.Square(side_length=1.6).shift(0.45 * m.RIGHT),
            )

        made = m.VGroup()
        names = ["Union", "Intersection", "Difference", "Exclusion"]
        for kind, name in zip(
            [m.Union, m.Intersection, m.Difference, m.Exclusion], names, strict=True
        ):
            a, b = pair()
            shape = kind(a, b, color=m.BLUE, fill_opacity=0.7)
            outline = m.VGroup(a, b).set_stroke(m.GREY_B, width=2)
            label = m.Text(name, font="monospace", font_size=26).next_to(
                outline, m.DOWN, buff=0.4
            )
            made.add(m.VGroup(outline, shape, label))
        made.arrange(buff=0.6)
        self.play(m.LaggedStart(*[m.Create(cell[0]) for cell in made], lag_ratio=0.15))
        self.play(m.LaggedStart(*[m.FadeIn(cell[1:]) for cell in made], lag_ratio=0.15))
        self.wait()
```

Two shapes overlap in three regions: where only the first is, where only the second is, and
where both are. Each of these classes makes a new path from some of those regions, styled as
you say: the originals stay as they are. A cutout cuts holes in a shape, and a convex hull
wraps points as a band would.

::: manimgx.Union
    options:
      heading_level: 2

::: manimgx.Intersection
    options:
      heading_level: 2

::: manimgx.Difference
    options:
      heading_level: 2

::: manimgx.Exclusion
    options:
      heading_level: 2

::: manimgx.Cutout
    options:
      heading_level: 2

::: manimgx.ConvexHull
    options:
      heading_level: 2

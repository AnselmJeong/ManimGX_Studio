---
title: "Groups"
description: "Mobjects made of other mobjects, and the methods that add, remove, arrange and sort a mobject's parts."
---

# Groups

```python fold title="The film's code"
import manimgx as m


class GroupsHero(m.Scene):
    def construct(self) -> None:
        shapes = m.VGroup(
            m.Circle(color=m.BLUE, fill_opacity=0.5),
            m.Square(color=m.GREEN, fill_opacity=0.5),
            m.Triangle(color=m.YELLOW, fill_opacity=0.5),
            m.Star(color=m.RED, fill_opacity=0.5),
        )
        shapes.arrange(buff=0.6)
        self.play(m.LaggedStart(*[m.Create(shape) for shape in shapes], lag_ratio=0.2))
        self.play(shapes.animate.arrange_in_grid(rows=2, buff=0.6))
        self.play(shapes.animate.arrange(m.DOWN, buff=0.3).scale(0.6))
        self.play(shapes.animate.set_color(m.TEAL))
        self.wait()
```

A mobject can hold other mobjects, its parts. A group holds nothing else: its parts are
what it shows. Move, scale, color or animate a group, and every part changes with it.

`m.VGroup` and `m.Group` are one class, by two names: Manim CE's code writes both. A group
is a list of its parts: `group[0]` is the first one, `group[1:3]` is a group of
the second and the third, `len(group)` counts them, and `for part in group:` goes through
them. Every mobject's parts work the same way: a formula's terms, a graph's axes.

::: manimgx.Group
    options:
      heading_level: 2

::: manimgx.VGroup
    options:
      heading_level: 2

## Add and remove parts

::: manimgx.Mobject.add_to_back
    options:
      heading_level: 3

::: manimgx.Mobject.insert
    options:
      heading_level: 3

::: manimgx.Mobject.remove
    options:
      heading_level: 3

::: manimgx.Mobject.get_family
    options:
      heading_level: 3

::: manimgx.Mobject.family_members_with_points
    options:
      heading_level: 3

## Lay parts out

::: manimgx.Mobject.arrange
    options:
      heading_level: 3

::: manimgx.Mobject.arrange_in_grid
    options:
      heading_level: 3

## Order parts

::: manimgx.Mobject.sort
    options:
      heading_level: 3

::: manimgx.Mobject.shuffle
    options:
      heading_level: 3

::: manimgx.Mobject.invert
    options:
      heading_level: 3

## Name parts

::: manimgx.VDict
    options:
      heading_level: 3

::: manimgx.index_labels
    options:
      heading_level: 3

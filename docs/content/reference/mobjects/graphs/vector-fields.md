---
title: "Vector fields"
description: "A vector at every point of the plane, drawn as arrows or as stream lines, and the mobjects it carries."
---

# Vector fields

```python fold title="The film's code"
import manimgx as m
import numpy as np


def swirl(point: np.ndarray) -> np.ndarray:
    x, y = point[0], point[1]
    return np.array([-y, x, 0]) / 3 + np.array([0.3 * np.sin(y), 0, 0])


class VectorFieldsHero(m.Scene):
    def construct(self) -> None:
        field = m.ArrowVectorField(swirl)
        dots = m.VGroup(*[m.Dot([x, 0, 0], color=m.YELLOW) for x in [1, 2, 3]])
        self.play(m.Create(field))
        self.add(dots)
        for dot in dots:
            dot.add_updater(field.get_nudge_updater())
        self.wait(3)
```

A vector field gives a vector at every point of the plane: a function from a point to a
vector. Draw it as arrows, one at each point of a grid, or as stream lines, the paths that
particles would follow. The field's color shows its strength. A field also moves mobjects:
it carries them as a current carries a leaf.

::: manimgx.VectorField
    options:
      heading_level: 2

::: manimgx.ArrowVectorField
    options:
      heading_level: 2

::: manimgx.StreamLines
    options:
      heading_level: 2

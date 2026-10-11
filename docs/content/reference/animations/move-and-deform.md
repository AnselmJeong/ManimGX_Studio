---
title: "Move and deform"
description: "Turn a mobject about a point, move it along a path, or carry every point through a function, a matrix or a flow."
---

# Move and deform

```python fold title="The film's code"
import manimgx as m
import numpy as np


class MoveAndDeformHero(m.Scene):
    def construct(self) -> None:
        grid = m.NumberPlane(
            x_range=[-4, 4, 1], y_range=[-3, 3, 1]
        ).prepare_for_nonlinear_transform()
        self.add(grid)
        self.play(m.ApplyMatrix([[1, 1], [0, 1]], grid), run_time=2)
        self.play(
            m.ApplyFunction(
                lambda mob: mob.apply_function(
                    lambda p: p + 0.3 * np.array([np.sin(p[1]), np.sin(p[0]), 0])
                ),
                grid,
            ),
            run_time=2,
        )
        self.wait()
```

Some changes are not a method call: a turn about a point that the mobject keeps turning
around, a trip along a path, a deformation of every point. These animations make them.

## Turn and follow

::: manimgx.Rotate
    options:
      heading_level: 3

::: manimgx.Rotating
    options:
      heading_level: 3

::: manimgx.MoveAlongPath
    options:
      heading_level: 3

## Through a function

Each point of the mobject goes where a function sends it. Curved images need more points:
insert curves first (see [insert_n_curves][manimgx.VMobject.insert_n_curves]).

::: manimgx.ApplyFunction
    options:
      heading_level: 3

::: manimgx.ApplyPointwiseFunction
    options:
      heading_level: 3

::: manimgx.ApplyMatrix
    options:
      heading_level: 3

::: manimgx.ApplyComplexFunction
    options:
      heading_level: 3

## Deform over time

::: manimgx.Homotopy
    options:
      heading_level: 3

::: manimgx.ComplexHomotopy
    options:
      heading_level: 3

::: manimgx.ApplyWave
    options:
      heading_level: 3

::: manimgx.PhaseFlow
    options:
      heading_level: 3

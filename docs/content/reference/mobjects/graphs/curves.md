---
title: "Curves"
description: "The graph of a function, a parametric curve and an implicit curve, in the frame's own coordinates."
---

# Curves

```python fold title="The film's code"
import manimgx as m
import numpy as np


def heart(t: float) -> np.ndarray:
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    return np.array([x, y, 0]) / 6


class CurvesHero(m.Scene):
    def construct(self) -> None:
        graph = m.FunctionGraph(np.sin, x_range=[-6, -1], color=m.BLUE)
        curve = m.ParametricFunction(heart, t_range=[0, 2 * np.pi], color=m.RED)
        circle = m.ImplicitFunction(
            lambda x, y: (x - 4) ** 2 + y**2 - 2.25, color=m.YELLOW
        )
        self.play(m.Create(graph), m.Create(curve), m.Create(circle), run_time=3)
        self.wait()
```

These curves are drawn in the frame's own coordinates: the graph of `sin` passes through
the point `[0, 0, 0]` of the frame. To draw a graph on axes, in their coordinates, use
[axes.plot][manimgx.Axes.plot], which makes one of these for you.

::: manimgx.FunctionGraph
    options:
      heading_level: 2

::: manimgx.ParametricFunction
    options:
      heading_level: 2

::: manimgx.ImplicitFunction
    options:
      heading_level: 2

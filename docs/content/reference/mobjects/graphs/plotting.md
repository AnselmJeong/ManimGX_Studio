---
title: "Plotting"
description: "The graph of a function on axes, in their coordinates, and what explains it: its label, the area under it, its slope, its derivative."
---

# Plotting

```python fold title="The film's code"
import manimgx as m


def curve(x: float) -> float:
    return 0.25 * x**2 + 0.5


class PlottingHero(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[0, 4, 1], y_range=[0, 5, 1], x_length=8, y_length=5.5)
        axes.add_coordinates()
        graph = axes.plot(curve, color=m.BLUE)
        label = axes.get_graph_label(graph, r"\frac{x^2}{4} + \frac{1}{2}", x_val=3.6)
        rectangles = axes.get_riemann_rectangles(
            graph, x_range=[1, 3], dx=0.25, fill_opacity=0.6
        )
        slope = axes.get_secant_slope_group(
            1.5, graph, dx=1, secant_line_color=m.YELLOW
        )
        self.play(m.Create(axes))
        self.play(m.Create(graph), m.Write(label))
        self.play(
            m.LaggedStart(
                *[m.GrowFromEdge(r, m.DOWN) for r in rectangles], lag_ratio=0.1
            )
        )
        self.play(m.FadeOut(rectangles), m.Create(slope))
        self.wait()
```

[plot][manimgx.Axes.plot] draws the graph of a Python function of x on axes, in their
coordinates: it is a curve, a mobject as any other, to style and animate. The axes then
make what explains it: a label at its end, the area under it, rectangles for its integral,
its slope at a point, the graph of its derivative.

These methods make new mobjects, and add nothing: add them to the scene, or animate them.

## Graphs

::: manimgx.Axes.plot
    options:
      heading_level: 3

::: manimgx.Axes.plot_line_graph
    options:
      heading_level: 3

::: manimgx.Axes.plot_polar_graph
    options:
      heading_level: 3

::: manimgx.Axes.plot_implicit_curve
    options:
      heading_level: 3

::: manimgx.Axes.plot_derivative_graph
    options:
      heading_level: 3

::: manimgx.Axes.plot_antiderivative_graph
    options:
      heading_level: 3

## Points on a graph

::: manimgx.Axes.input_to_graph_point
    options:
      heading_level: 3

::: manimgx.Axes.i2gp
    options:
      heading_level: 3

::: manimgx.Axes.input_to_graph_coords
    options:
      heading_level: 3

::: manimgx.Axes.get_graph_label
    options:
      heading_level: 3

::: manimgx.Axes.get_T_label
    options:
      heading_level: 3

::: manimgx.Axes.get_vertical_lines_to_graph
    options:
      heading_level: 3

## Areas

::: manimgx.Axes.get_area
    options:
      heading_level: 3

::: manimgx.Axes.get_riemann_rectangles
    options:
      heading_level: 3

## Slopes

::: manimgx.Axes.slope_of_tangent
    options:
      heading_level: 3

::: manimgx.Axes.angle_of_tangent
    options:
      heading_level: 3

::: manimgx.Axes.get_secant_slope_group
    options:
      heading_level: 3

::: manimgx.mobjects.plotting.SecantSlopeGroup
    options:
      heading_level: 3

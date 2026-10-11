---
title: "Axes"
description: "Axes with coordinates of their own, their labels and numbers, and lines from them to a point."
---

# Axes

```python fold title="The film's code"
import manimgx as m


class AxesHero(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(x_range=[-1, 5, 1], y_range=[-1, 4, 1], x_length=9, y_length=6)
        axes.add_coordinates()
        names = axes.get_axis_labels("x", "y")
        point = axes.c2p(3, 2)
        dot = m.Dot(point, color=m.YELLOW)
        lines = axes.get_lines_to_point(point, color=m.YELLOW)
        label = m.MathTex("(3, 2)", color=m.YELLOW).next_to(dot, m.UR, buff=0.15)
        self.play(m.Create(axes), m.Write(names))
        self.play(m.GrowFromCenter(dot), m.Create(lines), m.Write(label))
        self.wait()
```

Axes have a range on each axis, `[start, end, step]`, and a length in the frame:
`x_range=[-3, 3, 1]` numbers the x-axis from −3 to 3 with a tick at every unit, and
`x_length=8` makes it 8 units long. The axes' coordinates are theirs: the point where x is 2
and y is 4 is `axes.c2p(2, 4)`, wherever the axes are and however long.

::: manimgx.Axes
    options:
      heading_level: 2
      members: [x_range, y_range, x_axis, y_axis, axes]

## Coordinates

::: manimgx.Axes.coords_to_point
    options:
      heading_level: 3

::: manimgx.Axes.point_to_coords
    options:
      heading_level: 3

::: manimgx.Axes.polar_to_point
    options:
      heading_level: 3

::: manimgx.Axes.get_origin
    options:
      heading_level: 3

::: manimgx.Axes.get_x_unit_size
    options:
      heading_level: 3

::: manimgx.Axes.get_y_unit_size
    options:
      heading_level: 3

## Each axis

::: manimgx.Axes.get_x_axis
    options:
      heading_level: 3

::: manimgx.Axes.get_y_axis
    options:
      heading_level: 3

::: manimgx.Axes.get_z_axis
    options:
      heading_level: 3

::: manimgx.Axes.get_axis
    options:
      heading_level: 3

::: manimgx.Axes.get_axes
    options:
      heading_level: 3

## Labels and numbers

::: manimgx.Axes.add_coordinates
    options:
      heading_level: 3

::: manimgx.Axes.get_axis_labels
    options:
      heading_level: 3

::: manimgx.Axes.get_x_axis_label
    options:
      heading_level: 3

::: manimgx.Axes.get_y_axis_label
    options:
      heading_level: 3

## Lines to a point

::: manimgx.Axes.get_vertical_line
    options:
      heading_level: 3

::: manimgx.Axes.get_horizontal_line
    options:
      heading_level: 3

::: manimgx.Axes.get_lines_to_point
    options:
      heading_level: 3

## Axes in three dimensions

::: manimgx.ThreeDAxes
    options:
      heading_level: 3

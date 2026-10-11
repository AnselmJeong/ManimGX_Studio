---
title: "Paths"
description: "The curves a shape is made of, how to draw a path of your own, and how to find points along one."
---

# Paths

```python fold title="The film's code"
import manimgx as m


class PathsHero(m.Scene):
    def construct(self) -> None:
        path = m.VMobject(color=m.YELLOW, stroke_width=6)
        path.start_new_path([-5, -1, 0])
        path.add_line_to([-3, 2, 0])
        path.add_smooth_curve_to([0, 0, 0])
        path.add_cubic_bezier_curve_to([1, 3, 0], [3, -3, 0], [5, 1, 0])
        anchors = m.VGroup(
            *[m.Dot(point, color=m.BLUE) for point in path.get_anchors()]
        )
        dot = m.Dot(color=m.RED).move_to(path.get_start())
        self.play(m.Create(path), run_time=2)
        self.play(m.FadeIn(anchors))
        self.play(m.MoveAlongPath(dot, path), run_time=2)
        self.wait()
```

A shape is a path: curves, each from one point to the next. A curve starts at an anchor,
bends toward two handles, and ends at the next anchor. The stroke follows the curves, and
the fill closes each part of the path back to its start. Circles, polygons, text and graphs
are all paths, so all of this works on them too.

To draw a path of your own, make an empty `m.VMobject()`, then give it its points: as
corners, as a smooth curve through them, or one line and curve at a time.

::: manimgx.VMobject
    options:
      heading_level: 2
      members: false

## Draw a path

::: manimgx.VMobject.set_points_as_corners
    options:
      heading_level: 3

::: manimgx.VMobject.set_points_smoothly
    options:
      heading_level: 3

::: manimgx.VMobject.start_new_path
    options:
      heading_level: 3

::: manimgx.VMobject.add_line_to
    options:
      heading_level: 3

::: manimgx.VMobject.add_points_as_corners
    options:
      heading_level: 3

::: manimgx.VMobject.add_smooth_curve_to
    options:
      heading_level: 3

::: manimgx.VMobject.add_cubic_bezier_curve_to
    options:
      heading_level: 3

::: manimgx.VMobject.add_quadratic_bezier_curve_to
    options:
      heading_level: 3

::: manimgx.VMobject.add_cubic_bezier_curve
    options:
      heading_level: 3

::: manimgx.VMobject.add_cubic_bezier_curves
    options:
      heading_level: 3

::: manimgx.VMobject.add_subpath
    options:
      heading_level: 3

::: manimgx.VMobject.append_vectorized_mobject
    options:
      heading_level: 3

::: manimgx.VMobject.close_path
    options:
      heading_level: 3

::: manimgx.VMobject.is_closed
    options:
      heading_level: 3

## Smooth or sharp

::: manimgx.VMobject.make_smooth
    options:
      heading_level: 3

::: manimgx.VMobject.make_jagged
    options:
      heading_level: 3

::: manimgx.VMobject.insert_n_curves
    options:
      heading_level: 3

## Along a path

::: manimgx.Mobject.get_start
    options:
      heading_level: 3

::: manimgx.Mobject.get_end
    options:
      heading_level: 3

::: manimgx.Mobject.get_midpoint
    options:
      heading_level: 3

::: manimgx.VMobject.point_from_proportion
    options:
      heading_level: 3

::: manimgx.VMobject.proportion_from_point
    options:
      heading_level: 3

::: manimgx.VMobject.get_arc_length
    options:
      heading_level: 3

::: manimgx.VMobject.get_subcurve
    options:
      heading_level: 3

## Which way it runs

::: manimgx.VMobject.get_direction
    options:
      heading_level: 3

::: manimgx.VMobject.reverse_direction
    options:
      heading_level: 3

::: manimgx.VMobject.force_direction
    options:
      heading_level: 3

## Its points

::: manimgx.Mobject.points
    options:
      heading_level: 3

::: manimgx.Mobject.set_points
    options:
      heading_level: 3

::: manimgx.Mobject.reset_points
    options:
      heading_level: 3

::: manimgx.Mobject.has_points
    options:
      heading_level: 3

::: manimgx.VMobject.append_points
    options:
      heading_level: 3

::: manimgx.VMobject.get_anchors
    options:
      heading_level: 3

::: manimgx.VMobject.get_subpaths
    options:
      heading_level: 3

::: manimgx.VMobject.get_num_curves
    options:
      heading_level: 3

::: manimgx.bezier
    options:
      heading_level: 3

## Paths made from paths

::: manimgx.CubicBezier
    options:
      heading_level: 3

::: manimgx.DashedVMobject
    options:
      heading_level: 3

::: manimgx.CurvesAsSubmobjects
    options:
      heading_level: 3

::: manimgx.VectorizedPoint
    options:
      heading_level: 3

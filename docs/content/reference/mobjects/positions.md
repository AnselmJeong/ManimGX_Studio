---
title: "Positions"
description: "Where a mobject is in the frame, and the methods that move it to a point, beside another mobject or to an edge."
---

# Positions

```python fold title="The film's code"
import manimgx as m


class PositionsHero(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            background_line_style={"stroke_color": m.GREY_D, "stroke_width": 1},
            axis_config={"stroke_color": m.GREY_B, "stroke_width": 2},
        )
        self.add(plane)
        names = ["ORIGIN", "UP", "DOWN", "LEFT", "RIGHT", "UL", "UR", "DL", "DR"]
        points = [m.ORIGIN, m.UP, m.DOWN, m.LEFT, m.RIGHT, m.UL, m.UR, m.DL, m.DR]
        dots = m.VGroup()
        labels = m.VGroup()
        for name, point in zip(names, points, strict=True):
            dot = m.Dot(2.5 * point, radius=0.12, color=m.YELLOW)
            label = m.Text(name, font="monospace", font_size=30)
            label.next_to(dot, m.DOWN, buff=0.2)
            label.add_background_rectangle(opacity=1, buff=0.05)
            dots.add(dot)
            labels.add(label)
        self.play(
            m.LaggedStart(*[m.GrowFromCenter(dot) for dot in dots], lag_ratio=0.1)
        )
        self.play(m.FadeIn(labels))
        self.wait()
```

Every mobject has a place in the frame. A place is a point, three numbers `[x, y, z]`,
measured in units from the frame's center. x grows to the right, y grows upward, and z
grows out of the screen, toward the viewer. The frame's short side is 8 units: a wide
video shows y from −4 to 4, and x from about −7.1 to 7.1.

A mobject's place is its bounding box: the smallest box, along the axes, around what it
draws. Its center, its edges and its corners are points of that box. The methods below read
those points, and move the mobject so that one of them goes where you say. Each method
moves the mobject's parts with it, and gives the mobject back, so that calls chain:
`m.Text("Title").scale(1.5).to_edge(m.UP)`.

## Directions

The axis directions are unit vectors; the diagonals are sums of them. Multiply a direction
by a number, and add directions together, to make other points: `3 * m.RIGHT + 2 * m.UP`
is `[3, 2, 0]`.

<div class="mx-constants" markdown>

::: manimgx.ORIGIN
    options:
      heading_level: 3

::: manimgx.UP
    options:
      heading_level: 3

::: manimgx.DOWN
    options:
      heading_level: 3

::: manimgx.LEFT
    options:
      heading_level: 3

::: manimgx.RIGHT
    options:
      heading_level: 3

::: manimgx.UL
    options:
      heading_level: 3

::: manimgx.UR
    options:
      heading_level: 3

::: manimgx.DL
    options:
      heading_level: 3

::: manimgx.DR
    options:
      heading_level: 3

::: manimgx.IN
    options:
      heading_level: 3

::: manimgx.OUT
    options:
      heading_level: 3

::: manimgx.X_AXIS
    options:
      heading_level: 3

::: manimgx.Y_AXIS
    options:
      heading_level: 3

::: manimgx.Z_AXIS
    options:
      heading_level: 3

</div>

## Where a mobject is

Each of these reads a point of the mobject's bounding box, or one of its coordinates.

::: manimgx.Mobject.get_center
    options:
      heading_level: 3

::: manimgx.Mobject.get_top
    options:
      heading_level: 3

::: manimgx.Mobject.get_bottom
    options:
      heading_level: 3

::: manimgx.Mobject.get_left
    options:
      heading_level: 3

::: manimgx.Mobject.get_right
    options:
      heading_level: 3

::: manimgx.Mobject.get_corner
    options:
      heading_level: 3

::: manimgx.Mobject.get_critical_point
    options:
      heading_level: 3

::: manimgx.Mobject.get_boundary_point
    options:
      heading_level: 3

::: manimgx.Mobject.get_x
    options:
      heading_level: 3

::: manimgx.Mobject.get_y
    options:
      heading_level: 3

::: manimgx.Mobject.get_z
    options:
      heading_level: 3

::: manimgx.Mobject.boundary_box
    options:
      heading_level: 3

## Move a mobject

::: manimgx.Mobject.move_to
    options:
      heading_level: 3

::: manimgx.Mobject.shift
    options:
      heading_level: 3

::: manimgx.Mobject.center
    options:
      heading_level: 3

::: manimgx.Mobject.set_x
    options:
      heading_level: 3

::: manimgx.Mobject.set_y
    options:
      heading_level: 3

::: manimgx.Mobject.set_z
    options:
      heading_level: 3

## Place a mobject by another

A gap between two mobjects is a buff. These are its usual sizes.

<div class="mx-constants" markdown>

::: manimgx.SMALL_BUFF
    options:
      heading_level: 3

::: manimgx.MED_SMALL_BUFF
    options:
      heading_level: 3

::: manimgx.MED_LARGE_BUFF
    options:
      heading_level: 3

::: manimgx.LARGE_BUFF
    options:
      heading_level: 3

::: manimgx.DEFAULT_MOBJECT_TO_MOBJECT_BUFFER
    options:
      heading_level: 3

::: manimgx.DEFAULT_MOBJECT_TO_EDGE_BUFFER
    options:
      heading_level: 3

</div>

::: manimgx.Mobject.next_to
    options:
      heading_level: 3

::: manimgx.Mobject.align_to
    options:
      heading_level: 3

::: manimgx.Mobject.match_x
    options:
      heading_level: 3

::: manimgx.Mobject.match_y
    options:
      heading_level: 3

::: manimgx.Mobject.match_z
    options:
      heading_level: 3

## Place a mobject in the frame

::: manimgx.Mobject.to_edge
    options:
      heading_level: 3

::: manimgx.Mobject.to_corner
    options:
      heading_level: 3

::: manimgx.Mobject.shift_onto_screen
    options:
      heading_level: 3

::: manimgx.Mobject.is_off_screen
    options:
      heading_level: 3

## Compute a point

Points are NumPy arrays, so NumPy computes with them. These functions do what a scene
often needs.

::: manimgx.interpolate
    options:
      heading_level: 3

::: manimgx.midpoint
    options:
      heading_level: 3

::: manimgx.normalize
    options:
      heading_level: 3

::: manimgx.rotate_vector
    options:
      heading_level: 3

::: manimgx.angle_of_vector
    options:
      heading_level: 3

::: manimgx.angle_between_vectors
    options:
      heading_level: 3

::: manimgx.line_intersection
    options:
      heading_level: 3

::: manimgx.perpendicular_bisector
    options:
      heading_level: 3

::: manimgx.polylabel
    options:
      heading_level: 3

::: manimgx.inverse_interpolate
    options:
      heading_level: 3

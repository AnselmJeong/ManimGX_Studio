---
title: "Planes"
description: "Grids of coordinates that fill the frame: the number plane, the complex plane, the polar plane."
---

# Planes

```python fold title="The film's code"
import manimgx as m


class PlanesHero(m.Scene):
    def construct(self) -> None:
        plane = m.ComplexPlane().add_coordinates()
        z = m.Dot(plane.n2p(2 + 1j), color=m.YELLOW)
        label = m.MathTex("2 + i", color=m.YELLOW).next_to(z, m.UR, buff=0.1)
        self.play(m.Create(plane, run_time=2))
        self.play(m.GrowFromCenter(z), m.Write(label))
        self.play(plane.animate.apply_complex_function(lambda w: w**2 / 4), run_time=3)
        self.wait()
```

A plane is axes with a grid: a line at every step of each axis. Unless you size it, a number
plane fills the frame, with the frame's own coordinates, so that a point of the plane is the
point of the frame: it is the grid to see positions by. A complex plane reads its points as
complex numbers, and a polar plane draws circles around its center and rays out of it.

A plane bends with everything on it: insert more curves first
([prepare_for_nonlinear_transform][manimgx.NumberPlane.prepare_for_nonlinear_transform]),
and its lines curve smoothly.

::: manimgx.NumberPlane
    options:
      heading_level: 2
      inherited_members: [prepare_for_nonlinear_transform]

::: manimgx.ComplexPlane
    options:
      heading_level: 2

::: manimgx.PolarPlane
    options:
      heading_level: 2

## Complex numbers and points

A point `[x, y, 0]` stands for the complex number x + yi.

::: manimgx.complex_to_R3
    options:
      heading_level: 3

::: manimgx.R3_to_complex
    options:
      heading_level: 3

::: manimgx.complex_func_to_R3_func
    options:
      heading_level: 3

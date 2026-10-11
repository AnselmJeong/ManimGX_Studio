---
title: "3D scenes"
description: "A scene seen in three dimensions: set where the camera looks from, move it in a play, turn it around the scene."
---

# 3D scenes

```python fold title="The film's code"
import manimgx as m
import numpy as np


class ThreeDScenesHero(m.ThreeDScene):
    def construct(self) -> None:
        axes = m.ThreeDAxes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            z_range=[0, 2],
            x_length=7,
            y_length=7,
            z_length=3,
        )

        def height(u: float, v: float) -> np.ndarray:
            return axes.c2p(u, v, 2 * np.exp(-(u**2 + v**2) / 2))

        hill = m.Surface(height, u_range=[-2.5, 2.5], v_range=[-2.5, 2.5])
        title = m.Text("A hill", font_size=40).to_corner(m.UL)
        self.add_fixed_in_frame_mobjects(title)
        self.add(axes, hill)
        self.move_camera(phi=65 * m.DEGREES, theta=-45 * m.DEGREES, run_time=2)
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(3)
```

A 3D scene is a scene whose camera looks at the frame from an angle. Two angles give it:
`phi`, from straight above (0 looks straight down, as a flat scene does), and `theta`,
around the vertical axis. The camera stays aimed at the frame's center; it shows the scene in
perspective, and what is nearer covers what is farther.

::: manimgx.ThreeDScene
    options:
      heading_level: 2

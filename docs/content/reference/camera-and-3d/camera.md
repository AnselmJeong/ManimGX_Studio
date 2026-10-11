---
title: "Camera"
description: "The camera's frame, to pan and zoom; the look of the picture; and the mobjects that stay fixed on the screen."
---

# Camera

```python fold title="The film's code"
import manimgx as m


class CameraHero(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=3, color=m.BLUE)
        tangent = m.Line(4 * m.LEFT, 4 * m.RIGHT, color=m.YELLOW).shift(3 * m.UP)
        self.add(circle, tangent)
        frame = self.camera.frame
        self.play(frame.animate.scale(0.25).move_to(3 * m.UP), run_time=2)
        self.wait()
        self.play(frame.animate.scale(4).move_to(m.ORIGIN), run_time=2)
```

Every scene has a camera, `self.camera`. Its frame, `self.camera.frame`, is a mobject: move
it to pan, scale it to zoom, and animate it as any other mobject. A frame half as large
shows everything twice as large.

The camera also sets the picture's look: its background, and, for 3D, its exposure, its
tone mapping, its bloom and its shadows.

::: manimgx.Camera
    options:
      heading_level: 2
      members: false

## The frame

::: manimgx.Camera.frame
    options:
      heading_level: 3

::: manimgx.Camera.frame_center
    options:
      heading_level: 3

::: manimgx.Camera.frame_width
    options:
      heading_level: 3

::: manimgx.Camera.frame_height
    options:
      heading_level: 3

::: manimgx.Camera.auto_zoom
    options:
      heading_level: 3

## The look

::: manimgx.Camera.background_color
    options:
      heading_level: 3

::: manimgx.Camera.background_opacity
    options:
      heading_level: 3

::: manimgx.Camera.exposure
    options:
      heading_level: 3

::: manimgx.Camera.tone_mapping
    options:
      heading_level: 3

::: manimgx.Camera.bloom
    options:
      heading_level: 3

::: manimgx.Camera.ambient_occlusion
    options:
      heading_level: 3

::: manimgx.Camera.ambient_occlusion_radius
    options:
      heading_level: 3

::: manimgx.Camera.light_source
    options:
      heading_level: 3

## Fixed on the screen

::: manimgx.Camera.fixed_in_frame_mobjects
    options:
      heading_level: 3

::: manimgx.Camera.add_fixed_in_frame_mobjects
    options:
      heading_level: 3

## Its angles, in 3D

::: manimgx.Camera.three_d
    options:
      heading_level: 3

::: manimgx.Camera.get_phi
    options:
      heading_level: 3

::: manimgx.Camera.get_theta
    options:
      heading_level: 3

::: manimgx.Camera.get_gamma
    options:
      heading_level: 3

::: manimgx.Camera.get_zoom
    options:
      heading_level: 3

::: manimgx.Camera.get_focal_distance
    options:
      heading_level: 3

::: manimgx.Camera.set_phi
    options:
      heading_level: 3

::: manimgx.Camera.set_theta
    options:
      heading_level: 3

::: manimgx.Camera.set_gamma
    options:
      heading_level: 3

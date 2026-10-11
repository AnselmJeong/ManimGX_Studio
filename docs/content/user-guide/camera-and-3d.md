# Camera and 3D

The camera decides what the video shows. Its frame is a rectangle in the scene: the frame
that [Positions](positions.md) measures. Move the frame, and the view moves with it.

## Pan and zoom

`self.camera.frame` is a mobject. Animate it as any other mobject:

```python
import manimgx as m


class Zoom(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=3, color=m.BLUE)
        tangent = m.Line(4 * m.LEFT, 4 * m.RIGHT, color=m.YELLOW)
        tangent.shift(3 * m.UP)
        self.add(circle, tangent)
        frame = self.camera.frame
        self.play(frame.animate.scale(0.25).move_to(3 * m.UP), run_time=2)
        self.wait()
        self.play(frame.animate.scale(4).move_to(m.ORIGIN), run_time=2)
```

- Move the frame to pan: `frame.animate.move_to(point)`.
- Scale it to zoom: a frame half as large shows everything twice as large.

## Three dimensions

To make a scene in 3D, make it from `m.ThreeDScene`. Its camera looks at the frame from
two angles:

- `phi`, its angle from straight above: 0 looks straight down, as in a flat scene.
- `theta`, its angle around the vertical axis.

```python
import manimgx as m
import numpy as np


class Hill(m.ThreeDScene):
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
        title = m.Text("A hill", font_size=40)
        title.to_corner(m.UL)
        self.add_fixed_in_frame_mobjects(title)
        self.add(axes, hill)
        self.move_camera(phi=65 * m.DEGREES, theta=-45 * m.DEGREES, run_time=2)
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(3)
```

- `self.set_camera_orientation(phi=..., theta=...)` turns the camera at once, and
  `self.move_camera(...)` turns it in an animation.
- `self.begin_ambient_camera_rotation(rate=0.3)` turns the camera around the scene, until
  `self.stop_ambient_camera_rotation()`.
- `self.add_fixed_in_frame_mobjects(title)` keeps a mobject still on the screen while the
  camera moves: here, the title stays in its corner.

Every mobject has three coordinates, so flat mobjects work in 3D too. The
[reference][manimgx.mobjects.three_d] shows the mobjects made for 3D, such as
spheres and cubes.

## Next

[Sound and voice](sound-and-voice.md) shows how to add sound and a voice to your video.

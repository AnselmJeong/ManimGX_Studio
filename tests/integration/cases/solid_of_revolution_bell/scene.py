"""Show me how rotating the curve y = e^(-x^2) around the y-axis builds a 3D bell shape."""

import math

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "manimgx Camera lacks reorient/move_camera Euler triples; using "
    "Scene.set_camera_orientation at start and Scene.move_camera "
    "to animate into a 3D view while the surface forms."
)


class TeacherScene(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes(
            x_range=(-2.5, 2.5, 1.0),
            y_range=(-2.5, 2.5, 1.0),
            z_range=(0.0, 1.5, 0.5),
            x_length=6.0,
            y_length=6.0,
            z_length=3.0,
        )

        # 2D Gaussian curve lying in the xz-plane (y=0): y-value of e^(-x^2)
        # maps to z in 3D so the rotation about the x-axis sweeps out the bell.
        def bell_2d(t: float) -> np.ndarray:
            x = t
            z = math.exp(-t * t)
            return np.asarray(axes.c2p(x, 0.0, z))

        bell2d = m.ParametricFunction(
            bell_2d,
            t_range=(-2.0, 2.0, 0.05),
            color=m.YELLOW,
            stroke_width=4.0,
        ).set_shade_in_3d(True)

        # Parametric surface of revolution about the x-axis:
        # (u, v) -> (u, sin(v) * e^(-u^2), cos(v) * e^(-u^2))
        def bell_surface_func(u: float, v: float) -> np.ndarray:
            r = math.exp(-u * u)
            return np.asarray(axes.c2p(u, r * math.sin(v), r * math.cos(v)))

        bell_surface = m.Surface(
            bell_surface_func,
            u_range=(-2.0, 2.0),
            v_range=(0.0, m.TAU),
            resolution=(32, 32),
            color=m.YELLOW,
            fill_opacity=0.5,
        )

        # Start with a nearly side-on view (small phi tilt so the curve reads 2D).
        self.set_camera_orientation(phi=85 * m.DEGREES, theta=-90 * m.DEGREES)

        self.play(m.Create(axes), run_time=1.5)
        self.play(m.Create(bell2d), run_time=2.0)
        self.wait(0.5)

        # Move camera to a tilted 3D view while we sweep the curve into 3D.
        self.move_camera(phi=65 * m.DEGREES, theta=-60 * m.DEGREES, run_time=2.0)

        # Rotate the 2D curve about the x-axis to trace out the 3D bell.
        self.play(
            m.Rotate(bell2d, m.PI, axis=m.RIGHT),
            run_time=3.0,
        )

        # Reveal the full surface of revolution.
        self.play(m.FadeIn(bell_surface), run_time=2.5)
        self.wait(0.5)

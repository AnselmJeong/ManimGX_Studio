"""A surface plot on 3D axes, a curve drawn across it with a ball riding its tip, and the
camera circling the whole time: every frame is new. (Manim Community Edition.)"""

from manim import *


class Orbit(ThreeDScene):
    def construct(self) -> None:
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[-2, 2, 1],
            x_length=7,
            y_length=7,
            z_length=4,
        )
        surface = Surface(
            lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(48, 48),
            checkerboard_colors=[BLUE_D, BLUE_E],
        )
        curve = ParametricFunction(
            lambda t: axes.c2p(
                2.4 * np.cos(t),
                2.4 * np.sin(t),
                np.sin(2.4 * np.cos(t)) * np.cos(2.4 * np.sin(t)) + 0.08,
            ),
            t_range=[0, 2 * np.pi],
            color=YELLOW,
            stroke_width=6,
        )
        ball = Dot3D(curve.get_start(), radius=0.12, color=YELLOW)
        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)
        self.add(axes, surface, ball)
        self.begin_ambient_camera_rotation(rate=0.3)
        self.play(
            Create(curve), MoveAlongPath(ball, curve), run_time=6, rate_func=linear
        )
        self.wait(4)

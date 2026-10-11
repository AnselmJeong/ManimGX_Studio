import math

import numpy as np

import manimgx as m


def f(x: float, y: float) -> float:
    return 0.4 * (x * x + y * y)


class TeacherScene(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=65 * m.DEGREES, theta=-30 * m.DEGREES)
        axes = m.ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[0, 4, 1],
        )
        self.add(axes)

        title = (
            m.Tex(
                "Gradient descent on ",
                "$f(x,y) = 0.4(x^2 + y^2)$",
            )
            .scale(0.7)
            .to_edge(m.UP, buff=0.3)
        )
        title[1].set_color(m.YELLOW)
        self.add_fixed_in_frame_mobjects(title)

        surface = m.Surface(
            lambda u, v: np.array([u, v, f(u, v)]),
            u_range=[-2.5, 2.5],
            v_range=[-2.5, 2.5],
            resolution=(20, 20),
        )
        surface.set_fill_by_value(
            axes=axes, colors=[(m.BLUE, 0), (m.YELLOW, 2), (m.RED, 4)]
        )
        self.play(m.FadeIn(surface))

        t = m.ValueTracker(0.0)

        def ball_pos() -> np.ndarray:
            tv = t.get_value()
            r = 2.4 * (1 - tv)
            angle = 4 * tv * math.pi
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            return np.array([x, y, f(x, y) + 0.15])

        ball = m.always_redraw(
            lambda: m.Sphere(radius=0.12, color=m.RED).move_to(ball_pos()),
        )
        self.add(ball)

        self.play(t.animate.set_value(0.95), run_time=5.0, rate_func=m.smooth)
        self.wait(1.2)

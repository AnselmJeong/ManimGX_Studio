import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Sine = $y$-coordinate on the unit circle")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        circle_center = np.array([-3.8, -0.3, 0.0])
        circle = m.Circle(radius=1.4, color=m.WHITE, stroke_width=2).move_to(
            circle_center
        )

        ax = m.Axes(
            x_range=[0, 2 * math.pi, math.pi / 2],
            y_range=[-1.5, 1.5, 1],
            x_length=6.5,
            y_length=3.5,
        ).shift(m.RIGHT * 2.3 + m.DOWN * 0.3)
        sin_curve = ax.plot(
            lambda x: math.sin(x), color=m.BLUE, x_range=[0, 2 * math.pi]
        )
        self.play(m.Create(circle), m.Create(ax), m.Create(sin_curve))

        theta = m.ValueTracker(0.0)

        def circle_pt() -> np.ndarray:
            t = theta.get_value()
            return circle_center + 1.4 * np.array([math.cos(t), math.sin(t), 0.0])

        radius_line = m.always_redraw(
            lambda: m.Line(circle_center, circle_pt(), color=m.RED, stroke_width=2),
        )
        circle_dot = m.always_redraw(
            lambda: m.Dot(circle_pt(), color=m.YELLOW, radius=0.1),
        )
        graph_dot = m.always_redraw(
            lambda: m.Dot(
                ax.c2p(theta.get_value(), math.sin(theta.get_value())),
                color=m.YELLOW,
                radius=0.1,
            ),
        )
        self.add(radius_line, circle_dot, graph_dot)

        self.play(
            theta.animate.set_value(2 * math.pi), run_time=6.0, rate_func=m.linear
        )
        self.wait(1.2)

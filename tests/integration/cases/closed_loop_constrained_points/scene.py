import math

import numpy as np

import manimgx as m


def curve_pt(theta: float) -> np.ndarray:
    r = 1.6 + 0.5 * math.cos(2 * theta)
    return np.array([r * math.cos(theta), r * math.sin(theta), 0.0])


SPEEDS = [1.0, 1.4, 0.7, 1.6]
PHASES = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
COLORS = [m.YELLOW, m.GREEN, m.RED, m.BLUE]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        loop = m.ParametricFunction(
            curve_pt,
            t_range=[0, 2 * math.pi],
            color=m.WHITE,
            stroke_width=2,
        )
        self.play(m.Create(loop))

        title = (
            m.Tex(
                "Four points moving at different speeds along a closed loop",
            )
            .scale(0.75)
            .to_edge(m.UP, buff=0.4)
        )
        self.play(m.Write(title))

        t = m.ValueTracker(0.0)

        def dot_pos(i: int) -> np.ndarray:
            theta = (t.get_value() * SPEEDS[i] + PHASES[i]) % (2 * math.pi)
            return curve_pt(theta)

        dots = [
            m.always_redraw(
                lambda i=i: m.Dot(dot_pos(i), color=COLORS[i], radius=0.1),
            )
            for i in range(4)
        ]
        polygon = m.always_redraw(
            lambda: m.Polygon(
                *[dot_pos(i) for i in range(4)],
                color=m.PURPLE,
                stroke_width=2,
                fill_color=m.PURPLE,
                fill_opacity=0.2,
            )
        )
        for d in dots:
            self.add(d)
        self.add(polygon)

        self.play(t.animate.set_value(2 * math.pi), run_time=6.0, rate_func=m.linear)
        self.wait(1.5)

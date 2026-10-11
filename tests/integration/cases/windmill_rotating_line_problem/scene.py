import math

import numpy as np

import manimgx as m

POINTS = [
    np.array([-2.0, 1.0, 0.0]),
    np.array([-1.0, -1.5, 0.0]),
    np.array([0.5, 0.5, 0.0]),
    np.array([1.5, 1.8, 0.0]),
    np.array([2.0, -1.0, 0.0]),
    np.array([-0.5, -0.5, 0.0]),
]
PIVOT_IDX = 2


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Windmill: line rotates through point set")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        dots = m.VGroup(*[m.Dot(p, color=m.WHITE, radius=0.1) for p in POINTS])
        self.play(m.FadeIn(dots))

        pivot = POINTS[PIVOT_IDX]
        angle = m.ValueTracker(0.0)

        def line() -> m.Line:
            theta = angle.get_value()
            d = np.array([math.cos(theta), math.sin(theta), 0.0])
            return m.Line(
                pivot - 4 * d,
                pivot + 4 * d,
                color=m.YELLOW,
                stroke_width=2.5,
            )

        pivot_dot = m.Dot(pivot, color=m.RED, radius=0.13)
        self.add(m.always_redraw(line), pivot_dot)
        self.play(angle.animate.set_value(math.pi), run_time=5.0, rate_func=m.linear)
        self.wait(1.5)

import math

import numpy as np

import manimgx as m

POINTS_AND_COLORS = [
    (np.array([-2.0, 1.0, 0.0]), m.RED),
    (np.array([-1.0, -1.5, 0.0]), m.BLUE),
    (np.array([0.5, 0.5, 0.0]), m.RED),
    (np.array([1.5, 1.8, 0.0]), m.BLUE),
    (np.array([2.0, -1.0, 0.0]), m.RED),
    (np.array([-0.5, -0.5, 0.0]), m.BLUE),
]
PIVOT_IDX = 2


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Windmill with 2-coloring").scale(0.85).to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        dots = m.VGroup(*[m.Dot(p, color=c, radius=0.13) for p, c in POINTS_AND_COLORS])
        self.play(m.FadeIn(dots))

        pivot = POINTS_AND_COLORS[PIVOT_IDX][0]
        angle = m.ValueTracker(0.0)

        def line() -> m.Line:
            theta = angle.get_value()
            d = np.array([math.cos(theta), math.sin(theta), 0.0])
            return m.Line(
                pivot - 4 * d,
                pivot + 4 * d,
                color=m.YELLOW,
                stroke_width=2,
            )

        self.add(m.always_redraw(line))

        caption = (
            m.Tex(
                "Invariant: red and blue counts on each side stay equal",
            )
            .scale(0.65)
            .to_edge(m.DOWN, buff=0.5)
        )
        self.play(m.Write(caption))

        self.play(angle.animate.set_value(math.pi), run_time=5.0, rate_func=m.linear)
        self.wait(1.5)

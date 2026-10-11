import math

import manimgx as m


def heat_at(x: float, t: float) -> float:
    sigma_sq = 0.15 + 0.3 * t
    return math.sqrt(0.15 / sigma_sq) * math.exp(-(x * x) / (2 * sigma_sq))


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Heat equation: temperature on a rod").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        ax = m.Axes(
            x_range=[-2, 2, 0.5],
            y_range=[0, 1.2, 0.5],
            x_length=10,
            y_length=4,
        ).shift(m.DOWN * 0.3)
        self.add(ax)

        t = m.ValueTracker(0.0)
        curve = m.always_redraw(
            lambda: ax.plot(
                lambda x: heat_at(x, t.get_value()),
                color=m.RED,
                x_range=[-2, 2],
            ),
        )
        self.add(curve)
        self.play(t.animate.set_value(2.5), run_time=5.0)
        self.wait(1.5)

import math

import manimgx as m


def step_smoothed(x: float, t: float) -> float:
    return 0.5 * (1.0 - math.erf(x / math.sqrt(0.4 + t)))


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Two regions at different temperatures equilibrate",
            )
            .scale(0.8)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        ax = m.Axes(
            x_range=[-3, 3, 1],
            y_range=[0, 1.2, 0.5],
            x_length=10,
            y_length=4,
        ).shift(m.DOWN * 0.3)
        self.add(ax)

        t = m.ValueTracker(0.001)
        curve = m.always_redraw(
            lambda: ax.plot(
                lambda x: step_smoothed(x, t.get_value()),
                color=m.RED,
                x_range=[-3, 3],
            ),
        )
        self.add(curve)
        self.play(t.animate.set_value(3.0), run_time=5.0)
        self.wait(1.5)

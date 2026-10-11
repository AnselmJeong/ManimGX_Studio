import math

import manimgx as m


def beta_pdf(x: float, a: float, b: float) -> float:
    if x <= 0 or x >= 1:
        return 0.0
    coef = math.gamma(a + b) / (math.gamma(a) * math.gamma(b))
    return float(coef * (x ** (a - 1)) * ((1 - x) ** (b - 1)))


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Beta distribution updates with coin flips")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        ax = m.Axes(
            x_range=[0, 1, 0.25],
            y_range=[0, 5, 1],
            x_length=10,
            y_length=5,
        ).shift(m.DOWN * 0.3)
        self.add(ax)

        a = m.ValueTracker(1.0)
        b = m.ValueTracker(1.0)
        curve = m.always_redraw(
            lambda: ax.plot(
                lambda x: beta_pdf(x, a.get_value(), b.get_value()),
                color=m.YELLOW,
                x_range=[0.01, 0.99],
            ),
        )
        self.add(curve)

        for h, t in [
            (1, 0),
            (2, 0),
            (3, 0),
            (3, 1),
            (4, 1),
            (5, 1),
            (5, 2),
            (6, 2),
            (7, 2),
            (7, 3),
        ]:
            self.play(
                a.animate.set_value(1 + h), b.animate.set_value(1 + t), run_time=0.4
            )
        self.wait(2.0)

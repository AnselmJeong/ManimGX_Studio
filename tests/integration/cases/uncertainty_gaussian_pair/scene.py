import math

import manimgx as m


def gaussian(x: float, sigma: float) -> float:
    return (1.0 / (sigma * math.sqrt(2 * math.pi))) * math.exp(
        -(x * x) / (2 * sigma * sigma)
    )


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.MathTex(
            "\\sigma_x \\cdot \\sigma_p \\geq \\tfrac{1}{2}",
            color=m.YELLOW,
        ).to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        ax_x = m.Axes(
            x_range=[-4, 4, 1],
            y_range=[0, 1.5, 0.5],
            x_length=5,
            y_length=2.7,
        ).shift(m.LEFT * 3 + m.DOWN * 0.5)
        ax_p = m.Axes(
            x_range=[-4, 4, 1],
            y_range=[0, 1.5, 0.5],
            x_length=5,
            y_length=2.7,
        ).shift(m.RIGHT * 3 + m.DOWN * 0.5)
        x_label = m.Tex("position $x$").scale(0.65).next_to(ax_x, m.UP, buff=0.15)
        p_label = m.Tex("momentum $p$").scale(0.65).next_to(ax_p, m.UP, buff=0.15)
        self.play(m.Create(ax_x), m.Create(ax_p), m.Write(x_label), m.Write(p_label))

        sigma = m.ValueTracker(1.0)
        x_curve = m.always_redraw(
            lambda: ax_x.plot(
                lambda x: 2.5 * gaussian(x, sigma.get_value()), color=m.BLUE
            ),
        )
        p_curve = m.always_redraw(
            lambda: ax_p.plot(
                lambda x: 2.5 * gaussian(x, 0.5 / sigma.get_value()), color=m.RED
            ),
        )
        self.add(x_curve, p_curve)
        self.play(sigma.animate.set_value(0.4), run_time=2.5)
        self.play(sigma.animate.set_value(2.5), run_time=2.5)
        self.wait(1.0)

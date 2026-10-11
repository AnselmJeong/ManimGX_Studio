import math

import manimgx as m


def gaussian(x: float, sigma: float) -> float:
    return (1.0 / (sigma * math.sqrt(2 * math.pi))) * math.exp(
        -(x * x) / (2 * sigma * sigma)
    )


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Time vs frequency: width tradeoff").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        ax_time = m.Axes(
            x_range=[-4, 4, 1],
            y_range=[0, 1.5, 0.5],
            x_length=5,
            y_length=2.7,
        ).shift(m.LEFT * 3 + m.DOWN * 0.5)
        ax_freq = m.Axes(
            x_range=[-4, 4, 1],
            y_range=[0, 1.5, 0.5],
            x_length=5,
            y_length=2.7,
        ).shift(m.RIGHT * 3 + m.DOWN * 0.5)
        time_label = m.Tex("time").scale(0.6).next_to(ax_time, m.UP, buff=0.1)
        freq_label = m.Tex("frequency").scale(0.6).next_to(ax_freq, m.UP, buff=0.1)
        self.play(
            m.Create(ax_time),
            m.Create(ax_freq),
            m.Write(time_label),
            m.Write(freq_label),
        )

        sigma = m.ValueTracker(1.0)
        time_curve = m.always_redraw(
            lambda: ax_time.plot(
                lambda x: 2.5 * gaussian(x, sigma.get_value()), color=m.BLUE
            ),
        )
        freq_curve = m.always_redraw(
            lambda: ax_freq.plot(
                lambda x: 2.5 * gaussian(x, 1.0 / sigma.get_value()), color=m.RED
            ),
        )
        self.add(time_curve, freq_curve)
        self.play(sigma.animate.set_value(0.35), run_time=2.5)
        self.play(sigma.animate.set_value(3.0), run_time=2.5)
        self.wait(1.2)

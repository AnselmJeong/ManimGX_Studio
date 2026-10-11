import math

import manimgx as m

FREQS = [1, 2, 4]
AMPS = [1.0, 0.5, 0.3]


def composite(x: float) -> float:
    return sum(a * math.sin(f * x) for f, a in zip(FREQS, AMPS))


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Wave decomposition into pure frequencies")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        ax_top = m.Axes(
            x_range=[0, 2 * math.pi, math.pi / 2],
            y_range=[-2, 2, 1],
            x_length=10,
            y_length=1.8,
        ).shift(m.UP * 2.0)
        composite_curve = ax_top.plot(
            composite, color=m.WHITE, x_range=[0, 2 * math.pi]
        )
        self.play(m.Create(ax_top), m.Create(composite_curve))

        colors = [m.YELLOW, m.GREEN, m.RED]
        for i, (freq, amp) in enumerate(zip(FREQS, AMPS)):
            y_offset = 0.4 - i * 1.7
            ax = m.Axes(
                x_range=[0, 2 * math.pi, math.pi / 2],
                y_range=[-1.2, 1.2, 1],
                x_length=10,
                y_length=1.3,
            ).shift(m.UP * y_offset)
            curve = ax.plot(
                lambda x, f=freq, a=amp: a * math.sin(f * x),
                color=colors[i],
                x_range=[0, 2 * math.pi],
            )
            self.play(m.Create(ax), m.Create(curve), run_time=0.7)
        self.wait(2.0)

import math

import manimgx as m

FREQS = [1, 3, 5]
AMPS = [1.0, 0.5, 0.3]


def composite(x: float) -> float:
    return sum(a * math.sin(f * x) for f, a in zip(FREQS, AMPS))


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Fourier transform: time $\\to$ frequency",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        ax_time = m.Axes(
            x_range=[0, 2 * math.pi, math.pi / 2],
            y_range=[-2, 2, 1],
            x_length=4.5,
            y_length=2.8,
        ).shift(m.LEFT * 3.6)
        time_curve = ax_time.plot(composite, color=m.BLUE, x_range=[0, 2 * math.pi])
        self.play(m.Create(ax_time), m.Create(time_curve))

        arrow = m.Arrow(
            m.LEFT * 1.0, m.RIGHT * 1.0, color=m.YELLOW, buff=0, stroke_width=5
        )
        f_op = (
            m.MathTex("\\mathcal{F}", color=m.YELLOW)
            .scale(1.5)
            .next_to(arrow, m.UP, buff=0.2)
        )
        self.play(m.GrowArrow(arrow), m.Write(f_op))

        ax_freq = m.Axes(
            x_range=[0, 7, 1],
            y_range=[0, 1.2, 0.5],
            x_length=4.5,
            y_length=2.8,
        ).shift(m.RIGHT * 3.6)
        spectrum = m.VGroup()
        for f, a in zip(FREQS, AMPS):
            spectrum.add(
                m.Line(
                    ax_freq.c2p(f, 0), ax_freq.c2p(f, a), color=m.RED, stroke_width=4
                ),
                m.Dot(ax_freq.c2p(f, a), color=m.RED, radius=0.08),
            )
        self.play(m.Create(ax_freq))
        self.play(m.Create(spectrum))
        self.wait(2.0)

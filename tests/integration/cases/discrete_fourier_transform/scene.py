import math

import manimgx as m

N = 16
SIGNAL = [
    math.sin(2 * math.pi * k / N) + 0.5 * math.sin(2 * math.pi * 3 * k / N)
    for k in range(N)
]


def dft_magnitude(signal: list[float]) -> list[float]:
    n = len(signal)
    mags = []
    for k in range(n // 2):
        re = sum(signal[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
        im = -sum(signal[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))
        mags.append(math.sqrt(re * re + im * im) / n)
    return mags


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Discrete Fourier Transform").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        ax_signal = m.Axes(
            x_range=[0, N, 4],
            y_range=[-1.5, 1.5, 1],
            x_length=10,
            y_length=2.5,
        ).shift(m.UP * 1.5)
        ax_label = m.Tex("signal").scale(0.55).next_to(ax_signal, m.LEFT, buff=0.3)
        self.play(m.Create(ax_signal), m.Write(ax_label))

        bars_signal = m.VGroup()
        for k, v in enumerate(SIGNAL):
            bars_signal.add(
                m.Line(
                    ax_signal.c2p(k, 0),
                    ax_signal.c2p(k, v),
                    color=m.BLUE,
                    stroke_width=4,
                ),
            )
        self.play(m.Create(bars_signal))

        ax_dft = m.Axes(
            x_range=[0, N // 2, 2],
            y_range=[0, 0.7, 0.25],
            x_length=10,
            y_length=2.5,
        ).shift(m.DOWN * 1.5)
        dft_label = m.Tex("spectrum").scale(0.55).next_to(ax_dft, m.LEFT, buff=0.3)
        self.play(m.Create(ax_dft), m.Write(dft_label))

        mags = dft_magnitude(SIGNAL)
        bars_dft = m.VGroup()
        for k, mag in enumerate(mags):
            bars_dft.add(
                m.Line(
                    ax_dft.c2p(k, 0),
                    ax_dft.c2p(k, mag),
                    color=m.RED,
                    stroke_width=4,
                ),
            )
        self.play(
            m.LaggedStart(*[m.Create(b) for b in bars_dft], lag_ratio=0.05),
            run_time=1.5,
        )
        self.wait(2.0)

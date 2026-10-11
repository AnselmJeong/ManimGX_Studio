"""A travelling wave: VALUE is frequency in Hz, wavelength is fixed."""

import math

import manimgx as m

VALUE = 1.0
PACE = 1.0


class Lesson(m.Scene):
    def construct(self) -> None:
        m.config.background_color = "#101825"
        title = m.Text("파동: 움직임이 전달되는 방식", font_size=36).to_edge(
            m.UP, buff=0.4
        )
        axes = m.Axes(
            x_range=[0, 8, 1],
            y_range=[-1.5, 1.5, 1],
            x_length=10.5,
            y_length=3.4,
            tips=False,
        ).shift(m.UP * 0.1)
        clock = m.ValueTracker(0)
        wavelength = 4.0

        def displacement(x: float) -> float:
            return math.sin(2 * math.pi * (x / wavelength - VALUE * clock.get_value()))

        wave = m.always_redraw(
            lambda: axes.plot(displacement, color=m.BLUE, stroke_width=4)
        )
        dot = m.always_redraw(
            lambda: m.Dot(axes.c2p(2, displacement(2)), color=m.YELLOW, radius=0.11)
        )
        guide = m.DashedLine(axes.c2p(2, -1.3), axes.c2p(2, 1.3), color=m.GRAY)
        caption = m.Text(
            "노란 점은 제자리에서 위아래로 진동합니다", font_size=24
        ).to_edge(m.DOWN)
        formula = m.MathTex(r"y(x,t)=A\sin(kx-\omega t)", font_size=34).move_to(
            [0, -2.25, 0]
        )
        meta = m.Text(
            f"진동수 {VALUE:g} Hz   ·   파장 4 m   ·   파동 속력 {4 * VALUE:g} m/s",
            font_size=22,
        ).move_to([0, -2.95, 0])
        self.play(m.Write(title), m.Create(axes), run_time=1.2 * PACE)
        self.play(
            m.Create(wave),
            m.Create(guide),
            m.FadeIn(dot),
            m.FadeIn(caption),
            run_time=1.5 * PACE,
        )
        self.play(clock.animate.set_value(3), run_time=3 * PACE, rate_func=m.linear)
        next_caption = m.Text(
            "점은 이동하지 않아도, 파동의 모양은 오른쪽으로 진행합니다", font_size=24
        ).to_edge(m.DOWN)
        self.play(
            m.Write(formula), m.Transform(caption, next_caption), run_time=1.2 * PACE
        )
        self.play(clock.animate.set_value(7), run_time=4 * PACE, rate_func=m.linear)
        self.play(m.FadeIn(meta), run_time=0.8 * PACE)
        self.play(clock.animate.set_value(10), run_time=3 * PACE, rate_func=m.linear)

"""Small-angle pendulum; VALUE is length in metres, g = 9.81 m/s²."""

import math

import manimgx as m

VALUE = 1.5
PACE = 1.0


class Lesson(m.Scene):
    def construct(self) -> None:
        m.config.background_color = "#101825"
        title = m.Text("진자: 길이가 리듬을 결정합니다", font_size=36).to_edge(
            m.UP, buff=0.4
        )
        pivot = [-2.5, 1.9, 0]
        length = 2.7
        clock = m.ValueTracker(0)
        omega = math.sqrt(9.81 / VALUE)
        period = 2 * math.pi / omega

        def position() -> list[float]:
            angle = 0.18 * math.cos(omega * clock.get_value())
            return [
                pivot[0] + length * math.sin(angle),
                pivot[1] - length * math.cos(angle),
                0,
            ]

        rod = m.always_redraw(
            lambda: m.Line(pivot, position(), color=m.WHITE, stroke_width=4)
        )
        bob = m.always_redraw(lambda: m.Dot(position(), color=m.TEAL, radius=0.23))
        pin = m.Dot(pivot, color=m.WHITE, radius=0.07)
        guide = m.DashedLine(
            pivot, [pivot[0], pivot[1] - length - 0.35, 0], color=m.GRAY
        )
        formula = m.MathTex(r"T \approx 2\pi\sqrt{\frac{L}{g}}", font_size=48).move_to(
            [2.8, 0.8, 0]
        )
        numbers = m.Text(f"L = {VALUE:g} m\nT ≈ {period:.2f} s", font_size=30).move_to(
            [2.8, -0.65, 0]
        )
        note = m.Text("작은 진폭 · 마찰 없음 · g = 9.81 m/s²", font_size=22).move_to(
            [1.6, -2.3, 0]
        )
        caption = m.Text(
            "한 번 왕복하는 데 걸리는 시간이 주기입니다", font_size=24
        ).to_edge(m.DOWN)
        self.play(m.Write(title), m.Create(guide), m.FadeIn(pin), run_time=1.2 * PACE)
        self.play(m.Create(rod), m.FadeIn(bob), m.FadeIn(caption), run_time=1.2 * PACE)
        self.play(
            clock.animate.set_value(period * 2),
            run_time=period * 2 * PACE,
            rate_func=m.linear,
        )
        self.play(
            m.Write(formula), m.FadeIn(numbers), m.FadeIn(note), run_time=1.5 * PACE
        )
        next_caption = m.Text(
            "진자의 길이가 4배가 되면, 주기는 약 2배가 됩니다", font_size=24
        ).to_edge(m.DOWN)
        self.play(m.Transform(caption, next_caption), run_time=0.7 * PACE)
        self.play(
            clock.animate.set_value(period * 4),
            run_time=period * 2 * PACE,
            rate_func=m.linear,
        )
        self.wait(1.5 * PACE)

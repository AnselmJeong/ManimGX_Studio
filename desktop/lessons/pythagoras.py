"""Squares on the sides of a right triangle; VALUE is side a, side b = 3."""

import math

import manimgx as m

VALUE = 2.0
PACE = 1.0


class Lesson(m.Scene):
    def construct(self) -> None:
        m.config.background_color = "#101825"
        title = m.Text("피타고라스: 길이를 넓이로 보기", font_size=36).to_edge(
            m.UP, buff=0.4
        )
        a, b = VALUE, 3.0
        c = math.hypot(a, b)
        triangle = m.Polygon(
            [0, 0, 0], [a, 0, 0], [0, b, 0], color=m.WHITE, fill_opacity=0.1
        )
        square_a = m.Polygon(
            [0, 0, 0], [a, 0, 0], [a, -a, 0], [0, -a, 0], color=m.BLUE, fill_opacity=0.3
        )
        square_b = m.Polygon(
            [0, 0, 0], [0, b, 0], [-b, b, 0], [-b, 0, 0], color=m.TEAL, fill_opacity=0.3
        )
        square_c = m.Polygon(
            [a, 0, 0],
            [0, b, 0],
            [b, b + a, 0],
            [a + b, a, 0],
            color=m.YELLOW,
            fill_opacity=0.2,
        )
        mark = m.VGroup(
            m.Line([0.3, 0, 0], [0.3, 0.3, 0]), m.Line([0.3, 0.3, 0], [0, 0.3, 0])
        )
        la = m.MathTex("a^2", font_size=38).move_to(square_a.get_center())
        lb = m.MathTex("b^2", font_size=38).move_to(square_b.get_center())
        lc = m.MathTex("c^2", font_size=38).move_to(square_c.get_center())
        diagram = m.VGroup(triangle, square_a, square_b, square_c, mark, la, lb, lc)
        diagram.scale(5.0 / (b + 2 * a)).move_to([-2.5, -0.1, 0])
        caption = m.Text(
            "직각삼각형의 세 변 위에 정사각형을 만듭니다", font_size=24
        ).to_edge(m.DOWN)
        self.play(
            m.Write(title),
            m.Create(triangle),
            m.Create(mark),
            m.FadeIn(caption),
            run_time=1.5 * PACE,
        )
        self.play(m.FadeIn(square_a), m.Write(la), run_time=1.2 * PACE)
        self.play(m.FadeIn(square_b), m.Write(lb), run_time=1.2 * PACE)
        self.play(m.FadeIn(square_c), m.Write(lc), run_time=1.2 * PACE)
        self.wait(1 * PACE)
        equation = m.MathTex("a^2+b^2=c^2", font_size=42).move_to([3.4, 1.0, 0])
        numbers = m.MathTex(f"{a:g}^2+3^2={a * a + 9:g}", font_size=36).move_to(
            [3.4, -0.15, 0]
        )
        result = m.Text(f"빗변의 길이 c ≈ {c:.2f}", font_size=26).move_to(
            [3.4, -1.35, 0]
        )
        next_caption = m.Text(
            "두 작은 정사각형의 넓이 합은 큰 정사각형의 넓이와 같습니다", font_size=24
        ).to_edge(m.DOWN)
        self.play(
            m.Write(equation), m.Transform(caption, next_caption), run_time=1.5 * PACE
        )
        self.play(m.Write(numbers), m.FadeIn(result), run_time=1.5 * PACE)
        self.wait(3 * PACE)

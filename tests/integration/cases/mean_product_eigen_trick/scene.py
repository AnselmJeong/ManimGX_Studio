import math

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Quick eigenvalue trick: mean and product").to_edge(
            m.UP, buff=0.3
        )
        self.play(m.Write(title))

        mat = (
            m.MathTex("A = \\begin{bmatrix} 8 & 4 \\\\ 1 & 6 \\end{bmatrix}")
            .scale(0.95)
            .move_to(m.UP * 1.5 + m.LEFT * 3.5)
        )
        self.play(m.Write(mat))

        line1 = (
            m.MathTex("m = \\tfrac{\\mathrm{tr}\\,A}{2} = 7", color=m.YELLOW)
            .scale(0.85)
            .move_to(m.UP * 1.5 + m.RIGHT * 1.5)
        )
        line2 = (
            m.MathTex("p = \\det A = 44", color=m.GREEN)
            .scale(0.85)
            .move_to(m.UP * 0.7 + m.RIGHT * 1.5)
        )
        line3 = (
            m.MathTex("\\lambda = m \\pm \\sqrt{m^2 - p}", color=m.BLUE)
            .scale(0.85)
            .move_to(m.DOWN * 0.1 + m.RIGHT * 1.5)
        )
        line4 = (
            m.MathTex("\\lambda = 7 \\pm \\sqrt{5}", color=m.RED)
            .scale(0.95)
            .move_to(m.DOWN * 1.0 + m.RIGHT * 1.5)
        )
        for line in [line1, line2, line3, line4]:
            self.play(m.Write(line), run_time=0.6)

        number = m.NumberLine(
            x_range=[0, 14, 2], length=5.0, include_numbers=True
        ).move_to(m.DOWN * 2.5)
        m_dot = m.Dot(number.n2p(7), color=m.YELLOW, radius=0.1)
        l1 = m.Dot(number.n2p(7 + math.sqrt(5)), color=m.RED, radius=0.1)
        l2 = m.Dot(number.n2p(7 - math.sqrt(5)), color=m.RED, radius=0.1)
        m_lab = m.MathTex("m", color=m.YELLOW).scale(0.7).next_to(m_dot, m.UP, buff=0.1)
        self.play(m.Create(number), m.FadeIn(m_dot), m.Write(m_lab))
        self.play(m.FadeIn(l1), m.FadeIn(l2))
        self.wait(1.5)

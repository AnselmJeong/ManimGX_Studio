import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Finding eigenvalues: ", "$\\det(A - \\lambda I) = 0$").to_edge(
            m.UP, buff=0.5
        )
        title[1].set_color(m.YELLOW)
        self.play(m.Write(title))

        A = (
            m.MathTex(
                "A",
                "=",
                "\\begin{pmatrix} 3 & 1 \\\\ 0 & 2 \\end{pmatrix}",
            )
            .scale(1.1)
            .shift(m.UP * 1.2)
        )
        self.play(m.Write(A))

        step1 = (
            m.MathTex(
                "A - \\lambda I",
                "=",
                "\\begin{pmatrix} 3-\\lambda & 1 \\\\ 0 & 2-\\lambda \\end{pmatrix}",
            )
            .scale(1.0)
            .next_to(A, m.DOWN, buff=0.6)
        )
        self.play(m.Write(step1))
        self.wait(0.6)

        step2 = (
            m.MathTex(
                "(3-\\lambda)(2-\\lambda) - 0 \\cdot 1 = 0",
            )
            .scale(1.0)
            .next_to(step1, m.DOWN, buff=0.5)
        )
        self.play(m.Write(step2))
        self.wait(0.6)

        solution = (
            m.MathTex(
                "\\lambda_1 = 3",
                "\\quad",
                "\\lambda_2 = 2",
            )
            .scale(1.3)
            .next_to(step2, m.DOWN, buff=0.6)
        )
        solution[0].set_color(m.YELLOW)
        solution[2].set_color(m.YELLOW)
        self.play(m.Write(solution))
        self.wait(2.0)

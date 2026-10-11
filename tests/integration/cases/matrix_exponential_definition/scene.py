import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Matrix exponential: series definition").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        defn = (
            m.MathTex(
                "\\exp(X) \\;=\\; I \\;+\\; X \\;+\\; \\tfrac{1}{2!} X^2 \\;+\\;"
                " \\tfrac{1}{3!} X^3 \\;+\\; \\cdots",
            )
            .scale(0.95)
            .move_to(m.UP * 1.4)
        )
        self.play(m.Write(defn))

        x_matrix = (
            m.MathTex(
                "X = \\begin{bmatrix} 0 & -1 \\\\ 1 & 0 \\end{bmatrix}", color=m.YELLOW
            )
            .scale(0.95)
            .move_to(m.LEFT * 3.2 + m.DOWN * 0.5)
        )
        x2 = m.MathTex("X^2 = -I", color=m.BLUE).scale(0.95).move_to(m.DOWN * 0.5)
        x3 = (
            m.MathTex("X^3 = -X", color=m.GREEN)
            .scale(0.95)
            .move_to(m.RIGHT * 3.2 + m.DOWN * 0.5)
        )
        self.play(m.Write(x_matrix))
        self.play(m.Write(x2), m.Write(x3))

        result = (
            m.MathTex(
                "\\exp(X) = R_1 = \\begin{bmatrix} \\cos 1 & -\\sin 1 \\\\ \\sin 1 &"
                " \\cos 1 \\end{bmatrix}",
                color=m.YELLOW,
            )
            .scale(0.85)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(result))
        self.wait(2.0)

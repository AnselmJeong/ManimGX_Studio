import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.MathTex(
            "\\frac{d}{dt}|\\psi\\rangle = -\\frac{i}{\\hbar} H |\\psi\\rangle"
        ).to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        psi = (
            m.MathTex(
                "|\\psi(t)\\rangle = e^{-iHt/\\hbar}\\, |\\psi(0)\\rangle",
                color=m.YELLOW,
            )
            .scale(1.0)
            .move_to(m.UP * 0.7)
        )
        self.play(m.Write(psi))

        H = (
            m.MathTex(
                "H = \\begin{bmatrix} E_0 & V \\\\ V^* & E_1 \\end{bmatrix}",
                color=m.BLUE,
            )
            .scale(0.9)
            .move_to(m.LEFT * 2.7 + m.DOWN * 1.0)
        )
        sup = (
            m.MathTex(
                "|\\psi\\rangle = c_0 |0\\rangle + c_1 |1\\rangle",
                color=m.GREEN,
            )
            .scale(0.9)
            .move_to(m.RIGHT * 2.0 + m.DOWN * 1.0)
        )
        self.play(m.Write(H), m.Write(sup))

        note = (
            m.Tex("\\emph{superposition + unitary evolution}", color=m.WHITE)
            .scale(0.75)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(note))
        self.wait(2.0)

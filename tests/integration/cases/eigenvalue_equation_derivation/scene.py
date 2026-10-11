import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Deriving the eigenvalue equation").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        steps = [
            ("A\\mathbf v = \\lambda \\mathbf v", m.WHITE),
            ("A\\mathbf v = \\lambda I \\mathbf v", m.YELLOW),
            ("A\\mathbf v - \\lambda I \\mathbf v = \\mathbf 0", m.BLUE),
            ("(A - \\lambda I)\\mathbf v = \\mathbf 0", m.GREEN),
            ("\\det(A - \\lambda I) = 0", m.RED),
        ]
        group = m.VGroup()
        for s, col in steps:
            group.add(m.MathTex(s, color=col).scale(0.95))
        group.arrange(m.DOWN, buff=0.45).move_to(m.DOWN * 0.3)

        for line in group:
            self.play(m.Write(line), run_time=0.7)
            self.wait(0.2)
        self.wait(1.5)

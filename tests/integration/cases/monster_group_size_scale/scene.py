import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("The Monster Group is enormous").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        entries = [
            ("C_2", "2", m.BLUE),
            ("S_5", "120", m.GREEN),
            ("A_{10}", "1{,}814{,}400", m.YELLOW),
            ("\\text{Monster}", "8 \\times 10^{53}", m.RED),
        ]
        for i, (name, size, color) in enumerate(entries):
            y = 1.8 - i * 1.2
            label = m.MathTex(name, color=color).scale(0.95).move_to([-4.0, y, 0])
            value = m.MathTex(size, color=color).scale(0.95).move_to([3.0, y, 0])
            self.play(m.Write(label), m.Write(value), run_time=0.7)
        self.wait(2.0)

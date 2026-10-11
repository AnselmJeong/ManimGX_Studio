import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Pauli matrices: spin eigenstates").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        entries = [
            (
                "\\sigma_x = \\begin{bmatrix} 0 & 1 \\\\ 1 & 0 \\end{bmatrix}",
                "\\pm 1",
                m.BLUE,
            ),
            (
                "\\sigma_y = \\begin{bmatrix} 0 & -i \\\\ i & 0 \\end{bmatrix}",
                "\\pm 1",
                m.GREEN,
            ),
            (
                "\\sigma_z = \\begin{bmatrix} 1 & 0 \\\\ 0 & -1 \\end{bmatrix}",
                "\\pm 1",
                m.YELLOW,
            ),
        ]
        rows = m.VGroup()
        for mat, ev, col in entries:
            mat_obj = m.MathTex(mat, color=col).scale(0.85)
            ev_obj = m.MathTex("\\lambda = " + ev, color=col).scale(0.85)
            row = m.VGroup(mat_obj, ev_obj).arrange(m.RIGHT, buff=1.2)
            rows.add(row)
        rows.arrange(m.DOWN, buff=0.55).move_to(m.DOWN * 0.2)

        for row in rows:
            self.play(m.Write(row), run_time=0.7)

        note = (
            m.MathTex("\\sigma_i^2 = I,\\quad \\det \\sigma_i = -1", color=m.RED)
            .scale(0.85)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(note))
        self.wait(2.0)

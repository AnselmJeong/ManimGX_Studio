import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("$\\exp(t J)$ where $J$ is 90$^\\circ$ rotation").to_edge(
            m.UP, buff=0.3
        )
        self.play(m.Write(title))

        terms = [
            "I",
            "+\\; t\\,J",
            "+\\; \\tfrac{t^2}{2!} J^2",
            "+\\; \\tfrac{t^3}{3!} J^3",
            "+\\; \\tfrac{t^4}{4!} J^4",
            "+\\cdots",
        ]
        rotations = [
            "I",
            "J",
            "-I",
            "-J",
            "I",
            "\\cdots",
        ]
        colors = [m.WHITE, m.RED, m.YELLOW, m.GREEN, m.BLUE, m.GREY_B]

        rows = m.VGroup()
        for i, (t_str, rot, col) in enumerate(zip(terms, rotations, colors)):
            term = m.MathTex(t_str, color=col).scale(0.9)
            eq = m.MathTex("\\Rightarrow", color=col).scale(0.9)
            cycle = m.MathTex(f"J^{i} = {rot}", color=col).scale(0.9)
            row = m.VGroup(term, eq, cycle).arrange(m.RIGHT, buff=0.3)
            rows.add(row)
        rows.arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.25).move_to(m.DOWN * 0.3)

        for row in rows:
            self.play(m.Write(row), run_time=0.45)

        bottom = (
            m.MathTex("\\exp(t J) = \\cos(t)\\,I + \\sin(t)\\,J", color=m.YELLOW)
            .scale(0.95)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(bottom))
        self.wait(2.0)

import manimgx as m

ENTRIES = [
    ("Real", "a", m.WHITE, "1D"),
    ("Complex", "a + b\\,i", m.BLUE, "2D"),
    ("Vec3", "(a,\\ b,\\ c)", m.GREEN, "3D"),
    ("Quaternion", "a + b\\,i + c\\,j + d\\,k", m.YELLOW, "4D"),
]
X_POS = [-5.0, -1.7, 1.5, 5.0]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Number systems by dimension").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        for x, (name, formula, color, dim) in zip(X_POS, ENTRIES):
            grp = (
                m.VGroup(
                    m.Tex(name, color=color).scale(0.9),
                    m.MathTex(formula).scale(0.85),
                    m.Tex(dim, color=color).scale(0.7),
                )
                .arrange(m.DOWN, buff=0.4)
                .move_to([x, 0.2, 0])
            )
            self.play(m.Write(grp), run_time=0.6)
            self.wait(0.2)

        rules = (
            m.MathTex(
                "i^2 = j^2 = k^2 = ijk = -1",
                color=m.YELLOW,
            )
            .scale(0.95)
            .to_edge(m.DOWN, buff=0.7)
        )
        self.play(m.Write(rules))
        self.wait(2.0)

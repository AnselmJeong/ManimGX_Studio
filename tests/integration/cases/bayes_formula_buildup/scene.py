import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Building Bayes' rule").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        eq1 = m.MathTex("P(H | E)").scale(1.6)
        self.play(m.Write(eq1))
        self.wait(0.6)

        eq2 = m.MathTex(
            "P(H | E) = \\frac{P(E | H) \\cdot P(H)}{P(E)}",
        ).scale(1.4)
        self.play(m.Transform(eq1, eq2))
        self.wait(0.6)

        legend = (
            m.VGroup(
                m.Tex("$P(H|E)$: posterior", color=m.YELLOW).scale(0.65),
                m.Tex("$P(E|H)$: likelihood", color=m.GREEN).scale(0.65),
                m.Tex("$P(H)$: prior", color=m.BLUE).scale(0.65),
                m.Tex("$P(E)$: marginal evidence", color=m.RED).scale(0.65),
            )
            .arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.18)
            .to_edge(m.DOWN, buff=0.7)
        )
        self.play(m.Write(legend))
        self.wait(2.0)

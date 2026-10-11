import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Bayes' rule").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        bayes = m.MathTex(
            "P(H|E) = \\frac{P(E|H) \\cdot P(H)}{P(E)}",
        ).scale(1.4)
        bayes.set_color(m.YELLOW)
        self.play(m.Write(bayes))
        self.wait(0.5)

        legend = (
            m.VGroup(
                m.Tex("$H$: hypothesis", color=m.BLUE).scale(0.75),
                m.Tex("$E$: evidence", color=m.RED).scale(0.75),
            )
            .arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.3)
            .to_edge(m.DOWN, buff=0.7)
        )
        self.play(m.Write(legend))
        self.wait(2.0)

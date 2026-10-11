import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Medical test paradox").to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        rule = (
            m.MathTex(
                "P(\\text{sick} | +) = \\frac{P(+ | \\text{sick}) \\cdot"
                " P(\\text{sick})}{P(+)}",
            )
            .scale(0.95)
            .shift(m.UP * 1.4)
        )
        self.play(m.Write(rule))

        numbers = (
            m.MathTex(
                "= \\frac{0.99 \\cdot 0.01}{0.99 \\cdot 0.01 + 0.05 \\cdot 0.99}",
            )
            .scale(0.85)
            .shift(m.DOWN * 0.3)
        )
        self.play(m.Write(numbers))

        answer = (
            m.MathTex(
                "\\approx 0.167",
                color=m.YELLOW,
            )
            .scale(1.2)
            .shift(m.DOWN * 1.8)
        )
        self.play(m.Write(answer))

        caption = (
            m.Tex(
                "Only $\\sim$17\\% of positive tests are truly sick!",
                color=m.RED,
            )
            .scale(0.75)
            .to_edge(m.DOWN, buff=0.5)
        )
        self.play(m.Write(caption))
        self.wait(2.0)

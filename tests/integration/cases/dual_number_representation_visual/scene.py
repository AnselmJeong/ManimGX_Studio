import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Number ", "$e$", ": two views").to_edge(m.UP, buff=0.4)
        title[1].set_color(m.YELLOW)
        self.play(m.Write(title))

        decimal = (
            m.MathTex(
                "e = 2.71828\\ldots",
            )
            .scale(1.2)
            .shift(m.LEFT * 3.5 + m.UP * 0.6)
        )
        decimal_label = m.Tex("decimal").scale(0.6).next_to(decimal, m.DOWN, buff=0.4)
        self.play(m.Write(decimal), m.Write(decimal_label))

        limit = (
            m.MathTex(
                "e = \\lim_{n \\to \\infty}\\left(1 + \\tfrac{1}{n}\\right)^n",
            )
            .scale(0.95)
            .shift(m.RIGHT * 3 + m.UP * 0.6)
        )
        limit_label = m.Tex("limit").scale(0.6).next_to(limit, m.DOWN, buff=0.4)
        self.play(m.Write(limit), m.Write(limit_label))

        approx = (
            m.MathTex(
                "n = 1,\\ (1 + 1)^1 = 2",
            )
            .scale(0.8)
            .move_to(m.DOWN * 1.6)
        )
        self.play(m.Write(approx))
        for n in [5, 10, 100, 1000]:
            val = (1 + 1.0 / n) ** n
            new = (
                m.MathTex(
                    f"n = {n},\\ \\left(1 + \\tfrac{{1}}{{{n}}}\\right)^{{{n}}}"
                    f" \\approx {val:.4f}",
                )
                .scale(0.8)
                .move_to(m.DOWN * 1.6)
            )
            self.play(m.Transform(approx, new), run_time=0.7)
            self.wait(0.35)
        self.wait(1.5)

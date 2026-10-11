import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.MathTex(
                "\\sum_{n=1}^{\\infty} \\frac{1}{n^2} = \\frac{\\pi^2}{6}",
            )
            .scale(1.0)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        ax = m.Axes(
            x_range=[0, 12, 1],
            y_range=[0, 1.2, 0.5],
            x_length=10,
            y_length=4,
        ).shift(m.DOWN * 0.3)
        self.add(ax)

        bars = m.VGroup()
        for n in range(1, 11):
            h = 1.0 / (n * n)
            bar = m.Rectangle(
                width=0.5,
                height=h * 3.2,
                color=m.YELLOW,
                fill_color=m.YELLOW,
                fill_opacity=0.65,
                stroke_width=1,
            ).move_to(ax.c2p(n, h / 2))
            bars.add(bar)
        self.play(
            m.LaggedStart(*[m.FadeIn(b) for b in bars], lag_ratio=0.1), run_time=2.5
        )

        partial = sum(1.0 / (n * n) for n in range(1, 11))
        partial_label = (
            m.MathTex(
                f"\\sum_{{n=1}}^{{10}} \\tfrac{{1}}{{n^2}} \\approx {partial:.4f}",
            )
            .scale(0.7)
            .to_edge(m.DOWN, buff=0.45)
        )
        self.play(m.Write(partial_label))
        self.wait(2.0)

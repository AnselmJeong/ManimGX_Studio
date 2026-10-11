import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Exponential growth: $f(t) = 2^t$").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        ax = m.Axes(
            x_range=[0, 8, 1],
            y_range=[0, 130, 25],
            x_length=10,
            y_length=5,
        ).shift(m.DOWN * 0.3)
        self.add(ax)

        curve = ax.plot(lambda t: 2**t, color=m.YELLOW, x_range=[0, 7])
        self.play(m.Create(curve), run_time=2.5)

        dots = m.VGroup(
            *[m.Dot(ax.c2p(t, 2**t), color=m.RED, radius=0.08) for t in range(1, 8)]
        )
        self.play(m.FadeIn(dots))
        self.wait(2.0)

import manimgx as m

LIMIT = 1.0
NUM_DOTS = 12


class TeacherScene(m.Scene):
    def construct(self) -> None:
        line = m.NumberLine(
            x_range=[0, 2.4, 0.5],
            length=11,
            include_numbers=True,
        )
        self.play(m.Create(line), run_time=0.8)

        positions = [LIMIT + 1.0 / (n + 1) for n in range(NUM_DOTS)]
        dots = m.VGroup(
            *[m.Dot(line.n2p(p), color=m.YELLOW, radius=0.09) for p in positions]
        )
        self.play(
            m.LaggedStart(*[m.FadeIn(d, scale=0.4) for d in dots], lag_ratio=0.08),
            run_time=1.2,
        )
        self.wait(0.3)

        limit_pt = line.n2p(LIMIT)
        r = m.ValueTracker(1.3)
        circle = m.always_redraw(
            lambda: m.Circle(
                radius=r.get_value(),
                color=m.BLUE,
                stroke_width=3,
            ).move_to(limit_pt)
        )
        self.add(circle)
        self.wait(0.4)

        caption = (
            m.Tex(
                "All but finitely many dots fit inside any neighborhood of ",
                "$1$",
            )
            .scale(0.7)
            .to_edge(m.UP, buff=0.6)
        )
        caption[1].set_color(m.YELLOW)
        self.play(m.Write(caption))

        self.play(r.animate.set_value(0.04), run_time=4.5, rate_func=m.smooth)
        self.wait(1.5)

import manimgx as m

RADII = [3.0, 2.4, 1.8, 1.2, 0.6]
COLORS = [m.WHITE, m.BLUE, m.GREEN, m.YELLOW, m.RED]
SCORES = [1, 5, 10, 25, 50]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Nested target rings").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        rings = m.VGroup(
            *[
                m.Circle(
                    radius=r,
                    color=c,
                    fill_color=c,
                    fill_opacity=0.35,
                    stroke_width=2.5,
                )
                for r, c in zip(RADII, COLORS)
            ]
        )
        self.play(
            m.LaggedStart(*[m.Create(r) for r in rings], lag_ratio=0.15), run_time=2.5
        )

        for r, c, s in zip(RADII, COLORS, SCORES):
            label = m.MathTex(f"{s}", color=c).scale(0.55).move_to([0, r - 0.15, 0])
            self.play(m.Write(label), run_time=0.2)
        self.wait(2.0)

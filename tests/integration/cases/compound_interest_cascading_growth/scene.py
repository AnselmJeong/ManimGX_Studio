import manimgx as m

INITIAL = 100
RATE = 0.25
STEPS = 6


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex(
            "Compound interest: ",
            "$P(1 + r)^n$",
        ).to_edge(m.UP, buff=0.4)
        title[1].set_color(m.YELLOW)
        self.play(m.Write(title))

        BASE_Y = -2.0
        for k in range(STEPS):
            val = INITIAL * (1 + RATE) ** k
            height = (val / INITIAL) * 0.6
            bar = m.Rectangle(
                width=0.85,
                height=height,
                color=m.YELLOW,
                fill_color=m.YELLOW,
                fill_opacity=0.6,
                stroke_width=1.5,
            ).move_to([-4.5 + k * 1.6, BASE_Y + height / 2, 0])
            amount = (
                m.Integer(int(val), color=m.YELLOW)
                .scale(0.55)
                .next_to(bar, m.UP, buff=0.12)
            )
            n_label = m.MathTex(f"n={k}").scale(0.5).next_to(bar, m.DOWN, buff=0.15)
            self.play(m.FadeIn(bar), m.Write(amount), m.Write(n_label), run_time=0.5)
        self.wait(2.0)

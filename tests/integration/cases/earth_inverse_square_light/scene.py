import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Inverse-square law: intensity $\\propto 1/r^2$",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        sun = m.Dot(m.LEFT * 5, color=m.YELLOW, radius=0.2)
        sun_label = (
            m.Tex("source", color=m.YELLOW).scale(0.6).next_to(sun, m.DOWN, buff=0.2)
        )
        self.play(m.FadeIn(sun), m.Write(sun_label))

        for r in [1.5, 3.0, 4.5]:
            circle = m.Circle(
                radius=r,
                color=m.WHITE,
                stroke_width=1.5,
                stroke_opacity=0.55,
            ).move_to(m.LEFT * 5)
            r_label = (
                m.MathTex(f"r={r:g}", color=m.WHITE)
                .scale(0.55)
                .move_to(
                    m.LEFT * 5 + m.RIGHT * r + m.UP * 0.25,
                )
            )
            intensity = 1.0 / (r * r)
            int_label = (
                m.MathTex(
                    f"I = {intensity:.2f}",
                    color=m.RED,
                )
                .scale(0.55)
                .next_to(r_label, m.DOWN, buff=0.1)
            )
            self.play(
                m.Create(circle),
                m.Write(r_label),
                m.Write(int_label),
                run_time=0.8,
            )
        self.wait(2.0)

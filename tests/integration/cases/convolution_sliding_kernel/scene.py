import manimgx as m

SIGNAL = [0, 0, 0, 1, 2, 3, 2, 1, 0, 0, 0]
KERNEL = [0.2, 0.6, 0.2]
CELL = 0.55


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Convolution: kernel slides over signal")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        sig_grp = m.VGroup()
        for i, v in enumerate(SIGNAL):
            sig_grp.add(
                m.VGroup(
                    m.Square(side_length=CELL, color=m.WHITE, stroke_width=1.5),
                    m.MathTex(str(v)).scale(0.55),
                ).move_to([(i - 5) * CELL + 0.1, 1.2, 0]),
            )
        self.play(m.Create(sig_grp))

        ker_grp = m.VGroup()
        for j, k in enumerate(KERNEL):
            ker_grp.add(
                m.VGroup(
                    m.Square(
                        side_length=CELL,
                        color=m.YELLOW,
                        fill_color=m.YELLOW,
                        fill_opacity=0.35,
                        stroke_width=1.5,
                    ),
                    m.MathTex(f"{k}").scale(0.5),
                ).move_to([(j - 1) * CELL, -1.4, 0]),
            )
        self.play(m.FadeIn(ker_grp))
        self.wait(0.4)

        for shift_steps in range(-3, 4):
            target_x = shift_steps * CELL
            current_center = ker_grp.get_center()[0]
            self.play(
                ker_grp.animate.shift(m.RIGHT * (target_x - current_center)),
                run_time=0.4,
            )
        self.wait(1.5)

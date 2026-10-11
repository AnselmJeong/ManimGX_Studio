import manimgx as m


class TeacherScene(m.MovingCameraScene):
    def construct(self) -> None:
        line = m.NumberLine(
            x_range=[-2, 4, 1],
            length=16,
            include_numbers=True,
        )
        one_dot = m.Dot(line.n2p(1.0), color=m.YELLOW, radius=0.12)
        self.add(line, one_dot)
        self.wait(0.4)

        for k in range(1, 5):
            eps = 10 ** (-k)
            level_scale = 10 ** (k - 1)

            left_pt = line.n2p(1.0 - eps)
            right_pt = line.n2p(1.0 + eps)
            left_dot = m.Dot(left_pt, color=m.BLUE, radius=0.06 / level_scale)
            right_dot = m.Dot(right_pt, color=m.BLUE, radius=0.06 / level_scale)
            left_label = (
                m.MathTex(f"1 - 10^{{-{k}}}")
                .scale(0.55 / level_scale)
                .next_to(
                    left_dot,
                    m.DOWN,
                    buff=0.1 / level_scale,
                )
            )
            right_label = (
                m.MathTex(f"1 + 10^{{-{k}}}")
                .scale(0.55 / level_scale)
                .next_to(
                    right_dot,
                    m.DOWN,
                    buff=0.1 / level_scale,
                )
            )

            self.play(
                m.FadeIn(left_dot),
                m.FadeIn(right_dot),
                m.Write(left_label),
                m.Write(right_label),
                run_time=0.6,
            )

            self.play(
                self.camera.frame.animate.set(width=8.0 * eps).move_to(line.n2p(1.0)),
                run_time=1.4,
            )
            self.wait(0.3)

        self.wait(1.5)

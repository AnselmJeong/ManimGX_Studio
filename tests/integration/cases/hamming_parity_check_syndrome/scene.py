import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Hamming(7,4): parity check syndromes")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        bits = m.VGroup()
        for i in range(7):
            circle = m.Circle(radius=0.32, color=m.WHITE, stroke_width=2).move_to(
                [-3 + i, 0, 0]
            )
            label = m.MathTex(f"b_{i + 1}").scale(0.55).move_to(circle.get_center())
            bits.add(m.VGroup(circle, label))
        self.add(bits)

        checks = [
            ("$p_1$: 1,3,5,7", [0, 2, 4, 6], m.RED),
            ("$p_2$: 2,3,6,7", [1, 2, 5, 6], m.GREEN),
            ("$p_4$: 4,5,6,7", [3, 4, 5, 6], m.BLUE),
        ]
        for i, (txt, idxs, color) in enumerate(checks):
            label = (
                m.Tex(txt, color=color)
                .scale(0.55)
                .shift(
                    m.LEFT * 5 + m.DOWN * (1 + i * 0.5),
                )
            )
            self.play(m.Write(label))
            self.play(
                *[
                    bits[idx][0].animate.set_color(color).set_stroke(width=3)
                    for idx in idxs
                ],
                run_time=0.5,
            )
            self.play(
                *[
                    bits[idx][0].animate.set_color(m.WHITE).set_stroke(width=2)
                    for idx in idxs
                ],
                run_time=0.5,
            )
        self.wait(1.5)

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Each parity bit covers a power-of-two subset",
            )
            .scale(0.75)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        entries = m.VGroup()
        for i in range(1, 9):
            x = -3.5 + (i - 1) * 1.0
            num_label = m.MathTex(f"{i}").scale(0.85).move_to([x, 1.4, 0])
            binary = m.MathTex(f"{i:03b}").scale(0.7).move_to([x, 0.6, 0])
            entries.add(num_label, binary)
        self.play(m.Write(entries))

        legend = (
            m.VGroup(
                m.Tex(
                    "Position $i$ in binary = which parity bits check it",
                    color=m.YELLOW,
                ).scale(0.6),
                m.Tex(
                    "Parity bit $p_{2^k}$ checks positions with bit $k$ set",
                    color=m.WHITE,
                ).scale(0.55),
            )
            .arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.3)
            .to_edge(m.DOWN, buff=0.6)
        )
        self.play(m.Write(legend))
        self.wait(2.0)

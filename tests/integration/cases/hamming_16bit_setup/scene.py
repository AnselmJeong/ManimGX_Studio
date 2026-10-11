import manimgx as m

PARITY_POSITIONS = {0, 1, 2, 4, 8}


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Hamming(16, 11) layout").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        cells = m.VGroup()
        for i in range(4):
            for j in range(4):
                idx = i * 4 + j
                color = m.RED if idx in PARITY_POSITIONS else m.WHITE
                cell = m.VGroup(
                    m.Square(
                        side_length=0.85,
                        color=color,
                        stroke_width=2,
                        fill_color=color,
                        fill_opacity=0.2,
                    ),
                    m.MathTex(str(idx)).scale(0.65).set_color(color),
                ).move_to([(j - 1.5) * 0.95, (1.5 - i) * 0.95, 0])
                cells.add(cell)
        self.play(m.Create(cells))

        caption = (
            m.Tex(
                "Parity bits at powers of 2: 0, 1, 2, 4, 8",
            )
            .scale(0.65)
            .to_edge(m.DOWN, buff=0.5)
        )
        self.play(m.Write(caption))
        self.wait(2.0)

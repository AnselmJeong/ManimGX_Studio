import manimgx as m

ROWS = 5
SPACING = 0.22
DOT_RADIUS = 0.08


class TeacherScene(m.Scene):
    def construct(self) -> None:
        equation = m.MathTex(
            "1 + 2 + 4 + \\cdots + 2^n",
            "=",
            "2^{n+1} - 1",
        ).to_edge(m.UP)
        self.play(m.Write(equation))

        colors = [m.YELLOW, m.GREEN, m.BLUE, m.PURPLE, m.RED]
        total_count = 2**ROWS - 1
        total_width = (total_count - 1) * SPACING

        positions: list[tuple[int, float]] = []
        for k in range(ROWS):
            count = 2**k
            start_idx = sum(2**j for j in range(k))
            for i in range(count):
                positions.append((k, (start_idx + i) * SPACING - total_width / 2))

        all_dots = m.VGroup(
            *[
                m.Dot(radius=DOT_RADIUS, color=colors[k]).move_to([x, -0.4, 0])
                for k, x in positions
            ]
        )

        visible = 0
        brace = None
        label = None
        for k in range(ROWS):
            count = 2**k
            new_dots = all_dots[visible : visible + count]
            visible += count

            self.play(
                m.LaggedStart(
                    *[m.FadeIn(d, scale=0.3) for d in new_dots],
                    lag_ratio=0.04,
                ),
                run_time=0.5,
            )

            visible_dots = all_dots[:visible]
            running_sum = 2 ** (k + 1) - 1
            new_brace = m.Brace(visible_dots, m.DOWN, buff=0.15)
            new_label = m.MathTex(str(running_sum)).next_to(new_brace, m.DOWN, buff=0.1)

            if brace is None or label is None:
                brace, label = new_brace, new_label
                self.play(m.GrowFromCenter(brace), m.Write(label))
            else:
                self.play(
                    m.Transform(brace, new_brace),
                    m.Transform(label, new_label),
                )
            self.wait(0.3)

        self.wait(1.2)

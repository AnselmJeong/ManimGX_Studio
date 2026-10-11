import numpy as np

import manimgx as m

N = 6


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Dynamic programming on a grid").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        rng = np.random.default_rng(42)
        values = rng.integers(1, 10, (N, N))

        cells = []
        for i in range(N):
            row = []
            for j in range(N):
                cell_grp = m.VGroup(
                    m.Square(side_length=0.65, color=m.WHITE, stroke_width=1.5),
                    m.Integer(int(values[i, j])).scale(0.6),
                ).move_to([(j - N / 2 + 0.5) * 0.7, (N / 2 - 0.5 - i) * 0.7, 0])
                row.append(cell_grp)
            cells.append(row)
        all_cells = m.VGroup(*[c for row in cells for c in row])
        self.play(m.FadeIn(all_cells))

        self.play(
            *[
                cells[i][i][0].animate.set_color(m.YELLOW).set_stroke(width=4)
                for i in range(N)
            ],
            run_time=1.5,
        )

        sum_val = sum(int(values[i, i]) for i in range(N))
        sum_label = m.MathTex(
            f"\\text{{path sum}} = {sum_val}",
            color=m.YELLOW,
        ).to_edge(m.DOWN, buff=0.5)
        self.play(m.Write(sum_label))
        self.wait(2.0)

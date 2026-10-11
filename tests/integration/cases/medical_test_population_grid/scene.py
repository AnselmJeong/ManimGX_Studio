import numpy as np

import manimgx as m

N_COLS = 50
N_ROWS = 20
CELL = 0.13


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Medical test on 1000 people").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        grid = m.VGroup()
        x_off = -3.5
        y_off = -2.0
        for i in range(N_ROWS):
            for j in range(N_COLS):
                grid.add(
                    m.Square(
                        side_length=CELL,
                        color=m.GREY,
                        fill_color=m.GREY,
                        fill_opacity=0.5,
                        stroke_width=0,
                    ).move_to([x_off + j * CELL * 1.4, y_off + i * CELL * 1.4, 0]),
                )
        self.add(grid)

        rng = np.random.default_rng(42)
        sick_idx = rng.choice(N_COLS * N_ROWS, 10, replace=False).tolist()
        self.play(
            *[
                grid[i].animate.set_color(m.RED).set_fill(m.RED, opacity=1.0)
                for i in sick_idx
            ],
            run_time=1.0,
        )

        all_idx = set(range(N_COLS * N_ROWS))
        healthy = sorted(all_idx - set(sick_idx))
        false_pos = rng.choice(healthy, 90, replace=False).tolist()
        self.play(
            *[
                grid[i].animate.set_color(m.ORANGE).set_fill(m.ORANGE, opacity=0.7)
                for i in false_pos
            ],
            run_time=1.5,
        )

        caption = (
            m.Tex(
                "Red = sick (10); Orange = false positive (90)",
            )
            .scale(0.7)
            .to_edge(m.DOWN, buff=0.4)
        )
        self.play(m.Write(caption))
        self.wait(2.0)

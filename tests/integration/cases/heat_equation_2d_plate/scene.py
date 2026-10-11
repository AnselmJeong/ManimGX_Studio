import math

import manimgx as m

GRID = 10
CELL = 0.5


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("2D heat diffusion on a plate").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        t = m.ValueTracker(0.0)

        def temp_at(i: int, j: int, time: float) -> float:
            x = (i - GRID / 2 + 0.5) * CELL
            y = (j - GRID / 2 + 0.5) * CELL
            sigma_sq = 0.3 + time * 0.4
            return math.exp(-(x * x + y * y) / sigma_sq)

        def make_cells() -> m.VGroup:
            grp = m.VGroup()
            time = t.get_value()
            for i in range(GRID):
                for j in range(GRID):
                    temp = temp_at(i, j, time)
                    intensity = max(0, min(255, int(255 * temp)))
                    color = f"#{intensity:02X}00{255 - intensity:02X}"
                    grp.add(
                        m.Square(
                            side_length=CELL,
                            color=color,
                            fill_color=color,
                            fill_opacity=0.9,
                            stroke_width=0,
                        ).move_to(
                            [
                                (i - GRID / 2 + 0.5) * CELL,
                                (j - GRID / 2 + 0.5) * CELL,
                                0,
                            ]
                        ),
                    )
            return grp

        self.add(m.always_redraw(make_cells))
        self.play(t.animate.set_value(2.5), run_time=4.5)
        self.wait(1.0)

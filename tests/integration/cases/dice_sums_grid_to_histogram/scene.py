"""Show why the sum of two dice is more likely to be 7 than 12 — by laying out the 36 outcomes as a grid and rearranging into a histogram."""

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "Tests arrange_in_grid + sum-based color coding + MoveToTarget rearrangement "
    "from 6x6 grid into 11 histogram columns (sums 2..12)."
)


class TeacherScene(m.Scene):
    def construct(self):
        # Colors by sum (2..12): triangular distribution peaks at 7.
        sum_colors = {
            2: m.BLUE_E,
            3: m.BLUE_D,
            4: m.BLUE_C,
            5: m.TEAL_D,
            6: m.TEAL_C,
            7: m.YELLOW,
            8: m.GOLD_C,
            9: m.ORANGE,
            10: m.RED_C,
            11: m.RED_D,
            12: m.RED_E,
        }

        cell_side = 0.5

        # Build the 6x6 grid. Cell (i, j) = die1=i+1, die2=j+1, sum=i+j+2.
        cells: list[m.VGroup] = []
        for i in range(6):
            for j in range(6):
                s = (i + 1) + (j + 1)
                sq = (
                    m.Square(
                        side_length=cell_side,
                        color=sum_colors[s],
                    )
                    .set_fill(sum_colors[s], opacity=0.75)
                    .set_stroke(m.WHITE, 1.2)
                )
                label = m.Integer(s, font_size=20).set_color(m.BLACK)
                grp = m.VGroup(sq, label)
                label.move_to(sq.get_center())
                cells.append(grp)

        grid = m.VGroup(*cells).arrange_in_grid(6, 6, buff=0.02)
        grid.shift(2.2 * m.LEFT + 0.4 * m.UP)

        # Axis labels for the grid.
        grid_title = m.Text("36 outcomes  (die 1, die 2)", font_size=24).next_to(
            grid, m.UP, buff=0.25
        )

        self.play(m.Write(grid_title), run_time=0.8)
        self.play(
            m.LaggedStart(
                *[m.FadeIn(c) for c in cells],
                lag_ratio=0.02,
            ),
            run_time=1.8,
        )
        self.wait(0.4)

        # Group cells by their sum, preserving grid order within each group.
        by_sum: dict[int, list[m.VGroup]] = {s: [] for s in range(2, 13)}
        for idx, cell in enumerate(cells):
            i, j = divmod(idx, 6)
            s = (i + 1) + (j + 1)
            by_sum[s].append(cell)

        # Histogram layout: 11 columns at evenly-spaced x positions along the bottom.
        column_spacing = 0.56
        base_y = -2.4
        base_x = -column_spacing * 5  # columns at -5..+5 offsets

        for col_idx, s in enumerate(range(2, 13)):
            stack = by_sum[s]
            x = base_x + col_idx * column_spacing
            for k, cell in enumerate(stack):
                target_pos = np.array([x, base_y + k * cell_side, 0.0])
                target = cell.generate_target()
                target.move_to(target_pos)

        # Axis for the histogram.
        hist_axis = m.Line(
            np.array([base_x - 0.35, base_y - cell_side / 2.0, 0.0]),
            np.array(
                [base_x + 10 * column_spacing + 0.35, base_y - cell_side / 2.0, 0.0]
            ),
            color=m.WHITE,
            stroke_width=2.0,
        )
        tick_labels = m.VGroup()
        for col_idx, s in enumerate(range(2, 13)):
            x = base_x + col_idx * column_spacing
            tick = m.Line(
                np.array([x, base_y - cell_side / 2.0, 0.0]),
                np.array([x, base_y - cell_side / 2.0 - 0.08, 0.0]),
                color=m.WHITE,
                stroke_width=2.0,
            )
            lbl = m.Integer(s, font_size=22).next_to(tick, m.DOWN, buff=0.08)
            tick_labels.add(tick, lbl)

        self.play(m.Create(hist_axis), m.FadeIn(tick_labels), run_time=0.9)

        # Slide every cell into its histogram slot.
        self.play(
            m.LaggedStart(
                *[m.MoveToTarget(cell) for cell in cells],
                lag_ratio=0.02,
            ),
            run_time=3.5,
        )

        # Emphasize the 7-column peak.
        seven_group = m.VGroup(*by_sum[7])
        peak_box = m.SurroundingRectangle(
            seven_group, color=m.YELLOW, buff=0.05, stroke_width=3.0
        )
        peak_label = m.Text("6 ways to make 7", font_size=24, color=m.YELLOW).next_to(
            peak_box, m.UP, buff=0.15
        )
        self.play(m.Create(peak_box), m.Write(peak_label), run_time=1.0)

        self.wait(0.5)

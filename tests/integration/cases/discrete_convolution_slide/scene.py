"""Show what convolving the sequences (1, 2, 3) and (4, 5, 6) looks like step by step."""

import manimgx as m

CELL = 1.0  # world-space width/height of each cell (one manimgx unit)
TOP_Y = 1.8
BOT_Y = 0.3
OUT_Y = -1.8


def _cell(value: int, color: str) -> m.VGroup:
    """A labeled square cell: filled square + integer label centered inside."""
    square = m.Square(side_length=CELL).set_stroke(m.WHITE, 2).set_fill(color, 0.35)
    label = m.MathTex(str(value), font_size=38)
    label.move_to(square.get_center())
    return m.VGroup(square, label)


class TeacherScene(m.Scene):
    def construct(self):
        # Top row: (1, 2, 3), centered on x = 0.
        top_values = [1, 2, 3]
        top_row = m.VGroup(*[_cell(v, m.BLUE) for v in top_values])
        for i, cell in enumerate(top_row):
            cell.move_to([(i - 1) * CELL, TOP_Y, 0.0])

        # Bottom row: (4, 5, 6), drawn in reading order — to be flipped (convolution).
        bot_values = [4, 5, 6]
        bot_row = m.VGroup(*[_cell(v, m.YELLOW) for v in bot_values])
        for i, cell in enumerate(bot_row):
            cell.move_to([(i - 1) * CELL, BOT_Y, 0.0])

        self.play(m.FadeIn(top_row), m.FadeIn(bot_row), run_time=1.0)

        # Flip the bottom row 180 degrees — this is the "reverse g" step of convolution.
        self.play(m.Rotate(bot_row, m.PI), run_time=1.2)

        # Output row placeholder: three empty labels for c_0, c_1, c_2.
        output_labels: list[m.MathTex] = []
        for n in range(3):
            placeholder = m.MathTex(f"c_{n} = ?", font_size=36)
            placeholder.move_to([(n - 1) * 2.2, OUT_Y, 0.0])
            output_labels.append(placeholder)
        output_group = m.VGroup(*output_labels)
        self.play(m.Write(output_group), run_time=1.0)

        # March the flipped bot_row across the top_row and collect aligned products.
        # After the Rotate, the cell that VISUALLY shows "6" sits at x=-1, "5" at x=0, "4" at x=1.
        # Position the flipped row so its rightmost visible cell aligns with top[0] (index 0).
        # top_row centers: top[0] = -1, top[1] = 0, top[2] = 1.
        # For output index n, the flipped row's cells overlap top_row cells i where i + j = n.
        # We realize that by shifting the flipped row left-to-right in CELL-sized steps.

        # Start: shift bot_row left so only its rightmost cell aligns with top[0] (n=0).
        # After rotate, bot_row's geometric center is still at (0, BOT_Y). We want to move it.
        start_shift = (
            -2.0 * CELL * m.RIGHT
        )  # bot_row center at x=-2; its visible "4" at x=-1 overlaps top[0] at x=-1.
        self.play(bot_row.animate.shift(start_shift), run_time=0.8)

        # Pair products for the three march steps:
        products_by_n = {
            0: [(0, 0, 1 * 4)],
            1: [(0, 1, 1 * 5), (1, 0, 2 * 4)],
            2: [(0, 2, 1 * 6), (1, 1, 2 * 5), (2, 0, 3 * 4)],
        }

        results = {0: 4, 1: 13, 2: 28}

        for n in range(3):
            # Highlight each aligned pair with a SurroundingRectangle pulse.
            pair_highlights: list[m.Animation] = []
            for top_idx, _bot_idx, _prod in products_by_n[n]:
                top_cell = top_row[top_idx]
                # The bot cell overlapping top_cell is the one currently at the same x.
                target_x = top_cell.get_center()[0]
                # Find the submobject of bot_row whose center is nearest target_x.
                nearest = min(bot_row, key=lambda c: abs(c.get_center()[0] - target_x))
                pair_rect = m.SurroundingRectangle(
                    m.VGroup(top_cell, nearest), color=m.GREEN, buff=0.08
                )
                pair_highlights.append(m.Create(pair_rect))
            if pair_highlights:
                self.play(*pair_highlights, run_time=0.7)

            # Resolve the output cell for this step.
            final_label = m.MathTex(
                f"c_{n} = {results[n]}", font_size=36, color=m.GREEN
            )
            final_label.move_to(output_labels[n].get_center())
            self.play(m.FadeTransform(output_labels[n], final_label), run_time=0.7)

            # Shift the bottom row right by one cell for the next alignment — skip after last.
            if n < 2:
                self.play(bot_row.animate.shift(CELL * m.RIGHT), run_time=0.6)

        self.wait(0.5)

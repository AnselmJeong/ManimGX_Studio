"""Show me why the area of a circle is pi*R^2 using the sector-parallelogram trick."""

import itertools

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        radius = 1.6
        n_sectors = 12
        colors = [m.TEAL_E, m.BLUE_E]

        # Build the circle out of N sectors, alternating colors.
        sectors = m.VGroup()
        color_cycle = itertools.cycle(colors)
        for i in range(n_sectors):
            color = next(color_cycle)
            sector = m.Sector(
                radius=radius,
                start_angle=i * 2 * m.PI / n_sectors,
                angle=2 * m.PI / n_sectors,
                color=color,
                fill_opacity=1.0,
                stroke_color=m.WHITE,
                stroke_width=1.0,
            )
            sectors.add(sector)

        # Recenter so the circle sits above the horizontal axis
        sectors.move_to(1.2 * m.UP)

        self.play(
            m.LaggedStart(*[m.Create(s) for s in sectors], lag_ratio=0.05), run_time=2.5
        )
        self.wait(0.3)

        # Now fan out the sectors into a parallelogram-like arrangement.
        # The target positions form two rows: even-index sectors go on the
        # bottom row pointing up, odd-index sectors go on the top row
        # flipped 180 degrees to interlock.
        sector_width = radius * 2 * m.PI / n_sectors  # arc length per sector
        row_y_bottom = -0.3
        row_y_top = row_y_bottom + radius

        for i, sector in enumerate(sectors):
            target = sector.generate_target()
            half = i // 2
            x = -((n_sectors // 2) - 1) / 2 * sector_width + half * sector_width
            if i % 2 == 0:
                # Bottom row, pointing up.
                target.rotate(-i * 2 * m.PI / n_sectors)
                target.move_to(np.array([x, row_y_bottom, 0.0]))
            else:
                # Top row, flipped by PI to interlock.
                target.rotate(m.PI - i * 2 * m.PI / n_sectors)
                target.move_to(np.array([x, row_y_top, 0.0]))

        self.play(
            m.LaggedStart(
                *[m.MoveToTarget(s) for s in sectors],
                lag_ratio=0.05,
            ),
            run_time=3.5,
        )
        self.wait(0.3)

        # Labels: width ~ pi*R, height ~ R.
        total_width = (n_sectors // 2) * sector_width  # ~ pi*R
        left_edge = -total_width / 2
        right_edge = total_width / 2

        width_brace = m.Line(
            np.array([left_edge, row_y_bottom - 0.55, 0.0]),
            np.array([right_edge, row_y_bottom - 0.55, 0.0]),
            color=m.YELLOW,
            stroke_width=4.0,
        )
        width_label = m.MathTex(R"\pi R", color=m.YELLOW).next_to(
            width_brace, m.DOWN, buff=0.15
        )

        height_brace = m.Line(
            np.array([right_edge + 0.4, row_y_bottom, 0.0]),
            np.array([right_edge + 0.4, row_y_top + radius * 0.02, 0.0]),
            color=m.GREEN,
            stroke_width=4.0,
        )
        height_label = m.MathTex("R", color=m.GREEN).next_to(
            height_brace, m.RIGHT, buff=0.15
        )

        self.play(
            m.Create(width_brace),
            m.Write(width_label),
            m.Create(height_brace),
            m.Write(height_label),
            run_time=1.5,
        )
        self.wait(0.3)

        area_eq = m.MathTex(R"A = \pi R \cdot R = \pi R^2").scale(1.1).to_edge(m.UP)
        self.play(m.Write(area_eq), run_time=1.5)
        self.wait(0.5)

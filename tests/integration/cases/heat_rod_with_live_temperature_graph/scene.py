"""Show the heat equation solution: a rod whose colors blend over time with a temperature graph below that flattens together."""

import math

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "Tests ONE ValueTracker driving (a) N colored rod cells via add_updater and "
    "(b) a plot(...) curve via always_redraw. Uses hand-coded analytic solution "
    "T(x,t) = 0.5 + 0.4 * exp(-t) * sin(pi*x) to avoid simulation."
)


def _temp_to_color(t_val: float) -> str:
    """Map temperature in [0, 1] to a hex color (cold=blue, hot=red)."""
    t_val = max(0.0, min(1.0, t_val))
    # Linear interpolation from cold blue (35, 90, 190) to hot red (230, 60, 60).
    r = round(35.0 + (230.0 - 35.0) * t_val)
    g = round(90.0 + (60.0 - 90.0) * t_val)
    b = round(190.0 + (60.0 - 190.0) * t_val)
    return f"#{r:02x}{g:02x}{b:02x}"


class TeacherScene(m.Scene):
    def construct(self):
        # Analytical solution: T(x, t) = 0.5 + 0.4 * exp(-t) * sin(pi * x), x in [0, 1].
        def temperature(x: float, t: float) -> float:
            return 0.5 + 0.4 * math.exp(-t) * math.sin(math.pi * x)

        # Rod: N thin cells stacked horizontally, above the axes.
        N = 30
        rod_length = 8.0
        cell_w = rod_length / N
        cell_h = 0.7
        rod_y = 2.3

        rod_cells: list[m.Rectangle] = []
        for i in range(N):
            x_center = -rod_length / 2.0 + (i + 0.5) * cell_w
            cell = m.Rectangle(
                width=cell_w,
                height=cell_h,
            ).set_stroke(opacity=0.0)
            cell.move_to(np.array([x_center, rod_y, 0.0]))
            rod_cells.append(cell)
        rod = m.VGroup(*rod_cells)

        # Thin outline around the rod to mark its extent.
        rod_frame = m.Rectangle(
            width=rod_length, height=cell_h, color=m.WHITE, stroke_width=1.5
        ).move_to(np.array([0.0, rod_y, 0.0]))

        # Axes below the rod for the temperature curve.
        axes = m.Axes(
            x_range=(0.0, 1.0, 0.25),
            y_range=(0.0, 1.0, 0.25),
            x_length=8.0,
            y_length=2.6,
            axis_config={"include_numbers": False},
        ).shift(1.2 * m.DOWN)

        x_label = m.MathTex("x", font_size=32).next_to(axes, m.RIGHT, buff=0.15)
        y_label = m.MathTex("T", font_size=32).next_to(axes, m.UP, buff=0.15)

        title = m.MathTex(
            R"T(x, t) = \tfrac{1}{2} + \tfrac{2}{5}\,e^{-t}\sin(\pi x)",
            font_size=32,
        ).to_edge(m.UP, buff=0.25)

        # Time tracker — the single driver.
        t_tracker = m.ValueTracker(0.0)

        # Cell color updater: each cell samples its own x = (i + 0.5) / N in [0, 1].
        def make_cell_updater(idx: int):
            x_sample = (idx + 0.5) / N

            def update(cell: m.Rectangle) -> None:
                temp = temperature(x_sample, t_tracker.get_value())
                cell.set_fill(_temp_to_color(temp), opacity=1.0)

            return update

        for i, cell in enumerate(rod_cells):
            cell.add_updater(make_cell_updater(i))

        # Live temperature curve: always_redraw sample of the analytic solution.
        temp_curve = m.always_redraw(
            lambda: axes.plot(
                lambda x: temperature(x, t_tracker.get_value()),
                x_range=(0.0, 1.0),
                color=m.YELLOW,
                stroke_width=4.0,
            )
        )

        # Initial time readout (bottom-right).
        time_readout = m.always_redraw(
            lambda: m.MathTex(
                rf"t = {t_tracker.get_value():.2f}",
                font_size=30,
            ).to_corner(m.DR, buff=0.4)
        )

        # Build the scene.
        self.play(m.Write(title), run_time=0.8)
        self.play(m.Create(rod_frame), m.FadeIn(rod), run_time=1.0)
        self.play(m.Create(axes), m.Write(x_label), m.Write(y_label), run_time=1.0)
        self.add(temp_curve, time_readout)
        self.wait(0.5)

        # Flatten: t: 0 -> 3 over 5 seconds.
        self.play(t_tracker.animate.set_value(3.0), run_time=5.0, rate_func=m.linear)

        self.wait(0.5)

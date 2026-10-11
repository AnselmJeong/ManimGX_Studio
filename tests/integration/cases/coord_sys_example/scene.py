# Source: manim/mobject/graphing/coordinate_systems.py
# ruff: noqa: B023
import numpy as np

import manimgx as m


class CoordSysExample(m.Scene):
    def construct(self):
        # the location of the ticks depends on the x_range and y_range.
        grid = m.Axes(
            x_range=[0, 1, 0.05],  # step size determines num_decimal_places.
            y_range=[0, 1, 0.05],
            x_length=9,
            y_length=5.5,
            axis_config={
                "numbers_to_include": np.arange(0, 1 + 0.1, 0.1),
                "font_size": 24,
            },
            tips=False,
        )

        # Labels for the x-axis and y-axis.
        y_label = grid.get_y_axis_label("y", edge=m.LEFT, direction=m.LEFT, buff=0.4)
        x_label = grid.get_x_axis_label("x")
        grid_labels = m.VGroup(x_label, y_label)

        graphs = m.VGroup()
        for n in np.arange(1, 20 + 0.5, 0.5):
            graphs += grid.plot(lambda x: x**n, color=m.WHITE)
            graphs += grid.plot(
                lambda x: x ** (1 / n),
                color=m.WHITE,
                use_smoothing=False,
            )

        # Extra lines and labels for point (1,1)
        graphs += grid.get_horizontal_line(grid @ (1, 1, 0), color=m.BLUE)
        graphs += grid.get_vertical_line(grid @ (1, 1, 0), color=m.BLUE)
        graphs += m.Dot(point=grid @ (1, 1, 0), color=m.YELLOW)
        graphs += m.Tex("(1,1)").scale(0.75).next_to(grid @ (1, 1, 0))
        title = m.Title(
            # spaces between braces to prevent SyntaxError
            r"Graphs of $y=x^{ {1}\over{n} }$ and $y=x^n (n=1,2,3,...,20)$",
            include_underline=False,
            font_size=40,
        )

        self.add(title, graphs, grid, grid_labels)

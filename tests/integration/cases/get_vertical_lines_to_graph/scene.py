# Source: manim/mobject/graphing/coordinate_systems.py
import numpy as np

import manimgx as m


class GetVerticalLinesToGraph(m.Scene):
    def construct(self):
        ax = m.Axes(
            x_range=[0, 8.0, 1],
            y_range=[-1, 1, 0.2],
            axis_config={"font_size": 24},
        ).add_coordinates()

        curve = ax.plot(lambda x: np.sin(x) / np.e**2 * x)

        lines = ax.get_vertical_lines_to_graph(
            curve, x_range=[0, 4], num_lines=30, color=m.BLUE
        )

        self.add(ax, curve, lines)
        self.wait()

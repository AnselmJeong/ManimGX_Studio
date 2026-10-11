# Source: manim/mobject/graphing/coordinate_systems.py
import numpy as np

import manimgx as m


class GetAreaExample(m.Scene):
    def construct(self):
        ax = m.Axes().add_coordinates()
        curve = ax.plot(lambda x: 2 * np.sin(x), color=m.DARK_BLUE)
        area = ax.get_area(
            curve,
            x_range=(m.PI / 2, 3 * m.PI / 2),
            color=(m.GREEN_B, m.GREEN_D),
            opacity=1,
        )

        self.add(ax, curve, area)

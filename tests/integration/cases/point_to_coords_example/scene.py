# Source: manim/mobject/graphing/coordinate_systems.py
import numpy as np

import manimgx as m


class PointToCoordsExample(m.Scene):
    def construct(self):
        ax = m.Axes(x_range=[0, 10, 2]).add_coordinates()
        circ = m.Circle(radius=0.5).shift(m.UR * 2)

        # get the coordinates of the circle with respect to the axes
        coords = np.around(ax.point_to_coords(circ.get_right()), decimals=2)

        label = m.Matrix([[coords[0]], [coords[1]]]).scale(0.75).next_to(circ, m.RIGHT)

        self.add(ax, circ, label, m.Dot(circ.get_right()))
        self.wait()

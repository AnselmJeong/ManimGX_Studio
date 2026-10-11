# Source: manim/mobject/graphing/coordinate_systems.py
import numpy as np

import manimgx as m


class InputToGraphPointExample(m.Scene):
    def construct(self):
        ax = m.Axes()
        curve = ax.plot(lambda x: np.cos(x))
        # move a square to PI on the cosine curve.
        position = ax.input_to_graph_point(x=m.PI, graph=curve)
        sq = m.Square(side_length=1, color=m.YELLOW).move_to(position)

        self.add(ax, curve, sq)
        self.wait()

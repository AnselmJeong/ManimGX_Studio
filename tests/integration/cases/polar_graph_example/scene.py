# Source: manim/mobject/graphing/coordinate_systems.py
import numpy as np

import manimgx as m


class PolarGraphExample(m.Scene):
    def construct(self):
        plane = m.PolarPlane()
        r = lambda theta: 2 * np.sin(theta * 5)
        graph = plane.plot_polar_graph(r, [0, 2 * m.PI], color=m.ORANGE)
        self.add(plane, graph)
        self.wait()

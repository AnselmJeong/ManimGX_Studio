# Source: manim/utils/qhull.py
import numpy as np

import manimgx as m
from manimgx import QuickHull


class QuickHullConvexHullExample(m.Scene):
    def construct(self):
        points = np.array(
            [
                [-2.0, -1.0],
                [2.0, -1.0],
                [2.0, 1.0],
                [-2.0, 1.0],
                [0.0, 0.5],
                [-1.0, 0.0],
                [1.0, 0.2],
            ]
        )
        qh = QuickHull()
        qh.build(points)
        dots = m.Group(
            *[m.Dot(np.array([p[0], p[1], 0.0]), color=m.YELLOW) for p in points]
        )
        self.add(dots)
        self.wait()

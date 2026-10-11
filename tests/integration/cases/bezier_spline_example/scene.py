# Source: manim/mobject/geometry/arc.py
import numpy as np

import manimgx as m


class BezierSplineExample(m.Scene):
    def construct(self):
        p1 = np.array([-3, 1, 0])
        p1b = p1 + [1, 0, 0]
        d1 = m.Dot(point=p1).set_color(m.BLUE)
        l1 = m.Line(p1, p1b)
        p2 = np.array([3, -1, 0])
        p2b = p2 - [1, 0, 0]
        d2 = m.Dot(point=p2).set_color(m.RED)
        l2 = m.Line(p2, p2b)
        bezier = m.CubicBezier(p1b, p1b + 3 * m.RIGHT, p2b - 3 * m.RIGHT, p2b)
        self.add(l1, d1, l2, d2, bezier)

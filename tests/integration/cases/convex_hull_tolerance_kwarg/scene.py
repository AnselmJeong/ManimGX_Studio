# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class ConvexHullToleranceKwarg(m.Scene):
    def construct(self):
        points = [
            [-2.0, -1.5, 0.0],
            [1.5, -2.0, 0.0],
            [2.0, 0.5, 0.0],
            [0.5, 2.0, 0.0],
            [-1.5, 1.5, 0.0],
            [-1.5, 1.5001, 0.0],  # near-duplicate, expected to collapse
        ]
        hull = m.ConvexHull(*points, tolerance=1e-2, color=m.BLUE, stroke_width=4)
        dots = m.VGroup(*(m.Dot(point=p, radius=0.06, color=m.WHITE) for p in points))
        self.add(hull, dots)
        self.wait()

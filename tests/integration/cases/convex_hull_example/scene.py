# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class ConvexHullExample(m.Scene):
    def construct(self):
        points = [
            [-2.35, -2.25, 0],
            [1.65, -2.25, 0],
            [2.65, -0.25, 0],
            [1.65, 1.75, 0],
            [-0.35, 2.75, 0],
            [-2.35, 0.75, 0],
            [-0.35, -1.25, 0],
            [0.65, -0.25, 0],
            [-1.35, 0.25, 0],
            [0.15, 0.75, 0],
        ]
        hull = m.ConvexHull(*points, color=m.BLUE)
        dots = m.VGroup(*[m.Dot(point) for point in points])
        self.add(hull)
        self.add(dots)
        self.wait()

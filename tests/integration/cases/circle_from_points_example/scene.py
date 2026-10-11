# Source: manim/mobject/geometry/arc.py
import manimgx as m


class CircleFromPointsExample(m.Scene):
    def construct(self):
        circle = m.Circle.from_three_points(
            m.LEFT, m.LEFT + m.UP, m.UP * 2, color=m.RED
        )
        dots = m.VGroup(
            m.Dot(m.LEFT),
            m.Dot(m.LEFT + m.UP),
            m.Dot(m.UP * 2),
        )
        self.add(m.NumberPlane(), circle, dots)
        self.wait()

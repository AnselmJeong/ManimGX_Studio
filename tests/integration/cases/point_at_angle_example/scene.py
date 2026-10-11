# Source: manim/mobject/geometry/arc.py
import manimgx as m


class PointAtAngleExample(m.Scene):
    def construct(self):
        circle = m.Circle(radius=2.0)
        p1 = circle.point_at_angle(m.PI / 2)
        p2 = circle.point_at_angle(270 * m.DEGREES)

        s1 = m.Square(side_length=0.25).move_to(p1)
        s2 = m.Square(side_length=0.25).move_to(p2)
        self.add(circle, s1, s2)
        self.wait()

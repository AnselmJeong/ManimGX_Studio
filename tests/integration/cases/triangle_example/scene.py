# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class TriangleExample(m.Scene):
    def construct(self):
        triangle_1 = m.Triangle()
        triangle_2 = m.Triangle().scale(2).rotate(60 * m.DEGREES)
        tri_group = m.Group(triangle_1, triangle_2).arrange(buff=1)
        self.add(tri_group)
        self.wait()

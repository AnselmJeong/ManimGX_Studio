# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class RegularPolygonExample(m.Scene):
    def construct(self):
        poly_1 = m.RegularPolygon(n=6)
        poly_2 = m.RegularPolygon(n=6, start_angle=30 * m.DEGREES, color=m.GREEN)
        poly_3 = m.RegularPolygon(n=10, color=m.RED)

        poly_group = m.Group(poly_1, poly_2, poly_3).scale(1.5).arrange(buff=1)
        self.add(poly_group)
        self.wait()

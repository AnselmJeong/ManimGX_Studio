# Source: manim/mobject/geometry/arc.py
import manimgx as m


class CircleSurround(m.Scene):
    def construct(self):
        triangle1 = m.Triangle()
        circle1 = m.Circle().surround(triangle1)
        group1 = m.Group(triangle1, circle1)  # treat the two mobjects as one

        line2 = m.Line()
        circle2 = m.Circle().surround(line2, buffer_factor=2.0)
        group2 = m.Group(line2, circle2)

        # buffer_factor < 1, so the circle is smaller than the square
        square3 = m.Square()
        circle3 = m.Circle().surround(square3, buffer_factor=0.5)
        group3 = m.Group(square3, circle3)

        group = m.Group(group1, group2, group3).arrange(buff=1)
        self.add(group)
        self.wait()

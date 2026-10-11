# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class RoundedRectangleExample(m.Scene):
    def construct(self):
        rect_1 = m.RoundedRectangle(corner_radius=0.5)
        rect_2 = m.RoundedRectangle(corner_radius=1.5, height=4.0, width=4.0)

        rect_group = m.Group(rect_1, rect_2).arrange(buff=1)
        self.add(rect_group)
        self.wait()

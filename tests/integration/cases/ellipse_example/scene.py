# Source: manim/mobject/geometry/arc.py
import manimgx as m


class EllipseExample(m.Scene):
    def construct(self):
        ellipse_1 = m.Ellipse(width=2.0, height=4.0, color=m.BLUE_B)
        ellipse_2 = m.Ellipse(width=4.0, height=1.0, color=m.BLUE_D)
        ellipse_group = m.Group(ellipse_1, ellipse_2).arrange(buff=1)
        self.add(ellipse_group)
        self.wait()

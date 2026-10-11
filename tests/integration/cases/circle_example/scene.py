# Source: manim/mobject/geometry/arc.py
import manimgx as m


class CircleExample(m.Scene):
    def construct(self):
        circle_1 = m.Circle(radius=1.0)
        circle_2 = m.Circle(radius=1.5, color=m.GREEN)
        circle_3 = m.Circle(radius=1.0, color=m.BLUE_B, fill_opacity=1)

        circle_group = m.Group(circle_1, circle_2, circle_3).arrange(buff=1)
        self.add(circle_group)
        self.wait()

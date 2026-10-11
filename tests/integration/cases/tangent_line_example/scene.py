# Source: manim/mobject/geometry/line.py
import manimgx as m


class TangentLineExample(m.Scene):
    def construct(self):
        circle = m.Circle(radius=2)
        line_1 = m.TangentLine(circle, alpha=0.0, length=4, color=m.BLUE_D)  # right
        line_2 = m.TangentLine(circle, alpha=0.4, length=4, color=m.GREEN)  # top left
        self.add(circle, line_1, line_2)
        self.wait()

# Source: manim/mobject/geometry/line.py
import manimgx as m


class TangentLineVmobKwarg(m.Scene):
    def construct(self):
        circle = m.Circle(radius=1.5, color=m.GREY_B)
        # CE accepts ``vmob=`` (alias for the positional VMobject argument).
        line = m.TangentLine(vmob=circle, alpha=0.25, length=4, color=m.YELLOW)
        self.add(circle, line)
        self.wait()

# Source: manim/mobject/geometry/shape_matchers.py
import manimgx as m


class CrossScaleFactorKwarg(m.Scene):
    def construct(self):
        target = m.Square(side_length=2.0, color=m.GREY_C)
        cross = m.Cross(target, scale_factor=0.6, stroke_color=m.RED, stroke_width=8)
        self.add(target, cross)
        self.wait()

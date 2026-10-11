# Source: manim/mobject/geometry/line.py

import manimgx as m


class DoubleArrowExample(m.Scene):
    def construct(self):
        circle = m.Circle(radius=2.0)
        d_arrow = m.DoubleArrow(start=circle.get_left(), end=circle.get_right())
        d_arrow_2 = m.DoubleArrow(
            tip_shape_end=m.ArrowCircleFilledTip,
            tip_shape_start=m.ArrowCircleFilledTip,
        )
        group = m.Group(m.Group(circle, d_arrow), d_arrow_2).arrange(m.UP, buff=1)
        self.add(group)
        self.wait()

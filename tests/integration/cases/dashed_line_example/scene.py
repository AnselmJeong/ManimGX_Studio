# Source: manim/mobject/geometry/line.py
import manimgx as m


class DashedLineExample(m.Scene):
    def construct(self):
        # dash_length increased
        dashed_1 = m.DashedLine(
            m.config.left_side,
            m.config.right_side,
            dash_length=2.0,
        ).shift(m.UP * 2)
        # normal
        dashed_2 = m.DashedLine(m.config.left_side, m.config.right_side)
        # dashed_ratio decreased
        dashed_3 = m.DashedLine(
            m.config.left_side,
            m.config.right_side,
            dashed_ratio=0.1,
        ).shift(m.DOWN * 2)
        self.add(dashed_1, dashed_2, dashed_3)
        self.wait()

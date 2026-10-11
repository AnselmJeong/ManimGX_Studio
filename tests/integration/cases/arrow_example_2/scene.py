# Source: manim/mobject/geometry/line.py
import numpy as np

import manimgx as m


class ArrowExample(m.Scene):
    def construct(self):
        left_group = m.VGroup()
        # As buff increases, the size of the arrow decreases.
        for buff in np.arange(0, 2.2, 0.45):
            left_group += m.Arrow(buff=buff, start=2 * m.LEFT, end=2 * m.RIGHT)
        # Required to arrange arrows.
        left_group.arrange(m.DOWN)
        left_group.move_to(4 * m.LEFT)

        middle_group = m.VGroup()
        # As max_stroke_width_to_length_ratio gets bigger,
        # the width of stroke increases.
        for i in np.arange(0, 5, 0.5):
            middle_group += m.Arrow(max_stroke_width_to_length_ratio=i)
        middle_group.arrange(m.DOWN)

        UR_group = m.VGroup()
        # As max_tip_length_to_length_ratio increases,
        # the length of the tip increases.
        for i in np.arange(0, 0.3, 0.1):
            UR_group += m.Arrow(max_tip_length_to_length_ratio=i)
        UR_group.arrange(m.DOWN)
        UR_group.move_to(4 * m.RIGHT + 2 * m.UP)

        DR_group = m.VGroup()
        DR_group += m.Arrow(
            start=m.LEFT,
            end=m.RIGHT,
            color=m.BLUE,
            tip_shape=m.ArrowSquareTip,
        )
        DR_group += m.Arrow(
            start=m.LEFT,
            end=m.RIGHT,
            color=m.BLUE,
            tip_shape=m.ArrowSquareFilledTip,
        )
        DR_group += m.Arrow(
            start=m.LEFT,
            end=m.RIGHT,
            color=m.YELLOW,
            tip_shape=m.ArrowCircleTip,
        )
        DR_group += m.Arrow(
            start=m.LEFT,
            end=m.RIGHT,
            color=m.YELLOW,
            tip_shape=m.ArrowCircleFilledTip,
        )
        DR_group.arrange(m.DOWN)
        DR_group.move_to(4 * m.RIGHT + 2 * m.DOWN)

        self.add(left_group, middle_group, UR_group, DR_group)
        self.wait()

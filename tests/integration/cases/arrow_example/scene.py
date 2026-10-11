# Source: manim/mobject/geometry/line.py

import manimgx as m


class ArrowExample(m.Scene):
    def construct(self):
        arrow_1 = m.Arrow(start=m.RIGHT, end=m.LEFT, color=m.GOLD)
        arrow_2 = m.Arrow(
            start=m.RIGHT,
            end=m.LEFT,
            color=m.GOLD,
            tip_shape=m.ArrowSquareTip,
        ).shift(m.DOWN)
        g1 = m.Group(arrow_1, arrow_2)

        # the effect of buff
        square = m.Square(color=m.MAROON_A)
        arrow_3 = m.Arrow(start=m.LEFT, end=m.RIGHT)
        arrow_4 = m.Arrow(start=m.LEFT, end=m.RIGHT, buff=0).next_to(arrow_1, m.UP)
        g2 = m.Group(arrow_3, arrow_4, square)

        # a shorter arrow has a shorter tip and smaller stroke width
        arrow_5 = m.Arrow(start=m.ORIGIN, end=m.config.top).shift(m.LEFT * 4)
        arrow_6 = m.Arrow(start=m.config.top + m.DOWN, end=m.config.top).shift(
            m.LEFT * 3
        )
        g3 = m.Group(arrow_5, arrow_6)

        self.add(m.Group(g1, g2, g3).arrange(buff=2))
        self.wait()

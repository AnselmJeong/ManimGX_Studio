# Source: manim/mobject/geometry/tips.py
import manimgx as m


class ArrowTriangleFilledTipExample(m.Scene):
    def construct(self):
        arr = m.Arrow(
            m.LEFT * 2,
            m.RIGHT * 2,
            buff=0,
            tip_shape=m.ArrowTriangleFilledTip,
            color=m.YELLOW,
        )
        self.add(arr)
        self.wait()

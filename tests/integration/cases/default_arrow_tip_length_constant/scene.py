# Source: manim/constants.py
import manimgx as m


class DefaultArrowTipLengthConstant(m.Scene):
    def construct(self):
        arrow = m.Arrow(
            start=m.LEFT,
            end=m.RIGHT,
            tip_length=m.DEFAULT_ARROW_TIP_LENGTH,
        )
        self.add(arrow)
        self.wait()

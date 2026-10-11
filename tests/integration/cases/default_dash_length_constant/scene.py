# Source: manim/constants.py
import manimgx as m


class DefaultDashLengthConstant(m.Scene):
    def construct(self):
        dashed = m.DashedLine(
            start=m.LEFT,
            end=m.RIGHT,
            dash_length=m.DEFAULT_DASH_LENGTH,
        )
        self.add(dashed)
        self.wait()

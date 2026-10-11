# Source: manim/constants.py
import manimgx as m


class DefaultStrokeWidthConstant(m.Scene):
    def construct(self):
        square = m.Square(stroke_width=m.DEFAULT_STROKE_WIDTH)
        self.add(square)
        self.wait()

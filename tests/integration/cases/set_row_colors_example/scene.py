# Source: manim/mobject/matrix.py
import manimgx as m


class SetRowColorsExample(m.Scene):
    def construct(self):
        m0 = m.Matrix(
            [["\\pi", 1], [-1, 3]],
        ).set_row_colors([m.RED, m.BLUE], m.GREEN)
        self.add(m0)
        self.wait()

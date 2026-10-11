# Source: manim/mobject/matrix.py
import manimgx as m


class GetColumnsExample(m.Scene):
    def construct(self):
        m0 = m.Matrix([[r"\pi", 3], [1, 5]])
        m0.add(m.SurroundingRectangle(m0.get_columns()[1]))
        self.add(m0)
        self.wait()

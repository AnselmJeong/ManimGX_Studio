# Source: manim/mobject/matrix.py
import manimgx as m


class GetRowsExample(m.Scene):
    def construct(self):
        m0 = m.Matrix([["\\pi", 3], [1, 5]])
        m0.add(m.SurroundingRectangle(m0.get_rows()[1]))
        self.add(m0)
        self.wait()

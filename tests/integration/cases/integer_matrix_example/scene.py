# Source: manim/mobject/matrix.py
import manimgx as m


class IntegerMatrixExample(m.Scene):
    def construct(self):
        m0 = m.IntegerMatrix(
            [[3.7, 2], [42.2, 12]], left_bracket="(", right_bracket=")"
        )
        self.add(m0)
        self.wait()

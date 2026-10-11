# Source: manim/mobject/matrix.py
import manimgx as m


class MatrixWithBracketConfigExample(m.Scene):
    def construct(self):
        matrix = m.Matrix(
            [[1, 2], [3, 4]],
            bracket_config={"color": m.RED},
        )
        self.play(m.FadeIn(matrix))
        self.wait(0.2)

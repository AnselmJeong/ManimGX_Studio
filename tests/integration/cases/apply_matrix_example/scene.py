# Source: manim/animation/transform.py
import manimgx as m


class ApplyMatrixExample(m.Scene):
    def construct(self):
        matrix = [[1, 1], [0, 2 / 3]]
        self.play(
            m.ApplyMatrix(matrix, m.Text("Hello World!")),
            m.ApplyMatrix(matrix, m.NumberPlane()),
        )

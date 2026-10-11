# Source: manim/animation/transform.py
import numpy as np

import manimgx as m


class ApplyComplexFunctionExample(m.Scene):
    def construct(self):
        square = m.Square()
        self.add(square)
        self.play(m.ApplyComplexFunction(lambda z: np.exp(z * 1j), square))

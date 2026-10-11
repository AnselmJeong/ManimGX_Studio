# Source: manim/animation/transform.py
import numpy as np

import manimgx as m


class WarpSquare(m.Scene):
    def construct(self):
        square = m.Square()
        self.play(
            m.ApplyPointwiseFunction(
                lambda point: m.complex_to_R3(np.exp(m.R3_to_complex(point))),
                square,
            )
        )
        self.wait()

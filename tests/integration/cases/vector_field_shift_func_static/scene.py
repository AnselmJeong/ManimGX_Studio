# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class VectorFieldShiftFuncStatic(m.Scene):
    def construct(self):
        base = lambda p: np.array([p[0], p[1], 0.0])
        shifted = m.VectorField.shift_func(base, np.array([1.0, 0.0, 0.0]))
        field = m.ArrowVectorField(
            shifted,
            x_range=[-2, 2, 0.5],
            y_range=[-2, 2, 0.5],
        )
        self.add(field)
        self.wait(0.1)

# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class ArrowVectorFieldColorSchemeKwarg(m.Scene):
    def construct(self):
        field = m.ArrowVectorField(
            lambda p: np.array([p[1], -p[0], 0.0]),
            x_range=[-2, 2, 0.5],
            y_range=[-2, 2, 0.5],
            color_scheme=lambda v: float(abs(v[0]) + abs(v[1])),
        )
        self.add(field)
        self.wait(0.1)

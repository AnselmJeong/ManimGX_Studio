# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class ArrowVectorFieldVectorConfigKwarg(m.Scene):
    def construct(self):
        field = m.ArrowVectorField(
            lambda p: np.array([np.cos(p[0]), np.sin(p[1]), 0.0]),
            x_range=[-2, 2, 1.0],
            y_range=[-2, 2, 1.0],
            vector_config={"stroke_width": 4},
        )
        self.add(field)
        self.wait(0.1)

# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class VectorFieldFitToCoordinateSystem(m.Scene):
    def construct(self):
        axes = m.Axes(x_range=[-2, 2, 1], y_range=[-2, 2, 1], x_length=4, y_length=4)
        field = m.ArrowVectorField(
            lambda p: np.array([np.sin(p[1]), np.cos(p[0]), 0.0]),
            x_range=[-2, 2, 0.5],
            y_range=[-2, 2, 0.5],
        )
        field.fit_to_coordinate_system(axes)
        self.add(axes, field)
        self.wait(0.1)

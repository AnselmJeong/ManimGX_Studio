# Source: manim/mobject/vector_field.py
import numpy as np

import manimgx as m


class ArrowVectorFieldThreeDimensionsKwarg(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
        field = m.ArrowVectorField(
            lambda p: np.array([p[2], p[0], p[1]]),
            x_range=[-1.5, 1.5, 1.0],
            y_range=[-1.5, 1.5, 1.0],
            z_range=[-1.5, 1.5, 1.0],
            three_dimensions=True,
        )
        self.add(field)
        self.wait(0.1)

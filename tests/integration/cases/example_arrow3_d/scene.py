# Source: manim/mobject/three_d/three_dimensions.py
import numpy as np

import manimgx as m


class ExampleArrow3D(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes()
        arrow = m.Arrow3D(
            start=np.array([0, 0, 0]),
            end=np.array([2, 2, 2]),
            resolution=8,
        )
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        self.add(axes, arrow)
        self.wait()

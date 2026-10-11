# Source: manim/mobject/three_d/three_dimensions.py
import numpy as np

import manimgx as m


class ExampleLine3D(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes()
        line = m.Line3D(start=np.array([0, 0, 0]), end=np.array([2, 2, 2]))
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        self.add(axes, line)
        self.wait()

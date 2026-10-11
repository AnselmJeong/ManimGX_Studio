# Source: manim/mobject/three_d/three_dimensions.py
import numpy as np

import manimgx as m


class Arrow3DCeKwargAliases(m.ThreeDScene):
    def construct(self):
        arrow = m.Arrow3D(
            start=np.array([0.0, 0.0, 0.0]),
            end=np.array([2.0, 2.0, 2.0]),
            thickness=0.05,
            height=0.4,
            base_radius=0.1,
        )
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
        self.add(arrow)
        self.wait(0.1)

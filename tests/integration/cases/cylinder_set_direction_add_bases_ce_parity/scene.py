# Source: manim/mobject/three_d/three_dimensions.py
import numpy as np

import manimgx as m


class CylinderSetDirectionAddBasesCeParity(m.ThreeDScene):
    def construct(self):
        cyl = m.Cylinder(radius=0.6, height=2.0, direction=np.array([1.0, 0.0, 0.0]))
        cyl.set_direction(np.array([0.0, 1.0, 0.0]))
        cyl.add_bases()
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
        self.add(cyl)
        self.wait(0.1)

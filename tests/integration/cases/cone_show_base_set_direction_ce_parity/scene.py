# Source: manim/mobject/three_d/three_dimensions.py
import numpy as np

import manimgx as m


class ConeShowBaseSetDirectionCeParity(m.ThreeDScene):
    def construct(self):
        cone = m.Cone(base_radius=0.5, height=1.5, show_base=True)
        cone.set_direction(np.array([1.0, 0.0, 1.0]))
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
        self.add(cone)
        self.wait(0.1)

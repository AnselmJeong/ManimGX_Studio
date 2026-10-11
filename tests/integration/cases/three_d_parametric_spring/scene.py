# Source: manim/mobject/graphing/functions.py
import numpy as np

import manimgx as m


class ThreeDParametricSpring(m.ThreeDScene):
    def construct(self):
        curve1 = m.ParametricFunction(
            lambda u: (
                1.2 * np.cos(u),
                1.2 * np.sin(u),
                u * 0.05,
            ),
            color=m.RED,
            t_range=(-3 * m.TAU, 5 * m.TAU, 0.01),
        ).set_shade_in_3d(True)
        axes = m.ThreeDAxes()
        self.add(axes, curve1)
        self.set_camera_orientation(phi=80 * m.DEGREES, theta=-60 * m.DEGREES)
        self.wait()

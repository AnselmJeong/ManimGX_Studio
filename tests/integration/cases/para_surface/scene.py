# Source: manim/mobject/three_d/three_dimensions.py
import numpy as np

import manimgx as m


class ParaSurface(m.ThreeDScene):
    def func(self, u, v):
        return np.array([np.cos(u) * np.cos(v), np.cos(u) * np.sin(v), u])

    def construct(self):
        axes = m.ThreeDAxes(x_range=[-4, 4, 1], x_length=8)
        surface = m.Surface(
            lambda u, v: axes.c2p(*self.func(u, v)),
            u_range=[-m.PI, m.PI],
            v_range=[0, m.TAU],
            resolution=8,
        )
        self.set_camera_orientation(theta=70 * m.DEGREES, phi=75 * m.DEGREES)
        self.add(axes, surface)

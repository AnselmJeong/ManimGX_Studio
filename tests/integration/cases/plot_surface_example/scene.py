# Source: manim/mobject/graphing/coordinate_systems.py
import numpy as np

import manimgx as m


class PlotSurfaceExample(m.ThreeDScene):
    def construct(self):
        resolution_fa = 16
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=-60 * m.DEGREES)
        axes = m.ThreeDAxes(x_range=(-3, 3, 1), y_range=(-3, 3, 1), z_range=(-5, 5, 1))

        def param_trig(u, v):
            x = u
            y = v
            z = 2 * np.sin(x) + 2 * np.cos(y)
            return z

        trig_plane = m.Surface(
            lambda u, v: axes.c2p(u, v, param_trig(u, v)),
            resolution=(resolution_fa, resolution_fa),
            u_range=(-3, 3),
            v_range=(-3, 3),
        )
        trig_plane.set_fill_by_value(
            axes=axes,
            colorscale=[m.BLUE, m.GREEN, m.YELLOW, m.ORANGE, m.RED],
            axis=2,
        )
        self.add(axes, trig_plane)

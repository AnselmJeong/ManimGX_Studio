# Source: manim/mobject/three_d/three_dimensions.py
import numpy as np

import manimgx as m


class FillByValueExample(m.ThreeDScene):
    def construct(self):
        resolution_fa = 8
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=-160 * m.DEGREES)
        axes = m.ThreeDAxes(x_range=(0, 5, 1), y_range=(0, 5, 1), z_range=(-1, 1, 0.5))

        def param_surface(u, v):
            x = u
            y = v
            z = np.sin(x) * np.cos(y)
            return z

        surface_plane = m.Surface(
            lambda u, v: axes.c2p(u, v, param_surface(u, v)),
            resolution=(resolution_fa, resolution_fa),
            v_range=[0, 5],
            u_range=[0, 5],
        )
        surface_plane.set_style(fill_opacity=1)
        surface_plane.set_fill_by_value(
            axes=axes, colorscale=[(m.RED, -0.5), (m.YELLOW, 0), (m.GREEN, 0.5)], axis=2
        )
        self.add(axes, surface_plane)
        self.wait()

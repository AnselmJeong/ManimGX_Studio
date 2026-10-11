# Source: docs/source/examples.rst
import numpy as np

import manimgx as m


class ThreeDSurfacePlot(m.ThreeDScene):
    def construct(self):
        resolution_fa = 24
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=-30 * m.DEGREES)

        def param_gauss(u, v):
            x = u
            y = v
            sigma, mu = 0.4, [0.0, 0.0]
            d = np.linalg.norm(np.array([x - mu[0], y - mu[1]]))
            z = np.exp(-(d**2 / (2.0 * sigma**2)))
            return np.array([x, y, z])

        gauss_plane = m.Surface(
            param_gauss,
            resolution=(resolution_fa, resolution_fa),
            v_range=[-2, +2],
            u_range=[-2, +2],
        )

        gauss_plane.scale(2, about_point=m.ORIGIN)
        gauss_plane.set_style(fill_opacity=1, stroke_color=m.GREEN)
        gauss_plane.set_fill_by_checkerboard(m.ORANGE, m.BLUE, opacity=0.5)
        axes = m.ThreeDAxes()
        self.add(axes, gauss_plane)
        self.wait()

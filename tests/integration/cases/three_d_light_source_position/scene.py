# Source: docs/source/examples.rst
import numpy as np

import manimgx as m


class ThreeDLightSourcePosition(m.ThreeDScene):
    def construct(self):
        axes = m.ThreeDAxes()
        sphere = m.Surface(
            lambda u, v: np.array(
                [
                    1.5 * np.cos(u) * np.cos(v),
                    1.5 * np.cos(u) * np.sin(v),
                    1.5 * np.sin(u),
                ]
            ),
            v_range=[0, m.TAU],
            u_range=[-m.PI / 2, m.PI / 2],
            resolution=(15, 32),
        )
        sphere.set_fill_by_checkerboard(m.RED_D, m.RED_E)
        self.renderer.camera.light_source.move_to(
            3 * m.IN
        )  # changes the source of the light
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        self.add(axes, sphere)

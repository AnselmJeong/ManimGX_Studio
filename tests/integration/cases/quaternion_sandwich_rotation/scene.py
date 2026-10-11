import math

import numpy as np

import manimgx as m


class TeacherScene(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-30 * m.DEGREES)
        axes = m.ThreeDAxes(
            x_range=[-2, 2, 1],
            y_range=[-2, 2, 1],
            z_range=[-2, 2, 1],
        )
        self.add(axes)

        title = m.MathTex("p' = q\\, p\\, q^{-1}").to_edge(m.UP, buff=0.3)
        self.add_fixed_in_frame_mobjects(title)

        p = np.array([1.0, 0.0, 1.0])
        p_arrow = m.Arrow3D(start=np.array([0.0, 0.0, 0.0]), end=p, color=m.BLUE)
        self.play(m.Create(p_arrow))
        self.wait(0.4)

        theta = math.pi / 2
        rot = np.array(
            [
                [math.cos(theta), 0.0, math.sin(theta)],
                [0.0, 1.0, 0.0],
                [-math.sin(theta), 0.0, math.cos(theta)],
            ]
        )
        p_new = rot @ p
        p_new_arrow = m.Arrow3D(start=np.array([0.0, 0.0, 0.0]), end=p_new, color=m.RED)

        self.play(m.Transform(p_arrow, p_new_arrow), run_time=2.0)
        self.wait(1.5)

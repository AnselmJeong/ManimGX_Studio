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

        title = m.Tex("Cube rotation = vertex permutation").to_edge(m.UP, buff=0.3)
        self.add_fixed_in_frame_mobjects(title)

        cube = m.Cube(
            side_length=1.5, color=m.YELLOW, fill_opacity=0.45, stroke_width=2
        )
        self.play(m.FadeIn(cube))

        diag_axis = np.array([1.0, 1.0, 1.0]) / math.sqrt(3.0)
        for _ in range(3):
            self.play(
                cube.animate.rotate(2 * math.pi / 3, axis=diag_axis), run_time=1.6
            )
            self.wait(0.3)
        self.wait(1.0)

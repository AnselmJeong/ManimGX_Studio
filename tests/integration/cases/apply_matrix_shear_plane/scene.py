"""Show what the shear matrix [[1, 1], [0, 1]] does to the plane."""

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self):
        plane = m.NumberPlane(
            x_range=(-5.0, 5.0, 1.0),
            y_range=(-3.0, 3.0, 1.0),
            x_length=10.0,
            y_length=6.0,
        )
        arrow = m.Arrow(
            m.ORIGIN,
            plane.c2p(1, 1),
            buff=0,
            color=m.YELLOW,
            stroke_width=6,
        )

        self.play(m.Create(plane), run_time=1.5)
        self.play(m.GrowArrow(arrow), run_time=1.0)
        self.play(
            m.ApplyMatrix([[1, 1], [0, 1]], plane),
            m.ApplyMatrix([[1, 1], [0, 1]], arrow),
            run_time=3.0,
        )
        self.wait(0.5)

import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Polar grid with spirals").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        plane = m.PolarPlane(radius_max=3.5, size=7)
        self.add(plane)

        spiral1 = m.ParametricFunction(
            lambda theta: (
                0.3 * theta * np.array([math.cos(theta), math.sin(theta), 0.0])
            ),
            t_range=[0, 4 * math.pi],
            color=m.YELLOW,
            stroke_width=2.5,
        )
        spiral2 = m.ParametricFunction(
            lambda theta: (
                0.3
                * math.exp(0.1 * theta)
                * np.array([math.cos(theta), math.sin(theta), 0.0])
            ),
            t_range=[0, 4 * math.pi],
            color=m.RED,
            stroke_width=2.5,
        )

        self.play(m.Create(spiral1), run_time=2.0)
        self.play(m.Create(spiral2), run_time=2.0)
        self.wait(1.5)

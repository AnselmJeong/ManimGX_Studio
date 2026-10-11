import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Cardioid: $r = 1 + \\cos\\theta$").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        cardioid = m.ParametricFunction(
            lambda theta: (
                (1 + math.cos(theta))
                * np.array([math.cos(theta), math.sin(theta), 0.0])
            ),
            t_range=[0, 2 * math.pi],
            color=m.YELLOW,
            stroke_width=3,
        ).scale(2.0)
        self.play(m.Create(cardioid), run_time=4.0)
        self.wait(1.5)

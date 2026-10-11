import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Heart phase portrait").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        heart = m.ParametricFunction(
            lambda t: (
                0.15
                * np.array(
                    [
                        16 * math.sin(t) ** 3,
                        13 * math.cos(t)
                        - 5 * math.cos(2 * t)
                        - 2 * math.cos(3 * t)
                        - math.cos(4 * t),
                        0.0,
                    ]
                )
            ),
            t_range=[0, 2 * math.pi],
            color=m.RED,
            stroke_width=4,
        )
        self.play(m.Create(heart), run_time=3.5)
        self.wait(1.5)

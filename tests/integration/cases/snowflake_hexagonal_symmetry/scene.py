import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Snowflake: $D_6$ symmetry").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        snowflake = m.VGroup()
        for k in range(6):
            angle = k * math.pi / 3
            spine_dir = np.array([math.cos(angle), math.sin(angle), 0.0])
            spine = m.Line(
                np.array([0.0, 0.0, 0.0]), 2 * spine_dir, color=m.WHITE, stroke_width=3
            )
            snowflake.add(spine)
            for branch in [-1, 1]:
                branch_dir = np.array(
                    [
                        math.cos(angle + branch * math.pi / 4),
                        math.sin(angle + branch * math.pi / 4),
                        0.0,
                    ]
                )
                snowflake.add(
                    m.Line(
                        1.3 * spine_dir,
                        1.3 * spine_dir + 0.55 * branch_dir,
                        color=m.WHITE,
                        stroke_width=2,
                    ),
                )

        self.play(m.Create(snowflake), run_time=1.5)

        for _ in range(3):
            self.play(snowflake.animate.rotate(math.pi / 3), run_time=1.2)
            self.wait(0.3)
        self.wait(1.0)

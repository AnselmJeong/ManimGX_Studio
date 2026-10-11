import numpy as np

import manimgx as m

M = np.array([[1.0, 2.0], [2.0, 4.0]])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-5, 5, 1],
            y_range=[-3, 3, 1],
            x_length=11,
            y_length=7,
        )
        self.add(plane)

        cap = m.Tex("Singular matrix: ", "$\\det = 0$").to_edge(m.UP, buff=0.4)
        cap[1].set_color(m.RED)
        self.play(m.Write(cap))
        self.wait(0.4)

        self.play(m.ApplyMatrix(M.tolist(), plane), run_time=2.6)

        cap2 = (
            m.Tex(
                "Plane collapses onto a line — no inverse exists",
            )
            .scale(0.95)
            .set_color(m.RED)
            .to_edge(m.DOWN, buff=0.5)
        )
        self.play(m.Write(cap2))
        self.wait(2.0)

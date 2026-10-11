import numpy as np

import manimgx as m

M = np.array([[1.5, 0.5], [-0.5, 1.0]])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-4, 4, 1],
            y_range=[-3, 3, 1],
            x_length=10,
            y_length=7,
        )
        self.add(plane)

        cap = m.Tex("Apply ", "$M$").to_edge(m.UP, buff=0.4)
        cap[1].set_color(m.BLUE)
        self.play(m.Write(cap))
        self.play(m.ApplyMatrix(M.tolist(), plane), run_time=1.7)
        self.wait(0.5)

        M_inv = np.linalg.inv(M)
        cap2 = m.Tex("Apply ", "$M^{-1}$").to_edge(m.UP, buff=0.4)
        cap2[1].set_color(m.RED)
        self.play(m.Transform(cap, cap2))
        self.play(m.ApplyMatrix(M_inv.tolist(), plane), run_time=1.7)
        self.wait(0.5)

        cap3 = m.Tex("Back to identity: ", "$M^{-1} M = I$").to_edge(m.UP, buff=0.4)
        cap3[1].set_color(m.YELLOW)
        self.play(m.Transform(cap, cap3))
        self.wait(2.0)

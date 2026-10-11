import math

import numpy as np

import manimgx as m

THETA = math.pi / 4
M1 = np.array([[math.cos(THETA), -math.sin(THETA)], [math.sin(THETA), math.cos(THETA)]])
M2 = np.array([[1.0, 1.0], [0.0, 1.0]])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-5, 5, 1], y_range=[-3, 3, 1], x_length=11, y_length=7
        )
        self.add(plane)
        self.wait(0.3)

        cap1 = m.Tex("First apply ", "$A$").to_edge(m.UP, buff=0.4)
        cap1[1].set_color(m.BLUE)
        self.play(m.Write(cap1))
        self.play(m.ApplyMatrix(M1.tolist(), plane), run_time=1.6)
        self.wait(0.5)

        cap2 = m.Tex("Then apply ", "$B$").to_edge(m.UP, buff=0.4)
        cap2[1].set_color(m.RED)
        self.play(m.Transform(cap1, cap2))
        self.play(m.ApplyMatrix(M2.tolist(), plane), run_time=1.6)
        self.wait(0.5)

        cap3 = m.Tex("$=$ apply ", "$B A$", " in one step").to_edge(m.UP, buff=0.4)
        cap3[1].set_color(m.YELLOW)
        self.play(m.Transform(cap1, cap3))
        self.wait(2.0)

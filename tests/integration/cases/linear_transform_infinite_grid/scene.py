import numpy as np

import manimgx as m

M = np.array([[1.0, 1.5], [0.0, 1.0]])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-15, 15, 1],
            y_range=[-15, 15, 1],
            x_length=28,
            y_length=28,
            background_line_style={"stroke_color": m.BLUE_E, "stroke_width": 1.5},
        )
        self.add(plane)
        self.wait(0.5)

        caption = m.Tex("Every gridline transforms together").to_edge(m.UP, buff=0.4)
        self.play(m.Write(caption))
        self.wait(0.4)

        self.play(m.ApplyMatrix(M.tolist(), plane), run_time=3.0)
        self.wait(1.8)

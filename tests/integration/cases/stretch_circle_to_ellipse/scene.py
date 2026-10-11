import numpy as np

import manimgx as m

M = np.array([[1.8, 0.0], [0.0, 1.0]])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-4, 4, 1],
            y_range=[-2, 2, 1],
            x_length=10,
            y_length=6,
        )
        self.add(plane)

        title = (
            m.Tex(
                "Stretching a circle gives an ellipse",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        circle = m.Circle(radius=1.5, color=m.YELLOW, stroke_width=3)
        circle.move_to(plane.coords_to_point(0, 0))
        self.play(m.Create(circle))
        self.wait(0.4)

        self.play(m.ApplyMatrix(M.tolist(), circle), run_time=2.5)
        self.wait(2.0)

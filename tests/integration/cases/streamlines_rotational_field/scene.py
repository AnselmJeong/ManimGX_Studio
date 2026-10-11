"""Show the flow of the vector field F(x, y) = (-y, x)."""

import numpy as np

import manimgx as m


def _field(point: np.ndarray) -> np.ndarray:
    return np.array([-point[1], point[0], 0.0])


class TeacherScene(m.Scene):
    def construct(self):
        plane = m.NumberPlane(
            x_range=(-6.0, 6.0, 1.0),
            y_range=(-3.5, 3.5, 1.0),
            x_length=12.0,
            y_length=7.0,
        )
        lines = m.StreamLines(
            _field,
            x_range=[-5.0, 5.0, 0.5],
            y_range=[-3.0, 3.0, 0.5],
            stroke_width=2.0,
        )

        label = m.MathTex(R"F(x, y) = (-y, x)").to_corner(m.UR, buff=0.5)

        self.play(m.Create(plane), run_time=1.5)
        self.play(m.Write(label), run_time=1.0)
        self.play(lines.create(), run_time=3.0)
        self.wait(2.0)
        self.wait(0.5)

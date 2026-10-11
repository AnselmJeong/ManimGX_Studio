"""Draw the gradient field of f(x, y) = x^2 + y^2."""

import numpy as np

import manimgx as m


def _grad(point: np.ndarray) -> np.ndarray:
    return np.array([2.0 * point[0], 2.0 * point[1], 0.0]) / 6.0


class TeacherScene(m.Scene):
    def construct(self):
        axes = m.Axes(
            x_range=(-3.5, 3.5, 1.0),
            y_range=(-2.5, 2.5, 1.0),
            x_length=11.0,
            y_length=6.0,
        )
        field = m.ArrowVectorField(
            _grad,
            x_range=[-3.5, 3.5, 0.5],
            y_range=[-2.5, 2.5, 0.5],
        )

        label = m.MathTex(R"\nabla f = (2x, 2y)").to_corner(m.UR, buff=0.5)

        self.play(m.Create(axes), run_time=1.5)
        self.play(m.FadeIn(field), run_time=2.0)
        self.play(m.Write(label), run_time=1.0)
        self.wait(1.5)
        self.wait(0.5)

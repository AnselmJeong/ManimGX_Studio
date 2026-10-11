import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("A unit disk becomes an ellipse").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        plane = (
            m.NumberPlane(
                x_range=[-4, 4, 1],
                y_range=[-2.5, 2.5, 1],
                background_line_style={"stroke_opacity": 0.3, "stroke_color": m.GREY_B},
            )
            .scale(0.85)
            .shift(m.DOWN * 0.3)
        )
        self.play(m.Create(plane))

        disk = m.Circle(radius=1.0, color=m.BLUE, stroke_width=3.0).move_to(
            plane.coords_to_point(0, 0)
        )
        v1 = m.Arrow(
            plane.coords_to_point(0, 0),
            plane.coords_to_point(1, 1),
            color=m.YELLOW,
            buff=0,
            stroke_width=4,
        )
        v2 = m.Arrow(
            plane.coords_to_point(0, 0),
            plane.coords_to_point(1, -1),
            color=m.RED,
            buff=0,
            stroke_width=4,
        )
        self.play(m.Create(disk), m.GrowArrow(v1), m.GrowArrow(v2))

        A = np.array([[2.0, 2.0], [1.0, 2.0]])
        evals, evecs = np.linalg.eig(A)
        # Ellipse via parametric
        thetas = np.linspace(0, 2 * math.pi, 60)
        pts = []
        for th in thetas:
            v = np.array([math.cos(th), math.sin(th)])
            w = A @ v
            pts.append(plane.coords_to_point(w[0], w[1]))
        ellipse = m.VMobject(stroke_color=m.BLUE, stroke_width=3.0)
        ellipse.set_points_as_corners(pts + [pts[0]])

        # Map eigenvectors (assume unit length) — scale by λ
        evec1 = evecs[:, 0] / np.linalg.norm(evecs[:, 0]) * evals[0].real
        evec2 = evecs[:, 1] / np.linalg.norm(evecs[:, 1]) * evals[1].real
        v1_new = m.Arrow(
            plane.coords_to_point(0, 0),
            plane.coords_to_point(evec1[0], evec1[1]),
            color=m.YELLOW,
            buff=0,
            stroke_width=4,
        )
        v2_new = m.Arrow(
            plane.coords_to_point(0, 0),
            plane.coords_to_point(evec2[0], evec2[1]),
            color=m.RED,
            buff=0,
            stroke_width=4,
        )

        self.play(
            m.Transform(disk, ellipse),
            m.Transform(v1, v1_new),
            m.Transform(v2, v2_new),
            run_time=2.5,
        )

        eq = (
            m.MathTex("A = \\begin{bmatrix} 2 & 2 \\\\ 1 & 2 \\end{bmatrix}")
            .scale(0.75)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(eq))
        self.wait(1.5)

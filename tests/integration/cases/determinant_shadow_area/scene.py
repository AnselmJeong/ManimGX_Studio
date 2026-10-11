import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("$\\det A$ = ratio of areas").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        plane = (
            m.NumberPlane(
                x_range=[-3, 3, 1],
                y_range=[-2.4, 2.4, 1],
                background_line_style={"stroke_opacity": 0.3, "stroke_color": m.GREY_B},
            )
            .scale(0.9)
            .shift(m.DOWN * 0.3)
        )
        self.play(m.Create(plane))

        unit = m.Polygon(
            plane.coords_to_point(0, 0),
            plane.coords_to_point(1, 0),
            plane.coords_to_point(1, 1),
            plane.coords_to_point(0, 1),
            color=m.BLUE,
            fill_color=m.BLUE,
            fill_opacity=0.4,
            stroke_width=3,
        )
        self.play(m.Create(unit))

        A = np.array([[1.5, 0.4], [0.3, 1.2]])
        verts = [np.array([0, 0]), np.array([1, 0]), np.array([1, 1]), np.array([0, 1])]
        mapped = [A @ v for v in verts]
        target = m.Polygon(
            *[plane.coords_to_point(p[0], p[1]) for p in mapped],
            color=m.RED,
            fill_color=m.RED,
            fill_opacity=0.4,
            stroke_width=3,
        )
        self.play(m.Transform(unit, target), run_time=2.0)

        det = float(np.linalg.det(A))
        result = (
            m.MathTex(f"\\det A = {det:.2f}", color=m.YELLOW)
            .scale(0.95)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(result))
        self.wait(1.5)

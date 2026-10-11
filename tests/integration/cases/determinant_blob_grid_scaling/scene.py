import numpy as np

import manimgx as m

M = np.array([[2.0, 1.0], [0.0, 2.0]])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-1, 5, 1],
            y_range=[-1, 5, 1],
            x_length=8,
            y_length=8,
        )
        self.add(plane)

        square = m.Polygon(
            plane.coords_to_point(0, 0),
            plane.coords_to_point(1, 0),
            plane.coords_to_point(1, 1),
            plane.coords_to_point(0, 1),
            color=m.YELLOW,
            fill_color=m.YELLOW,
            fill_opacity=0.5,
            stroke_width=2.5,
        )
        area_label = m.MathTex("\\text{Area} = 1", color=m.YELLOW).to_corner(
            m.UR, buff=0.5
        )
        bg = m.BackgroundRectangle(
            area_label, color=m.BLACK, fill_opacity=0.75, buff=0.12
        )
        self.play(m.FadeIn(square), m.FadeIn(bg), m.Write(area_label))
        self.wait(0.5)

        det = float(np.linalg.det(M))
        new_corners = [
            plane.coords_to_point(*(M @ np.array([x, y])))
            for x, y in [(0, 0), (1, 0), (1, 1), (0, 1)]
        ]
        new_square = m.Polygon(
            *new_corners,
            color=m.YELLOW,
            fill_color=m.YELLOW,
            fill_opacity=0.5,
            stroke_width=2.5,
        )
        new_area_label = m.MathTex(
            f"\\text{{Area}} = {det:g}",
            color=m.YELLOW,
        ).to_corner(m.UR, buff=0.5)
        new_bg = m.BackgroundRectangle(
            new_area_label, color=m.BLACK, fill_opacity=0.75, buff=0.12
        )

        self.play(
            m.ApplyMatrix(M.tolist(), plane),
            m.Transform(square, new_square),
            m.Transform(area_label, new_area_label),
            m.Transform(bg, new_bg),
            run_time=2.2,
        )

        det_caption = (
            m.MathTex("\\det(M) = ", f"{det:g}").scale(1.0).to_edge(m.DOWN, buff=0.5)
        )
        det_caption[1].set_color(m.YELLOW)
        self.play(m.Write(det_caption))
        self.wait(2.0)

import numpy as np

import manimgx as m

M = np.array([[2.0, 1.0], [-1.0, 1.0]])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-3, 4, 1],
            y_range=[-2, 3, 1],
            x_length=10,
            y_length=7,
        )
        self.play(m.Create(plane), run_time=0.9)

        origin = plane.coords_to_point(0, 0)
        i_arrow = m.Arrow(
            origin,
            plane.coords_to_point(1, 0),
            color=m.GREEN,
            buff=0,
            stroke_width=6,
        )
        j_arrow = m.Arrow(
            origin,
            plane.coords_to_point(0, 1),
            color=m.RED,
            buff=0,
            stroke_width=6,
        )
        i_label = m.MathTex("\\hat{\\imath}", color=m.GREEN).next_to(
            i_arrow.get_end(),
            m.DR,
            buff=0.15,
        )
        j_label = m.MathTex("\\hat{\\jmath}", color=m.RED).next_to(
            j_arrow.get_end(),
            m.UL,
            buff=0.15,
        )
        self.play(
            m.GrowArrow(i_arrow),
            m.GrowArrow(j_arrow),
            m.Write(i_label),
            m.Write(j_label),
        )
        self.wait(0.5)

        new_i_xy = M @ np.array([1.0, 0.0])
        new_j_xy = M @ np.array([0.0, 1.0])
        new_i_pt = plane.coords_to_point(new_i_xy[0], new_i_xy[1])
        new_j_pt = plane.coords_to_point(new_j_xy[0], new_j_xy[1])
        new_i = m.Arrow(origin, new_i_pt, color=m.GREEN, buff=0, stroke_width=6)
        new_j = m.Arrow(origin, new_j_pt, color=m.RED, buff=0, stroke_width=6)
        new_i_label = (
            m.MathTex(
                "\\hat{\\imath}' = (2, -1)",
                color=m.GREEN,
            )
            .scale(0.8)
            .next_to(new_i_pt, m.DR, buff=0.15)
        )
        new_j_label = (
            m.MathTex(
                "\\hat{\\jmath}' = (1, 1)",
                color=m.RED,
            )
            .scale(0.8)
            .next_to(new_j_pt, m.UR, buff=0.15)
        )

        self.play(
            m.ApplyMatrix(M.tolist(), plane),
            m.Transform(i_arrow, new_i),
            m.Transform(j_arrow, new_j),
            m.Transform(i_label, new_i_label),
            m.Transform(j_label, new_j_label),
            run_time=2.2,
        )

        matrix = (
            m.Matrix([["2", "1"], ["-1", "1"]])
            .scale(0.9)
            .to_corner(
                m.UR,
                buff=0.5,
            )
        )
        matrix.get_columns()[0].set_color(m.GREEN)
        matrix.get_columns()[1].set_color(m.RED)
        matrix_bg = m.BackgroundRectangle(
            matrix,
            color=m.BLACK,
            fill_opacity=0.78,
            buff=0.12,
        )
        self.play(m.FadeIn(matrix_bg), m.Write(matrix))

        caption = (
            m.Tex(
                "Matrix columns ",
                "$=$",
                " transformed basis vectors",
            )
            .scale(0.75)
            .to_edge(m.DOWN, buff=0.4)
        )
        self.play(m.Write(caption))
        self.wait(2.0)

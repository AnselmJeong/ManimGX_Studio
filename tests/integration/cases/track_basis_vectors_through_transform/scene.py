import numpy as np

import manimgx as m

M = np.array([[3.0, 1.0], [0.0, 2.0]])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-2, 5, 1], y_range=[-2, 4, 1], x_length=10, y_length=7
        )
        self.add(plane)

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
            m.DOWN,
            buff=0.15,
        )
        j_label = m.MathTex("\\hat{\\jmath}", color=m.RED).next_to(
            j_arrow.get_end(),
            m.LEFT,
            buff=0.15,
        )
        self.play(m.GrowArrow(i_arrow), m.GrowArrow(j_arrow))
        self.play(m.Write(i_label), m.Write(j_label))
        self.wait(0.5)

        new_i_xy = M @ np.array([1.0, 0.0])
        new_j_xy = M @ np.array([0.0, 1.0])
        new_i = m.Arrow(
            origin,
            plane.coords_to_point(new_i_xy[0], new_i_xy[1]),
            color=m.GREEN,
            buff=0,
            stroke_width=6,
        )
        new_j = m.Arrow(
            origin,
            plane.coords_to_point(new_j_xy[0], new_j_xy[1]),
            color=m.RED,
            buff=0,
            stroke_width=6,
        )
        new_i_label = m.MathTex(
            f"({int(new_i_xy[0])}, {int(new_i_xy[1])})",
            color=m.GREEN,
        ).next_to(new_i.get_end(), m.DOWN, buff=0.2)
        new_j_label = m.MathTex(
            f"({int(new_j_xy[0])}, {int(new_j_xy[1])})",
            color=m.RED,
        ).next_to(new_j.get_end(), m.LEFT, buff=0.2)

        self.play(
            m.ApplyMatrix(M.tolist(), plane),
            m.Transform(i_arrow, new_i),
            m.Transform(j_arrow, new_j),
            m.Transform(i_label, new_i_label),
            m.Transform(j_label, new_j_label),
            run_time=2.5,
        )
        self.wait(1.8)

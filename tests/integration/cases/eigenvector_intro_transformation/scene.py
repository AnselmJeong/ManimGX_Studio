import numpy as np

import manimgx as m

M = np.array([[2.0, 1.0], [0.0, 3.0]])
EIGEN = np.array([1.0, 1.0])
OTHER = np.array([1.0, 0.4])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-1, 5, 1],
            y_range=[-1, 4, 1],
            x_length=10,
            y_length=8,
        )
        self.add(plane)

        origin = plane.coords_to_point(0, 0)
        eigen_arr = m.Arrow(
            origin,
            plane.coords_to_point(EIGEN[0], EIGEN[1]),
            color=m.YELLOW,
            buff=0,
            stroke_width=6,
        )
        other_arr = m.Arrow(
            origin,
            plane.coords_to_point(OTHER[0], OTHER[1]),
            color=m.BLUE,
            buff=0,
            stroke_width=6,
        )
        eigen_label = m.MathTex(
            "\\vec{v}_{\\text{eig}}",
            color=m.YELLOW,
        ).next_to(eigen_arr.get_end(), m.UP, buff=0.15)
        other_label = m.MathTex(
            "\\vec{w}",
            color=m.BLUE,
        ).next_to(other_arr.get_end(), m.DOWN, buff=0.15)
        self.play(m.GrowArrow(eigen_arr), m.GrowArrow(other_arr))
        self.play(m.Write(eigen_label), m.Write(other_label))
        self.wait(0.4)

        new_eigen = M @ EIGEN
        new_other = M @ OTHER
        new_eigen_arr = m.Arrow(
            origin,
            plane.coords_to_point(new_eigen[0], new_eigen[1]),
            color=m.YELLOW,
            buff=0,
            stroke_width=6,
        )
        new_other_arr = m.Arrow(
            origin,
            plane.coords_to_point(new_other[0], new_other[1]),
            color=m.BLUE,
            buff=0,
            stroke_width=6,
        )

        self.play(
            m.ApplyMatrix(M.tolist(), plane),
            m.Transform(eigen_arr, new_eigen_arr),
            m.Transform(other_arr, new_other_arr),
            run_time=2.5,
        )

        caption = (
            m.Tex(
                "Eigenvector only ",
                "stretches",
                "; other vectors ",
                "rotate too",
            )
            .scale(0.8)
            .to_edge(m.UP, buff=0.4)
        )
        caption[1].set_color(m.YELLOW)
        caption[3].set_color(m.BLUE)
        self.play(m.Write(caption))
        self.wait(2.0)

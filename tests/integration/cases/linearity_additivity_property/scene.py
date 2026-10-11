import numpy as np

import manimgx as m

V = np.array([2.0, 0.5])
W = np.array([0.5, 1.5])
M = np.array([[1.0, -0.5], [0.5, 1.0]])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-1, 5, 1],
            y_range=[-1, 4, 1],
            x_length=10,
            y_length=7,
        )
        self.add(plane)
        origin = plane.coords_to_point(0, 0)

        def arrow(start_xy, end_xy, color, stroke=5):
            return m.Arrow(
                plane.coords_to_point(*start_xy),
                plane.coords_to_point(*end_xy),
                color=color,
                buff=0,
                stroke_width=stroke,
            )

        v_arr = arrow((0, 0), tuple(V), m.YELLOW)
        w_arr = arrow(tuple(V), tuple(V + W), m.BLUE)
        sum_arr = arrow((0, 0), tuple(V + W), m.GREEN, 6)
        self.play(m.GrowArrow(v_arr), m.GrowArrow(w_arr))
        self.play(m.GrowArrow(sum_arr))
        self.wait(0.5)

        Mv = M @ V
        Mw = M @ W
        Mvw = M @ (V + W)
        new_v = arrow((0, 0), tuple(Mv), m.YELLOW)
        new_w = arrow(tuple(Mv), tuple(Mv + Mw), m.BLUE)
        new_sum = arrow((0, 0), tuple(Mvw), m.GREEN, 6)
        self.play(
            m.Transform(v_arr, new_v),
            m.Transform(w_arr, new_w),
            m.Transform(sum_arr, new_sum),
            m.ApplyMatrix(M.tolist(), plane),
            run_time=2.2,
        )

        caption = (
            m.MathTex(
                "T(\\vec{v} + \\vec{w}) = T(\\vec{v}) + T(\\vec{w})",
                color=m.YELLOW,
            )
            .scale(0.9)
            .to_edge(m.UP, buff=0.4)
        )
        self.play(m.Write(caption))
        self.wait(2.0)

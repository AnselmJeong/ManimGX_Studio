import numpy as np

import manimgx as m

V = np.array([2.0, 1.0, 0.0])
W = np.array([1.0, 2.0, 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-1, 4, 1],
            y_range=[-1, 4, 1],
            x_length=10,
            y_length=8,
        )
        self.play(m.Create(plane), run_time=0.8)

        origin = plane.coords_to_point(0, 0)
        v_end = plane.coords_to_point(V[0], V[1])
        w_end = plane.coords_to_point(W[0], W[1])
        sum_end = plane.coords_to_point((V + W)[0], (V + W)[1])

        v_arrow = m.Arrow(origin, v_end, color=m.YELLOW, buff=0, stroke_width=5)
        w_arrow = m.Arrow(origin, w_end, color=m.BLUE, buff=0, stroke_width=5)
        v_label = m.MathTex("\\vec{v}", color=m.YELLOW).next_to(
            v_arrow.get_end(), m.DR, buff=0.1
        )
        w_label = m.MathTex("\\vec{w}", color=m.BLUE).next_to(
            w_arrow.get_end(), m.UL, buff=0.1
        )
        self.play(m.GrowArrow(v_arrow), m.GrowArrow(w_arrow))
        self.play(m.Write(v_label), m.Write(w_label))
        self.wait(0.5)

        w_shifted = m.Arrow(v_end, sum_end, color=m.BLUE, buff=0, stroke_width=5)
        self.play(m.Transform(w_arrow, w_shifted), m.FadeOut(w_label), run_time=1.2)
        self.wait(0.3)

        sum_arrow = m.Arrow(origin, sum_end, color=m.GREEN, buff=0, stroke_width=6)
        sum_label = m.MathTex(
            "\\vec{v} + \\vec{w}",
            color=m.GREEN,
        ).next_to(sum_arrow.get_end(), m.UR, buff=0.1)
        self.play(m.GrowArrow(sum_arrow), m.Write(sum_label))
        self.wait(2.0)

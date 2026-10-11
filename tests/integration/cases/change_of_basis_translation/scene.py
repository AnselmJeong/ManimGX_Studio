import numpy as np

import manimgx as m

V = np.array([2.0, 1.0])
B1 = np.array([1.0, 1.0])
B2 = np.array([-1.0, 1.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        plane = m.NumberPlane(
            x_range=[-3, 4, 1],
            y_range=[-2, 3, 1],
            x_length=11,
            y_length=8,
        )
        self.play(m.Create(plane), run_time=0.9)

        origin = plane.coords_to_point(0, 0)
        v_end = plane.coords_to_point(V[0], V[1])
        v_arrow = m.Arrow(origin, v_end, color=m.YELLOW, buff=0, stroke_width=5)
        v_std = (
            m.MathTex(
                "\\vec{v} = (2, 1)_{\\text{std}}",
                color=m.YELLOW,
            )
            .scale(0.85)
            .next_to(v_arrow.get_end(), m.UR, buff=0.2)
        )
        self.play(m.GrowArrow(v_arrow), m.Write(v_std))
        self.wait(0.5)

        b1_end = plane.coords_to_point(B1[0], B1[1])
        b2_end = plane.coords_to_point(B2[0], B2[1])
        b1_arrow = m.Arrow(origin, b1_end, color=m.GREEN, buff=0, stroke_width=5)
        b2_arrow = m.Arrow(origin, b2_end, color=m.RED, buff=0, stroke_width=5)
        b1_label = m.MathTex("\\vec{b}_1", color=m.GREEN).next_to(
            b1_arrow.get_end(), m.DR, buff=0.1
        )
        b2_label = m.MathTex("\\vec{b}_2", color=m.RED).next_to(
            b2_arrow.get_end(), m.UL, buff=0.1
        )
        self.play(
            m.GrowArrow(b1_arrow),
            m.GrowArrow(b2_arrow),
            m.Write(b1_label),
            m.Write(b2_label),
        )
        self.wait(0.5)

        B = np.column_stack([B1, B2])
        c = np.linalg.solve(B, V)
        v_jen = (
            m.MathTex(
                f"\\vec{{v}} = ({c[0]:.2f}, {c[1]:.2f})_{{J}}",
                color=m.YELLOW,
            )
            .scale(0.85)
            .next_to(v_arrow.get_end(), m.UR, buff=0.2)
        )
        self.play(m.Transform(v_std, v_jen))

        caption = (
            m.Tex(
                "Same vector, different coordinates in different bases",
            )
            .scale(0.8)
            .to_edge(m.DOWN, buff=0.4)
        )
        self.play(m.Write(caption))
        self.wait(2.0)

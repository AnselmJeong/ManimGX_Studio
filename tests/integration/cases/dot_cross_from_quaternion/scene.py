import numpy as np

import manimgx as m

V = np.array([2.5, 1.5, 0.0])
W = np.array([1.0, 2.0, 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex(
                "Quaternion mult = scalar (dot) + vector (cross)",
            )
            .scale(0.75)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        origin = np.array([0.0, 0.0, 0.0])
        v_arr = m.Arrow(origin, V, color=m.GREEN, buff=0, stroke_width=5)
        w_arr = m.Arrow(origin, W, color=m.RED, buff=0, stroke_width=5)
        v_label = m.MathTex("\\vec{v}", color=m.GREEN).next_to(
            v_arr.get_end(), m.UR, buff=0.1
        )
        w_label = m.MathTex("\\vec{w}", color=m.RED).next_to(
            w_arr.get_end(), m.UL, buff=0.1
        )
        self.play(
            m.GrowArrow(v_arr), m.GrowArrow(w_arr), m.Write(v_label), m.Write(w_label)
        )

        dot_val = float(np.dot(V[:2], W[:2]))
        cross_val = float(V[0] * W[1] - V[1] * W[0])

        dot_label = m.MathTex(
            f"\\vec{{v}} \\cdot \\vec{{w}} = {dot_val:.2f}",
            color=m.YELLOW,
        ).shift(m.DOWN * 2.5 + m.LEFT * 3)
        cross_label = m.MathTex(
            f"\\vec{{v}} \\times \\vec{{w}} = {cross_val:.2f}",
            color=m.BLUE,
        ).shift(m.DOWN * 2.5 + m.RIGHT * 3)
        self.play(m.Write(dot_label), m.Write(cross_label))
        self.wait(2.0)

import numpy as np

import manimgx as m

A = 3.0
B = 4.0
SCALE = 0.7


class TeacherScene(m.Scene):
    def construct(self) -> None:
        center = -np.array([A * SCALE / 2.0, B * SCALE / 2.0, 0.0])
        p1 = center
        p2 = p1 + np.array([A * SCALE, 0.0, 0.0])
        p3 = p1 + np.array([0.0, B * SCALE, 0.0])

        triangle = m.Polygon(
            p1,
            p2,
            p3,
            color=m.WHITE,
            fill_color=m.GREY,
            fill_opacity=0.3,
            stroke_width=2,
        )

        hyp = p3 - p2
        t = np.dot(p1 - p2, hyp) / np.dot(hyp, hyp)
        foot = p2 + t * hyp

        altitude = m.Line(p1, foot, color=m.RED, stroke_width=3)

        a_label = (
            m.MathTex("a", color=m.GREEN)
            .scale(0.85)
            .move_to(
                (p1 + p2) / 2 + np.array([0.0, -0.25, 0.0]),
            )
        )
        b_label = (
            m.MathTex("b", color=m.BLUE)
            .scale(0.85)
            .move_to(
                (p1 + p3) / 2 + np.array([-0.25, 0.0, 0.0]),
            )
        )
        h_label = (
            m.MathTex("h", color=m.RED)
            .scale(0.85)
            .move_to(
                (p1 + foot) / 2 + np.array([0.15, 0.15, 0.0]),
            )
        )

        self.play(m.Create(triangle))
        self.play(m.Write(a_label), m.Write(b_label))
        self.play(m.Create(altitude), m.Write(h_label))

        eq = m.MathTex(
            "\\frac{1}{h^2} = \\frac{1}{a^2} + \\frac{1}{b^2}",
            color=m.YELLOW,
        ).to_edge(m.DOWN, buff=0.6)
        self.play(m.Write(eq))
        self.wait(2.0)

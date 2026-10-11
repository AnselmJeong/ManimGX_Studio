import math

import numpy as np

import manimgx as m

SIZE = 1.8


class TeacherScene(m.Scene):
    def construct(self) -> None:
        TL = SIZE * np.array([math.cos(math.pi / 2), math.sin(math.pi / 2), 0])
        BL = SIZE * np.array([math.cos(7 * math.pi / 6), math.sin(7 * math.pi / 6), 0])
        BR = SIZE * np.array([math.cos(-math.pi / 6), math.sin(-math.pi / 6), 0])
        TL += m.LEFT * 3
        BL += m.LEFT * 3
        BR += m.LEFT * 3

        triangle = m.Polygon(TL, BL, BR, color=m.WHITE, stroke_width=3, fill_opacity=0)
        x_label = m.MathTex("x", color=m.GREEN).scale(1.3).next_to(BL, m.DL, buff=0.15)
        y_label = m.MathTex("y", color=m.RED).scale(1.3).next_to(TL, m.UP, buff=0.15)
        z_label = m.MathTex("z", color=m.YELLOW).scale(1.3).next_to(BR, m.DR, buff=0.15)

        self.play(m.Create(triangle))
        self.play(m.Write(x_label), m.Write(y_label), m.Write(z_label))
        self.wait(0.6)

        right_x = 3.5
        exp_eq = m.MathTex("x^y = z").scale(1.4).move_to([right_x, 1.5, 0])
        log_eq = m.MathTex("\\log_x z = y").scale(1.4).move_to([right_x, 0, 0])
        root_eq = m.MathTex("z^{1/y} = x").scale(1.4).move_to([right_x, -1.5, 0])

        self.play(m.Write(exp_eq))
        self.wait(0.4)
        self.play(m.Write(log_eq))
        self.wait(0.4)
        self.play(m.Write(root_eq))

        caption = (
            m.Tex("Three operations, one triangle").scale(0.8).to_edge(m.DOWN, buff=0.4)
        )
        self.play(m.Write(caption))
        self.wait(2.0)

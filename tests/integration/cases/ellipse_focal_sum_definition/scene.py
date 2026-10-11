import math

import numpy as np

import manimgx as m

A_AX = 2.6
B_AX = 1.9
C = math.sqrt(A_AX * A_AX - B_AX * B_AX)
F1 = np.array([-C, 0.0, 0.0])
F2 = np.array([C, 0.0, 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        ellipse = m.Ellipse(
            width=2 * A_AX, height=2 * B_AX, color=m.WHITE, stroke_width=2
        )
        self.add(ellipse)

        title = (
            m.Tex(
                "Ellipse: sum of focal distances = constant",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        f1_dot = m.Dot(F1, color=m.YELLOW, radius=0.1)
        f2_dot = m.Dot(F2, color=m.YELLOW, radius=0.1)
        f1_label = (
            m.MathTex("F_1", color=m.YELLOW)
            .scale(0.7)
            .next_to(f1_dot, m.DOWN, buff=0.1)
        )
        f2_label = (
            m.MathTex("F_2", color=m.YELLOW)
            .scale(0.7)
            .next_to(f2_dot, m.DOWN, buff=0.1)
        )
        self.play(
            m.FadeIn(f1_dot), m.FadeIn(f2_dot), m.Write(f1_label), m.Write(f2_label)
        )

        t = m.ValueTracker(0.0)

        def point() -> np.ndarray:
            theta = t.get_value()
            return np.array([A_AX * math.cos(theta), B_AX * math.sin(theta), 0.0])

        p_dot = m.always_redraw(lambda: m.Dot(point(), color=m.GREEN, radius=0.1))
        line1 = m.always_redraw(
            lambda: m.Line(F1, point(), color=m.BLUE, stroke_width=2.5)
        )
        line2 = m.always_redraw(
            lambda: m.Line(F2, point(), color=m.RED, stroke_width=2.5)
        )
        self.add(p_dot, line1, line2)

        sum_label = m.always_redraw(
            lambda: (
                m.MathTex(
                    "|F_1 P| + |F_2 P| \\approx"
                    f" {np.linalg.norm(point() - F1) + np.linalg.norm(point() - F2):.2f}",
                )
                .scale(0.7)
                .to_edge(m.DOWN, buff=0.45)
            ),
        )
        self.add(sum_label)

        self.play(t.animate.set_value(2 * math.pi), run_time=6.0, rate_func=m.linear)
        self.wait(1.0)

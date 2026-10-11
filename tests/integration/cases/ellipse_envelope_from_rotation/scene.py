import math

import numpy as np

import manimgx as m

R = 2.5
FOCUS = np.array([1.0, 0.0, 0.0])
N_LINES = 80


class TeacherScene(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=R, color=m.WHITE, stroke_width=2)
        self.add(circle)

        focus_dot = m.Dot(FOCUS, color=m.YELLOW, radius=0.1)
        focus_label = m.MathTex("F", color=m.YELLOW).next_to(focus_dot, m.UR, buff=0.1)
        self.play(m.FadeIn(focus_dot), m.Write(focus_label))

        bisectors = m.VGroup()
        for k in range(N_LINES):
            angle = 2 * math.pi * k / N_LINES
            p = R * np.array([math.cos(angle), math.sin(angle), 0.0])
            mid = (p + FOCUS) / 2
            direction = p - FOCUS
            perp = np.array([-direction[1], direction[0], 0.0])
            perp = perp / np.linalg.norm(perp) * 2.5
            bisectors.add(
                m.Line(
                    mid - perp,
                    mid + perp,
                    color=m.BLUE,
                    stroke_width=1.0,
                    stroke_opacity=0.45,
                ),
            )
        self.play(m.Create(bisectors, lag_ratio=0.005), run_time=4.0)

        title = (
            m.Tex(
                "Envelope of perpendicular bisectors = ellipse",
            )
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))
        self.wait(1.5)

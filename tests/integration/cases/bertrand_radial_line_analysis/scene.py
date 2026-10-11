import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Bertrand: geometric analysis").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        R = 2.2
        center = np.array([-1.5, -0.4, 0.0])
        circle = m.Circle(radius=R, color=m.WHITE, stroke_width=2.0).move_to(center)
        triangle = (
            m.RegularPolygon(n=3, color=m.YELLOW, stroke_width=2.0)
            .scale(R)
            .move_to(center)
        )
        self.play(m.Create(circle), m.Create(triangle))

        radius_line = m.Line(
            center, center + np.array([R, 0.0, 0.0]), color=m.WHITE, stroke_width=2.0
        )
        self.play(m.Create(radius_line))

        half_pt = center + np.array([R / 2.0, 0.0, 0.0])
        marker = m.Dot(half_pt, color=m.RED, radius=0.07)
        marker_label = (
            m.MathTex("R/2", color=m.RED).scale(0.65).next_to(marker, m.DOWN, buff=0.18)
        )
        self.play(m.FadeIn(marker), m.Write(marker_label))

        inner_arc = m.Arc(
            radius=R / 2.0, start_angle=0, angle=m.TAU, color=m.BLUE, stroke_width=2.5
        ).move_to(center)
        self.play(m.Create(inner_arc))

        long_chord = m.Line(
            center
            + 0.3 * R * np.array([1.0, 0.0, 0.0])
            + np.array([0.0, math.sqrt(R * R - (0.3 * R) ** 2), 0.0]),
            center
            + 0.3 * R * np.array([1.0, 0.0, 0.0])
            - np.array([0.0, math.sqrt(R * R - (0.3 * R) ** 2), 0.0]),
            color=m.BLUE,
            stroke_width=2.5,
        )
        self.play(m.Create(long_chord))

        info = (
            m.MathTex("d < R/2 \\;\\Rightarrow\\; \\text{long chord}", color=m.BLUE)
            .scale(0.75)
            .move_to([3.0, 1.5, 0])
        )
        prob = (
            m.MathTex(
                "P = \\dfrac{\\pi (R/2)^2}{\\pi R^2} = \\dfrac{1}{4}", color=m.YELLOW
            )
            .scale(0.8)
            .move_to([3.0, 0.2, 0])
        )
        self.play(m.Write(info))
        self.play(m.Write(prob))
        self.wait(2.0)

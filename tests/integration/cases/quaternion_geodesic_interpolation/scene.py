import math

import numpy as np

import manimgx as m

R = 2.5


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Geodesic interpolation (SLERP) on a sphere")
            .scale(0.85)
            .to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        circle = m.Circle(radius=R, color=m.WHITE, stroke_width=2)
        self.add(circle)

        p1 = R * np.array([math.cos(0.3), math.sin(0.3), 0.0])
        p2 = R * np.array([math.cos(2.5), math.sin(2.5), 0.0])
        p1_dot = m.Dot(p1, color=m.GREEN, radius=0.1)
        p2_dot = m.Dot(p2, color=m.RED, radius=0.1)
        p1_label = m.MathTex("q_1", color=m.GREEN).next_to(p1_dot, m.UR, buff=0.1)
        p2_label = m.MathTex("q_2", color=m.RED).next_to(p2_dot, m.UL, buff=0.1)
        self.play(
            m.FadeIn(p1_dot), m.FadeIn(p2_dot), m.Write(p1_label), m.Write(p2_label)
        )

        chord = m.Line(p1, p2, color=m.YELLOW, stroke_width=2)
        chord_label = (
            m.Tex("linear (chord)", color=m.YELLOW)
            .scale(0.5)
            .next_to(
                chord.get_center(),
                m.DOWN,
                buff=0.15,
            )
        )
        self.play(m.Create(chord), m.Write(chord_label))

        arc = m.ArcBetweenPoints(p1, p2, radius=R, color=m.BLUE, stroke_width=3)
        arc_label = (
            m.Tex("geodesic (arc)", color=m.BLUE)
            .scale(0.5)
            .next_to(
                arc,
                m.UP,
                buff=0.2,
            )
        )
        self.play(m.Create(arc), m.Write(arc_label))
        self.wait(2.0)

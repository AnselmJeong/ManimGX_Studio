import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Fixed points: stable vs unstable").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        plane = (
            m.NumberPlane(
                x_range=[-3, 3, 1],
                y_range=[-2.2, 2.2, 1],
                background_line_style={"stroke_opacity": 0.3, "stroke_color": m.GREY_B},
            )
            .scale(0.9)
            .shift(m.DOWN * 0.3)
        )
        self.play(m.Create(plane))

        stable_pt = plane.coords_to_point(-1.5, 0.6)
        unstable_pt = plane.coords_to_point(1.5, -0.6)
        s_dot = m.Dot(stable_pt, color=m.BLUE, radius=0.12)
        u_dot = m.Dot(unstable_pt, color=m.RED, radius=0.12)
        s_lab = (
            m.MathTex("|f'(z)|<1", color=m.BLUE)
            .scale(0.6)
            .next_to(s_dot, m.UP, buff=0.15)
        )
        u_lab = (
            m.MathTex("|f'(z)|>1", color=m.RED)
            .scale(0.6)
            .next_to(u_dot, m.UP, buff=0.15)
        )
        self.play(m.FadeIn(s_dot), m.FadeIn(u_dot), m.Write(s_lab), m.Write(u_lab))

        in_arrows = m.VGroup()
        out_arrows = m.VGroup()
        for k in range(8):
            theta = k * math.pi / 4
            d = 0.7 * np.array([math.cos(theta), math.sin(theta), 0.0])
            in_arrows.add(
                m.Arrow(
                    stable_pt + d,
                    stable_pt + 0.25 * d / 0.7,
                    color=m.BLUE,
                    buff=0,
                    stroke_width=2.5,
                    max_tip_length_to_length_ratio=0.4,
                )
            )
            out_arrows.add(
                m.Arrow(
                    unstable_pt + 0.25 * d / 0.7,
                    unstable_pt + d,
                    color=m.RED,
                    buff=0,
                    stroke_width=2.5,
                    max_tip_length_to_length_ratio=0.3,
                )
            )

        self.play(m.FadeIn(in_arrows), m.FadeIn(out_arrows), run_time=1.0)

        eq = (
            m.MathTex("f(z) = z^2 + c,\\quad f(z) = z", color=m.YELLOW)
            .scale(0.8)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(eq))
        self.wait(1.5)

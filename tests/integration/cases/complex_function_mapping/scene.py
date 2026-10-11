import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("$w = f(z)$: input plane $\\mapsto$ output plane").to_edge(
            m.UP, buff=0.3
        )
        self.play(m.Write(title))

        left = m.NumberPlane(
            x_range=[-2, 2, 1],
            y_range=[-2, 2, 1],
            x_length=3.0,
            y_length=3.0,
            background_line_style={"stroke_opacity": 0.3, "stroke_color": m.GREY_B},
        ).shift(m.LEFT * 3.3 + m.DOWN * 0.3)
        right = m.NumberPlane(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=3.0,
            y_length=3.0,
            background_line_style={"stroke_opacity": 0.3, "stroke_color": m.GREY_B},
        ).shift(m.RIGHT * 3.3 + m.DOWN * 0.3)
        l_lab = (
            m.MathTex("z\\text{-plane}", color=m.BLUE)
            .scale(0.7)
            .next_to(left, m.UP, buff=0.15)
        )
        r_lab = (
            m.MathTex("w = z^2", color=m.GREEN)
            .scale(0.7)
            .next_to(right, m.UP, buff=0.15)
        )
        self.play(m.Create(left), m.Create(right), m.Write(l_lab), m.Write(r_lab))

        center = 0.7 + 0.5j
        thetas = np.linspace(0, 2 * math.pi, 60)
        in_pts = []
        out_pts = []
        for th in thetas:
            z = center + 0.3 * complex(math.cos(th), math.sin(th))
            in_pts.append(left.coords_to_point(z.real, z.imag))
            w = z * z
            out_pts.append(right.coords_to_point(w.real, w.imag))
        in_circ = m.VMobject(stroke_color=m.YELLOW, stroke_width=3.0)
        in_circ.set_points_as_corners(in_pts + [in_pts[0]])
        out_circ = m.VMobject(stroke_color=m.YELLOW, stroke_width=3.0)
        out_circ.set_points_as_corners(out_pts + [out_pts[0]])

        c_dot = m.Dot(
            left.coords_to_point(center.real, center.imag), color=m.RED, radius=0.07
        )
        cw = center * center
        c_dot_o = m.Dot(
            right.coords_to_point(cw.real, cw.imag), color=m.RED, radius=0.07
        )

        self.play(m.FadeIn(c_dot), m.FadeIn(c_dot_o))
        self.play(m.Create(in_circ), m.Create(out_circ), run_time=1.5)

        note = (
            m.MathTex("|f'(z)|\\text{ = local stretch}", color=m.WHITE)
            .scale(0.75)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.play(m.Write(note))
        self.wait(1.5)

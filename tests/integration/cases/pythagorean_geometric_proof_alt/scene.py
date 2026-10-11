import numpy as np

import manimgx as m

A = 3
B = 4
C = 5
SCALE = 0.6


class TeacherScene(m.Scene):
    def construct(self) -> None:
        p1 = np.array([0.0, 0.0, 0.0])
        p2 = np.array([A * SCALE, 0.0, 0.0])
        p3 = np.array([0.0, B * SCALE, 0.0])

        triangle = m.Polygon(
            p1,
            p2,
            p3,
            color=m.WHITE,
            fill_color=m.GREY,
            fill_opacity=0.35,
            stroke_width=2,
        )

        a_sq = m.Polygon(
            p1,
            p2,
            p2 + np.array([0.0, -A * SCALE, 0.0]),
            p1 + np.array([0.0, -A * SCALE, 0.0]),
            color=m.GREEN,
            fill_color=m.GREEN,
            fill_opacity=0.45,
            stroke_width=2,
        )
        a_label = (
            m.MathTex(
                f"a^2 = {A * A}",
                color=m.GREEN,
            )
            .scale(0.65)
            .move_to(a_sq.get_center())
        )

        b_sq = m.Polygon(
            p1,
            p3,
            p3 + np.array([-B * SCALE, 0.0, 0.0]),
            p1 + np.array([-B * SCALE, 0.0, 0.0]),
            color=m.RED,
            fill_color=m.RED,
            fill_opacity=0.45,
            stroke_width=2,
        )
        b_label = (
            m.MathTex(
                f"b^2 = {B * B}",
                color=m.RED,
            )
            .scale(0.65)
            .move_to(b_sq.get_center())
        )

        hyp = p3 - p2
        perp = np.array([hyp[1], -hyp[0], 0.0])
        c_sq = m.Polygon(
            p2,
            p3,
            p3 + perp,
            p2 + perp,
            color=m.BLUE,
            fill_color=m.BLUE,
            fill_opacity=0.45,
            stroke_width=2,
        )
        c_label = (
            m.MathTex(
                f"c^2 = {C * C}",
                color=m.BLUE,
            )
            .scale(0.65)
            .move_to(c_sq.get_center())
        )

        group = m.VGroup(triangle, a_sq, a_label, b_sq, b_label, c_sq, c_label)
        group.move_to(m.ORIGIN + m.UP * 0.2)

        self.play(m.FadeIn(triangle))
        self.play(m.FadeIn(a_sq), m.Write(a_label))
        self.play(m.FadeIn(b_sq), m.Write(b_label))
        self.play(m.FadeIn(c_sq), m.Write(c_label))

        eq = (
            m.MathTex(
                f"{A * A}",
                "+",
                f"{B * B}",
                "=",
                f"{C * C}",
            )
            .scale(1.3)
            .to_edge(m.DOWN, buff=0.5)
        )
        eq[0].set_color(m.GREEN)
        eq[2].set_color(m.RED)
        eq[4].set_color(m.BLUE)
        self.play(m.Write(eq))
        self.wait(2.0)

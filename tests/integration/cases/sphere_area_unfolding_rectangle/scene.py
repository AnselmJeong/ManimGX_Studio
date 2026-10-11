import math

import manimgx as m

R = 1.4


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Sphere surface area = ", "$4\\pi R^2$").to_edge(m.UP, buff=0.3)
        title[1].set_color(m.YELLOW)
        self.play(m.Write(title))

        circle = m.Circle(
            radius=R,
            color=m.BLUE,
            fill_color=m.BLUE,
            fill_opacity=0.45,
            stroke_width=2,
        ).shift(m.LEFT * 3.7)
        radius_label = m.MathTex("R", color=m.BLUE).next_to(circle, m.UP, buff=0.15)
        self.play(m.Create(circle), m.Write(radius_label))

        arrow = m.Arrow(m.LEFT * 1.6, m.RIGHT * 0.4, color=m.YELLOW, buff=0)
        self.play(m.GrowArrow(arrow))

        rect_w = 2 * math.pi * R * 0.6
        rect_h = 2 * R
        rect = m.Rectangle(
            width=rect_w,
            height=rect_h,
            color=m.YELLOW,
            fill_color=m.YELLOW,
            fill_opacity=0.4,
            stroke_width=2,
        ).shift(m.RIGHT * 3)
        w_label = m.MathTex("2\\pi R").scale(0.75).next_to(rect, m.DOWN, buff=0.2)
        h_label = m.MathTex("2R").scale(0.75).next_to(rect, m.RIGHT, buff=0.2)
        self.play(m.Create(rect), m.Write(w_label), m.Write(h_label))

        eq = (
            m.MathTex(
                "(2\\pi R)(2R) = 4\\pi R^2",
            )
            .scale(1.0)
            .to_edge(m.DOWN, buff=0.6)
        )
        self.play(m.Write(eq))
        self.wait(2.0)

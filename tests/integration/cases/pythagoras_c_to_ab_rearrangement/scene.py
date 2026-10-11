import numpy as np

import manimgx as m

A = 2.0
B = 1.4
SIDE = A + B


def _shift(point: tuple[float, float]) -> np.ndarray:
    return np.array([point[0] - SIDE / 2, point[1] - SIDE / 2, 0.0])


def tri(p1, p2, p3, color=m.BLUE) -> m.Polygon:
    return m.Polygon(
        _shift(p1),
        _shift(p2),
        _shift(p3),
        color=color,
        fill_color=color,
        fill_opacity=0.55,
        stroke_width=2,
    )


def quad(p1, p2, p3, p4, color, opacity=0.35) -> m.Polygon:
    return m.Polygon(
        _shift(p1),
        _shift(p2),
        _shift(p3),
        _shift(p4),
        color=color,
        fill_color=color,
        fill_opacity=opacity,
        stroke_width=2.5,
    )


class TeacherScene(m.Scene):
    def construct(self) -> None:
        big = m.Square(side_length=SIDE, color=m.WHITE, stroke_width=3)
        self.play(m.Create(big), run_time=0.8)

        t1 = tri((0, 0), (A, 0), (0, B))
        t2 = tri((A, 0), (A + B, 0), (A + B, A))
        t3 = tri((A + B, A), (A + B, A + B), (B, A + B))
        t4 = tri((B, A + B), (0, A + B), (0, B))
        c_sq = quad((A, 0), (A + B, A), (B, A + B), (0, B), m.YELLOW)
        c_label = m.MathTex("c^2", color=m.YELLOW).move_to(c_sq.get_center())

        self.play(
            m.FadeIn(t1),
            m.FadeIn(t2),
            m.FadeIn(t3),
            m.FadeIn(t4),
            m.FadeIn(c_sq),
            run_time=0.9,
        )
        self.play(m.Write(c_label))
        self.wait(1.0)

        t1_end = tri((0, 0), (A, 0), (A, B))
        t4_end = tri((0, 0), (A, B), (0, B))
        t2_end = tri((A, B), (A + B, B), (A + B, A + B))
        t3_end = tri((A, B), (A + B, A + B), (A, A + B))

        a_sq = quad((0, B), (A, B), (A, A + B), (0, A + B), m.GREEN)
        b_sq = quad((A, 0), (A + B, 0), (A + B, B), (A, B), m.RED)
        a_label = m.MathTex("a^2", color=m.GREEN).move_to(a_sq.get_center())
        b_label = m.MathTex("b^2", color=m.RED).move_to(b_sq.get_center())

        self.play(
            m.FadeOut(c_sq),
            m.FadeOut(c_label),
            m.Transform(t1, t1_end),
            m.Transform(t2, t2_end),
            m.Transform(t3, t3_end),
            m.Transform(t4, t4_end),
            m.FadeIn(a_sq),
            m.FadeIn(b_sq),
            run_time=2.2,
        )
        self.play(m.Write(a_label), m.Write(b_label))
        self.wait(0.6)

        equation = (
            m.MathTex("a^2", "+", "b^2", "=", "c^2")
            .scale(1.1)
            .to_edge(m.DOWN, buff=0.7)
        )
        equation[0].set_color(m.GREEN)
        equation[2].set_color(m.RED)
        equation[4].set_color(m.YELLOW)
        self.play(m.Write(equation))
        self.wait(1.8)

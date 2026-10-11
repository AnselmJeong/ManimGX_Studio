import math

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Romeo and Juliet: $\\dot x = -y,\\;\\dot y = x$").to_edge(
            m.UP, buff=0.3
        )
        self.play(m.Write(title))

        scale_l = (
            m.NumberLine(x_range=[-2, 2, 1], length=3.0, include_numbers=False)
            .rotate(m.PI / 2)
            .shift(m.LEFT * 3.2 + m.DOWN * 0.5)
        )
        scale_r = (
            m.NumberLine(x_range=[-2, 2, 1], length=3.0, include_numbers=False)
            .rotate(m.PI / 2)
            .shift(m.RIGHT * 3.2 + m.DOWN * 0.5)
        )
        lab_l = (
            m.Tex("Romeo $x$", color=m.RED)
            .scale(0.8)
            .next_to(scale_l, m.DOWN, buff=0.3)
        )
        lab_r = (
            m.Tex("Juliet $y$", color=m.BLUE)
            .scale(0.8)
            .next_to(scale_r, m.DOWN, buff=0.3)
        )
        self.play(m.Create(scale_l), m.Create(scale_r), m.Write(lab_l), m.Write(lab_r))

        t = m.ValueTracker(0.0)
        dot_l = m.always_redraw(
            lambda: m.Dot(
                scale_l.n2p(math.cos(t.get_value())), color=m.RED, radius=0.13
            )
        )
        dot_r = m.always_redraw(
            lambda: m.Dot(
                scale_r.n2p(math.sin(t.get_value())), color=m.BLUE, radius=0.13
            )
        )
        self.add(dot_l, dot_r)

        arrow_lr = m.CurvedArrow(
            scale_l.get_center() + m.UP * 1.4,
            scale_r.get_center() + m.UP * 1.4,
            color=m.YELLOW,
            angle=-0.5,
        )
        arrow_rl = m.CurvedArrow(
            scale_r.get_center() + m.DOWN * 1.4,
            scale_l.get_center() + m.DOWN * 1.4,
            color=m.YELLOW,
            angle=-0.5,
        )
        self.play(m.Create(arrow_lr), m.Create(arrow_rl))

        self.play(t.animate.set_value(2 * math.pi), run_time=4.0, rate_func=m.linear)
        self.wait(1.5)

import math

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Continuous symmetries: $SO(2)$ vs $\\mathbb{R}$").to_edge(
            m.UP, buff=0.3
        )
        self.play(m.Write(title))

        circle = m.Circle(radius=1.5, color=m.YELLOW, stroke_width=2.5).shift(
            m.LEFT * 3
        )
        c_label = (
            m.MathTex("SO(2)", color=m.YELLOW)
            .scale(0.85)
            .next_to(circle, m.DOWN, buff=0.4)
        )
        line = m.NumberLine(x_range=[0, 6, 1], length=4.5, include_numbers=True).shift(
            m.RIGHT * 3 + m.DOWN * 0.1
        )
        l_label = (
            m.MathTex("\\mathbb{R}", color=m.GREEN)
            .scale(0.9)
            .next_to(line, m.DOWN, buff=0.4)
        )

        self.add(circle, line)
        self.play(m.Write(c_label), m.Write(l_label))

        t = m.ValueTracker(0.0)
        rotating_mark = m.always_redraw(
            lambda: m.Dot(
                circle.get_center()
                + 1.5
                * np.array(
                    [
                        math.cos(t.get_value() + math.pi / 2),
                        math.sin(t.get_value() + math.pi / 2),
                        0.0,
                    ]
                ),
                color=m.RED,
                radius=0.12,
            ),
        )
        sliding_mark = m.always_redraw(
            lambda: m.Dot(
                line.n2p(3 + math.sin(t.get_value())), color=m.RED, radius=0.12
            ),
        )
        self.add(rotating_mark, sliding_mark)

        self.play(t.animate.set_value(2 * math.pi), run_time=5.0, rate_func=m.linear)
        self.wait(1.0)

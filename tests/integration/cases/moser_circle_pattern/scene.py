import math

import numpy as np

import manimgx as m

RADIUS = 2.6
# Angles chosen to keep chord intersections in general position
# (no three chords concurrent) so the M(n) count matches the formula.
_BASE = np.arange(0, 6, 6.0 / 7)
ANGLES = np.concatenate([_BASE, _BASE + 0.5])[:10]


def moser(n: int) -> int:
    return math.comb(n, 4) + math.comb(n, 2) + 1


def dot_pos(i: int) -> np.ndarray:
    return RADIUS * np.array([math.cos(ANGLES[i]), math.sin(ANGLES[i]), 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=RADIUS, color=m.WHITE, stroke_width=2.5)

        n_value = m.Integer(0, color=m.WHITE)
        m_value = m.Integer(1, color=m.YELLOW)
        n_row = m.VGroup(m.MathTex("n", "="), n_value).arrange(m.RIGHT, buff=0.18)
        m_row = m.VGroup(m.MathTex("M(n)", "="), m_value).arrange(m.RIGHT, buff=0.18)
        labels = (
            m.VGroup(n_row, m_row)
            .arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.35)
            .to_corner(m.UL, buff=0.6)
        )

        self.play(m.Create(circle), run_time=0.8)
        self.add(labels)

        for n in range(1, len(ANGLES) + 1):
            new_dot = m.Dot(dot_pos(n - 1), color=m.YELLOW, radius=0.08)
            new_chords = m.VGroup(
                *[
                    m.Line(
                        dot_pos(i),
                        dot_pos(n - 1),
                        stroke_width=1.5,
                        color=m.BLUE,
                    )
                    for i in range(n - 1)
                ]
            )

            anims: list[m.Animation] = [
                m.FadeIn(new_dot, scale=0.4),
                n_value.animate.set_value(n),
                m_value.animate.set_value(moser(n)),
            ]
            if len(new_chords) > 0:
                anims.append(m.Create(new_chords, lag_ratio=0.05))

            self.play(*anims, run_time=0.55)
            self.wait(0.35)

        self.wait(1.5)

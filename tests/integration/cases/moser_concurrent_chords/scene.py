import itertools
import math

import numpy as np

import manimgx as m

RADIUS = 2.5


def pos(angle: float) -> np.ndarray:
    return RADIUS * np.array([math.cos(angle), math.sin(angle), 0.0])


REGULAR = [k * math.pi / 3 for k in range(6)]
PERTURBED = [a + 0.18 * (1 if i % 2 == 0 else -1) for i, a in enumerate(REGULAR)]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=RADIUS, color=m.WHITE, stroke_width=2)
        self.add(circle)

        dots = m.VGroup(*[m.Dot(pos(a), color=m.YELLOW, radius=0.1) for a in REGULAR])
        chords = m.VGroup(
            *[
                m.Line(
                    pos(REGULAR[i]),
                    pos(REGULAR[j]),
                    color=m.BLUE,
                    stroke_width=2,
                )
                for i, j in itertools.combinations(range(6), 2)
            ]
        )
        self.play(m.FadeIn(dots), m.Create(chords, lag_ratio=0.05), run_time=1.6)
        self.wait(0.4)

        center_dot = m.Dot(m.ORIGIN, color=m.RED, radius=0.18)
        cap1 = m.Tex(
            "Three long diagonals meet at the center",
            color=m.RED,
        ).to_edge(m.UP)
        self.play(m.FadeIn(center_dot, scale=0.4), m.Write(cap1))
        self.wait(1.5)

        new_chords = m.VGroup(
            *[
                m.Line(
                    pos(PERTURBED[i]),
                    pos(PERTURBED[j]),
                    color=m.BLUE,
                    stroke_width=2,
                )
                for i, j in itertools.combinations(range(6), 2)
            ]
        )
        new_dots = m.VGroup(
            *[m.Dot(pos(a), color=m.YELLOW, radius=0.1) for a in PERTURBED]
        )
        cap2 = m.Tex(
            "Perturb slightly — a small triangle appears",
            color=m.GREEN,
        ).to_edge(m.UP)

        self.play(
            m.Transform(chords, new_chords),
            m.Transform(dots, new_dots),
            m.FadeOut(center_dot),
            m.Transform(cap1, cap2),
            run_time=2.2,
        )
        self.wait(2.0)

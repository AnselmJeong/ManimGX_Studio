import itertools
import math

import numpy as np

import manimgx as m

N = 6
RADIUS = 2.5
ANGLES = [0.0, 0.7, 1.3, 1.9, 2.6, 3.4]


def pos(i: int) -> np.ndarray:
    return RADIUS * np.array([math.cos(ANGLES[i]), math.sin(ANGLES[i]), 0.0])


def line_intersection(
    p1: np.ndarray,
    p2: np.ndarray,
    p3: np.ndarray,
    p4: np.ndarray,
) -> np.ndarray | None:
    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]
    x3, y3 = p3[0], p3[1]
    x4, y4 = p4[0], p4[1]
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    if 0 <= t <= 1 and 0 <= u <= 1:
        return np.array([x1 + t * (x2 - x1), y1 + t * (y2 - y1), 0.0])
    return None


class TeacherScene(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=RADIUS, color=m.WHITE, stroke_width=2)
        self.play(m.Create(circle), run_time=0.8)

        dots = m.VGroup(*[m.Dot(pos(i), color=m.YELLOW, radius=0.1) for i in range(N)])
        self.play(m.FadeIn(dots))

        chords = m.VGroup(
            *[
                m.Line(pos(i), pos(j), color=m.BLUE, stroke_width=1.6)
                for i, j in itertools.combinations(range(N), 2)
            ]
        )
        self.play(m.Create(chords, lag_ratio=0.06), run_time=1.6)

        intersections: list[np.ndarray] = []
        for quad in itertools.combinations(range(N), 4):
            a, b, c, d = sorted(quad)
            p = line_intersection(pos(a), pos(c), pos(b), pos(d))
            if p is not None:
                intersections.append(p)

        int_dots = m.VGroup(
            *[m.Dot(p, color=m.RED, radius=0.08) for p in intersections]
        )
        self.play(
            m.LaggedStart(
                *[m.FadeIn(d, scale=0.3) for d in int_dots],
                lag_ratio=0.05,
            ),
            run_time=1.5,
        )

        formula = (
            m.MathTex(
                "\\binom{6}{4}",
                "=",
                str(math.comb(N, 4)),
            )
            .scale(1.2)
            .to_corner(m.UR, buff=0.6)
        )
        formula[2].set_color(m.RED)
        self.play(m.Write(formula))
        self.wait(2.0)

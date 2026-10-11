import numpy as np

import manimgx as m

A = np.array([0.0, 1.6, 0.0])
B = np.array([-1.4, -0.8, 0.0])
C = np.array([1.4, -0.8, 0.0])
M = np.array([0.0, 0.0, 0.0])

EDGES = [(A, B), (B, C), (C, A), (A, M), (B, M), (C, M)]

ABM = (A + B + M) / 3
BCM = (B + C + M) / 3
CAM = (C + A + M) / 3
OUTER = np.array([0.0, -2.6, 0.0])

DUAL_EDGES = [
    (ABM, OUTER),
    (BCM, OUTER),
    (CAM, OUTER),
    (ABM, BCM),
    (BCM, CAM),
    (CAM, ABM),
]


class TeacherScene(m.Scene):
    def construct(self) -> None:
        edges = m.VGroup(
            *[m.Line(p1, p2, color=m.BLUE, stroke_width=3) for p1, p2 in EDGES]
        )
        verts = m.VGroup(*[m.Dot(p, color=m.YELLOW, radius=0.12) for p in [A, B, C, M]])
        self.play(m.Create(edges), m.FadeIn(verts), run_time=1.2)

        title = m.Tex("Planar graph", " $\\to$ ", "Dual graph").to_edge(m.UP)
        title[0].set_color(m.YELLOW)
        title[2].set_color(m.RED)
        self.play(m.Write(title))
        self.wait(0.5)

        dual_verts = m.VGroup(
            *[m.Dot(c, color=m.RED, radius=0.12) for c in [ABM, BCM, CAM, OUTER]]
        )
        dual_edges = m.VGroup(
            *[m.Line(p1, p2, color=m.ORANGE, stroke_width=2.5) for p1, p2 in DUAL_EDGES]
        )

        self.play(
            edges.animate.set_opacity(0.35),
            verts.animate.set_opacity(0.45),
            run_time=0.6,
        )
        self.play(m.FadeIn(dual_verts), m.Create(dual_edges), run_time=1.8)
        self.wait(2.0)

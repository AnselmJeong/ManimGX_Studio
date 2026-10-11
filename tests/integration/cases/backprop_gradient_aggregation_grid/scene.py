import math

import numpy as np

import manimgx as m

EXAMPLES = 9


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex(
            "Gradient = average over training examples",
        ).to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        rng = np.random.default_rng(42)
        angles = [
            a + 0.35 * (rng.random() - 0.5) for a in np.linspace(0.3, 2.4, EXAMPLES)
        ]
        magnitudes = [1.0 + 0.25 * rng.random() for _ in range(EXAMPLES)]

        origin = np.array([0.0, -0.5, 0.0])
        arrows = m.VGroup()
        for a, mag in zip(angles, magnitudes):
            end = origin + mag * 1.6 * np.array([math.cos(a), math.sin(a), 0.0])
            arrow = m.Arrow(origin, end, color=m.BLUE, buff=0, stroke_width=2)
            arrow.set_opacity(0.55)
            arrows.add(arrow)
        self.play(
            m.LaggedStart(*[m.GrowArrow(a) for a in arrows], lag_ratio=0.06),
            run_time=1.6,
        )
        self.wait(0.4)

        avg_x = sum(mag * math.cos(a) for mag, a in zip(magnitudes, angles)) / EXAMPLES
        avg_y = sum(mag * math.sin(a) for mag, a in zip(magnitudes, angles)) / EXAMPLES
        avg_end = origin + np.array([avg_x, avg_y, 0.0]) * 2.8
        avg_arrow = m.Arrow(origin, avg_end, color=m.YELLOW, buff=0, stroke_width=7)
        avg_label = m.MathTex("\\nabla L", color=m.YELLOW).next_to(
            avg_arrow.get_end(),
            m.UR,
            buff=0.15,
        )

        self.play(m.GrowArrow(avg_arrow), m.Write(avg_label), run_time=1.4)
        self.wait(2.0)

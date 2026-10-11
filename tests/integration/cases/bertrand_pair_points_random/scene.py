import math
import random

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        random.seed(42)
        title = m.Tex("Bertrand: pair of endpoints").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        circle = m.Circle(radius=2.2, color=m.WHITE, stroke_width=2.0).shift(
            m.LEFT * 2.5
        )
        triangle = (
            m.RegularPolygon(n=3, color=m.YELLOW, stroke_width=2.0)
            .scale(2.2)
            .shift(m.LEFT * 2.5)
        )
        self.play(m.Create(circle), m.Create(triangle))

        long_count = 0
        total = 80
        chord_threshold = 2.2 * math.sqrt(3)
        chords = m.VGroup()
        for _ in range(total):
            a = random.uniform(0, 2 * math.pi)
            b = random.uniform(0, 2 * math.pi)
            p1 = circle.get_center() + 2.2 * np.array([math.cos(a), math.sin(a), 0.0])
            p2 = circle.get_center() + 2.2 * np.array([math.cos(b), math.sin(b), 0.0])
            length = float(np.linalg.norm(p1 - p2))
            color = m.BLUE if length > chord_threshold else m.GREY_B
            chord = m.Line(p1, p2, color=color, stroke_width=1.2)
            chords.add(chord)
            if length > chord_threshold:
                long_count += 1

        self.play(m.LaggedStartMap(m.FadeIn, chords, lag_ratio=0.02, run_time=2.5))

        ratio = long_count / total
        result = m.MathTex(f"P \\approx {ratio:.2f}").scale(1.0).move_to([3.0, 0.5, 0])
        truth = (
            m.MathTex("\\text{(true: } 1/3\\text{)}", color=m.YELLOW)
            .scale(0.7)
            .next_to(result, m.DOWN, buff=0.3)
        )
        self.play(m.Write(result), m.Write(truth))
        self.wait(2.0)

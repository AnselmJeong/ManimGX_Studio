import math
import random

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        random.seed(7)
        title = m.Tex("Bertrand: random midpoint").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        R = 2.2
        center = m.LEFT * 2.5
        circle = m.Circle(radius=R, color=m.WHITE, stroke_width=2.0).move_to(center)
        triangle = (
            m.RegularPolygon(n=3, color=m.YELLOW, stroke_width=2.0)
            .scale(R)
            .move_to(center)
        )
        self.play(m.Create(circle), m.Create(triangle))

        long_count = 0
        total = 80
        threshold = R / 2.0
        chords = m.VGroup()
        for _ in range(total):
            r = math.sqrt(random.uniform(0, 1)) * R
            theta = random.uniform(0, 2 * math.pi)
            mid = center + r * np.array([math.cos(theta), math.sin(theta), 0.0])
            d = float(np.linalg.norm(mid - center))
            half = math.sqrt(max(R * R - d * d, 0.0))
            perp = np.array([-math.sin(theta), math.cos(theta), 0.0])
            p1 = mid + half * perp
            p2 = mid - half * perp
            is_long = d < threshold
            color = m.BLUE if is_long else m.GREY_B
            chord = m.Line(p1, p2, color=color, stroke_width=1.2)
            chords.add(chord)
            if is_long:
                long_count += 1

        self.play(m.LaggedStartMap(m.FadeIn, chords, lag_ratio=0.02, run_time=2.5))

        ratio = long_count / total
        result = m.MathTex(f"P \\approx {ratio:.2f}").scale(1.0).move_to([3.0, 0.5, 0])
        truth = (
            m.MathTex("\\text{(true: } 1/4\\text{)}", color=m.YELLOW)
            .scale(0.7)
            .next_to(result, m.DOWN, buff=0.3)
        )
        self.play(m.Write(result), m.Write(truth))
        self.wait(2.0)

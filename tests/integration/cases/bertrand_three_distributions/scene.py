import math
import random

import numpy as np

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        random.seed(11)
        title = m.Tex("Where do the midpoints live?").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        R = 1.6
        left_c = np.array([-3.2, -0.4, 0.0])
        right_c = np.array([3.2, -0.4, 0.0])
        cl = m.Circle(radius=R, color=m.WHITE, stroke_width=2.0).move_to(left_c)
        cr = m.Circle(radius=R, color=m.WHITE, stroke_width=2.0).move_to(right_c)
        cl_lab = (
            m.Tex("Endpoint pair", color=m.BLUE).scale(0.7).next_to(cl, m.UP, buff=0.2)
        )
        cr_lab = (
            m.Tex("Midpoint uniform", color=m.GREEN)
            .scale(0.7)
            .next_to(cr, m.UP, buff=0.2)
        )
        self.play(m.Create(cl), m.Create(cr), m.Write(cl_lab), m.Write(cr_lab))

        left_dots = m.VGroup()
        for _ in range(120):
            a = random.uniform(0, 2 * math.pi)
            b = random.uniform(0, 2 * math.pi)
            p1 = left_c + R * np.array([math.cos(a), math.sin(a), 0.0])
            p2 = left_c + R * np.array([math.cos(b), math.sin(b), 0.0])
            mid = 0.5 * (p1 + p2)
            left_dots.add(m.Dot(mid, color=m.BLUE, radius=0.025))

        right_dots = m.VGroup()
        for _ in range(120):
            r = math.sqrt(random.uniform(0, 1)) * R
            th = random.uniform(0, 2 * math.pi)
            right_dots.add(
                m.Dot(
                    right_c + r * np.array([math.cos(th), math.sin(th), 0.0]),
                    color=m.GREEN,
                    radius=0.025,
                )
            )

        self.play(
            m.LaggedStartMap(m.FadeIn, left_dots, lag_ratio=0.01, run_time=1.8),
            m.LaggedStartMap(m.FadeIn, right_dots, lag_ratio=0.01, run_time=1.8),
        )
        self.wait(2.0)

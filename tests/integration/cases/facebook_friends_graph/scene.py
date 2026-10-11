import math

import numpy as np

import manimgx as m

NAMES = ["A", "R", "M", "L", "P"]
RADIUS = 2.2
ANGLES = [math.pi / 2 + 2 * math.pi * k / len(NAMES) for k in range(len(NAMES))]
FRIENDSHIPS = [(0, 1), (0, 2), (1, 2), (0, 3), (0, 4), (1, 3)]


def position(i: int) -> np.ndarray:
    return RADIUS * np.array([math.cos(ANGLES[i]), math.sin(ANGLES[i]), 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        accounts = m.VGroup()
        for i, name in enumerate(NAMES):
            circle = m.Circle(
                radius=0.4,
                color=m.BLUE,
                fill_color=m.BLUE,
                fill_opacity=0.3,
            )
            letter = m.Tex(name, color=m.WHITE).scale(0.85)
            accounts.add(m.VGroup(circle, letter).move_to(position(i)))

        self.play(
            m.LaggedStart(*[m.GrowFromCenter(a) for a in accounts], lag_ratio=0.1),
            run_time=1.2,
        )
        self.wait(0.3)

        edges = m.VGroup(
            *[
                m.Line(position(i), position(j), color=m.YELLOW, stroke_width=2.5)
                for i, j in FRIENDSHIPS
            ]
        )
        self.play(m.Create(edges, lag_ratio=0.12), run_time=1.4)
        for a in accounts:
            self.add(a)
        self.wait(1.0)

        abstract = m.VGroup(
            *[
                m.Dot(position(i), color=m.YELLOW, radius=0.13)
                for i in range(len(NAMES))
            ]
        )
        self.play(
            *[m.Transform(a, d) for a, d in zip(accounts, abstract)],
            run_time=1.6,
        )

        caption = m.Tex("Concrete", " $\\to$ ", "Abstract graph").to_edge(m.UP)
        caption[0].set_color(m.BLUE)
        caption[2].set_color(m.YELLOW)
        self.play(m.Write(caption))
        self.wait(1.8)

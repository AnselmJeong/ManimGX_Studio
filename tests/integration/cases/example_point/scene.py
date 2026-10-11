# Source: manim/mobject/types/point_cloud_mobject.py
import numpy as np

import manimgx as m


class ExamplePoint(m.Scene):
    def construct(self):
        rng = np.random.default_rng(0)
        colorList = [m.RED, m.GREEN, m.BLUE, m.YELLOW]
        for _ in range(200):
            point = m.Point(
                location=[
                    0.63 * rng.integers(-4, 4),
                    0.37 * rng.integers(-4, 4),
                    0,
                ],
                color=rng.choice(colorList),
            )
            self.add(point)
        for _ in range(200):
            point = m.Point(
                location=[
                    0.37 * rng.integers(-4, 4),
                    0.63 * rng.integers(-4, 4),
                    0,
                ],
                color=rng.choice(colorList),
            )
            self.add(point)
        self.add(point)
        self.wait()

# Source: manim/mobject/geometry/polygram.py

import numpy as np

import manimgx as m


class PolygramExample(m.Scene):
    def construct(self):
        hexagram = m.Polygram(
            [
                [0, 2, 0],
                [-np.sqrt(3), -1, 0],
                [np.sqrt(3), -1, 0],
            ],
            [
                [-np.sqrt(3), 1, 0],
                [0, -2, 0],
                [np.sqrt(3), 1, 0],
            ],
        )
        self.add(hexagram)

        dot = m.Dot()
        self.play(m.MoveAlongPath(dot, hexagram), run_time=5, rate_func=m.linear)
        self.remove(dot)
        self.wait()

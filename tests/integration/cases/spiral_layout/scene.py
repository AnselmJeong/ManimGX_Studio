# Source: manim/mobject/graph.py
import manimgx as m


class SpiralLayout(m.Scene):
    def construct(self):
        graph = m.Graph(
            [1, 2, 3, 4, 5, 6],
            [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 1), (5, 1), (1, 3), (3, 5)],
            layout="spiral",
            labels=True,
        )
        self.add(graph)
        self.wait()

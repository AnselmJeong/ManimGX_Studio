# Source: manim/mobject/graph.py
import manimgx as m


class ChangeGraphLayout(m.Scene):
    def construct(self):
        G = m.Graph(
            [1, 2, 3, 4, 5],
            [(1, 2), (2, 3), (3, 4), (4, 5)],
            layout={
                1: [-2, 0, 0],
                2: [-1, 0, 0],
                3: [0, 0, 0],
                4: [1, 0, 0],
                5: [2, 0, 0],
            },
        )
        self.play(m.Create(G))
        self.play(m.Transform(G, G.copy().change_layout("circular")))
        self.wait()

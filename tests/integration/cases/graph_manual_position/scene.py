# Source: manim/mobject/graph.py
import manimgx as m


class GraphManualPosition(m.Scene):
    def construct(self):
        vertices = [1, 2, 3, 4]
        edges = [(1, 2), (2, 3), (3, 4), (4, 1)]
        lt = {1: [0, 0, 0], 2: [1, 1, 0], 3: [1, -1, 0], 4: [-1, 0, 0]}
        G = m.Graph(vertices, edges, layout=lt)
        self.add(G)
        self.wait()

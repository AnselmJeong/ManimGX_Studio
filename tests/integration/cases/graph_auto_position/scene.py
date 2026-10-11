# Source: manim/mobject/graph.py
import manimgx as m


class GraphAutoPosition(m.Scene):
    def construct(self):
        vertices = [1, 2, 3, 4, 5, 6, 7, 8]
        edges = [
            (1, 7),
            (1, 8),
            (2, 3),
            (2, 4),
            (2, 5),
            (2, 8),
            (3, 4),
            (6, 1),
            (6, 2),
            (6, 3),
            (7, 2),
            (7, 4),
        ]
        autolayouts = [
            "circular",
            "kamada_kawai",
            "planar",
            "shell",
            "spectral",
            "spiral",
        ]
        graphs = [m.Graph(vertices, edges, layout=lt).scale(0.5) for lt in autolayouts]
        r1 = m.VGroup(*graphs[:3]).arrange()
        r2 = m.VGroup(*graphs[3:6]).arrange()
        r3 = m.VGroup(*graphs[6:]).arrange()
        self.add(m.VGroup(r1, r2, r3).arrange(direction=m.DOWN))
        self.wait()

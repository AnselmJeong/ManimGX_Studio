# Source: manim/mobject/graph.py
import manimgx as m


class LabeledModifiedGraph(m.Scene):
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
        g = m.Graph(
            vertices,
            edges,
            layout="circular",
            layout_scale=3,
            labels=True,
            vertex_config={7: {"fill_color": m.RED}},
            edge_config={
                (1, 7): {"stroke_color": m.RED},
                (2, 7): {"stroke_color": m.RED},
                (4, 7): {"stroke_color": m.RED},
            },
        )
        self.add(g)
        self.wait()

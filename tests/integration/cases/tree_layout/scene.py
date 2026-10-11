# Source: manim/mobject/graph.py
import manimgx as m


class TreeLayout(m.Scene):
    def construct(self):
        graph = m.Graph(
            [1, 2, 3, 4, 5, 6, 7],
            [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7)],
            layout="tree",
            layout_config={"root_vertex": 1},
            labels=True,
        )
        self.add(graph)
        self.wait()

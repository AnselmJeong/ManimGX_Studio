# Source: manim/mobject/graph.py
import manimgx as m


class ShellLayout(m.Scene):
    def construct(self):
        nlist = [[1, 2, 3], [4, 5, 6, 7, 8, 9]]
        graph = m.Graph(
            [1, 2, 3, 4, 5, 6, 7, 8, 9],
            [
                (1, 2),
                (2, 3),
                (3, 1),
                (4, 1),
                (4, 2),
                (5, 2),
                (6, 2),
                (6, 3),
                (7, 3),
                (8, 3),
                (8, 1),
                (9, 1),
            ],
            layout="shell",
            layout_config={"nlist": nlist},
            labels=True,
        )
        self.add(graph)
        self.wait()

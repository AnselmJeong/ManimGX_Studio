# Source: manim/mobject/graph.py
import manimgx as m


class KamadaKawaiLayout(m.Scene):
    def construct(self):
        from collections import defaultdict

        distances: dict[int, dict[int, float]] = defaultdict(dict)

        # set desired distances
        distances[1][2] = 1  # distance between vertices 1 and 2 is 1
        distances[2][3] = 1  # distance between vertices 2 and 3 is 1
        distances[3][4] = 2  # etc
        distances[4][5] = 3
        distances[5][6] = 5
        distances[6][1] = 8

        graph = m.Graph(
            [1, 2, 3, 4, 5, 6],
            [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 1)],
            layout="kamada_kawai",
            layout_config={"dist": distances},
            layout_scale=4,
            labels=True,
        )
        self.add(graph)
        self.wait()

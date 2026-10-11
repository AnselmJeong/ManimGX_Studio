# Source: manim/mobject/graph.py
import numpy as np

import manimgx as m


class LinearNN(m.Scene):
    def construct(self):
        edges = []
        partitions = []
        c = 0
        layers = [2, 3, 3, 2]  # the number of neurons in each layer

        for i in layers:
            partitions.append(list(range(c + 1, c + i + 1)))
            c += i
        for i, v in enumerate(layers[1:]):
            last = sum(layers[: i + 1])
            for j in range(v):
                for k in range(last - layers[i], last):
                    edges.append((k + 1, j + last + 1))

        vertices: list[np.int_] = list(np.arange(1, sum(layers) + 1))

        graph = m.Graph(
            vertices,
            edges,
            layout="partite",
            partitions=partitions,
            layout_scale=3,
            vertex_config={"radius": 0.20},
        )
        self.add(graph)
        self.wait()

# Source: manim/mobject/graph.py
# ruff: noqa: C414, C416
import numpy as np

import manimgx as m


class CustomLayoutExample(m.Scene):
    def construct(self):
        import networkx as nx

        # create custom layout
        def custom_layout(
            graph: nx.Graph,
            scale: float | tuple[float, float, float] = 2,
            n: int | None = None,
            *args: object,
            **kwargs: object,
        ):
            assert n is not None
            nodes = sorted(list(graph))
            height = len(nodes) // n
            return {
                node: (
                    scale * np.array([(i % n) - (n - 1) / 2, -(i // n) + height / 2, 0])
                )
                for i, node in enumerate(graph)
            }

        # draw graph
        n = 4
        graph = m.Graph(
            [i for i in range(4 * 2 - 1)],
            [(0, 1), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (4, 5), (5, 6)],
            labels=True,
            layout=custom_layout,
            layout_config={"n": n},
        )
        self.add(graph)

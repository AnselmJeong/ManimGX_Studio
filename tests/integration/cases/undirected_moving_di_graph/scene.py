# Source: manim/mobject/graph.py
# ruff: noqa: C416
import manimgx as m


class UndirectedMovingDiGraph(m.Scene):
    def construct(self):
        vertices = [i for i in range(5)]
        edges = [
            (0, 1),
            (1, 2),
            (3, 2),
            (3, 4),
        ]

        edge_config = {
            "stroke_width": 2,
            "tip_config": {"tip_length": 0, "tip_width": 0},
            (3, 4): {"color": m.RED},
        }

        g = m.DiGraph(
            vertices,
            edges,
            labels=True,
            layout="circular",
            edge_config=edge_config,
        ).scale(1.4)

        self.play(m.Create(g))
        self.wait()

        self.play(
            g[1].animate.move_to([1, 1, 1]),
            g[2].animate.move_to([-1, 1, 2]),
            g[3].animate.move_to([-1.5, -1.5, -1]),
            g[4].animate.move_to([1, -2, -1]),
        )
        self.wait()

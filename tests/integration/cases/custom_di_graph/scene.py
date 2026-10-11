# Source: manim/mobject/graph.py
# ruff: noqa: C416
import manimgx as m


class CustomDiGraph(m.Scene):
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
            "tip_config": {
                "tip_shape": m.ArrowSquareTip,
                "tip_length": 0.15,
            },
            (3, 4): {
                "color": m.RED,
                "tip_config": {"tip_length": 0.25, "tip_width": 0.25},
            },
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

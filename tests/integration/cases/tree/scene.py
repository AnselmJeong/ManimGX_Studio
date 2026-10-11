# Source: manim/mobject/graph.py
# ruff: noqa: UP031
import networkx as nx

import manimgx as m


class Tree(m.Scene):
    def construct(self):
        G = nx.Graph()

        G.add_node("ROOT")

        for i in range(5):
            G.add_node("Child_%i" % i)
            G.add_node("Grandchild_%i" % i)
            G.add_node("Greatgrandchild_%i" % i)
            G.add_edge("ROOT", "Child_%i" % i)
            G.add_edge("Child_%i" % i, "Grandchild_%i" % i)
            G.add_edge("Grandchild_%i" % i, "Greatgrandchild_%i" % i)
        vertices: list[str] = list(G.nodes)
        edges: list[tuple[str, str]] = list(G.edges)
        self.play(m.Create(m.Graph(vertices, edges, layout="tree", root_vertex="ROOT")))

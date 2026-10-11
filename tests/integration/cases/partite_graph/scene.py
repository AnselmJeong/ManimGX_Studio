# Source: manim/mobject/graph.py
import networkx as nx

import manimgx as m


class PartiteGraph(m.Scene):
    def construct(self):
        G = nx.Graph()
        G.add_nodes_from([0, 1, 2, 3])
        G.add_edges_from([(0, 2), (0, 3), (1, 2)])
        vertices: list[int] = list(G.nodes)
        edges: list[tuple[int, int]] = list(G.edges)
        graph = m.Graph(vertices, edges, layout="partite", partitions=[[0, 1]])
        self.play(m.Create(graph))

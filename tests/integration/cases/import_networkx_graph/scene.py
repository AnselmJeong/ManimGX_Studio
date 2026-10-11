# Source: manim/mobject/graph.py
import networkx as nx
import numpy as np

import manimgx as m

nxgraph = nx.erdos_renyi_graph(14, 0.5, seed=42)


class ImportNetworkxGraph(m.Scene):
    def construct(self):
        G = m.Graph.from_networkx(
            nxgraph, layout="spring", layout_scale=3.5, layout_config={"seed": 42}
        )
        self.play(m.Create(G))
        self.play(
            *[
                G[v].animate.move_to(
                    5 * m.RIGHT * np.cos(ind / 7 * m.PI)
                    + 3 * m.UP * np.sin(ind / 7 * m.PI)
                )
                for ind, v in enumerate(G.vertices)
            ]
        )
        self.play(m.Uncreate(G))

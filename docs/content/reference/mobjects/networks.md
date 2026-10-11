---
title: "Networks"
description: "Graphs in the sense of networks: vertices joined by edges, laid out for you or by hand, which grow and change as a scene plays."
---

# Networks

```python fold title="The film's code"
import manimgx as m


class NetworksHero(m.Scene):
    def construct(self) -> None:
        vertices = [1, 2, 3, 4, 5, 6]
        edges = [(1, 2), (2, 3), (3, 1), (3, 4), (4, 5), (5, 6), (6, 4)]
        graph = m.Graph(vertices, edges, layout="spring", labels=True, layout_scale=3)
        self.play(m.Create(graph))
        self.play(graph.animate.change_layout("circular", layout_scale=3))
        self.wait()
```

A network is vertices, joined by edges: a graph, as graph theory says it. (For the graph of
a function, see [Plotting](graphs/plotting.md).) [Graph][manimgx.Graph] joins its vertices
with lines, [DiGraph][manimgx.DiGraph] with arrows, from each edge's first vertex to its
second. Each lays its vertices out for you (`layout="spring"`, `"circular"`, `"tree"`, …),
or where you place them; a vertex is a dot unless you give another mobject.

Both can do what follows: add and remove vertices and edges, change their layout, and read
a network from NetworkX.

::: manimgx.Graph
    options:
      heading_level: 2
      members: false

::: manimgx.DiGraph
    options:
      heading_level: 2
      members: false

::: manimgx.mobjects.graph.TipConfig
    options:
      heading_level: 3

## What a network can do

Graph and DiGraph are both made from GenericGraph, which holds what they can do.

::: manimgx.mobjects.graph.GenericGraph
    options:
      heading_level: 3
      extra:
        members_only: true
      members: [vertices, edges, add_vertices, remove_vertices, add_edges, remove_edges, change_layout, from_networkx, update_edges]

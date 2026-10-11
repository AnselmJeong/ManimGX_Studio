# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class GraphAddRemoveExample(m.Scene):
    def construct(self):
        g = m.Graph(vertices=[1, 2, 3], edges=[(1, 2), (2, 3)])
        g.add_vertices(4, 5)
        g.add_edges((3, 4), (4, 5))
        g.remove_edges((1, 2))
        g.remove_vertices(5)
        self.add(g)
        self.wait()

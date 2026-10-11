# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class GraphVertexTypeEdgeTypeExample(m.Scene):
    def construct(self):
        g = m.Graph(
            vertices=[1, 2, 3],
            edges=[(1, 2), (2, 3), (1, 3)],
            labels=True,
            label_fill_color=m.RED,
            vertex_type=m.LabeledDot,
            edge_type=m.Line,
        )
        self.add(g)
        self.wait()

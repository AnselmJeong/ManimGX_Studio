# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class LayoutFunctionProtocolExample(m.Scene):
    def construct(self):
        def grid_layout(graph, scale=2.0, **kwargs):
            nodes = list(graph)
            # CE's change_layout calls Mobject.move_to with these values, which
            # requires 3D points — 2-tuples raise a broadcasting error.
            return {n: (scale * (i - 1), 0.0, 0.0) for i, n in enumerate(nodes)}

        g = m.Graph(
            vertices=[0, 1, 2],
            edges=[(0, 1), (1, 2)],
            layout=grid_layout,
        )
        self.add(g)
        self.wait()

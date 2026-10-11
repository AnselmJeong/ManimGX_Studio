# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class GraphVertexMobjectsExample(m.Scene):
    def construct(self):
        custom = m.Dot(color=m.YELLOW, radius=0.18)
        g = m.Graph(
            vertices=[1, 2, 3],
            edges=[(1, 2), (2, 3)],
            vertex_mobjects={1: custom},
        )
        self.add(g)
        self.wait()

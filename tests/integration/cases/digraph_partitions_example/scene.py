# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class DiGraphPartitionsExample(m.Scene):
    def construct(self):
        g = m.DiGraph(
            vertices=[0, 1, 2, 3],
            edges=[(0, 2), (1, 3)],
            layout="partite",
            partitions=[[0, 1], [2, 3]],
        )
        self.add(g)
        self.wait()

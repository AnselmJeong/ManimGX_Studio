# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class ComplexPlaneNumberKwargExample(m.Scene):
    def construct(self):
        cp = m.ComplexPlane()
        pt = cp.number_to_point(number=2 + 1j)
        also = cp.n2p(number=2 + 1j)
        self.add(cp, m.Dot(pt), m.Dot(also))
        self.wait()

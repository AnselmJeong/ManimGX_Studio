# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class ComplexPlaneExample(m.Scene):
    def construct(self):
        plane = m.ComplexPlane().add_coordinates()
        self.add(plane)
        d1 = m.Dot(plane.n2p(2 + 1j), color=m.YELLOW)
        d2 = m.Dot(plane.n2p(-3 - 2j), color=m.YELLOW)
        label1 = m.MathTex("2+i").next_to(d1, m.UR, 0.1)
        label2 = m.MathTex("-3-2i").next_to(d2, m.UR, 0.1)
        self.add(
            d1,
            label1,
            d2,
            label2,
        )
        self.wait()

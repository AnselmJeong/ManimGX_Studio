# Source: manim/mobject/geometry/arc.py
import manimgx as m


class DotExample(m.Scene):
    def construct(self):
        dot1 = m.Dot(point=m.LEFT, radius=0.08)
        dot2 = m.Dot(point=m.ORIGIN)
        dot3 = m.Dot(point=m.RIGHT)
        self.add(dot1, dot2, dot3)
        self.wait()

# Source: manim/mobject/geometry/arc.py
import manimgx as m


class ArcExample(m.Scene):
    def construct(self):
        self.add(m.Arc(angle=m.PI))
        self.wait()

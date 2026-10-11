# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class RegularPolygramExample(m.Scene):
    def construct(self):
        pentagram = m.RegularPolygram(5, radius=2)
        self.add(pentagram)
        self.wait()

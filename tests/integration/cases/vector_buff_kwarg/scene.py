# Source: manim/mobject/geometry/line.py
import manimgx as m


class VectorBuffKwarg(m.Scene):
    def construct(self):
        plane = m.NumberPlane()
        v = m.Vector([2, 1], buff=0.6, color=m.YELLOW)
        self.add(plane, v)
        self.wait()

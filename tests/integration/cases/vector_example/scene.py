# Source: manim/mobject/geometry/line.py
import manimgx as m


class VectorExample(m.Scene):
    def construct(self):
        plane = m.NumberPlane()
        vector_1 = m.Vector([1, 2])
        vector_2 = m.Vector([-5, -2])
        self.add(plane, vector_1, vector_2)
        self.wait()

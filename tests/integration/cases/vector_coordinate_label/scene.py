# Source: manim/mobject/geometry/line.py
import manimgx as m


class VectorCoordinateLabel(m.Scene):
    def construct(self):
        plane = m.NumberPlane()

        vec_1 = m.Vector([1, 2])
        vec_2 = m.Vector([-3, -2])
        label_1 = vec_1.coordinate_label()
        label_2 = vec_2.coordinate_label(color=m.YELLOW)

        self.add(plane, vec_1, vec_2, label_1, label_2)
        self.wait()

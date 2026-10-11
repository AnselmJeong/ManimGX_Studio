# Source: manim/mobject/three_d/polyhedra.py
import manimgx as m


class DodecahedronScene(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        obj = m.Dodecahedron()
        self.add(obj)
        self.wait()

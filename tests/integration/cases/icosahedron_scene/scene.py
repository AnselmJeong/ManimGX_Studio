# Source: manim/mobject/three_d/polyhedra.py
import manimgx as m


class IcosahedronScene(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        obj = m.Icosahedron()
        self.add(obj)
        self.wait()

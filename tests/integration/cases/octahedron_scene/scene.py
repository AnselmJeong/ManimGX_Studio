# Source: manim/mobject/three_d/polyhedra.py
import manimgx as m


class OctahedronScene(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        obj = m.Octahedron()
        self.add(obj)
        self.wait()

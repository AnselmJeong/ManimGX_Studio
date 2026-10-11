# Source: manim/mobject/three_d/polyhedra.py
import manimgx as m


class PolyhedronSubMobjects(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        octahedron = m.Octahedron(edge_length=3)
        octahedron.graph[0].set_color(m.RED)
        octahedron.faces[2].set_color(m.YELLOW)
        self.add(octahedron)

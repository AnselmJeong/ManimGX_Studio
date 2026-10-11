# Source: manim/mobject/three_d/polyhedra.py
import manimgx as m


class SquarePyramidScene(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        vertex_coords = [[1, 1, 0], [1, -1, 0], [-1, -1, 0], [-1, 1, 0], [0, 0, 2]]
        faces_list = [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4], [0, 1, 2, 3]]
        pyramid = m.Polyhedron(vertex_coords, faces_list)
        self.add(pyramid)
        self.wait()

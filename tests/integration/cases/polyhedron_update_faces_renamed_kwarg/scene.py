# Source: manim/mobject/three_d/polyhedra.py
import manimgx as m


class PolyhedronUpdateFacesRenamedKwarg(m.ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * m.DEGREES, theta=30 * m.DEGREES)
        poly = m.Polyhedron(
            vertex_coords=[[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1]],
            faces_list=[[0, 2, 4], [1, 2, 4], [0, 3, 4], [1, 3, 4]],
        )
        # CE signature: ``update_faces(self, m)``. Passing ``poly`` rebuilds
        # the face submobjects from current graph vertex positions.
        poly.update_faces(poly)
        self.add(poly)
        self.wait(0.1)

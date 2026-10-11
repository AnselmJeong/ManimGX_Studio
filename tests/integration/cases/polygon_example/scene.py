# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class PolygonExample(m.Scene):
    def construct(self):
        isosceles = m.Polygon([-5, 1.5, 0], [-2, 1.5, 0], [-3.5, -2, 0])
        position_list = [
            [4, 1, 0],  # middle right
            [4, -2.5, 0],  # bottom right
            [0, -2.5, 0],  # bottom left
            [0, 3, 0],  # top left
            [2, 1, 0],  # middle
            [4, 3, 0],  # top right
        ]
        square_and_triangles = m.Polygon(*position_list, color=m.PURPLE_B)
        self.add(isosceles, square_and_triangles)
        self.wait()

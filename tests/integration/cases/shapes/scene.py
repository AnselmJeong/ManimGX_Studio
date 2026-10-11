# Source: docs/source/tutorials/building_blocks.rst
import manimgx as m


class Shapes(m.Scene):
    def construct(self):
        circle = m.Circle()
        square = m.Square()
        triangle = m.Triangle()

        circle.shift(m.LEFT)
        square.shift(m.UP)
        triangle.shift(m.RIGHT)

        self.add(circle, square, triangle)
        self.wait(1)

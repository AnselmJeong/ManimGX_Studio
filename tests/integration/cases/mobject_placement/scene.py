# Source: docs/source/tutorials/building_blocks.rst
import manimgx as m


class MobjectPlacement(m.Scene):
    def construct(self):
        circle = m.Circle()
        square = m.Square()
        triangle = m.Triangle()

        # place the circle two units left from the origin
        circle.move_to(m.LEFT * 2)
        # place the square to the left of the circle
        square.next_to(circle, m.LEFT)
        # align the left border of the triangle to the left border of the circle
        triangle.align_to(circle, m.LEFT)

        self.add(circle, square, triangle)
        self.wait(1)

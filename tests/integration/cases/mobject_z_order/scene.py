# Source: docs/source/tutorials/building_blocks.rst
import manimgx as m


class MobjectZOrder(m.Scene):
    def construct(self):
        circle = m.Circle().shift(m.LEFT)
        square = m.Square().shift(m.UP)
        triangle = m.Triangle().shift(m.RIGHT)

        circle.set_stroke(color=m.GREEN, width=20)
        square.set_fill(m.YELLOW, opacity=1.0)
        triangle.set_fill(m.PINK, opacity=0.5)

        self.add(triangle, square, circle)
        self.wait(1)

# Source: docs/source/examples.rst
import manimgx as m


class MovingAround(m.Scene):
    def construct(self):
        square = m.Square(color=m.BLUE, fill_opacity=1)

        self.play(square.animate.shift(m.LEFT))
        self.play(square.animate.set_fill(m.ORANGE))
        self.play(square.animate.scale(0.3))
        self.play(m.Rotate(square, angle=0.4))

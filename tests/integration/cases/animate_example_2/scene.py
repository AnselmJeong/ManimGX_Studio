# Source: docs/source/tutorials/building_blocks.rst
import manimgx as m


class AnimateExample(m.Scene):
    def construct(self):
        square = m.Square().set_fill(m.RED, opacity=1.0)
        self.add(square)

        # animate the change of color
        self.play(square.animate.set_fill(m.WHITE))
        self.wait(1)

        # animate the change of position and the rotation at the same time
        self.play(square.animate.shift(m.UP), m.Rotate(square, angle=m.PI / 3))
        self.wait(1)

# Source: docs/source/tutorials/quickstart.rst
import manimgx as m


class DifferentRotations2(m.Scene):
    def construct(self):
        left_square = m.Square(color=m.BLUE, fill_opacity=0.7).shift(2 * m.LEFT)
        right_square = m.Square(color=m.GREEN, fill_opacity=0.7).shift(2 * m.RIGHT)
        self.play(
            m.Rotate(left_square, angle=m.PI),
            m.Rotate(right_square, angle=m.PI),
            run_time=2,
        )
        self.wait()

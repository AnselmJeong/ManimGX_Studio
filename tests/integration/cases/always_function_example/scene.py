# Source: manimgx API coverage (CE 0.21 `always`)
import manimgx as m


class AlwaysFunctionExample(m.Scene):
    def construct(self):
        square = m.Square(color=m.BLUE).shift(3 * m.LEFT)
        dot = m.Dot(color=m.YELLOW)
        m.always(dot.next_to, square, m.UP)
        self.add(square, dot)
        self.play(square.animate.shift(6 * m.RIGHT), run_time=2)

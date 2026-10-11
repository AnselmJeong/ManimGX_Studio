# Source: manim/animation/updaters/mobject_update_utils.py
import manimgx as m


class ShiftingSquare(m.Scene):
    def construct(self):
        sq = m.Square().set_fill(opacity=1)
        tri = m.Triangle()
        m.VGroup(sq, tri).arrange(m.LEFT)

        # construct a square which is continuously
        # shifted to the right
        m.always_shift(sq, m.RIGHT, rate=5)

        self.add(sq)
        self.play(tri.animate.set_fill(opacity=1))

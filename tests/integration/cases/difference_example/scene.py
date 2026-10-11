# Source: manim/mobject/geometry/boolean_ops.py
import manimgx as m


class DifferenceExample(m.Scene):
    def construct(self):
        sq = m.Square(color=m.RED, fill_opacity=1)
        sq.move_to([-2, 0, 0])
        cr = m.Circle(color=m.BLUE, fill_opacity=1)
        cr.move_to([-1.3, 0.7, 0])
        un = m.Difference(sq, cr, color=m.GREEN, fill_opacity=1)
        un.move_to([1.5, 0, 0])
        self.add(sq, cr, un)
        self.wait()

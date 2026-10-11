# Source: manim/animation/movement.py
import manimgx as m


class MoveAlongPathExample(m.Scene):
    def construct(self):
        d1 = m.Dot().set_color(m.ORANGE)
        l1 = m.Line(m.LEFT, m.RIGHT)
        l2 = m.VMobject()
        self.add(d1, l1, l2)
        l2.add_updater(
            lambda x: x.become(m.Line(m.LEFT, d1.get_center()).set_color(m.ORANGE))
        )
        self.play(m.MoveAlongPath(d1, l1), rate_func=m.linear)

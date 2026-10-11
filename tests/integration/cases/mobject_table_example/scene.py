# Source: manim/mobject/table.py
import manimgx as m


class MobjectTableExample(m.Scene):
    def construct(self):
        cross = m.VGroup(
            m.Line(m.UP + m.LEFT, m.DOWN + m.RIGHT),
            m.Line(m.UP + m.RIGHT, m.DOWN + m.LEFT),
        )
        a = m.Circle().set_color(m.RED).scale(0.5)
        b = cross.set_color(m.BLUE).scale(0.5)
        t0 = m.MobjectTable(
            [
                [a.copy(), b.copy(), a.copy()],
                [b.copy(), a.copy(), a.copy()],
                [a.copy(), b.copy(), b.copy()],
            ]
        )
        line = m.Line(t0.get_corner(m.DL), t0.get_corner(m.UR)).set_color(m.RED)
        self.add(t0, line)
        self.wait()

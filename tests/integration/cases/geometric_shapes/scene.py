# Source: manim/mobject/mobject.py
import manimgx as m


class GeometricShapes(m.Scene):
    def construct(self):
        d = m.Dot()
        c = m.Circle()
        s = m.Square()
        t = m.Triangle()
        d.next_to(c, m.RIGHT)
        s.next_to(c, m.LEFT)
        t.next_to(c, m.DOWN)
        self.add(d, c, s, t)
        self.wait()

# Source: manim/mobject/mobject.py
import manimgx as m


class FlipExample(m.Scene):
    def construct(self):
        s = m.Line(m.LEFT, m.RIGHT + m.UP).shift(4 * m.LEFT)
        self.add(s)
        s2 = s.copy().flip()
        self.add(s2)
        self.wait()

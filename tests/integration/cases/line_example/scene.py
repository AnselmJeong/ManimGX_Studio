# Source: manim/mobject/geometry/line.py
import manimgx as m


class LineExample(m.Scene):
    def construct(self):
        line1 = m.Line(m.LEFT * 2, m.RIGHT * 2)
        line2 = m.Line(m.LEFT * 2, m.RIGHT * 2, buff=0.5)
        line3 = m.Line(m.LEFT * 2, m.RIGHT * 2, path_arc=m.PI / 2)
        grp = m.VGroup(line1, line2, line3).arrange(m.DOWN, buff=2)
        self.add(grp)
        self.wait()

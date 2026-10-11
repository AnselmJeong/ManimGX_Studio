# Source: manim/mobject/geometry/line.py
import manimgx as m


class LineExample(m.Scene):
    def construct(self):
        d = m.VGroup()
        for i in range(10):
            d.add(m.Dot())
        d.arrange_in_grid(buff=1)
        self.add(d)
        l = m.Line(d[0].get_center(), d[1].get_center())
        self.add(l)
        self.wait()
        l.put_start_and_end_on(d[1].get_center(), d[2].get_center())
        self.wait()
        l.put_start_and_end_on(d[4].get_center(), d[7].get_center())
        self.wait()

# Source: manim/mobject/mobject.py
import manimgx as m


class Example(m.Scene):
    def construct(self):
        s1 = m.Square()
        s2 = m.Square()
        s3 = m.Square()
        s4 = m.Square()
        x = m.VGroup(s1, s2, s3, s4).set_x(0).arrange(buff=1.0)
        self.add(x)
        self.wait()

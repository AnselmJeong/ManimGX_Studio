# Source: manim/mobject/mobject.py
import manimgx as m


class ShuffleSubmobjectsExample(m.Scene):
    def construct(self):
        s = m.VGroup(*[m.Dot().shift(i * 0.1 * m.RIGHT) for i in range(-20, 20)])
        s2 = s.copy()
        s2.shift(m.DOWN)
        self.play(m.Write(s), m.Write(s2))

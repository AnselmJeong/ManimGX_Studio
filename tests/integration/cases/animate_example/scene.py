# Source: manim/mobject/mobject.py
import manimgx as m


class AnimateExample(m.Scene):
    def construct(self):
        s = m.Square()
        self.play(m.Create(s))
        self.play(s.animate.shift(m.RIGHT))
        self.play(s.animate.scale(2))
        self.play(m.Rotate(s, angle=m.PI / 2))
        self.play(m.Uncreate(s))

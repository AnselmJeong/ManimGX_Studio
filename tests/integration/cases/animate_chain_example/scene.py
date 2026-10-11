# Source: manim/mobject/mobject.py
import manimgx as m


class AnimateChainExample(m.Scene):
    def construct(self):
        s = m.Square()
        self.play(m.Create(s))
        self.play(
            s.animate.shift(m.RIGHT).scale(2),
            m.Rotate(s, angle=m.PI / 2),
        )
        self.play(m.Uncreate(s))

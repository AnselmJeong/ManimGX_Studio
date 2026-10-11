# Source: manim/animation/creation.py
import manimgx as m


class UnwriteReverseFalse(m.Scene):
    def construct(self):
        text = m.Tex("Alice and Bob").scale(3)
        self.add(text)
        self.play(m.Unwrite(text, reverse=False))

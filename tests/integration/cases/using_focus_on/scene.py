# Source: manim/animation/indication.py
import manimgx as m


class UsingFocusOn(m.Scene):
    def construct(self):
        dot = m.Dot(color=m.PURE_YELLOW).shift(m.DOWN)
        self.add(m.Tex("Focusing on the dot below:"), dot)
        self.play(m.FocusOn(dot))
        self.wait()

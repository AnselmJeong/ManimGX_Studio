# Source: manim/animation/indication.py
import manimgx as m


class UsingFlash(m.Scene):
    def construct(self):
        dot = m.Dot(color=m.PURE_YELLOW).shift(m.DOWN)
        self.add(m.Tex("Flash the dot below:"), dot)
        self.play(m.Flash(dot))
        self.wait()

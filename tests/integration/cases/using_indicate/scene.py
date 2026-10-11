# Source: manim/animation/indication.py
import manimgx as m


class UsingIndicate(m.Scene):
    def construct(self):
        tex = m.Tex("Indicate").scale(3)
        self.play(m.Indicate(tex))
        self.wait()

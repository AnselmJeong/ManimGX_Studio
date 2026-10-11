# Source: manim/animation/indication.py
import manimgx as m


class ApplyingWaves(m.Scene):
    def construct(self):
        tex = m.Tex("Wiggle").scale(3)
        self.play(m.Wiggle(tex))
        self.wait()

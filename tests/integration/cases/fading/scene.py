# Source: manim/animation/fading.py
import manimgx as m


class Fading(m.Scene):
    def construct(self):
        tex_in = m.Tex("Fade", "In").scale(3)
        tex_out = m.Tex("Fade", "Out").scale(3)
        self.play(m.FadeIn(tex_in, shift=m.DOWN, scale=0.66))
        self.play(m.ReplacementTransform(tex_in, tex_out))
        self.play(m.FadeOut(tex_out, shift=m.DOWN * 2, scale=1.5))

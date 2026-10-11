# Source: manim/mobject/text/tex_mobject.py
import manimgx as m


class Formula(m.Scene):
    def construct(self):
        t = m.MathTex(r"\int_a^b f'(x) dx = f(b)- f(a)")
        self.add(t)
        self.wait()

# Source: manim/mobject/matrix.py
import manimgx as m


class MobjectMatrixExample(m.Scene):
    def construct(self):
        a = m.Circle().scale(0.3)
        b = m.Square().scale(0.3)
        c = m.MathTex("\\pi").scale(2)
        d = m.Star().scale(0.3)
        m0 = m.MobjectMatrix([[a, b], [c, d]])
        self.add(m0)
        self.wait()

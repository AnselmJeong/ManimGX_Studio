# Source: manim/mobject/mobject.py
import manimgx as m


class ToCornerExample(m.Scene):
    def construct(self):
        c = m.Circle()
        c.to_corner(m.UR)
        t = m.Tex("To the corner!")
        t2 = m.MathTex("x^3").shift(m.DOWN)
        self.add(c, t, t2)
        t.to_corner(m.DL, buff=0)
        t2.to_corner(m.UL, buff=1.5)
        self.wait()

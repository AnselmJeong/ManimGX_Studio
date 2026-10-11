# Source: manim/animation/creation.py
import manimgx as m


class SpiralInExample(m.Scene):
    def construct(self):
        pi = m.MathTex(r"\pi").scale(7)
        pi.shift(2.25 * m.LEFT + 1.5 * m.UP)
        circle = m.Circle(color=m.GREEN_C, fill_opacity=1).shift(m.LEFT)
        square = m.Square(color=m.BLUE_D, fill_opacity=1).shift(m.UP)
        shapes = m.VGroup(pi, circle, square)
        self.play(m.SpiralIn(shapes))

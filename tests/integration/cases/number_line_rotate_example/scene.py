# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class NumberLineRotateExample(m.Scene):
    def construct(self):
        a = m.NumberLine(x_range=(-3, 3, 1)).shift(m.UP * 2)
        b = m.NumberLine(x_range=(-3, 3, 1)).shift(m.DOWN * 2)
        a.rotate_about_zero(m.PI / 4)
        b.rotate_about_number(1, m.PI / 6)
        self.add(a, b)
        self.wait()

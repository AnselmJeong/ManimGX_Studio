# Source: manim/mobject/matrix.py
import manimgx as m


class GetBracketsExample(m.Scene):
    def construct(self):
        m0 = m.Matrix([["\\pi", 3], [1, 5]])
        bra = m0.get_brackets()
        colors = [m.BLUE, m.GREEN]
        for k in range(len(colors)):
            bra[k].set_color(colors[k])
        self.add(m0)
        self.wait()

# Source: docs/source/contributing/docs/examples.rst
import manimgx as m


class Formula1(m.Scene):
    def construct(self):
        t = m.MathTex(r"\int_a^b f'(x) dx = f(b) - f(a)")
        self.add(t)
        self.wait(1)

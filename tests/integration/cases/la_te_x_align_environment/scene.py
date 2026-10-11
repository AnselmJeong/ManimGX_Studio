# Source: docs/source/guides/using_text.rst
import manimgx as m


class LaTeXAlignEnvironment(m.Scene):
    def construct(self):
        tex = m.MathTex(r"f(x) &= 3 + 2 + 1\\ &= 5 + 1 \\ &= 6", font_size=96)
        self.add(tex)
        self.wait()

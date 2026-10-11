# Source: docs/source/guides/using_text.rst
import manimgx as m


class LaTeXAttributes(m.Scene):
    def construct(self):
        tex = m.Tex(r"Hello \LaTeX", color=m.BLUE, font_size=144)
        self.add(tex)
        self.wait()

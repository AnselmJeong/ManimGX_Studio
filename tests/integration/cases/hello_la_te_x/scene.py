# Source: docs/source/guides/using_text.rst
import manimgx as m


class HelloLaTeX(m.Scene):
    def construct(self):
        tex = m.Tex(r"\LaTeX", font_size=144)
        self.add(tex)
        self.wait()

# Source: docs/source/guides/using_text.rst
import manimgx as m


class HelloCjkLatex(m.Scene):
    def construct(self):
        hello = m.Tex("Hello", font_size=144)
        cjk = m.Text("你好", font_size=144)
        latex = m.Tex(r"\LaTeX", font_size=144)
        m.VGroup(hello, cjk, latex).arrange(m.RIGHT, buff=0.4)
        self.add(hello, cjk, latex)

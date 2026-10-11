# Source: docs/source/guides/using_text.rst
import manimgx as m


class LaTeXSubstrings(m.Scene):
    def construct(self):
        tex = m.Tex("Hello", r"$\bigstar$", r"\LaTeX", font_size=144)
        tex.set_color_by_tex(r"$\bigstar$", m.RED)
        self.add(tex)
        self.wait()

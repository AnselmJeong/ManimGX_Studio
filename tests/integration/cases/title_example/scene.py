# Source: manim/mobject/text/tex_mobject.py
import manimgx as m


class TitleExample(m.Scene):
    def construct(self):
        banner = m.ManimBanner()
        title = m.Title("Manim version 0.1.0")
        self.add(banner, title)

# Source: manim/constants.py
import manimgx as m


class DefaultFontSizeConstant(m.Scene):
    def construct(self):
        text = m.Text("Manim", font_size=m.DEFAULT_FONT_SIZE)
        self.add(text)
        self.wait()

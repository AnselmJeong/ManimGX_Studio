# Source: manim/animation/creation.py
import manimgx as m


class ShowWrite(m.Scene):
    def construct(self):
        self.play(m.Write(m.Text("Hello", font_size=144)))

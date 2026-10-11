# Source: manim/animation/creation.py
import manimgx as m


class ShowWriteReversed(m.Scene):
    def construct(self):
        self.play(m.Write(m.Text("Hello", font_size=144), reverse=True, remover=False))

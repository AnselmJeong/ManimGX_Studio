# Source: manim/animation/transform.py
import manimgx as m


class FadeToColorExample(m.Scene):
    def construct(self):
        self.play(m.FadeToColor(m.Text("Hello World!"), color=m.RED))

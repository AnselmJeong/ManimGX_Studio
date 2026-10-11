# Source: manim/animation/transform.py
import manimgx as m


class ScaleInPlaceExample(m.Scene):
    def construct(self):
        self.play(m.ScaleInPlace(m.Text("Hello World!"), 2))

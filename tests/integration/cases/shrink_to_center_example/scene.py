# Source: manim/animation/transform.py
import manimgx as m


class ShrinkToCenterExample(m.Scene):
    def construct(self):
        self.play(m.ShrinkToCenter(m.Text("Hello World!")))

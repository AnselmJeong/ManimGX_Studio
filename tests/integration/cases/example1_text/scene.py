# Source: manim/mobject/text/text_mobject.py
import manimgx as m


class Example1Text(m.Scene):
    def construct(self):
        text = m.Text("Hello world").scale(3)
        self.add(text)
        self.wait()

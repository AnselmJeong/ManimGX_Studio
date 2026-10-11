# Source: manim/animation/creation.py
import manimgx as m


class AddTextWordByWordExample(m.Scene):
    def construct(self):
        text = m.Text("Hello world", font_size=72)
        self.play(m.AddTextWordByWord(text))
        self.wait(0.2)

# Source: manim/animation/creation.py
import manimgx as m


class RemoveTextLetterByLetterExample(m.Scene):
    def construct(self):
        text = m.Text("Hello", font_size=144)
        self.add(text)
        self.play(m.RemoveTextLetterByLetter(text))
        self.wait(0.2)

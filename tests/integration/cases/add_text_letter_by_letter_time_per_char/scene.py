# Source: manim/animation/creation.py
import manimgx as m


class AddTextLetterByLetterTimePerChar(m.Scene):
    def construct(self):
        text = m.Text("Hello", font_size=144)
        self.play(m.AddTextLetterByLetter(text, time_per_char=0.15))
        self.wait(0.2)

# Source: manim/mobject/geometry/shape_matchers.py
import manimgx as m


class UnderLine(m.Scene):
    def construct(self):
        man = m.Tex("Manim")  # Full Word
        ul = m.Underline(man)  # Underlining the word
        self.add(man, ul)
        self.wait()

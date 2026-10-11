# Source: manim/animation/creation.py
import manimgx as m


class ShowUncreate(m.Scene):
    def construct(self):
        self.play(m.Uncreate(m.Square()))

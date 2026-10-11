# Source: manim/animation/creation.py
import manimgx as m


class CreateScene(m.Scene):
    def construct(self):
        self.play(m.Create(m.Square()))

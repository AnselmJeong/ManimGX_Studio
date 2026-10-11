# Source: manim/animation/creation.py
import manimgx as m


class ShowDrawBorderThenFill(m.Scene):
    def construct(self):
        self.play(m.DrawBorderThenFill(m.Square(fill_opacity=1, fill_color=m.ORANGE)))

# Source: manim/mobject/frame.py
import manimgx as m


class FullScreenRectangleExample(m.Scene):
    def construct(self):
        backdrop = m.FullScreenRectangle(color=m.GREY_C, fill_opacity=0.6)
        self.add(backdrop)
        self.wait()

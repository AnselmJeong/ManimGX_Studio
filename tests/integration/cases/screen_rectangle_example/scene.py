# Source: manim/mobject/frame.py
import manimgx as m


class ScreenRectangleExample(m.Scene):
    def construct(self):
        rect = m.ScreenRectangle(aspect_ratio=16 / 9, height=4, color=m.BLUE)
        rect.set_stroke(width=4)
        self.add(rect)
        self.wait()

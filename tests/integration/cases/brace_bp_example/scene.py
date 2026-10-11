# Source: manim/mobject/svg/brace.py
import manimgx as m


class BraceBPExample(m.Scene):
    def construct(self):
        p1 = [0, 0, 0]
        p2 = [1, 2, 0]
        brace = m.BraceBetweenPoints(p1, p2)
        self.play(m.Create(m.NumberPlane()))
        self.play(m.Create(brace))
        self.wait(2)

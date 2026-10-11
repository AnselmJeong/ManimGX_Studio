# Source: manim/mobject/geometry/shape_matchers.py
import manimgx as m


class ExampleCross(m.Scene):
    def construct(self):
        cross = m.Cross()
        self.add(cross)
        self.wait()

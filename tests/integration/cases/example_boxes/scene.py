# Source: manim/mobject/mobject.py
import manimgx as m


class ExampleBoxes(m.Scene):
    def construct(self):
        boxes = m.VGroup(*[m.Square() for s in range(6)])
        boxes.arrange_in_grid(rows=2, buff=0.1)
        self.add(boxes)
        self.wait()

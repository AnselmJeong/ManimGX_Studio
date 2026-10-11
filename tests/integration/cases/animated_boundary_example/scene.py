# Source: manim/animation/changing.py
import manimgx as m


class AnimatedBoundaryExample(m.Scene):
    def construct(self):
        text = m.Text("So shiny!")
        boundary = m.AnimatedBoundary(
            text, colors=[m.RED, m.GREEN, m.BLUE], cycle_rate=3
        )
        self.add(text, boundary)
        self.wait(2)

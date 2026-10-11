# Source: manim/constants.py
import manimgx as m


class DefaultBufferConstants(m.Scene):
    def construct(self):
        square = m.Square().to_edge(m.LEFT, buff=m.DEFAULT_MOBJECT_TO_EDGE_BUFFER)
        circle = m.Circle().next_to(
            square, m.RIGHT, buff=m.DEFAULT_MOBJECT_TO_MOBJECT_BUFFER
        )
        self.add(square, circle)
        self.wait()

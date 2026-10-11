# Source: manim/mobject/vector_field.py
import manimgx as m


class BasicUsage(m.Scene):
    def construct(self):
        func = lambda pos: ((pos[0] * m.UR + pos[1] * m.LEFT) - pos) / 3
        self.add(m.StreamLines(func, virtual_time=2.9))
        self.wait()

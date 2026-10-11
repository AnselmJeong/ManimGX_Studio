# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class CapStyleExample(m.Scene):
    def construct(self):
        line = m.Line(m.LEFT, m.RIGHT, color=m.YELLOW, stroke_width=20)
        line.set_cap_style(m.CapStyleType.ROUND)
        self.add(line)
        self.wait()

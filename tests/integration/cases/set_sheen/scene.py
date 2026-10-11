# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class SetSheen(m.Scene):
    def construct(self):
        circle = m.Circle(fill_opacity=1).set_sheen(-0.3, m.DR)
        self.add(circle)
        self.wait()

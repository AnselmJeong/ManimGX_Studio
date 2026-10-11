# Source: manim/mobject/vector_field.py
import manimgx as m


class Coloring(m.Scene):
    def construct(self):
        func = lambda pos: pos - m.LEFT * 5
        colors = [
            m.RED,
            m.YELLOW,
            m.BLUE,
            m.DARK_GRAY,
        ]
        min_radius = m.Circle(radius=2, color=colors[0]).shift(m.LEFT * 5)
        max_radius = m.Circle(radius=10, color=colors[-1]).shift(m.LEFT * 5)
        vf = m.ArrowVectorField(
            func, min_color_scheme_value=2, max_color_scheme_value=10, colors=colors
        )
        self.add(vf, min_radius, max_radius)
        self.wait()

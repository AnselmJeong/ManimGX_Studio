# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class DifferentDensitiesExample(m.Scene):
    def construct(self):
        density_2 = m.Star(7, outer_radius=2, density=2, color=m.RED)
        density_3 = m.Star(7, outer_radius=2, density=3, color=m.PURPLE)

        self.add(m.VGroup(density_2, density_3).arrange(m.RIGHT))
        self.wait()

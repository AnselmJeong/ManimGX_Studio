# Source: manim/mobject/geometry/polygram.py
import manimgx as m


class PolygramRoundCorners(m.Scene):
    def construct(self):
        star = m.Star(outer_radius=2)

        shapes = m.VGroup(star)
        shapes.add(star.copy().round_corners(radius=0.1))
        shapes.add(star.copy().round_corners(radius=0.25))

        shapes.arrange(m.RIGHT)
        self.add(shapes)
        self.wait()

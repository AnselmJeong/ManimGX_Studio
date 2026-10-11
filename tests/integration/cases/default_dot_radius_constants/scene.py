# Source: manim/constants.py
import manimgx as m


class DefaultDotRadiusConstants(m.Scene):
    def construct(self):
        big = m.Dot(point=m.LEFT, radius=m.DEFAULT_DOT_RADIUS)
        small = m.Dot(point=m.RIGHT, radius=m.DEFAULT_SMALL_DOT_RADIUS)
        self.add(big, small)
        self.wait()

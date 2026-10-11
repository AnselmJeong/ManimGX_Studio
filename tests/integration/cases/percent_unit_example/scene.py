# Source: manim/utils/unit.py
import manimgx as m
from manimgx import Percent


class PercentUnitExample(m.Scene):
    def construct(self):
        half_width = 50 * Percent(m.X_AXIS)
        dot_left = m.Dot(m.LEFT * (half_width / 2), color=m.BLUE)
        dot_right = m.Dot(m.RIGHT * (half_width / 2), color=m.RED)
        self.add(dot_left, dot_right)
        self.wait()

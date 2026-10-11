# Source: manim/animation/transform.py
import manimgx as m


class SwapExample(m.Scene):
    def construct(self):
        left = m.Square(color=m.BLUE, fill_opacity=1.0).shift(2 * m.LEFT)
        right = m.Circle(color=m.RED, fill_opacity=1.0).shift(2 * m.RIGHT)
        self.add(left, right)
        self.play(m.Swap(left, right))

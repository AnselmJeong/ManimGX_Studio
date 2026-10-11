# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class VMobjectInterpolateColorExample(m.Scene):
    def construct(self):
        start = m.Square(side_length=1.2).set_fill(m.RED, opacity=1.0)
        end = m.Square(side_length=1.2).set_fill(m.BLUE, opacity=1.0)
        blended = m.Square(side_length=1.2).set_fill(m.WHITE, opacity=1.0)
        blended.interpolate_color(start, end, 0.5)
        row = m.Group(start, blended, end).arrange(m.RIGHT, buff=0.4)
        self.add(row)
        self.wait()

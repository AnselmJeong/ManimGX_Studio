# Source: manim/mobject/geometry/arc.py
import manimgx as m


class AnnotationDotFillColorKwarg(m.Scene):
    def construct(self):
        dot_a = m.AnnotationDot(fill_color=m.RED).shift(m.LEFT * 1.5)
        dot_b = m.AnnotationDot(fill_color=m.GREEN).shift(m.RIGHT * 1.5)
        self.add(dot_a, dot_b)
        self.wait()

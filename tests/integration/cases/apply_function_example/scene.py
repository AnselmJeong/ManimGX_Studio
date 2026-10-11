# Source: manim/animation/transform.py
import manimgx as m


class ApplyFunctionExample(m.Scene):
    def construct(self):
        square = m.Square()
        self.add(square)

        def to_red_circle(mobject):
            return m.Circle(color=m.RED, fill_opacity=1.0).move_to(mobject)

        self.play(m.ApplyFunction(to_red_circle, square))

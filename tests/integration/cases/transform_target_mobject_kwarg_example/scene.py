# Source: manim/animation/transform.py
import manimgx as m


class TransformTargetMobjectKwargExample(m.Scene):
    def construct(self):
        square = m.Square(color=m.BLUE, fill_opacity=1.0)
        circle = m.Circle(color=m.RED, fill_opacity=1.0)
        self.add(square)
        self.play(m.Transform(square, target_mobject=circle))

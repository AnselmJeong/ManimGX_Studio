# Source: manim/animation/transform.py
import manimgx as m


class FadeTransformTargetMobjectKwargExample(m.Scene):
    def construct(self):
        rect = m.Rectangle(width=3, height=1).shift(2 * m.LEFT)
        circ = m.Circle(fill_opacity=1.0).shift(2 * m.RIGHT)
        self.add(rect)
        self.play(m.FadeTransform(rect, target_mobject=circ))

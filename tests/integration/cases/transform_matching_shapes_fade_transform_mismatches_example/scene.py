# Source: manim/animation/transform_matching_parts.py
import manimgx as m


class TransformMatchingShapesFadeTransformMismatchesExample(m.Scene):
    def construct(self):
        src = m.MathTex("a", "+", "b")
        tgt = m.MathTex("c", "+", "d").shift(2 * m.DOWN)
        self.add(src)
        self.play(m.TransformMatchingShapes(src, tgt, fade_transform_mismatches=True))

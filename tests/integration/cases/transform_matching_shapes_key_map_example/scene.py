# Source: manim/animation/transform_matching_parts.py
import manimgx as m


class TransformMatchingShapesKeyMapExample(m.Scene):
    def construct(self):
        src = m.MathTex("a", "+", "b")
        tgt = m.MathTex("c", "+", "d")
        tgt.shift(2 * m.DOWN)
        self.add(src)
        self.play(
            m.TransformMatchingShapes(src, tgt, transform_mismatches=True, path_arc=0.5)
        )

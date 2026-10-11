# Source: manim/animation/transform_matching_parts.py
from manimgx import (
    BLUE,
    DOWN,
    GREEN,
    RED,
    RIGHT,
    YELLOW,
    Circle,
    Scene,
    Square,
    TransformMatchingAbstractBase,
    Triangle,
    VGroup,
)


class _TypeNameMatching(TransformMatchingAbstractBase):
    @staticmethod
    def get_mobject_parts(mobject):
        return list(mobject.submobjects) or [mobject]

    @staticmethod
    def get_mobject_key(mobject):
        return type(mobject).__name__


class TransformMatchingShapesKeyMapRealExample(Scene):
    def construct(self):
        # Source has a Square; target has a Triangle. Their type-name
        # keys don't match by default, so key_map forces the pairing
        # and the Square morphs into the Triangle instead of fading.
        src = VGroup(Square(color=BLUE), Circle(color=RED)).arrange(RIGHT)
        tgt = VGroup(Triangle(color=GREEN), Circle(color=YELLOW)).arrange(RIGHT)
        tgt.shift(2 * DOWN)
        self.add(src)
        self.play(_TypeNameMatching(src, tgt, key_map={"Square": "Triangle"}))

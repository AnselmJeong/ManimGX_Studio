# Source: manim/animation/transform_matching_parts.py
from manimgx import (
    DOWN,
    RIGHT,
    Circle,
    Scene,
    Square,
    Star,
    TransformMatchingAbstractBase,
    Triangle,
    VGroup,
)


class CustomTransformMatching(TransformMatchingAbstractBase):
    @staticmethod
    def get_mobject_parts(mobject):
        return list(mobject.submobjects) or [mobject]

    @staticmethod
    def get_mobject_key(mobject):
        return id(mobject)


class TransformMatchingAbstractBaseExample(Scene):
    def construct(self):
        a = VGroup(Square(), Circle()).arrange(RIGHT)
        b = VGroup(Triangle(), Star()).arrange(RIGHT).shift(2 * DOWN)
        self.add(a)
        self.play(CustomTransformMatching(a, b, fade_transform_mismatches=True))

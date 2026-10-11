# Source: manim/animation/animation.py
import manimgx as m


class MySquare(m.Square):
    @m.override_animation(m.FadeIn)
    def _fade_in_override(self, **kwargs):
        return m.Create(self, **kwargs)


class OverrideAnimationExample(m.Scene):
    def construct(self):
        self.play(m.FadeIn(MySquare()))

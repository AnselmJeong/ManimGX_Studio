# Source: manim/animation/fading.py
import manimgx as m


class FadeInExample(m.Scene):
    def construct(self):
        dot = m.Dot(m.UP * 2 + m.LEFT)
        self.add(dot)
        tex = m.Tex(
            "FadeIn with ", "shift ", r" or target\_position", " and scale"
        ).scale(1)
        animations = [
            m.FadeIn(tex[0]),
            m.FadeIn(tex[1], shift=m.DOWN),
            m.FadeIn(tex[2], target_position=dot),
            m.FadeIn(tex[3], scale=1.5),
        ]
        self.play(m.AnimationGroup(*animations, lag_ratio=0.5))

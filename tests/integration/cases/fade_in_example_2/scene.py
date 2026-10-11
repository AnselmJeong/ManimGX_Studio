# Source: manim/animation/fading.py
import manimgx as m


class FadeInExample(m.Scene):
    def construct(self):
        dot = m.Dot(m.UP * 2 + m.LEFT)
        self.add(dot)
        tex = m.Tex(
            "FadeOut with ", "shift ", r" or target\_position", " and scale"
        ).scale(1)
        animations = [
            m.FadeOut(tex[0]),
            m.FadeOut(tex[1], shift=m.DOWN),
            m.FadeOut(tex[2], target_position=dot),
            m.FadeOut(tex[3], scale=0.5),
        ]
        self.play(m.AnimationGroup(*animations, lag_ratio=0.5))

# Source: manim/mobject/logo.py
import manimgx as m


class ExpandDirections(m.Scene):
    def construct(self):
        banners = [m.ManimBanner().scale(0.5).shift(m.UP * x) for x in [-2, 0, 2]]
        self.play(
            banners[0].expand(direction="right"),
            banners[1].expand(direction="center"),
            banners[2].expand(direction="left"),
        )

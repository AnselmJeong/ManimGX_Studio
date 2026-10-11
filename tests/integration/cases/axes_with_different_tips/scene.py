# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class AxesWithDifferentTips(m.Scene):
    def construct(self):
        ax = m.Axes(axis_config={"tip_shape": m.StealthTip})
        self.add(ax)
        self.wait()

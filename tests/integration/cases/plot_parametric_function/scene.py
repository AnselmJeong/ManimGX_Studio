# Source: manim/mobject/graphing/functions.py
import numpy as np

import manimgx as m


class PlotParametricFunction(m.Scene):
    def func(self, t):
        return (np.sin(2 * t), np.sin(3 * t), 0)

    def construct(self):
        func = m.ParametricFunction(
            self.func,
            t_range=(0, m.TAU),
            fill_opacity=0,
        ).set_color(m.RED)
        self.add(func.scale(3))
        self.wait()

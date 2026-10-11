# Source: manim/mobject/graphing/functions.py
import numpy as np

import manimgx as m


class ExampleFunctionGraph(m.Scene):
    def construct(self):
        cos_func = m.FunctionGraph(
            lambda t: np.cos(t) + 0.5 * np.cos(7 * t) + (1 / 7) * np.cos(14 * t),
            color=m.RED,
        )

        sin_func_1 = m.FunctionGraph(
            lambda t: np.sin(t) + 0.5 * np.sin(7 * t) + (1 / 7) * np.sin(14 * t),
            color=m.BLUE,
        )

        sin_func_2 = m.FunctionGraph(
            lambda t: np.sin(t) + 0.5 * np.sin(7 * t) + (1 / 7) * np.sin(14 * t),
            x_range=[-4, 4],
            color=m.GREEN,
        ).move_to([0, 1, 0])

        self.add(cos_func, sin_func_1, sin_func_2)
        self.wait()

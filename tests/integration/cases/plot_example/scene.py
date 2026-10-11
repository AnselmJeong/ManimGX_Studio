# Source: manim/mobject/graphing/coordinate_systems.py
import numpy as np

import manimgx as m


class PlotExample(m.Scene):
    def construct(self):
        # construct the axes
        ax_1 = m.Axes(
            x_range=[0.001, 6],
            y_range=[-8, 2],
            x_length=5,
            y_length=3,
            tips=False,
        )
        ax_2 = ax_1.copy()
        ax_3 = ax_1.copy()

        # position the axes
        ax_1.to_corner(m.UL)
        ax_2.to_corner(m.UR)
        ax_3.to_edge(m.DOWN)
        axes = m.VGroup(ax_1, ax_2, ax_3)

        # create the logarithmic curves
        def log_func(x):
            return np.log(x)

        # a curve without adjustments; poor interpolation.
        curve_1 = ax_1.plot(log_func, color=m.PURE_RED)

        # disabling interpolation makes the graph look choppy as not enough
        # inputs are available
        curve_2 = ax_2.plot(log_func, use_smoothing=False, color=m.ORANGE)

        # taking more inputs of the curve by specifying a step for the
        # x_range yields expected results, but increases rendering time.
        curve_3 = ax_3.plot(log_func, x_range=(0.001, 6, 0.001), color=m.PURE_GREEN)

        curves = m.VGroup(curve_1, curve_2, curve_3)

        self.add(axes, curves)
        self.wait()

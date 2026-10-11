# Source: manim/mobject/graphing/coordinate_systems.py
import numpy as np

import manimgx as m


class ParametricCurveExample(m.Scene):
    def construct(self):
        ax = m.Axes()
        cardioid = m.ParametricFunction(
            lambda t: ax.coords_to_point(
                np.exp(1) * np.cos(t) * (1 - np.cos(t)),
                np.exp(1) * np.sin(t) * (1 - np.cos(t)),
            ),
            t_range=[0, 2 * m.PI],
            color="#0FF1CE",
        )
        self.add(ax, cardioid)

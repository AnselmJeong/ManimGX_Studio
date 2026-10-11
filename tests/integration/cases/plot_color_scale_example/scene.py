# Source: user regression for Axes.plot color scales
import numpy as np

import manimgx as m


class PlotColorScaleExample(m.Scene):
    def construct(self):
        base_axes = m.Axes(
            x_range=[0.001, 6],
            y_range=[-8, 2],
            x_length=5,
            y_length=3,
            tips=False,
        )
        ax_left = base_axes.copy().to_corner(m.UL)
        ax_right = base_axes.copy().to_corner(m.UR)
        ax_bottom = base_axes.copy().to_edge(m.DOWN)
        axes = m.VGroup(ax_left, ax_right, ax_bottom)

        repeated_stop_scale = [(m.RED, 0), (m.YELLOW, 0)]
        extended_stop_scale = [
            (m.RED, -1),
            (m.YELLOW, 0),
            (m.BLUE, 0.5),
            (m.GREEN, 1.2),
        ]

        def log_func(x):
            return np.log(x)

        gradient_curve = ax_left.plot(
            log_func,
            color=[m.PURE_RED, m.PURE_YELLOW],
        )
        repeated_stop_curve = ax_right.plot(
            log_func,
            x_range=(0.001, 6, 0.001),
            use_smoothing=True,
            colorscale=repeated_stop_scale,
        )
        extended_stop_curve = ax_bottom.plot(
            log_func,
            x_range=(0.001, 6, 0.001),
            colorscale=extended_stop_scale,
        )
        curves = m.VGroup(gradient_curve, repeated_stop_curve, extended_stop_curve)

        self.add(axes, curves)
        self.wait()

# Source: manim/animation/updaters/mobject_update_utils.py
import numpy as np

import manimgx as m


class TangentAnimation(m.Scene):
    def construct(self):
        ax = m.Axes()
        sine = ax.plot(np.sin, color=m.RED)
        alpha = m.ValueTracker(0)
        point = m.always_redraw(
            lambda: m.Dot(sine.point_from_proportion(alpha.get_value()), color=m.BLUE)
        )
        tangent = m.always_redraw(
            lambda: m.TangentLine(
                sine, alpha=alpha.get_value(), color=m.YELLOW, length=4
            )
        )
        self.add(ax, sine, point, tangent)
        self.play(alpha.animate.set_value(1), rate_func=m.linear, run_time=2)

# Regression: a complete Printery scene rendered under Manim CE 0.20.1 but
# failed under manimgx when it revealed a ParametricFunction by subcurve.
import numpy as np

import manimgx as m


class ParametricFunctionPointwiseBecomePartial(m.Scene):
    def construct(self) -> None:
        curve = m.ParametricFunction(
            lambda t: np.array([t, np.sin(2 * t), 0]),
            t_range=[-2, 2],
            color=m.BLUE,
        )
        partial = curve.copy().set_color(m.YELLOW)
        partial.pointwise_become_partial(curve, 0.2, 0.8)
        curve.set_stroke(opacity=0.25)
        self.add(curve, partial)
        self.wait(0.2)

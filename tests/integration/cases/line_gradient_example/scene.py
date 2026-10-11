# Source: manim/mobject/opengl/opengl_vectorized_mobject.py
import numpy as np

import manimgx as m


class LineGradientExample(m.Scene):
    def construct(self):
        curve = m.ParametricFunction(
            lambda t: [t, np.sin(t), 0],
            t_range=[-m.PI, m.PI, 0.01],
            stroke_width=10,
        )
        new_curve = m.CurvesAsSubmobjects(curve)
        new_curve.set_color_by_gradient(m.BLUE, m.RED)
        self.add(new_curve.shift(m.UP), curve)
        self.wait()

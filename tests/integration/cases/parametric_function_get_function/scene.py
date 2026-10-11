# Source: manim/mobject/graphing/  (Prompt 11 port)
import numpy as np

import manimgx as m


class ParametricFunctionGetFunctionExample(m.Scene):
    def construct(self):
        def f(t):
            return (np.cos(t), np.sin(t), 0)

        pf = m.ParametricFunction(f, t_range=(0, m.TAU))
        # Both getters are real user-facing methods on ParametricFunction.
        assert pf.get_function() is pf.function
        point = pf.get_point_from_function(0.0)
        assert point[0] == 1.0
        self.add(pf)
        self.wait()

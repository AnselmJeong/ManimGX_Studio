# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class FunctionGraphGetFunctionExample(m.Scene):
    def construct(self):
        fg = m.FunctionGraph(lambda x: x * x, x_range=(-2, 2))
        # CE and manimgx store the underlying function differently — CE wraps
        # it into a parametric, manimgx keeps the scalar — but both expose it
        # via the same self.function attribute, which is what get_function returns.
        assert fg.get_function() is fg.function
        pt = fg.get_point_from_function(1.5)
        assert abs(pt[1] - 2.25) < 1e-9
        self.add(fg)
        self.wait()

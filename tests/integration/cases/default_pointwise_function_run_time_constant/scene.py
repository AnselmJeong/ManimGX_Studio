# Source: manim/constants.py
import manimgx as m


class DefaultPointwiseFunctionRunTimeConstant(m.Scene):
    def construct(self):
        radius = m.DEFAULT_POINTWISE_FUNCTION_RUN_TIME / 3
        circle = m.Circle(radius=radius)
        self.add(circle)
        self.wait()

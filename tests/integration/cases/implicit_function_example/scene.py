# Source: manim/mobject/graphing/functions.py
import manimgx as m


class ImplicitFunctionExample(m.Scene):
    def construct(self):
        graph = m.ImplicitFunction(lambda x, y: x * y**2 - x**2 * y - 2, color=m.YELLOW)
        self.add(m.NumberPlane(), graph)
        self.wait()

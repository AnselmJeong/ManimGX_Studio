# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class ImplicitFunctionFuncAlias(m.Scene):
    def construct(self):
        circle = m.ImplicitFunction(func=lambda x, y: x * x + y * y - 1.0)
        self.add(circle)
        self.wait()

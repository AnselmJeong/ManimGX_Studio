# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class LinearBaseExample(m.Scene):
    def construct(self):
        scale = m.LinearBase(scale_factor=2.0)
        assert scale.function(3.0) == 6.0
        assert scale.inverse_function(6.0) == 3.0
        ax = m.Axes(
            x_range=[-2, 2, 1],
            x_length=6,
            x_axis_config={"scaling": scale},
            y_range=[-2, 2, 1],
            y_length=4,
        )
        self.add(ax)
        self.wait()

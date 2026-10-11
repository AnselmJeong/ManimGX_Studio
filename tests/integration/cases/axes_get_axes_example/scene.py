# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class AxesGetAxesExample(m.Scene):
    def construct(self):
        ax = m.Axes(x_range=(-3, 3, 1), y_range=(-2, 2, 1), x_length=6, y_length=4)
        axes_pair = ax.get_axes()
        assert len(list(axes_pair)) == 2
        self.add(ax)
        self.wait()

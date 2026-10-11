# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class ImplicitExample(m.Scene):
    def construct(self):
        ax = m.Axes()
        a = ax.plot_implicit_curve(
            lambda x, y: y * (x - y) ** 2 - 4 * x - 8, color=m.BLUE
        )
        self.add(ax, a)
        self.wait()

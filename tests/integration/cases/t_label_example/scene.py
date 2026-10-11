# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class TLabelExample(m.Scene):
    def construct(self):
        # defines the axes and linear function
        axes = m.Axes(x_range=[-1, 10], y_range=[-1, 10], x_length=9, y_length=6)
        func = axes.plot(lambda x: x, color=m.BLUE)
        # creates the T_label
        t_label = axes.get_T_label(x_val=4, graph=func, label=m.Tex("x-value"))
        self.add(axes, func, t_label)
        self.wait()

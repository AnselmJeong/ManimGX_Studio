# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class GetXAxisLabelExample(m.Scene):
    def construct(self):
        ax = m.Axes(x_range=(0, 8), y_range=(0, 5), x_length=8, y_length=5)
        x_label = ax.get_x_axis_label(
            m.Tex("$x$-values").scale(0.65), edge=m.DOWN, direction=m.DOWN, buff=0.5
        )
        self.add(ax, x_label)
        self.wait()

# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class GetYAxisLabelExample(m.Scene):
    def construct(self):
        ax = m.Axes(x_range=(0, 8), y_range=(0, 5), x_length=8, y_length=5)
        y_label = ax.get_y_axis_label(
            m.Tex("$y$-values").scale(0.65).rotate(90 * m.DEGREES),
            edge=m.LEFT,
            direction=m.LEFT,
            buff=0.3,
        )
        self.add(ax, y_label)
        self.wait()

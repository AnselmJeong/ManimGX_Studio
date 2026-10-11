# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class GetAxisLabelsExample(m.Scene):
    def construct(self):
        ax = m.Axes()
        labels = ax.get_axis_labels(
            m.Tex("x-axis").scale(0.7), m.Text("y-axis").scale(0.45)
        )
        self.add(ax, labels)
        self.wait()

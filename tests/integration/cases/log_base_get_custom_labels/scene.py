# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class LogBaseGetCustomLabelsExample(m.Scene):
    def construct(self):
        ax = m.Axes(
            x_range=[0, 3, 1],
            x_length=8,
            x_axis_config={"scaling": m.LogBase(base=10)},
            y_range=[0, 5, 1],
            y_length=4,
        )
        labels = m.LogBase(base=10).get_custom_labels([1, 2, 3])
        for label in labels:
            self.add(label)
        self.add(ax)
        self.wait()

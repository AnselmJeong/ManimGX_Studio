# Source: manim/mobject/graphing/probability.py
import manimgx as m


class ChangeBarValuesExample(m.Scene):
    def construct(self):
        values = [-10, -8, -6, -4, -2, 0, 2, 4, 6, 8, 10]

        chart = m.BarChart(
            values,
            y_range=[-10, 10, 2],
            y_axis_config={"font_size": 24},
        )
        self.add(chart)

        chart.change_bar_values(list(reversed(values)))
        self.add(chart.get_bar_labels(font_size=24))
        self.wait()

# Source: manim/mobject/graphing/  (Prompt 11 port)
import manimgx as m


class BarChartUpdateColorsExample(m.Scene):
    def construct(self):
        chart = m.BarChart(values=[1, 2, 3, 4], y_range=[0, 5, 1])
        chart.change_bar_values(values=[4, 3, 2, 1], update_colors=False)
        self.add(chart)
        self.wait()

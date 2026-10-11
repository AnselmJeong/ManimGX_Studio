# Source: manim/mobject/graphing/probability.py
import manimgx as m


class GetBarLabelsExample(m.Scene):
    def construct(self):
        chart = m.BarChart(values=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1], y_range=[0, 10, 1])

        c_bar_lbls = chart.get_bar_labels(
            color=m.WHITE, label_constructor=m.MathTex, font_size=36
        )

        self.add(chart, c_bar_lbls)
        self.wait()

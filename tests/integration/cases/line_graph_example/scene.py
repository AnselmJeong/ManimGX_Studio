# Source: manim/mobject/graphing/coordinate_systems.py
# ruff: noqa: C408
import manimgx as m


class LineGraphExample(m.Scene):
    def construct(self):
        plane = m.NumberPlane(
            x_range=(0, 7),
            y_range=(0, 5),
            x_length=7,
            axis_config={"include_numbers": True},
        )
        plane.center()
        line_graph = plane.plot_line_graph(
            x_values=[0, 1.5, 2, 2.8, 4, 6.25],
            y_values=[1, 3, 2.25, 4, 2.5, 1.75],
            line_color=m.GOLD_E,
            vertex_dot_style=dict(stroke_width=3, fill_color=m.PURPLE),
            stroke_width=4,
        )
        self.add(plane, line_graph)
        self.wait()

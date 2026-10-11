# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class GetHorizontalLineExample(m.Scene):
    def construct(self):
        ax = m.Axes().add_coordinates()
        point = ax @ (-4, 1.5)

        dot = m.Dot(point)
        line = ax.get_horizontal_line(point, line_func=m.Line)

        self.add(ax, line, dot)
        self.wait()

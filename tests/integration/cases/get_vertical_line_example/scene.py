# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class GetVerticalLineExample(m.Scene):
    def construct(self):
        ax = m.Axes().add_coordinates()
        point = ax.coords_to_point(-3.5, 2)

        dot = m.Dot(point)
        line = ax.get_vertical_line(point, line_config={"dashed_ratio": 0.85})

        self.add(ax, line, dot)
        self.wait()

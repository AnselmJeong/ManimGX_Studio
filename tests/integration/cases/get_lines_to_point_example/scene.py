# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class GetLinesToPointExample(m.Scene):
    def construct(self):
        ax = m.Axes()
        circ = m.Circle(radius=0.5).move_to([-4, -1.5, 0])

        lines_1 = ax.get_lines_to_point(circ.get_right(), color=m.GREEN_B)
        lines_2 = ax.get_lines_to_point(circ.get_corner(m.DL), color=m.BLUE_B)
        self.add(ax, lines_1, lines_2, circ)
        self.wait()

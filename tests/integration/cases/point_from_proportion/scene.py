# Source: manim/mobject/types/vectorized_mobject.py
import manimgx as m


class PointFromProportion(m.Scene):
    def construct(self):
        line = m.Line(2 * m.DL, 2 * m.UR)
        self.add(line)
        colors = (m.RED, m.BLUE, m.YELLOW)
        proportions = (1 / 4, 1 / 2, 3 / 4)
        for color, proportion in zip(colors, proportions):
            self.add(m.Dot(color=color).move_to(line.point_from_proportion(proportion)))
        self.wait()

# Source: manim/mobject/table.py
import manimgx as m


class MathTableExample(m.Scene):
    def construct(self):
        t0 = m.MathTable(
            [["+", 0, 5, 10], [0, 0, 5, 10], [2, 2, 7, 12], [4, 4, 9, 14]],
            include_outer_lines=True,
        )
        self.add(t0)
        self.wait()

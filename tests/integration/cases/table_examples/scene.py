# Source: manim/mobject/table.py
import numpy as np

import manimgx as m


class TableExamples(m.Scene):
    def construct(self):
        t0 = m.Table(
            [["First", "Second"], ["Third", "Fourth"]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
            top_left_entry=m.Text("TOP"),
        )
        t0.add_highlighted_cell((2, 2), color=m.GREEN)
        x_vals = np.linspace(-2, 2, 5)
        y_vals = np.exp(x_vals)
        t1 = m.DecimalTable(
            [x_vals, y_vals],
            row_labels=[m.MathTex("x"), m.MathTex("f(x)")],
            include_outer_lines=True,
        )
        t1.add(t1.get_cell((2, 2), color=m.RED))
        t2 = m.MathTable(
            [["+", 0, 5, 10], [0, 0, 5, 10], [2, 2, 7, 12], [4, 4, 9, 14]],
            include_outer_lines=True,
        )
        t2.get_horizontal_lines()[:3].set_color(m.BLUE)
        t2.get_vertical_lines()[:3].set_color(m.BLUE)
        t2.get_horizontal_lines()[:3].set_z_index(1)
        cross = m.VGroup(
            m.Line(m.UP + m.LEFT, m.DOWN + m.RIGHT),
            m.Line(m.UP + m.RIGHT, m.DOWN + m.LEFT),
        )
        a = m.Circle().set_color(m.RED).scale(0.5)
        b = cross.set_color(m.BLUE).scale(0.5)
        t3 = m.MobjectTable(
            [
                [a.copy(), b.copy(), a.copy()],
                [b.copy(), a.copy(), a.copy()],
                [a.copy(), b.copy(), b.copy()],
            ]
        )
        t3.add(m.Line(t3.get_corner(m.DL), t3.get_corner(m.UR)).set_color(m.RED))
        vals = np.arange(1, 21).reshape(5, 4)
        t4 = m.IntegerTable(vals, include_outer_lines=True)
        g1 = m.Group(t0, t1).scale(0.5).arrange(buff=1).to_edge(m.UP, buff=1)
        g2 = m.Group(t2, t3, t4).scale(0.5).arrange(buff=1).to_edge(m.DOWN, buff=1)
        self.add(g1, g2)
        self.wait()

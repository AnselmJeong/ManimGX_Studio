# Source: manim/mobject/table.py
import manimgx as m


class TableExamples(m.Scene):
    def construct(self):
        t0 = m.Table([["This", "is a"], ["simple", "Table in \\n Manim."]])
        t1 = m.Table(
            [["This", "is a"], ["simple", "Table."]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
        )
        t1.add_highlighted_cell((2, 2), color=m.YELLOW)
        t2 = m.Table(
            [["This", "is a"], ["simple", "Table."]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
            top_left_entry=m.Star().scale(0.3),
            include_outer_lines=True,
            arrange_in_grid_config={"cell_alignment": m.RIGHT},
        )
        t2.add(t2.get_cell((2, 2), color=m.RED))
        t3 = m.Table(
            [["This", "is a"], ["simple", "Table."]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
            top_left_entry=m.Star().scale(0.3),
            include_outer_lines=True,
            line_config={"stroke_width": 1, "color": m.YELLOW},
        )
        t3.remove(*t3.get_vertical_lines())
        g = m.Group(t0, t1, t2, t3).scale(0.7).arrange_in_grid(buff=1)
        self.add(g)
        self.wait()

# Source: manim/mobject/table.py
import manimgx as m


class GetCellExample(m.Scene):
    def construct(self):
        table = m.Table(
            [["First", "Second"], ["Third", "Fourth"]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
        )
        cell = table.get_cell((2, 2), color=m.RED)
        self.add(table, cell)
        self.wait()

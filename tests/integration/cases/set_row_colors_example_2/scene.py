# Source: manim/mobject/table.py
import manimgx as m


class SetRowColorsExample(m.Scene):
    def construct(self):
        table = m.Table(
            [["First", "Second"], ["Third", "Fourth"]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
        ).set_row_colors([m.RED, m.BLUE], m.GREEN)
        self.add(table)
        self.wait()

# Source: manim/mobject/table.py
import manimgx as m


class GetVerticalLinesExample(m.Scene):
    def construct(self):
        table = m.Table(
            [["First", "Second"], ["Third", "Fourth"]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
        )
        table.get_vertical_lines()[0].set_color(m.RED)
        self.add(table)
        self.wait()

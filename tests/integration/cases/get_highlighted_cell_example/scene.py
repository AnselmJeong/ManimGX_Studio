# Source: manim/mobject/table.py
import manimgx as m


class GetHighlightedCellExample(m.Scene):
    def construct(self):
        table = m.Table(
            [["First", "Second"], ["Third", "Fourth"]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
        )
        highlight = table.get_highlighted_cell((2, 2), color=m.GREEN)
        table.add_to_back(highlight)
        self.add(table)
        self.wait()

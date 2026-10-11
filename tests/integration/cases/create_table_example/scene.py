# Source: manim/mobject/table.py
import manimgx as m


class CreateTableExample(m.Scene):
    def construct(self):
        table = m.Table(
            [["First", "Second"], ["Third", "Fourth"]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
            include_outer_lines=True,
        )
        self.play(table.create())
        self.wait()

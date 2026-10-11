# Source: manim/mobject/table.py
import manimgx as m


class GetEntriesWithoutLabelsExample(m.Scene):
    def construct(self):
        table = m.Table(
            [["First", "Second"], ["Third", "Fourth"]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
        )
        ent = table.get_entries_without_labels()
        colors = [m.BLUE, m.GREEN, m.YELLOW, m.RED]
        for k in range(len(colors)):
            ent[k].set_color(colors[k])
        table.get_entries_without_labels((2, 2)).rotate(m.PI)
        self.add(table)
        self.wait()

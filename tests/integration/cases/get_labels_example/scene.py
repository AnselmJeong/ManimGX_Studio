# Source: manim/mobject/table.py
import manimgx as m


class GetLabelsExample(m.Scene):
    def construct(self):
        table = m.Table(
            [["First", "Second"], ["Third", "Fourth"]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
        )
        lab = table.get_labels()
        colors = [m.BLUE, m.GREEN, m.YELLOW, m.RED]
        for k in range(len(colors)):
            lab[k].set_color(colors[k])
        self.add(table)
        self.wait()

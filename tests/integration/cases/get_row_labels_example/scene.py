# Source: manim/mobject/table.py
import random

import manimgx as m

random.seed(0)


class GetRowLabelsExample(m.Scene):
    def construct(self):
        table = m.Table(
            [["First", "Second"], ["Third", "Fourth"]],
            row_labels=[m.Text("R1"), m.Text("R2")],
            col_labels=[m.Text("C1"), m.Text("C2")],
        )
        lab = table.get_row_labels()
        for item in lab:
            item.set_color(m.random_bright_color())
        self.add(table)
        self.wait()

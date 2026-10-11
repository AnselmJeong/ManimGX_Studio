---
title: "Matrices and tables"
description: "Entries in rows and columns: matrices between brackets, tables between lines, with entries of numbers, math, text or any mobject."
---

# Matrices and tables

```python fold title="The film's code"
import manimgx as m


class MatricesAndTablesHero(m.Scene):
    def construct(self) -> None:
        matrix = m.Matrix([[2, 0], [1, 3]])
        matrix.set_column_colors(m.YELLOW, m.BLUE)
        table = m.Table(
            [["1", "2"], ["4", "8"]],
            row_labels=[m.Text("x"), m.Text("2ˣ")],
            col_labels=[m.Text("a"), m.Text("b")],
        ).scale(0.7)
        m.VGroup(matrix, table).arrange(buff=1.5)
        self.play(m.Write(matrix))
        self.play(table.create())
        self.wait()
```

A matrix and a table hold entries in rows and columns: a matrix between brackets, a table
between lines, with labels for its rows and columns if you give them. Give the entries as
values, and each kind of matrix or table makes their mobjects: numbers, integers, math,
text, or the mobjects themselves. Each row, each column and each entry is a mobject, to
color and animate.

::: manimgx.Matrix
    options:
      heading_level: 2
      inherited_members: [entry, entry_config, cells, get_rows, get_columns, set_row_colors, set_column_colors]

::: manimgx.DecimalMatrix
    options:
      heading_level: 3

::: manimgx.IntegerMatrix
    options:
      heading_level: 3

::: manimgx.MobjectMatrix
    options:
      heading_level: 3

::: manimgx.Table
    options:
      heading_level: 2
      inherited_members: [entry, entry_config, cells, get_rows, get_columns, set_row_colors, set_column_colors]

::: manimgx.DecimalTable
    options:
      heading_level: 3

::: manimgx.IntegerTable
    options:
      heading_level: 3

::: manimgx.MathTable
    options:
      heading_level: 3

::: manimgx.MobjectTable
    options:
      heading_level: 3

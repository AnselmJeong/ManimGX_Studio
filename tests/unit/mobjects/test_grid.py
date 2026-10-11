"""A matrix and a table lay their entries out on a grid.

- A matrix places its cells `h_buff` and `v_buff` apart, by the corner it aligns them on, and
  its brackets outside them.
- A table's lines enclose its entries and bisect the gaps between rows and columns, in drawing
  order, styled as asked; a cell's rectangle spans its row's height and its column's width,
  with half a gap on each side, labels and an empty top-left corner included, however the
  table is moved and scaled.
"""

from itertools import pairwise

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

import manimgx as m
from manimgx.typing import Vector3D


@pytest.mark.parametrize(
    ("row_labels", "col_labels", "corner"),
    [
        (False, False, None),
        (True, False, None),
        (False, True, None),
        (True, True, None),
        (True, True, "empty"),
        (True, True, "visible"),
    ],
)
def test_table_positions_retain_cell_identity_including_empty_entries(
    row_labels: bool, col_labels: bool, corner: str | None
) -> None:
    data = [[m.VMobject(), m.Square()], [m.Circle(), m.VMobject()]]
    top_left = m.VMobject() if corner == "empty" else m.Square() if corner else None
    row_names = [m.Circle(), m.Circle()] if row_labels else []
    column_names = [m.Square(), m.Square()] if col_labels else []
    table = m.MobjectTable(
        data,
        row_labels=row_names,
        col_labels=column_names,
        top_left_entry=top_left,
    )
    expected = ([top_left] if top_left is not None else []) + column_names
    for r, row in enumerate(data):
        if row_labels:
            expected.append(row_names[r])
        expected.extend(row)
    assert list(table.get_entries()) == expected
    assert list(table.get_entries_without_labels()) == [
        entry for row in data for entry in row
    ]
    for r, row in enumerate(data, 1):
        for c, entry in enumerate(row, 1):
            assert table.get_entries_without_labels((r, c)) is entry
            assert table.get_entries((r + col_labels, c + row_labels)) is entry
    for r, label in enumerate(row_names, 1):
        assert table.get_entries((r + col_labels, 1)) is label
    for c, label in enumerate(column_names, 1):
        assert table.get_entries((1, c + row_labels)) is label
    if row_labels and col_labels:
        actual_corner = table.get_entries((1, 1))
        if top_left is not None:
            assert actual_corner is top_left
        else:
            assert actual_corner not in expected
            assert actual_corner.get_all_points().size == 0


def test_highlighting_an_empty_label_corner_does_not_change_a_data_entry() -> None:
    entry = m.Square()
    table = m.MobjectTable([[entry]], row_labels=[m.Circle()], col_labels=[m.Circle()])
    table.add_highlighted_cell((1, 1))
    corner = table.cells[0][0]
    assert entry.background_rectangle is None
    assert corner.background_rectangle is not None
    assert corner.background_rectangle in table.submobjects
    np.testing.assert_allclose(
        corner.background_rectangle.get_center(), table.get_cell((1, 1)).get_center()
    )


@pytest.mark.parametrize("corner", [m.DR, m.UL, m.ORIGIN])
@pytest.mark.parametrize("stretch", [True, False])
def test_matrix_cells_keep_constructor_grid_spacing(
    corner: Vector3D, stretch: bool
) -> None:
    cells = [
        [
            m.Rectangle(width=0.2 + column / 5, height=0.3 + row / 5)
            for column in range(3)
        ]
        for row in range(2)
    ]
    matrix = m.MobjectMatrix(
        cells,
        h_buff=1.7,
        v_buff=0.9,
        element_alignment_corner=corner,
        stretch_brackets=stretch,
    )
    anchor = cells[0][0].get_critical_point(corner)
    for row, entries in enumerate(cells):
        for column, entry in enumerate(entries):
            np.testing.assert_allclose(
                entry.get_critical_point(corner) - anchor,
                column * 1.7 * m.RIGHT + row * 0.9 * m.DOWN,
                atol=1e-12,
            )
    assert list(matrix.get_entries()) == [cell for row in cells for cell in row]
    left, right = matrix.get_brackets()
    assert left.get_right()[0] < matrix.get_entries().get_left()[0]
    assert right.get_left()[0] > matrix.get_entries().get_right()[0]


@given(
    rows=st.integers(1, 4),
    columns=st.integers(1, 4),
    outer=st.booleans(),
    inner=st.booleans(),
    labels=st.booleans(),
    corner=st.booleans(),
    h_buff=st.floats(0.1, 2),
    v_buff=st.floats(0.1, 2),
)
def test_lines_enclose_and_separate_rows_and_columns(
    rows: int,
    columns: int,
    outer: bool,
    inner: bool,
    labels: bool,
    corner: bool,
    h_buff: float,
    v_buff: float,
) -> None:
    table = m.MobjectTable(
        [
            [m.Rectangle(width=0.2 + c / 4, height=0.3 + r / 4) for c in range(columns)]
            for r in range(rows)
        ],
        row_labels=[m.Square(0.2) for _ in range(rows)] if labels else None,
        col_labels=[m.Square(0.2) for _ in range(columns)] if labels else None,
        top_left_entry=m.Square(0.2) if corner and labels else None,
        h_buff=h_buff,
        v_buff=v_buff,
        include_outer_lines=outer,
        include_inner_lines=inner,
        line_config={"color": m.RED, "stroke_width": 2},
    )
    row_groups, column_groups = table.get_rows(), table.get_columns()
    left = table.elements.get_left()[0] - h_buff / 2
    right = table.elements.get_right()[0] + h_buff / 2
    top = row_groups.get_top()[1] + v_buff / 2
    bottom = row_groups.get_bottom()[1] - v_buff / 2
    expected_horizontal = []
    expected_vertical = []
    if outer:
        expected_horizontal.extend(
            (([left, top, 0], [right, top, 0]), ([left, bottom, 0], [right, bottom, 0]))
        )
        expected_vertical.extend(
            (([left, top, 0], [left, bottom, 0]), ([right, top, 0], [right, bottom, 0]))
        )
    if inner:
        for above, below in pairwise(row_groups):
            y = (above.get_bottom()[1] + below.get_top()[1]) / 2
            expected_horizontal.append(([left, y, 0], [right, y, 0]))
        for before, after in pairwise(column_groups):
            x = (before.get_right()[0] + after.get_left()[0]) / 2
            expected_vertical.append(([x, bottom, 0], [x, top, 0]))
    for lines, expected in (
        (table.horizontal_lines, expected_horizontal),
        (table.vertical_lines, expected_vertical),
    ):
        assert len(lines) == len(expected)
        for line, ends in zip(lines, expected, strict=True):
            np.testing.assert_allclose(line.get_start_and_end(), ends, atol=1e-12)
            assert line.get_stroke_color() == m.RED
            assert line.get_stroke_width() == 2
            assert line in table.submobjects
    table.scale(1.7).shift(m.UR)
    for r, row in enumerate(table.get_rows(), 1):
        for c, column in enumerate(table.get_columns(), 1):
            cell = table.get_cell((r, c))
            np.testing.assert_allclose(
                [
                    cell.get_left()[0],
                    cell.get_right()[0],
                    cell.get_bottom()[1],
                    cell.get_top()[1],
                ],
                [
                    column.get_left()[0] - h_buff / 2,
                    column.get_right()[0] + h_buff / 2,
                    row.get_bottom()[1] - v_buff / 2,
                    row.get_top()[1] + v_buff / 2,
                ],
                atol=1e-12,
            )

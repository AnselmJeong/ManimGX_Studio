"""Code sets its glyphs in rows on a monospace column grid: a tab advances to the next tab stop,
an empty line is an empty row, and the line numbers end on one right edge."""

import numpy as np
import pytest

import manimgx as m


@pytest.mark.parametrize("font", [None, "Monospace"])
def test_default_code_font_is_the_bundled_monospace(font: str | None) -> None:
    listing = "from manim import Scene\n\nclass Example(Scene):\n    pass"
    default = m.Code(
        code_string=listing,
        paragraph_config={} if font is None else {"font": font},
    )
    bundled = m.Code(code_string=listing, paragraph_config={"font": "DejaVu Sans Mono"})
    # An installed system monospace must not change outlines, advances or line numbers.
    np.testing.assert_array_equal(default.get_all_points(), bundled.get_all_points())


@pytest.mark.parametrize("tab_width", [2, 4])
@pytest.mark.parametrize("font_size", [12, 36])
def test_code_rows_partition_glyphs_on_the_column_grid(
    tab_width: int, font_size: float
) -> None:
    code = m.Code(
        code_string="HH\n H\n\tH\n\nHH",
        tab_width=tab_width,
        line_numbers_from=98,
        paragraph_config={"font": "DejaVu Sans Mono", "font_size": font_size},
    )
    rows = code.code_lines
    assert [len(row) for row in rows] == [2, 1, 1, 0, 2]
    glyphs = [glyph for row in rows for glyph in row]
    assert len({id(glyph) for glyph in glyphs}) == len(glyphs)
    assert all(not glyph.submobjects for glyph in glyphs)
    origin = rows[0][0].get_x()
    step = rows[0][1].get_x() - origin
    assert rows[1][0].get_x() == pytest.approx(origin + step)
    assert rows[2][0].get_x() == pytest.approx(origin + tab_width * step)
    assert rows[4][0].get_x() == pytest.approx(origin)
    assert rows[4][1].get_x() == pytest.approx(origin + step)
    right = code.line_numbers[0].get_right()[0]
    assert all(row.get_right()[0] == pytest.approx(right) for row in code.line_numbers)

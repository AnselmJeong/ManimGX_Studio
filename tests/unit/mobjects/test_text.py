"""Text is set by Typst as its API says.

- A bulleted list is a Typst list: each item is a part, its bullet first, left of its text;
  `buff` is the space between items, added to the pitch of their baselines.
- Lines lie on a baseline grid: `line_spacing` is the space between them in ems, so their
  baselines are (1 + line_spacing) em apart (-1: CE's default, 0.3).
- A paragraph is one text of its lines, on that grid: its rows partition its glyphs (an empty
  line an empty row), each row at its start or where `alignment` puts it.
- A MathTex is one formula: its strings joined and typeset once, so parting it (into
  arguments, or with `{{…}}`) moves no glyph; a part is the ink its string adds to the
  formula (a fragment such as `\\frac{` adds none), colored apart from the others; an empty
  string is no part.
- A Tex is one text the same way, its strings joined by nothing unless `arg_separator` says:
  `Tex("Fade", "In")` reads "FadeIn", as Manim CE sets it; strings within one formula of a text
  cannot be told apart, and the spaces that isolating leaves alone stay.
- A document Typst cannot set raises Typst's error, once, however it is parted.
- A capital is as tall in every font environment: whatever fonts, in whatever order, given or
  by default, it is set at its calibrated height.
- A typeset mobject made to a width or a height is that size, and its font size is what the
  size makes it; a text's font size is the size asked for; resized, it reads back what it was
  set to. Its rules' widths scale with it unless set; fitted before coloring, a text keeps its
  ligatures' shapes.
- A title's color is its underline's too.
- `opacity` is every part's fill and stroke opacity, where `fill_opacity` or
  `stroke_opacity` doesn't give one, in each of Typst's front ends.

Baselines are read off capitals "H", whose ink sits on the baseline.
"""

from pathlib import Path
from typing import Literal

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

import manimgx as m
from manimgx.drawing import typesetting as tc


def _pitch(first: m.Mobject, second: m.Mobject) -> float:
    """How far below the first capital's baseline the second's is."""
    return first.get_bottom()[1] - second.get_bottom()[1]


def test_a_list_item_is_a_part_with_its_bullet_first() -> None:
    items = m.BulletedList("H", "H", "H")
    assert [len(part) for part in items] == [2, 2, 2]
    for bullet, letter in items:
        assert bullet.get_right()[0] < letter.get_left()[0]
        assert letter.get_bottom()[1] < bullet.get_y() < letter.get_top()[1]


@pytest.mark.parametrize("buff", [0.2, 0.5, 1.5])
def test_buff_is_the_space_added_between_items(buff: float) -> None:
    tight = m.BulletedList("H", "H", buff=0)
    spaced = m.BulletedList("H", "H", buff=buff)
    gap = _pitch(spaced[0][1], spaced[1][1]) - _pitch(tight[0][1], tight[1][1])
    assert gap == pytest.approx(buff, abs=1e-6)


@pytest.mark.parametrize("line_spacing", [-1, 0.5, 1, 4])
def test_line_spacing_is_the_space_between_lines_in_ems(line_spacing: float) -> None:
    solid = m.Text("H\nH", line_spacing=0)
    spaced = m.Text("H\nH", line_spacing=line_spacing)
    gap = 0.3 if line_spacing == -1 else line_spacing
    assert _pitch(*spaced) / _pitch(*solid) == pytest.approx(1 + gap)


@pytest.mark.parametrize("alignment", [None, "left", "center", "right"])
def test_a_paragraph_is_one_text_its_lines_aligned(
    alignment: Literal["left", "center", "right"] | None,
) -> None:
    lines = m.Paragraph("H", "HHH", alignment=alignment, line_spacing=1)
    assert [len(line) for line in lines] == [1, 3]
    assert _pitch(lines[0][0], lines[1][0]) == pytest.approx(
        _pitch(*m.Text("H\nH", line_spacing=1))
    )
    side = {"center": m.ORIGIN, "right": m.RIGHT}.get(alignment or "left", m.LEFT)
    first, second = (line.get_critical_point(side)[0] for line in lines)
    assert first == pytest.approx(second)
    # its rows partition its glyphs: an empty line an empty row, a ligature one glyph
    paragraph = m.Paragraph(
        "", "office", "", "ffi שלום", "", alignment=alignment, t2c={"f": m.RED}
    )
    assert len(paragraph) == 5
    assert all(not paragraph[i] for i in (0, 2, 4))
    glyphs = [glyph for row in paragraph for glyph in row]
    assert len({id(glyph) for glyph in glyphs}) == len(glyphs)
    assert {id(glyph) for glyph in glyphs} == {
        id(glyph) for glyph in paragraph.lines_text
    }


@pytest.mark.parametrize("kind", [m.Text, m.MathTex, m.Tex, m.Typst])
def test_opacity_is_each_parts_where_no_other_is_given(
    kind: type[m.Typst] | type[m.Text],
) -> None:
    faint = kind("x", opacity=0.3)
    parts = faint.family_members_with_points()
    assert parts
    for part in parts:
        assert part.get_fill_opacity() == pytest.approx(0.3)
        assert part.get_stroke_opacity() == pytest.approx(0.3)
    filled = kind("x", opacity=0.3, fill_opacity=0.8)
    for part in filled.family_members_with_points():
        assert part.get_fill_opacity() == pytest.approx(0.8)


def test_a_titles_color_is_its_underlines_too() -> None:
    """Title(color=c) is Title().set_color(c): the underline included."""
    given = m.Title("Title", color=m.RED)
    painted = m.Title("Title").set_color(m.RED)
    assert given.underline.get_color() == painted.underline.get_color() == m.RED


def _leaves(mob: m.Mobject) -> list[np.ndarray]:
    return [leaf.points for part in mob for leaf in part]


@pytest.mark.parametrize(
    ("strings", "counts"),
    [
        (("a", "+", "b", "=", "c"), (1, 1, 1, 1, 1)),
        (
            (r"\frac{", "a", "}{", "b", "}"),
            (0, 1, 0, 1, 1),
        ),  # (the bar: the closing brace's)
        ((r"e^{i", r"\pi}"), (3, 0)),  # (a group's ink: its opening string's)
        (("x", "^2"), (1, 1)),
        (("a", "_n", "+", "b", "^{n+1}"), (1, 1, 1, 1, 3)),
        ((r"\sum_{n=0}^{", "N", "}", "x^n"), (1, 1, 3, 2)),
        ((r"\quad", "x"), (0, 1)),
        (
            (
                r"\begin{aligned}",
                r"\dot{x} &= \sigma(y - x)\\",
                r"\dot{y} &= \rho x",
                r"\end{aligned}",
            ),
            (0, 9, 5, 0),
        ),
        ((r"\left[ \mu \frac{", "u", r"}{2} \right]", "+ 1"), (2, 1, 3, 2)),
    ],
)
def test_a_math_tex_is_one_formula_its_strings_draw(
    strings: tuple[str, ...], counts: tuple[int, ...]
) -> None:
    parted = m.MathTex(*strings)
    whole = m.MathTex(parted.tex_string)
    for part, string in zip(parted, strings, strict=True):
        assert isinstance(part, m.MathTexPart)
        assert part.tex_string == string
    assert tuple(len(part) for part in parted) == counts
    mine, theirs = _leaves(parted), _leaves(whole)
    assert len(mine) == len(theirs)
    for a, b in zip(mine, theirs, strict=True):
        np.testing.assert_allclose(a, b, atol=1e-9)
    for part, string in zip(parted, strings, strict=True):
        assert parted.get_part_by_tex(string, substring=False) is part
        if len(part):  # (colored apart from the others)
            part.set_color(m.YELLOW)
            assert all(leaf.get_color() == m.YELLOW for leaf in part)
            others = (leaf for other in parted if other is not part for leaf in other)
            assert all(leaf.get_color() == m.WHITE for leaf in others)
            part.set_color(m.WHITE)


def test_an_empty_string_is_no_part() -> None:
    formula = m.MathTex("", "H", "")
    assert formula.tex_strings == ["H"]
    assert formula.select("p0") is not formula[0]
    assert formula.select("p0")[0] is formula[0][0]


def test_double_braces_set_a_part_apart() -> None:
    """A fraction's bar is the ink of the brace that closes it, as in TeX."""
    eq = m.MathTex(r"{{x^2}} + \frac{ {{b}} }{ {{a}} }")
    parts = [part for part in eq if isinstance(part, m.MathTexPart)]
    assert [part.tex_string for part in parts] == [
        "x^2",
        r"+ \frac{",
        "b",
        "}{",
        "a",
        "}",
    ]
    assert [len(part) for part in eq] == [2, 1, 1, 0, 1, 1]


@pytest.mark.parametrize(
    ("strings", "counts"),
    [
        (("Fade", "In"), (4, 2)),
        (("of", "fice"), (2, 2)),  # one ligature, "ffi": the first string's
        (("x", "+", "y"), (1, 1, 1)),  # "+" read alone would begin an enumeration
        (("Profit ", "+ 10"), (5, 3)),  # "fi" is one glyph
        (("polka ", "dot"), (5, 3)),  # text, not a formula's `\dot`, whole or parted
        (("Area ", r"$\sqrt{x}$"), (4, 3)),  # the radical and its bar are the root's
        ((r"\textbf{", "Bold", "} type"), (0, 4, 4)),
        ((r"\textcolor{", "red}{RED}"), (3, 0)),  # (neither sets alone)
        (("{{Hello}} {{World}}",), (5, 0, 5)),
        (("First apply ", "$A$", " then ", r"$\sqrt{B}$"), (10, 1, 4, 3)),
        (("Concrete", r" $\to$ ", "Abstract graph"), (8, 1, 13)),
    ],
)
def test_a_tex_is_one_text_its_strings_draw(
    strings: tuple[str, ...], counts: tuple[int, ...]
) -> None:
    parted = m.Tex(*strings)
    whole = m.Tex(parted.tex_string)
    assert parted.tex_string == "".join(parted.tex_strings)
    assert tuple(len(part) for part in parted) == counts
    mine, theirs = _leaves(parted), _leaves(whole)
    assert len(mine) == len(theirs)
    for a, b in zip(mine, theirs, strict=True):
        np.testing.assert_array_equal(a, b)


def test_a_separators_glyphs_are_the_string_befores() -> None:
    parted = m.Tex("a", "b", arg_separator=", ")
    assert [len(part) for part in parted] == [2, 1]
    for a, b in zip(_leaves(parted), _leaves(m.Tex("a, b")), strict=True):
        np.testing.assert_array_equal(a, b)


def test_text_keeps_the_spaces_that_isolating_leaves_alone() -> None:
    text = m.Tex("x y", tex_to_color_map={"x": m.RED, "y": m.BLUE})
    assert text.tex_strings == ["x", " ", "y"]
    assert [part.get_color() for part in text if len(part)] == [m.RED, m.BLUE]
    formula = m.MathTex("x y", tex_to_color_map={"x": m.RED, "y": m.BLUE})
    assert formula.tex_strings == ["x", "y"]


@pytest.mark.parametrize("strings", [("$", "x", "$"), ("$a", "+", "b$")])
def test_strings_within_one_formula_of_a_text_cannot_be_told_apart(
    strings: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="cannot tell these parts apart"):
        m.Tex(*strings)


# characters that neither Typst nor LaTeX reads as markup, so a string reads alone as it does
# within a text
_PLAIN = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ,;:()"


@settings(max_examples=max(10, settings().max_examples // 4))
@given(st.lists(st.text(_PLAIN, max_size=6), min_size=1, max_size=4))
def test_parting_a_text_moves_none_of_its_glyphs(strings: list[str]) -> None:
    parted = m.Tex(*strings)
    mine, theirs = _leaves(parted), _leaves(m.Tex(parted.tex_string))
    assert len(mine) == len(theirs)
    for a, b in zip(mine, theirs, strict=True):
        np.testing.assert_array_equal(a, b)
    # each string is the glyphs it draws alone, unless a glyph (a ligature) spans two
    alone = [len(m.Tex(s)[0]) for s in parted.tex_strings]
    assume(sum(alone) == len(theirs))
    assert [len(part) for part in parted] == alone


@pytest.mark.parametrize("kind", [m.Tex, m.MathTex])
@pytest.mark.parametrize("strings", [("H",), ("H", "I")])
def test_a_document_typst_cannot_set_raises_its_error_once(
    kind: type[m.MathTex], strings: tuple[str, ...]
) -> None:
    with pytest.raises(tc.TypstError) as raised:
        kind(*strings, typst_preamble="#missing_preflight_function()\n")
    assert str(raised.value).count("unknown variable: missing_preflight_function") == 1


@pytest.mark.cold
def test_a_capital_is_as_tall_in_every_font_environment(
    two_fonts: tuple[str, str],
) -> None:
    first, second = two_fonts
    capitals: list[m.Text] = []
    for paths in ([first, second], [second, first], [first], [second]):
        as_strings: list[str | Path] = list(paths)
        as_paths: list[str | Path] = [Path(path) for path in paths]
        for fonts in (as_strings, as_paths):
            capitals.append(m.Text("H", font="Noto Sans", font_paths=fonts))
    try:
        for default in (first, second):
            m.Typst.set_default(font_paths=[default])
            capitals.append(m.Text("H", font="Noto Sans"))  # (by default)
            capitals.append(m.Text("HH", font="Noto Sans"))  # (another text)
            capitals.append(m.Text("H", font="Noto Sans", font_paths=None))
            capitals.append(m.Text("H", font="Noto Sans", font_paths=[]))
    finally:
        m.Typst.set_default()
    assert [capital.height for capital in capitals] == pytest.approx(
        [0.44895] * len(capitals)
    )
    assert [capital.font_size for capital in capitals] == pytest.approx(
        [48] * len(capitals)
    )
    # (the fonts differ, by the widths calibration leaves: the law has something to see)
    one, other = (m.Text("HH", font="Noto Sans", font_paths=[p]) for p in two_fonts)
    assert one.width != pytest.approx(other.width)


KINDS = [m.Typst, m.MathTex, m.Text, m.BulletedList]


@settings(max_examples=40)
@given(
    kind=st.sampled_from(KINDS),
    size=st.floats(12, 96),
    should_center=st.booleans(),
    width=st.none() | st.floats(0.5, 5),
    height=st.none() | st.floats(0.3, 3),
)
def test_a_typeset_mobject_made_to_a_size_is_that_size(
    kind: type[m.Typst],
    size: float,
    should_center: bool,
    width: float | None,
    height: float | None,
) -> None:
    reference = kind("Hi", font_size=48)
    made = kind("Hi", font_size=size)  # (a text's font size: the size asked for)
    assert made.font_size == pytest.approx(size)
    assert made.height == pytest.approx(reference.height * size / 48)
    assume(width is not None or height is not None)
    text = kind(
        "Hi", font_size=size, should_center=should_center, width=width, height=height
    )
    if width is not None:  # (a width, given, wins)
        assert text.width == pytest.approx(width)
    else:
        assert text.height == pytest.approx(height)
    assert text.font_size == pytest.approx(48 * text.height / reference.height)
    previous = text.font_size
    text.scale(1.7)
    assert text.font_size == pytest.approx(1.7 * previous)
    text.font_size = 36
    assert text.font_size == pytest.approx(36)
    text.width = 2.2
    assert text.width == pytest.approx(2.2)
    assert text.font_size == pytest.approx(48 * text.height / reference.height)
    text.height = 0.8
    assert text.height == pytest.approx(0.8)
    assert text.font_size == pytest.approx(48 * 0.8 / reference.height)


@pytest.mark.parametrize("fixed_stroke", [None, 3])
@pytest.mark.parametrize(("width", "height"), [(2, None), (None, 1.5), (2, 1.5)])
def test_fitted_typeset_rules_scale_unless_stroke_width_is_explicit(
    fixed_stroke: float | None, width: float | None, height: float | None
) -> None:
    reference = m.Typst("$ frac(a,b) $", stroke_width=fixed_stroke)
    text = m.Typst(
        "$ frac(a,b) $", stroke_width=fixed_stroke, width=width, height=height
    )
    originals = [
        part
        for part in reference.family_members_with_points()
        if part.get_stroke_width() > 0
    ]
    rules = [
        part
        for part in text.family_members_with_points()
        if part.get_stroke_width() > 0
    ]
    assert len(originals) == len(rules) > 0
    scale = text.height / reference.height if fixed_stroke is None else 1
    for before, after in zip(originals, rules, strict=True):
        assert after.get_stroke_width() == pytest.approx(
            before.get_stroke_width() * scale
        )
    widths = [part.get_stroke_width() for part in rules]
    text.font_size = text.font_size * 1.3
    for part, width in zip(rules, widths, strict=True):
        assert part.get_stroke_width() == pytest.approx(
            width * (1.3 if fixed_stroke is None else 1)
        )


def test_fitting_text_before_coloring_ligatures_preserves_their_geometry() -> None:
    expected = m.Text("office", t2c={"f": m.RED}).scale_to_fit_width(2)
    actual = m.Text("office", t2c={"f": m.RED}, width=2)
    before, after = (
        expected.family_members_with_points(),
        actual.family_members_with_points(),
    )
    assert len(before) == len(after)
    for original, fitted in zip(before, after, strict=True):
        np.testing.assert_array_equal(fitted.points, original.points)
        assert fitted.get_color() == original.get_color()

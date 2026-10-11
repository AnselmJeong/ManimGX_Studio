"""Code: a highlighted listing set by Typst's `raw`. Its grammars find the tokens; a theme
colors each scope as the pygments style colors the token there. With a monospaced font and
one glyph per character, column advances are rounded to whole Pango units."""

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import ClassVar, Literal

from typing_extensions import TypedDict

from manimgx.caches import forgets
from manimgx.constants import LEFT, ORIGIN, RIGHT, SCALE_FACTOR_PER_FONT_POINT, UP
from manimgx.drawing.paint import WHITE, ManimColor
from manimgx.drawing.typesetting import typst_string
from manimgx.mobject import Mobject, VGroup, VMobject
from manimgx.mobjects.annotations import FrameOptions, SurroundingRectangle
from manimgx.mobjects.shapes import Dot, Line
from manimgx.mobjects.text import Typst
from manimgx.typing import StrPath

__all__ = ["Code"]

# CE's Text asks Pango for font_size / 4.8 points, set at 96 dpi, and its line spacing / 4.8 in
# Pango's units; CE takes 0.05 scene units for one. Typst sets the code in points that stand for
# Pango's units: a Typst mobject's scene units per point are its font_size / 960.
_PANGO_PER_FONT_SIZE = 1 / 4.8
_UNITS_PER_POINT = 96 / 72
_SCENE_PER_UNIT = 0.05
_POINT = _SCENE_PER_UNIT / SCALE_FACTOR_PER_FONT_POINT
_LINE_SPACING = 0.3  # CE's Text's, for a line_spacing of -1

_PYTHON = frozenset({"python", "py", "python3", "py3"})
_LINE = "line"  # a line's label: "line1" the first
# pygments' Python lexer: these are builtins wherever they stand, parameters too
_PSEUDO_BUILTINS = re.compile(r"(?<![.\w])(?:self|cls)\b")

type CodeStyle = Literal["vim"]


@dataclass(frozen=True, slots=True)
class _Style:
    """A pygments style for Typst: its background, text and line-number colors, and a theme
    coloring each grammar scope as the style colors the token there."""

    background: str
    foreground: str
    line_numbers: str
    builtins: str  # pygments' pseudo-builtins (Python's self and cls)
    theme: Mapping[str, str]  # scope selector: color


_STYLES: dict[CodeStyle, _Style] = {
    "vim": _Style(
        background="#000000",
        foreground="#cccccc",
        line_numbers="#cccccc",  # the style's "inherit": the text's color
        builtins="#cd00cd",
        theme={
            # Comment
            "comment": "#000080",
            # Keyword, Keyword.Constant, Operator.Word
            "keyword": "#cdcd00",
            "storage.modifier": "#cdcd00",
            "constant.language": "#cdcd00",
            "keyword.operator.logical": "#cdcd00",
            "keyword.control.import.as": "#cdcd00",
            # Keyword.Namespace
            "keyword.control.import": "#cd00cd",
            # Operator ("." and "->" among them, but for a module's path)
            "keyword.operator": "#3399cc",
            "punctuation.accessor": "#3399cc",
            "punctuation.separator.annotation.return": "#3399cc",
            "meta.statement.import punctuation.accessor": "#cccccc",
            # Name.Class, Name.Variable.Magic
            "entity.name.class": "#00cdcd",
            "support.variable.magic": "#00cdcd",
            # Name.Builtin, Name.Exception
            "support.function.builtin": "#cd00cd",
            "support.type": "#cd00cd",
            "support.type.exception": "#666699",
            # Name.Decorator: a decorator is plain text, builtin or not
            "meta.annotation support.function.builtin": "#cccccc",
            "meta.annotation support.type": "#cccccc",
            # String: its prefix, escapes, placeholders, a regex's syntax, a docstring, and
            # an f-string's braces, conversion and format
            "string": "#cd0000",
            "string keyword": "#cd0000",
            "string keyword.operator": "#cd0000",
            "string constant": "#cd0000",
            "storage.type.string": "#cd0000",
            "constant.character.escape": "#cd0000",
            "comment.block.documentation": "#cd0000",
            "punctuation.section.interpolation": "#cd0000",
            "storage.modifier.conversion": "#cd0000",
            "constant.other.format-spec": "#cd0000",
            # Number
            "constant.numeric": "#cd00cd",
        },
    ),
}


class CodeText(TypedDict, total=False):
    """The text of a [Code][manimgx.Code] listing: its `paragraph_config`, the text
    keywords that apply to a listing."""

    font: str
    """The font family: "Monospace", the default, is the bundled DejaVu Sans Mono on
    every platform; any other family is one manimgx ships, or else the system's."""
    font_size: float
    """The size of the text: an em is `font_size / 72` scene units (default 24)."""
    line_spacing: float
    """How far apart the lines are, beyond the font size: their baselines are
    `(1 + line_spacing) * font_size / 96` scene units apart (default 0.5; -1 for
    0.3)."""
    disable_ligatures: bool
    """Whether every character is a glyph of its own, with no ligatures (default
    True)."""


def _theme(style: _Style) -> str:
    """The style as a TextMate theme (Typst takes only the scopes' colors from it)."""
    rules = "".join(
        f"<dict><key>scope</key><string>{scope}</string><key>settings</key><dict>"
        f"<key>foreground</key><string>{color}</string></dict></dict>"
        for scope, color in style.theme.items()
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>'
        "<key>settings</key><array><dict><key>settings</key><dict><key>foreground</key>"
        f"<string>{style.foreground}</string></dict></dict>{rules}</array></dict></plist>"
    )


@forgets
@cache
def _advance(face: str) -> float:
    """A character's advance in `face`, in scene units, as Typst sets it: the font's own."""
    first, second = Typst(f"#set text({face})\n00", font_size=_POINT).submobjects
    return second.get_left()[0] - first.get_left()[0]


def _typeset(
    lines: list[str],
    text: CodeText,
    color: str,
    *,
    style: _Style | None = None,
    language: str | None = None,
    suffix: str = "",
) -> list[VGroup]:
    """Each line's glyphs, with fixed baseline spacing and adjusted monospaced columns,
    highlighted in `style` if given; `suffix` closes the first and last lines.
    """
    size = text.get("font_size", 24)
    spacing = text.get("line_spacing", -1)
    em = size * _PANGO_PER_FONT_SIZE * _UNITS_PER_POINT
    pitch = size * (1 + (_LINE_SPACING if spacing == -1 else spacing))
    pitch *= _PANGO_PER_FONT_SIZE
    font = text.get("font", "Monospace")
    family = "DejaVu Sans Mono" if font == "Monospace" else font
    face = f"font: {typst_string(family)}, size: {em}pt"
    ligatures = "false" if text.get("disable_ligatures", True) else "true"
    closing = (
        f"; if it.number in (1, it.count) {{ {typst_string(suffix)} }}"
        if suffix
        else ""
    )
    highlighting = (
        f"lang: {typst_string(language) if language else 'none'},"
        f" theme: {f'bytes({typst_string(_theme(style))})' if style else 'none'}"
    )
    source = (
        f'#set text({face}, fill: rgb("{color}"), ligatures: {ligatures},'
        ' top-edge: "baseline", bottom-edge: "baseline")\n'
        f"#set par(leading: {pitch}pt)\n"
        f"#show raw: set text({face})\n"
        # each line labelled, its glyphs a group of their own
        f"#show raw.line: it => [#box({{ it.body{closing} }})"
        f'#label("{_LINE}" + str(it.number))]\n'
        f"#raw({typst_string(chr(10).join(lines))}, block: true, {highlighting})"
    )
    groups = Typst(source, font_size=_POINT, color=color).labels
    empty = VGroup()
    rows = [
        VGroup(*groups.get(f"{_LINE}{n}", empty).submobjects)
        for n in range(1, len(lines) + 1)
    ]
    # Typst advances a character by the font's own width, Pango by that rounded to a whole
    # unit: each column moves by the difference, times the columns before it. A line whose
    # glyphs are not one a character (a ligature, a cluster) stays as Typst set it.
    advance = _advance(face)
    step = math.floor(advance / _SCENE_PER_UNIT + 0.5) * _SCENE_PER_UNIT
    at: dict[int, list[Mobject]] = {}
    plain = ManimColor(color)
    python = language is not None and language.lower() in _PYTHON
    builtins = style.builtins if style is not None and python else None
    last = len(lines) - 1
    for i, (line, row) in enumerate(zip(lines, rows)):
        closed = line + suffix if i in (0, last) else line
        columns = [c for c, ch in enumerate(closed) if not ch.isspace()]
        if len(columns) != len(row.submobjects):
            continue
        glyph_at = dict(zip(columns, row.submobjects))
        for column, glyph in glyph_at.items():
            at.setdefault(column, []).append(glyph)
        if builtins is None:
            continue
        for match in _PSEUDO_BUILTINS.finditer(line):
            word = VGroup(*(glyph_at[c] for c in range(*match.span())))
            if all(glyph.get_fill_color() == plain for glyph in word):
                word.set_fill(builtins)  # not in a string or a comment
    for column, placed in at.items():
        offset = RIGHT * column * (step - advance)
        for glyph in placed:
            glyph._geometry = glyph._geometry.translated(offset)
    return rows


class Code(VMobject):
    r"""A listing of source code, highlighted: its lines, their numbers, and a rectangle
    or a window behind them.

    The code is highlighted by Typst's grammars, in the colors of `formatter_style`, with
    a monospaced font by default. The parts are
    [background][manimgx.Code.background], [line_numbers][manimgx.Code.line_numbers] (if
    the lines are numbered) and [code_lines][manimgx.Code.code_lines], whose i-th part is
    the i-th line, a group of its glyphs, spaces excluded. Tabs are expanded, and empty
    lines at the start and at the end are dropped.

    Args:
        code_file: A file to read the code from (UTF-8); its extension names the
            language unless `language` does.
        code_string: The code, when there is no `code_file`; one of the two is needed
            (ValueError otherwise).
        language: The language to highlight the code as, by name or file extension
            ("python", "rust", "cpp", "js", …: those Typst's `raw` knows); None, or a
            language it doesn't know, for plain text.
        formatter_style: The colors: "vim", the only style, on a black background.
        tab_width: How many columns apart the tab stops are.
        add_line_numbers: Whether the lines are numbered, on their left.
        line_numbers_from: The first line's number.
        background: "rectangle", or "window": a rectangle with a window's three buttons
            at its top.
        background_config: [Surrounding rectangle
            keywords][manimgx.mobjects.annotations.FrameOptions] for the
            background, over `default_background_config`: a margin of 0.3, round
            corners, a thin white outline, and the style's background color.
        paragraph_config: [Code text
            keywords][manimgx.mobjects.code.CodeText] for the text, over
            `default_paragraph_config`.

    Examples:
        ```python
        import manimgx as m


        class CodeExample(m.Scene):
            def construct(self) -> None:
                python = m.Code(
                    code_string='def greet(name):\n    return f"Hello, {name}!"\n',
                    language="python",
                )
                rust = m.Code(
                    code_string='fn main() {\n    println!("Hello!");\n}\n',
                    language="rust",
                    background="window",
                    add_line_numbers=False,
                )
                self.add(m.VGroup(python, rust).arrange(m.DOWN, buff=0.5).scale(1.4))
        ```
    """

    default_background_config: ClassVar[FrameOptions] = {
        "buff": 0.3,
        "stroke_color": WHITE,
        "corner_radius": 0.2,
        "stroke_width": 1,
        "fill_opacity": 1,
    }  # and the style's background, unless a fill_color is given
    """The background's keywords unless `background_config` changes them; its fill is
    the style's background color unless a `fill_color` is given."""
    default_paragraph_config: ClassVar[CodeText] = {
        "font": "Monospace",
        "font_size": 24,
        "line_spacing": 0.5,
        "disable_ligatures": True,
    }
    """The text's keywords unless `paragraph_config` changes them."""

    def __init__(
        self,
        code_file: StrPath | None = None,
        code_string: str | None = None,
        language: str | None = None,
        formatter_style: CodeStyle = "vim",
        tab_width: int = 4,
        add_line_numbers: bool = True,
        line_numbers_from: int = 1,
        background: Literal["rectangle", "window"] = "rectangle",
        background_config: FrameOptions | None = None,
        paragraph_config: CodeText | None = None,
    ) -> None:
        super().__init__()
        if code_file is not None:
            code_string = Path(code_file).read_text(encoding="utf-8")
            language = language or Path(code_file).suffix.removeprefix(".") or None
        elif code_string is None:
            raise ValueError("Either a code file or a code string must be specified.")
        style = _STYLES[formatter_style]
        text = self.default_paragraph_config | (paragraph_config or {})
        # tabs expanded, empty lines trimmed off
        code = (
            code_string.expandtabs(tab_width).replace("\r\n", "\n").replace("\r", "\n")
        )
        lines = code.strip("\n").split("\n")
        if not any(line.strip() for line in lines):
            lines = [""] * len(lines)

        # CE closes the first and last lines with an ascender, a descender and the first line
        # number, so that a listing's height depends on its lines alone, then takes them away
        suffix = f" pA{line_numbers_from}"
        closing = len(suffix) - 1  # its glyphs: all but the space
        rows = _typeset(
            lines, text, style.foreground, style=style, language=language, suffix=suffix
        )
        self.code_lines = VGroup(*rows).move_to(ORIGIN)
        """The lines, a part: its i-th part is the i-th line, a group of its glyphs."""

        if add_line_numbers:
            numbers = range(line_numbers_from, line_numbers_from + len(lines))
            self.line_numbers = VGroup(
                *_typeset([str(n) for n in numbers], text, style.line_numbers)
            ).move_to(ORIGIN)
            """The line numbers, a part (if the lines are numbered): its i-th part is
            the i-th line's number, lined up on the right."""
            right = self.line_numbers.get_right()[0]
            for row in self.line_numbers.submobjects:
                row.shift(RIGHT * (right - row.get_right()[0]))
            self.line_numbers.next_to(self.code_lines, LEFT)
            first = VGroup(*rows[0].submobjects[-len(str(line_numbers_from)) :])
            self.line_numbers.shift(
                UP * (first.get_y() - self.line_numbers.submobjects[0].get_y())
            )
            self.add(self.line_numbers)

        # what CE keeps of the closings: their height, on the left edge of their glyphs and of
        # the space before each, which CE's Text puts on the glyph before it
        boundary = sorted({0, len(rows) - 1})
        glyphs = [glyph for row in rows for glyph in row.submobjects]
        closings = [g for i in boundary for g in rows[i].submobjects[-closing:]]
        spaces = []
        for i in boundary:
            before = sum(len(row.submobjects) for row in rows[: i + 1]) - closing
            spaces.append(
                glyphs[before - 1] if before else rows[i].submobjects[-closing]
            )
        edge = min(
            [g.get_center()[0] for g in spaces] + [g.get_left()[0] for g in closings]
        )
        extent = Line(
            [edge, min(g.get_bottom()[1] for g in closings), 0],
            [edge, max(g.get_top()[1] for g in closings), 0],
        )
        for i in boundary:
            rows[i].remove(*rows[i].submobjects[-closing:])
        self.add(self.code_lines)

        config = self.default_background_config | (background_config or {})
        if config.get("fill_color") is None:
            config["fill_color"] = style.background
        listing = VGroup(*self.submobjects, extent)
        if background == "rectangle":
            self.background = SurroundingRectangle(listing, **config)
            """The rectangle behind the listing, its first part; a window's buttons are
            its submobjects."""
        elif background == "window":
            buttons = VGroup(
                *(
                    Dot(radius=0.1, stroke_width=0, color=c)
                    for c in ["#ff5f56", "#ffbd2e", "#27c93f"]
                )
            ).arrange(RIGHT, buff=0.1)
            buttons.next_to(listing, UP, buff=0.1).align_to(listing, LEFT).shift(
                LEFT * 0.1
            )
            self.background = SurroundingRectangle(listing, buttons, **config)
            buttons.shift(UP * 0.1 + LEFT * 0.1)
            self.background.add(buttons)
        else:
            raise ValueError(f"Unknown background type: {background}")
        self.add_to_back(self.background)

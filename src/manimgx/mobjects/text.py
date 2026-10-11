"""Typeset mobjects from Typst, literal Unicode, and LaTeX source.

Typst documents as mobjects: every glyph and shape of the layout becomes a part (a glyph its
outline, shared per font and glyph, placed where Typst put it). After CE 0.21 (MIT).

CE's Pango text classes, typeset by Typst: one submobject per non-space glyph, in reading
order, sized so a font-size-48 capital has CE's height.

The text is set literally, as Typst strings. Slant and weight (`t2s`, `t2w`) change the layout,
so they are set as runs; color does not: every glyph knows the characters it draws,
so `gradient`, `t2g` and `t2c` color it by character, and a glyph whose characters differ in
color is cut at its carets. A key is a slice "[a:b]" or each occurrence of a string; a key that
occurs nowhere picks nothing.

CE's LaTeX classes, typeset by Typst: LaTeX converted by mitex, so `MathTex("a", "=", "b")[i]`
is part i. A MathTex's strings are one formula, a Tex's one text: joined, and typeset once.

"""

from __future__ import annotations

from warnings import deprecated

__all__ = [
    "BulletedList",
    "MathTex",
    "MathTexOptions",
    "MathTexPart",
    "MathTypst",
    "Paragraph",
    "SingleStringMathTex",
    "Tex",
    "Text",
    "TextOptions",
    "Title",
    "Typst",
    "TypstGlyph",
    "TypstOptions",
]

import bisect
import re
import unicodedata
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal, Self, Unpack

import numpy as np

from manimgx import _engine
from manimgx.caches import Memo
from manimgx.constants import (
    DEFAULT_FONT_SIZE,
    MED_LARGE_BUFF,
    MED_SMALL_BUFF,
    NORMAL,
    SCALE_FACTOR_PER_FONT_POINT,
    SMALL_BUFF,
)
from manimgx.drawing.geometry import (
    EMPTY,
    Blend,
    Shape,
    _pathops,
    _to_path,
    extent,
    interpolate,
    placed_box,
)
from manimgx.drawing.paint import (
    WHITE,
    Colors,
    Look,
    ManimColor,
    ParsableManimColor,
    Repaint,
    _Look,
    color_gradient,
)
from manimgx.drawing.typesetting import (
    ADVANCE,
    DRAWN,
    FILL,
    GLYPH,
    KEY,
    KIND,
    NODE,
    PLACEMENT,
    STROKE,
    WIDTH,
    Layout,
    TypstError,
    typeset,
    typst_string,
)
from manimgx.mobject import Mobject, Pivot, VGroup, VMobject, _append_path, prototype
from manimgx.typing import Vector3DLike

_HEX: Memo[tuple[float, ...], str] = Memo(1 << 12)


def _ink(rgba: np.ndarray, color: str) -> str:
    """A paint Typst gave: its default ink (black) is `color`."""
    return color if not rgba[:3].any() else _hex(rgba)


def _hex(rgba: np.ndarray) -> str:
    key = tuple(rgba[:3])
    color = _HEX.get(key)
    if color is None:
        r, g, b = (round(c * 255) for c in key)
        color = _HEX.keep(key, f"#{r:02x}{g:02x}{b:02x}")
    return color


class _TypstOptions(_Look, Repaint, total=False):
    """TypstOptions's keys, open, for the keywords that add to them."""

    font_size: float
    """The size of the text: an em is `font_size / 96` scene units, 0.5 at the default,
    48 (a [Text][manimgx.Text] is sized by its capitals instead: 0.449 units tall at
    48)."""
    typst_preamble: str
    """Typst code set before the document: `#set` and `#show` rules, `#let`
    definitions, imports (default "")."""
    font_paths: list[str | Path] | None
    """Directories of font files (.ttf, .otf, .ttc, .otc), searched with their
    subdirectories before the fonts manimgx ships; a path to a file adds nothing
    (default None)."""
    should_center: bool
    """Whether the mobject is centered on the origin (default True)."""
    height: float | None
    """The height to scale the mobject to, in scene units, instead of sizing it by
    `font_size` (default None)."""
    width: float | None
    """The width to scale the mobject to, in scene units, instead of sizing it by
    `font_size`; with a `height` too, the width is set last (default None)."""
    package_path: str | Path | None
    """The directory Typst packages are imported from, which holds them as
    `namespace/name/version` directories: `#import "@preview/name:1.0.0"` reads
    `preview/name/1.0.0` (default None: none but mitex, which manimgx's engine holds).
    Nothing is downloaded."""


class TypstOptions(_TypstOptions, total=False, closed=True):
    """[Typst][manimgx.Typst]'s keywords, for the classes that pass them on: text and
    LaTeX.

    Beyond these, they take the [look keywords][manimgx.drawing.paint.Look], and the
    [paint keywords][manimgx.drawing.paint.Repaint], which paint over the colors the
    typesetting gives the parts.
    """


class TypstGlyph(VMobject):
    """One glyph as Typst set it, a part of a typeset mobject: its outline, placed, and
    which characters of the source it draws.

    `node` is where the glyph's source node starts in the Typst code (-1 if it isn't
    from the code), `drawn` the bytes of that node's text it draws, `key` its outline,
    `x_advance` its width in font units.
    """

    # Immutable float64 bytes, shared by copies; absent for ordinary glyphs.
    _carets: bytes = b""

    node: int
    """Where the source node the glyph came from starts in the Typst code, in bytes. A
    glyph a package's code drew (a radical a package's function sets) came from the
    innermost element of the code around it (its equation); -1 if none is."""
    drawn: tuple[int, int]
    """The bytes of that node's text the glyph's cluster draws, from and to: of a string
    literal, the bytes of its value; -1, -1 if the node is an element around it."""
    key: int
    """The provenance key of its outline and font carets, the same in every process.
    Assigning a key does not change the live glyph's outline or carets."""
    x_advance: float
    """Its advance, the width it takes in the line, in font units: a ligature's carets
    divide it."""


class Typst(VMobject):
    r"""A Typst document, typeset in the engine: every glyph and shape of its layout is
    a part, white unless styled.

    The code is Typst markup, a document's body on a page as large as what it holds:
    `*strong*`, `_emphasis_`, math between `$` signs, `#set` and `#show` rules, and the
    rest of Typst. The parts are what Typst lays out, in document order, spaces
    excluded: glyphs ([TypstGlyph][manimgx.mobjects.text.TypstGlyph]) and
    shapes (a rule, a fraction's bar, a box). A labelled box, `#box[…] <name>`, is a
    group: [select][manimgx.Typst.select] gives it. Packages are imported from
    `package_path` (and mitex, `@preview/mitex:0.2.7`, from ManimGX's engine), never
    downloaded; code Typst can't typeset raises a
    [TypstError][manimgx.drawing.typesetting.TypstError].

    Text is set in Libertinus Serif and math in New Computer Modern Math, Typst's
    defaults, unless the code sets another font. The fonts are those ManimGX ships, so a
    document looks the same on every machine: Typst's own (these two, New Computer
    Modern and DejaVu Sans Mono), Noto Sans, and Noto faces for the scripts those lack,
    from Arabic, Hebrew and Devanagari to Chinese, Japanese and Korean, with symbols and
    emoji; a character a font lacks is set in one that has it. Fonts in `font_paths`
    come first, and a system font is read only for a family the code names that none of
    these has. A paragraph's direction and the forms of Han characters follow the code's
    `lang` and `dir` (`#set text(lang: "ja")`, `#set text(dir: rtl)`); a
    [Text][manimgx.Text] sets them from its characters.

    What Typst paints in its default ink, black, takes `color`, and the colors the code
    sets are kept, unless paint keywords (`fill_color` and the rest) paint over every
    part. A document is typeset once: the same code is read back from a cache on disk,
    in any process.

    Args:
        typst_code: The document: Typst markup.
        font_size: The size of the text: an em is `font_size / 96` scene units (0.5 at
            48).
        typst_preamble: Typst code set before the document: rules, definitions,
            imports.
        font_paths: Directories of font files, searched, with their subdirectories,
            before the fonts ManimGX ships.
        should_center: Whether the mobject is centered on the origin.
        height: The height to scale the mobject to, in scene units; None to size it by
            `font_size`.
        width: The width to scale it to, in scene units, after `height`; None to size
            it by `font_size`.
        package_path: The directory Typst packages are imported from (as
            `namespace/name/version` directories), besides mitex, which ManimGX's
            engine holds; None for none but mitex.
        font_scale: How much larger than `font_size` the text is set: the layout is
            scaled by `font_size * font_scale`, while
            [font_size][manimgx.Typst.font_size] reads `font_size`. A
            [Text][manimgx.Text] sets it to its font's own scale, which makes a capital
            as tall in every font.
        color: The color of Typst's default ink, black; None for white.
        fill_color: A fill color for every part; None keeps the typeset ones.
        fill_opacity: A fill opacity for every part, from 0 to 1; None keeps the
            typeset ones.
        stroke_color: A stroke color for every part; None keeps the typeset ones.
        stroke_opacity: A stroke opacity for every part, from 0 to 1; None keeps the
            typeset ones.
        stroke_width: A stroke width for every part, in hundredths of a scene unit;
            None keeps the typeset ones, which scale with the mobject.
        opacity: The opacity of every part's fill and stroke, from 0 to 1, where
            `fill_opacity` or `stroke_opacity` doesn't give one; None keeps the
            typeset ones.

    Examples:
        ```python
        import manimgx as m


        class TypstExample(m.Scene):
            def construct(self) -> None:
                document = m.Typst(
                    "*Typst* markup, _typeset_ in the engine:\n\n"
                    "$ sum_(k=1)^n k = (n(n+1))/2 $\n\n"
                    "with #text(fill: orange)[colors of its own]",
                    font_size=64,
                )
                self.play(m.Write(document))
        ```
    """

    @prototype
    def __init__(
        self,
        typst_code: str,
        *,
        font_size: float = DEFAULT_FONT_SIZE,
        typst_preamble: str = "",
        font_paths: list[str | Path] | None = None,
        should_center: bool = True,
        height: float | None = None,
        width: float | None = None,
        package_path: str | Path | None = None,
        font_scale: float = 1.0,
        color: Colors | None = None,
        fill_color: Colors | None = None,
        fill_opacity: float | Sequence[float] | None = None,
        stroke_color: Colors | None = None,
        stroke_opacity: float | Sequence[float] | None = None,
        stroke_width: float | None = None,
        opacity: float | None = None,
        **kwargs: Unpack[Look],
    ):
        super().__init__(stroke_color=None, fill_color=None, **kwargs)
        self.set_color(WHITE if color is None else color)
        # how much larger than font_size the text is set (a font's calibration: see Text)
        self._font_scale = font_scale
        self.typst_code = typst_code
        """The Typst code the mobject was typeset from."""
        self.typst_preamble = typst_preamble
        """The Typst code set before it."""
        # unless a stroke width is given, a stroke keeps its share of its part's size as
        # typeset: (part, its size and its stroke width as typeset)
        self._strokes_scale = stroke_width is None
        self._strokes: list[tuple[VMobject, float, float]] = []
        # A height overrides font sizing; width is fitted afterward in either case.
        placed = should_center and height is None
        self.initial_height = self._build(
            typeset(
                typst_code,
                typst_preamble,
                font_paths=font_paths,
                package_path=package_path,
            ),
            font_size * font_scale * SCALE_FACTOR_PER_FONT_POINT if placed else None,
        )
        if opacity is not None:  # both, where one isn't given its own
            fill_opacity = opacity if fill_opacity is None else fill_opacity
            stroke_opacity = opacity if stroke_opacity is None else stroke_opacity
        self.set_style(
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            stroke_color=stroke_color,
            stroke_opacity=stroke_opacity,
            stroke_width=stroke_width,
        )
        if should_center and not placed:
            self.center()
        if height is not None:
            self.set(height=height)
        elif not placed:
            self.font_size = font_size
        if width is not None:
            self.set(width=width)

    def _build(self, layout: Layout, scale: float | None) -> float:
        """Every glyph and shape of the layout, in document order, Typst's black ink painted this
        mobject's color, and the labelled groups. With `scale`, parts are built in place (the ink
        centered and scaled). Returns the ink's height as typeset."""
        rows = layout.rows
        # each part's placement (a glyph) or points (a shape), and the ink box around them all:
        # the one box, its curves' tight box
        places: list[np.ndarray] = []
        low, high = np.full(2, np.inf), np.full(2, -np.inf)
        for row in rows:
            if row[KIND] == GLYPH:
                _, outline, _ = layout.glyphs[int(row[KEY])]
                assert outline is not None
                a, b, c, d, e, f = row[PLACEMENT]
                place = np.array([[a, c, 0.0, e], [b, d, 0.0, f], [0.0, 0.0, 1.0, 0.0]])
                ink = placed_box(place, outline, True)[:, :2]
            else:
                place = layout.shapes[int(row[KEY])]
                ink = extent(place, True)[:, :2]
            places.append(place)
            if len(ink):
                low, high = (
                    np.minimum(low, ink.min(axis=0)),
                    np.maximum(high, ink.max(axis=0)),
                )
        height = float(high[1] - low[1]) if high[1] >= low[1] else 0.0
        if scale is not None and height > 0:
            shift = np.array([*((low + high) / 2), 0.0])
            for k, place in enumerate(places):
                if place.shape == (3, 4):  # a glyph's placement
                    place = place * scale
                    place[:, 3] -= shift * scale
                else:  # a shape's points
                    place = (place - shift) * scale
                places[k] = place
        else:
            scale = None
        ink_color = self.color.to_hex()
        parts: list[VMobject] = []
        for row, place in zip(rows, places):
            fill, stroke = row[FILL], row[STROKE]
            if row[KIND] == GLYPH:
                key = int(row[KEY])
                _, outline, carets = layout.glyphs[key]
                assert outline is not None
                # its color is its ink: both brushes, as `color=` means
                glyph = TypstGlyph(
                    color=_ink(fill, ink_color),
                    fill_opacity=float(fill[3]),
                    stroke_width=0,
                )
                glyph._geometry = Blend(((place, outline),), len(outline.array))
                node, drawn = row[NODE], row[DRAWN]
                glyph.node = int(node[0]) - layout.body if node[0] >= 0 else -1
                glyph.drawn = (int(drawn[0]), int(drawn[1]))
                glyph.key, glyph.x_advance = key, float(row[ADVANCE])
                if carets:
                    glyph._carets = carets
                part: VMobject = glyph
            else:
                part = VMobject(
                    color=_ink(fill, ink_color) if fill[0] >= 0 else ink_color,
                    fill_opacity=float(fill[3]) if fill[0] >= 0 else 0.0,
                    stroke_width=0,
                )
                part.points = place
            if stroke[0] >= 0 and row[WIDTH] > 0:
                size = max(part.width, part.height)
                width = float(row[WIDTH])
                part.set_stroke(
                    _ink(stroke, ink_color),
                    opacity=float(stroke[3]),
                    width=None if scale is None else width * scale * 100,
                )
                if self._strokes_scale and size > 0:
                    self._strokes.append((part, size / (scale or 1.0), width))
            parts.append(part)
        self.add(*parts)
        self.labels: dict[str, VGroup] = {}  # the parts inside each `<label>`
        for label, members in layout.labels:
            group = self.labels.setdefault(label, VGroup())
            group.add(*(parts[i] for i in members))
        return height

    def select(self, key: str | int) -> VGroup:
        """Find the parts of a labelled group: of every group with that label, as one.

        A label names a box in the code, `#box[…] <name>`; a
        [MathTypst][manimgx.MathTypst] makes a group of `{{ … }}` too, named by
        `{{ … : name }}` or numbered in order. An unknown label raises KeyError, a
        number out of range IndexError.

        Args:
            key: The label; or the number of a MathTypst's unnamed `{{ … }}` group, from
                0.

        Returns:
            A new group of the parts themselves (not copies), in order.

        Examples:
            ```python
            import manimgx as m


            class TypstSelectExample(m.Scene):
                def construct(self) -> None:
                    text = m.Typst(
                        "Label a #box[box] <noun> to #box[select] <verb> it",
                        font_size=96,
                    )
                    text.select("noun").set_color(m.YELLOW)
                    text.select("verb").set_color(m.BLUE)
                    self.add(text)
            ```
        """
        label = f"_grp-{key}" if isinstance(key, int) else key
        if label not in self.labels:
            error = IndexError if isinstance(key, int) else KeyError
            raise error(f"no group {key!r}; labels: {list(self.labels)}")
        return self.labels[label]

    @property
    def font_size(self) -> float:
        """The mobject's effective font size, including scaling. Explicit width or height
        determines this size when given at construction. Set it to a positive size to
        scale the mobject to it."""
        return (
            self.height
            / self.initial_height
            / SCALE_FACTOR_PER_FONT_POINT
            / self._font_scale
        )

    @font_size.setter
    def font_size(self, val: float) -> None:
        if val <= 0:
            raise ValueError("font_size must be greater than 0.")
        if self.height > 0:
            self.scale(val / self.font_size)

    def scale(
        self,
        scale_factor: float | Vector3DLike,
        scale_stroke: bool = False,
        **kwargs: Unpack[Pivot],
    ) -> Self:
        """Scale the mobject and its whole family about a point, as
        [Mobject.scale][manimgx.Mobject.scale] does; the strokes the typesetting drew (a
        rule, a box's outline) keep their share of their part's size, unless the mobject
        was made with a `stroke_width`.

        Args:
            scale_factor: The factor: 2 doubles the mobject's size, 0.5 halves it; or
                its factors along x, y and z.
            scale_stroke: Whether the other strokes' widths scale too, by the factor.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot].
        """
        result = super().scale(scale_factor, scale_stroke=scale_stroke, **kwargs)
        self._scale_strokes()
        return result

    def _scale_strokes(self) -> None:
        """Each typeset stroke's width, its share of its part's size again."""
        if not self._strokes_scale:
            return
        for part, typeset_size, typeset_width in self._strokes:
            if typeset_size > 0:
                width = typeset_width * max(part.width, part.height) / typeset_size
                part.set_stroke(width=width * 100, family=False)  # in 1/100 units

    def init_colors(self, propagate_colors: bool = True) -> Self:
        # Its parts are painted from the layout's ink; constructor style is not reused.
        self.__dict__.pop("style", None)
        return self


_MANIMGRP = "#let manimgrp(lbl, body) = [#box(body) #label(lbl)]"
# a string, `{{`, `}}`, a bracket, or a run of anything else: strings and content blocks hold no groups
_TOKEN = re.compile(r'"(?:\\[\s\S]|[^"\\])*"?|\{\{|\}\}|[\[\]]|[^"\[\]{}]+|[{}]')
_LABELLED = re.compile(r"^(.*)\s*:\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*$", re.DOTALL)


def _groups(expression: str) -> tuple[str, list[str]]:
    """The expression with each `{{ body }}` or `{{ body : label }}` as `manimgrp(label, body)`
    (unlabelled groups numbered `_grp-0`, `_grp-1`…), and the labels in order. A group runs to
    its matching `}}`; one never closed stays as written, with all that follows it."""
    tokens = _TOKEN.findall(expression)
    out: list[str] = []
    labels: list[str] = []
    i = brackets = auto = 0
    while i < len(tokens):
        token = tokens[i]
        i += 1
        if token == "[":
            brackets += 1
        elif token == "]" and brackets:
            brackets -= 1
        elif token == "{{" and not brackets:
            depth, inner, j = 1, 0, i
            while j < len(tokens) and depth:
                t, j = tokens[j], j + 1
                if t == "[":
                    inner += 1
                elif t == "]" and inner:
                    inner -= 1
                elif t in ("{{", "}}") and not inner:
                    depth += 1 if t == "{{" else -1
            if depth:
                out.append("{{" + "".join(tokens[i:]))
                break
            content, i = "".join(tokens[i : j - 1]), j
            if match := _LABELLED.match(content):
                body, label = match.group(1).strip(), match.group(2)
            else:
                body, label, auto = content.strip(), f"_grp-{auto}", auto + 1
            labels.append(label)
            out.append(f'manimgrp("{label}", {body})')
            continue
        out.append(token)
    return "".join(out), labels


class MathTypst(Typst):
    """A formula in Typst's math syntax, typeset in display style: its parts are its
    glyphs and shapes, white unless styled.

    `MathTypst("x^2 + y^2")` typesets `$ x^2 + y^2 $`, in New Computer Modern Math.
    Double braces make groups, which [select][manimgx.Typst.select] gives: `{{ x^2 }}`
    is numbered, 0 the first, and `{{ x^2 : square }}` is named "square"; the braces are
    not typeset.

    Args:
        math_expression: The formula, in Typst math.

    Examples:
        ```python
        import manimgx as m


        class MathTypstExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTypst(
                    "{{ a^2 : a }} + {{ b^2 : b }} = {{ c^2 : c }}", font_size=144
                )
                formula.select("a").set_color(m.BLUE)
                formula.select("b").set_color(m.GREEN)
                formula.select("c").set_color(m.YELLOW)
                self.play(m.Write(formula))
        ```
    """

    @prototype
    def __init__(self, math_expression: str, **kwargs: Unpack[TypstOptions]):
        processed, labels = _groups(math_expression)
        preamble = kwargs.get("typst_preamble", "")
        if labels and _MANIMGRP not in preamble:
            kwargs["typst_preamble"] = (
                f"{_MANIMGRP}\n{preamble}" if preamble else _MANIMGRP
            )
        super().__init__(f"$ {processed} $", **kwargs)


DEFAULT_FONT = (  # embedded in Typst: identical text on every machine
    "New Computer Modern"
)
_SANS = ("Noto Sans", "Noto Sans Hebrew")  # Typst's own fallback sets Hebrew in a serif
# CSS's and Pango's generic families, as faces ManimGX ships (lowercase keys)
_GENERIC: dict[str, tuple[str, ...]] = {
    "serif": (DEFAULT_FONT,),
    "sans-serif": _SANS,
    "sans": _SANS,
    "monospace": ("DejaVu Sans Mono",),
    "mono": ("DejaVu Sans Mono",),
}
# the scripts that decide a CJK text's language (its Han characters' regional forms)
_KANA = re.compile("[\u3040-\u30ff\u31f0-\u31ff]")
_HANGUL = re.compile("[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]")
_HAN = re.compile("[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0003ffff]")
_CE_CAP_HEIGHT_PER_POINT = 0.8979 / 96  # CE Text("A", font_size=96).height, measured
# The space between lines, in ems, for a line_spacing of -1: CE's default (its baselines are
# meant to be font_size * (1 + 0.3) apart)
_LINE_SPACING = 0.3
_WEIGHTS = {
    "THIN": 100,
    "ULTRALIGHT": 200,
    "LIGHT": 300,
    "SEMILIGHT": 350,
    "BOOK": 380,
    "NORMAL": 400,
    "MEDIUM": 500,
    "SEMIBOLD": 600,
    "BOLD": 700,
    "ULTRABOLD": 800,
    "HEAVY": 900,
    "ULTRAHEAVY": 950,
}
# CE's slants (any other is upright)
_SLANTS = {"ITALIC": "italic", "OBLIQUE": "oblique"}
_SLICE = re.compile(r"\[(-?\d*):(-?\d*)\]")  # CE's slice keys, "[a:b]"
_FAR = 1e6  # a cut's outer edges, in font units: past any glyph's ink

type Style = tuple[str, str]
"""A run's CE weight and CE slant."""


def _arguments(style: Style) -> str:
    """Typst's text arguments for a style."""
    weight, slant = style
    return (
        f"weight: {_WEIGHTS.get(weight.upper(), 400)},"
        f' style: "{_SLANTS.get(slant.upper(), "normal")}"'
    )


def _fonts(font: str) -> str:
    """Typst's font list for a CE font name: a generic family's faces, or the family named
    and then ManimGX's default face (for a family no font has, or a character it lacks).
    Typst falls back among ManimGX's fonts after them."""
    families = _GENERIC.get(font.lower(), (font, DEFAULT_FONT))
    return f"({''.join(f'{typst_string(f)}, ' for f in dict.fromkeys(families))})"


def _rules(text: str) -> str:
    """The Typst rules a text's characters call for: a right-to-left paragraph when its first
    strong character is (Unicode's rule, UAX #9 P2-P3; Typst takes a paragraph's direction
    from its language), and a CJK text's language, which picks its Han characters' regional
    forms: Japanese with kana, Korean with hangul, else Chinese (Simplified)."""
    rules = ""
    for ch in text:
        kind = unicodedata.bidirectional(ch)
        if kind in ("R", "AL"):
            rules += "#set text(dir: rtl)\n"
        if kind in ("L", "R", "AL"):
            break
    if _KANA.search(text):
        rules += '#set text(lang: "ja")\n'
    elif _HANGUL.search(text):
        rules += '#set text(lang: "ko")\n'
    elif _HAN.search(text):
        rules += '#set text(lang: "zh")\n'
    return rules


def _find(text: str, key: str) -> list[range]:
    """The characters of `text` a key picks, as CE defines them: "[a:b]" is a slice of the text
    as written; any other key, each occurrence of it (not overlapping)."""
    match = _SLICE.fullmatch(key)
    if match is not None:
        start, stop = (int(g) if g else None for g in match.groups())
        return [range(*slice(start, stop).indices(len(text)))]
    spans = []
    at = text.find(key) if key else -1
    while at != -1:
        spans.append(range(at, at + len(key)))
        at = text.find(key, at + len(key))
    return spans


def _literal(
    text: str,
    tab_width: int,
    out: list[str],
    runs: dict[int, list[int]],
    at: int,
    first: int,
) -> int:
    """Append `text` as a Typst string (set literally; tabs as `tab_width` spaces) and record,
    for each byte of its value, the character it came from. Return where the string ends.
    """
    value: list[str] = []
    chars: list[int] = []
    for k, ch in enumerate(text):
        piece = " " * tab_width if ch == "\t" else ch
        value.append(piece)
        chars.extend([first + k] * len(piece.encode()))
    literal = "#" + typst_string("".join(value))
    runs[at + 1] = chars  # the string's node starts after the "#"
    out.append(literal)
    return at + len(literal.encode())


def _lines(line_spacing: float) -> str:
    """The Typst rules that set lines on a baseline grid: baselines (1 + line_spacing) em
    apart, whatever the glyphs on them (-1: CE's default, 0.3). A line's box is its baseline,
    so the leading is the whole pitch."""
    gap = _LINE_SPACING if line_spacing == -1 else line_spacing
    return (
        '#set text(top-edge: "baseline", bottom-edge: "baseline")\n'
        f"#set par(leading: {1 + gap}em)\n"
    )


def _calibration(font: str, kwargs: TypstOptions) -> float:
    """A capital's exact measured scale, reusing Typst's cached construction."""
    options: TypstOptions = {"font_size": DEFAULT_FONT_SIZE}
    if "font_paths" in kwargs:
        options["font_paths"] = kwargs["font_paths"]
    probe = Typst(f"#text(font: {_fonts(font)})[H]", **options)
    target = _CE_CAP_HEIGHT_PER_POINT * DEFAULT_FONT_SIZE
    return target / probe.height if probe.height > 0 else 1.0


class TextOptions(_TypstOptions, total=False, closed=True):
    """[Text][manimgx.Text]'s keywords, for the classes that pass them on:
    [Paragraph][manimgx.Paragraph].

    Beyond these, they take the
    [Typst keywords][manimgx.mobjects.text.TypstOptions].
    """

    line_spacing: float
    """The space between lines, in ems: a text's baselines are `1 + line_spacing` ems
    apart, whatever the glyphs on them (default -1: 0.3)."""
    font: str
    """The font family: one manimgx ships (New Computer Modern, Libertinus Serif,
    DejaVu Sans Mono, Noto Sans, …), "serif", "sans-serif" or "monospace", one in
    `font_paths`, or else one of the system's; a family found nowhere falls back to New
    Computer Modern (default "": New Computer Modern)."""
    slant: str
    """The slant: `NORMAL`, `ITALIC` or `OBLIQUE` (default `NORMAL`)."""
    weight: str
    """The weight, by name, from `THIN` through `NORMAL` and `BOLD` to `ULTRAHEAVY`
    (default `NORMAL`); the font's nearest weight is used."""
    t2c: Mapping[str, ParsableManimColor] | None
    """A color for each key: a slice `"[a:b]"` of the text as written, spaces included,
    or a string, each occurrence of it (default None)."""
    t2g: Mapping[str, Sequence[ParsableManimColor]] | None
    """A gradient for each key: its colors spread along the characters the key picks, as
    `t2c` picks them (default None)."""
    t2s: Mapping[str, str] | None
    """A slant for each key, picking characters as `t2c` does (default None)."""
    t2w: Mapping[str, str] | None
    """A weight for each key, picking characters as `t2c` does (default None)."""
    gradient: Sequence[ParsableManimColor] | None
    """Colors spread along the whole text, character by character, spaces included
    (default None)."""
    tab_width: int
    """How many spaces a tab is set as (default 4)."""
    disable_ligatures: bool
    """Whether every character is a glyph of its own, with no ligatures (default False:
    "fi" may be one glyph)."""


class Text(Typst):
    """Text in a font, typeset by Typst as it is written: white unless styled.

    Spaces stay, a newline breaks the line, a tab is `tab_width` spaces, and nothing is
    markup ("= Title" is no heading). The lines are set on a grid: their baselines are
    `1 + line_spacing` ems apart, whatever the glyphs on them. The parts are the glyphs,
    in reading order, spaces excluded: `Text("Hello")[0]` is the "H", a
    [TypstGlyph][manimgx.mobjects.text.TypstGlyph]. A ligature is one glyph
    (the "ffi" of "office", in the default font) unless `disable_ligatures`.

    A text is set in one font, from the fonts ManimGX ships, so it looks the same on
    every machine: New Computer Modern unless `font` names another. "serif",
    "sans-serif" (or "sans") and "monospace" (or "mono") are New Computer Modern, Noto
    Sans and DejaVu Sans Mono. Fonts in `font_paths` come first; a family neither they
    nor ManimGX have is read from the system's fonts, and one found nowhere falls back
    to New Computer Modern. A character the font lacks is set in another font that has
    it: ManimGX ships Noto faces for Arabic, Hebrew, the Indic scripts, Thai, Chinese,
    Japanese, Korean and more, with symbols and emoji. In any font, a capital is 0.449
    scene units tall at the default size, 48, and in proportion at others: each font is
    scaled to that, and `font_size` still reads the size asked for.

    A text whose first letter is from a right-to-left script (Arabic, Hebrew) is set as
    a right-to-left paragraph, its lines lined up on the right. A Chinese, Japanese or
    Korean text takes its language from its characters (Japanese with kana, Korean with
    hangul, else Chinese), which gives its Han characters their regional forms.

    Keys pick characters: a slice `"[a:b]"` of the text as written, spaces included, or
    a string, each occurrence of it (a key that occurs nowhere picks nothing). `t2s` and
    `t2w` set what they pick in another slant or weight; `gradient`, then `t2g`, then
    `t2c` color it, each over the one before. Color never changes the layout: the text
    is laid out once, and each glyph takes the color of the characters it draws — a
    ligature that a color boundary crosses is cut there, each piece in its characters'
    color. A custom glyph's path-building methods also construct its color pieces.

    Args:
        text: The text, as written.
        line_spacing: The space between lines, in ems: the baselines are
            `1 + line_spacing` ems apart; -1 for 0.3.
        font: The font family, or "serif", "sans-serif" or "monospace"; "" for New
            Computer Modern.
        slant: `NORMAL`, `ITALIC` or `OBLIQUE`.
        weight: A weight by name, from `THIN` through `NORMAL` and `BOLD` to
            `ULTRAHEAVY`; the font's nearest weight is used.
        t2c: A color for each key.
        t2g: A gradient for each key: its colors spread along what the key picks.
        t2s: A slant for each key.
        t2w: A weight for each key.
        gradient: Colors spread along the whole text, character by character, spaces
            included.
        tab_width: How many spaces a tab is set as.
        disable_ligatures: Whether every character is a glyph of its own.
        **kwargs: [Typst keywords][manimgx.mobjects.text.TypstOptions]:
            `font_size` (48 unless given), `color`, `width` or `height`, and the rest.

    Examples:
        ```python
        import manimgx as m


        class TextExample(m.Scene):
            def construct(self) -> None:
                texts = m.VGroup(
                    m.Text("New Computer Modern"),
                    m.Text("sans-serif: Noto Sans", font="sans-serif"),
                    m.Text("monospace: DejaVu Sans Mono", font="monospace"),
                    m.Text("Libertinus Serif", font="Libertinus Serif"),
                    m.Text("bold and italic", weight=m.BOLD, slant=m.ITALIC),
                )
                self.add(texts.arrange(m.DOWN, buff=0.5).scale(1.3))
        ```

        ```python
        import manimgx as m


        class TextScriptsExample(m.Scene):
            def construct(self) -> None:
                texts = m.VGroup(
                    m.Text("Ελληνικά, кириллица"),
                    m.Text("مرحبا بالعالم"),
                    m.Text("สวัสดีชาวโลก"),
                    m.Text("你好，世界"),
                    m.Text("こんにちは、世界"),
                    m.Text("안녕하세요, 세계"),
                )
                self.add(texts.arrange(m.DOWN, buff=0.4).scale(1.2))
        ```

        ```python
        import manimgx as m


        class TextColoringExample(m.Scene):
            def construct(self) -> None:
                words = {"red": m.RED, "green": m.GREEN, "blue": m.BLUE}
                word = {"gradient": (m.RED, m.YELLOW)}
                texts = m.VGroup(
                    m.Text("red, green and blue", t2c=words),
                    m.Text("a slice of the text", t2c={"[2:7]": m.YELLOW}),
                    m.Text("a gradient along it all", gradient=(m.BLUE, m.GREEN)),
                    m.Text("a gradient in one word", t2g=word),
                )
                self.add(texts.arrange(m.DOWN, buff=0.5).scale(1.3))
        ```
    """

    @prototype
    def __init__(
        self,
        text: str,
        line_spacing: float = -1,
        font: str = "",
        slant: str = NORMAL,
        weight: str = NORMAL,
        t2c: Mapping[str, ParsableManimColor] | None = None,
        t2g: Mapping[str, Sequence[ParsableManimColor]] | None = None,
        t2s: Mapping[str, str] | None = None,
        t2w: Mapping[str, str] | None = None,
        gradient: Sequence[ParsableManimColor] | None = None,
        tab_width: int = 4,
        disable_ligatures: bool = False,
        **kwargs: Unpack[TypstOptions],
    ) -> None:
        if kwargs.get("fill_opacity") is None and kwargs.get("opacity") is None:
            kwargs["fill_opacity"] = 1.0  # filled, unless an opacity is given
        self.text = text
        """The text, as it was written."""
        self.original_text = text
        self.font = font
        self.slant, self.weight = slant, weight
        chars = text  # the text as written, as characters
        family = font or DEFAULT_FONT
        base: Style = (weight, slant)
        styles: list[Style] | None = None
        if t2w or t2s:
            styles = [base] * len(chars)
            for field, mapping in enumerate((t2w, t2s)):
                for key, value in (mapping or {}).items():
                    for span in _find(chars, key):
                        for i in span:
                            style = list(styles[i])
                            style[field] = value
                            styles[i] = (style[0], style[1])
        ligatures = ", ligatures: false" if disable_ligatures else ""
        head = f"#text(font: {_fonts(family)}, {_arguments(base)}{ligatures})["
        body, runs = self._source(text, tab_width, len(head.encode()), base, styles)
        rules = _rules(text) + (_lines(line_spacing) if "\n" in text else "")
        if rules:
            kwargs["typst_preamble"] = rules + kwargs.get("typst_preamble", "")
        # set larger by its font's calibration, so font_size stays the size asked for
        super().__init__(
            f"{head}{body}]", font_scale=_calibration(family, kwargs), **kwargs
        )
        self._chars = chars
        self._clusters = self._characters(runs)
        colors: dict[int, ManimColor] = {}
        if gradient:
            colors |= dict(enumerate(color_gradient(list(gradient), len(chars))))
        for key, stops in (t2g or {}).items():
            for span in _find(chars, key):
                if span:
                    colors |= dict(zip(span, color_gradient(list(stops), len(span))))
        for key, color in (t2c or {}).items():
            for span in _find(chars, key):
                colors |= dict.fromkeys(span, ManimColor(color))
        if colors:
            self._paint(colors)

    def _source(
        self,
        text: str,
        tab_width: int,
        at: int,
        base: Style,
        styles: list[Style] | None,
    ) -> tuple[str, dict[int, list[int]]]:
        """The Typst code setting the text (from byte `at`): a string per run of one style, and for
        each string where it starts and the character each byte of its value came from.
        """
        out: list[str] = []
        runs: dict[int, list[int]] = {}
        if styles is None or not text:
            _literal(text, tab_width, out, runs, at, 0)
            return "".join(out), runs
        start = 0
        for end in range(1, len(text) + 1):
            if end < len(text) and styles[end] == styles[start]:
                continue
            opener = (
                "" if styles[start] == base else f"#text({_arguments(styles[start])})["
            )
            out.append(opener)
            at += len(opener.encode())
            at = _literal(text[start:end], tab_width, out, runs, at, start)
            if opener:
                out.append("]")
                at += 1
            start = end
        return "".join(out), runs

    def _characters(self, runs: dict[int, list[int]]) -> list[range]:
        """Each part's characters: those its glyph's cluster draws, through the string it came
        from (none for a part not from the text: a list's marker, an underline)."""
        clusters = []
        for part in self.submobjects:
            drawn: list[int] = []
            if isinstance(part, TypstGlyph) and part.node in runs:
                drawn = runs[part.node][part.drawn[0] : part.drawn[1]]
            clusters.append(range(drawn[0], drawn[-1] + 1) if drawn else range(0))
        return clusters

    def _paint(self, colors: Mapping[int, ManimColor]) -> None:
        """Each glyph takes its characters' colors (a grapheme's color: its first character's);
        a glyph of several colors is cut at its carets."""
        graphemes = _engine.graphemes(self._chars)
        for part, chars in zip(self.submobjects, self._clusters):
            if not chars:
                continue
            heads = graphemes[
                bisect.bisect_left(graphemes, chars.start) : bisect.bisect_left(
                    graphemes, chars.stop
                )
            ]
            if not heads or heads[0] != chars.start:
                heads.insert(0, chars.start)
            paints = [colors.get(i) for i in heads]
            if len(set(paints)) == 1:
                if paints[0] is not None:
                    part.set_color(paints[0])
            elif isinstance(part, TypstGlyph):
                rtl = unicodedata.bidirectional(self._chars[chars.start]) in ("R", "AL")
                _cut(part, paints[::-1] if rtl else paints)


def _cut(glyph: TypstGlyph, paints: list[ManimColor | None]) -> None:
    """Cut a glyph at its carets (the font's, else equal parts) into pieces of one color each; the
    glyph becomes their group."""
    n = len(paints)
    carets: np.ndarray | tuple[float, ...] = np.frombuffer(glyph._carets, dtype="<f8")
    if len(carets) != n - 1:
        carets = tuple(glyph.x_advance * k / n for k in range(1, n))
    edges = [-_FAR, *carets, _FAR]
    runs: list[tuple[float, float, ManimColor | None]] = []
    for k, paint in enumerate(paints):
        if runs and runs[-1][2] == paint:
            runs[-1] = (runs[-1][0], edges[k + 1], paint)
        else:
            runs.append((edges[k], edges[k + 1], paint))
    ((placement, outline),) = glyph._geometry.terms
    tolerance = VMobject.tolerance_for_point_equality
    whole = _to_path(Blend.of(outline.array).points(), tolerance)
    pieces = []
    for x0, x1, paint in runs:
        corners = np.array(
            [
                [x0, -_FAR, 0],
                [x1, -_FAR, 0],
                [x1, _FAR, 0],
                [x0, _FAR, 0],
                [x0, -_FAR, 0],
            ]
        )
        strip = np.empty((16, 3))
        for i, alpha in enumerate(np.linspace(0, 1, 4)):
            strip[i::4] = interpolate(corners[:-1], corners[1:], alpha)
        result = _pathops().op(
            whole,
            _to_path(Blend.of(strip).points(), tolerance),
            _pathops().PathOp.INTERSECTION,
        )
        piece = glyph.copy()
        piece._geometry = EMPTY
        _append_path(piece, result)
        local = piece.points
        piece._geometry = Blend(((placement, Shape(np.array(local))),), len(local))
        if paint is not None:
            piece.set_color(paint)
        pieces.append(piece)
    glyph._geometry = EMPTY
    glyph.add(*pieces)


class Paragraph(VGroup):
    """Lines of text set as one paragraph: on one grid of baselines, each line at the
    paragraph's start or where `alignment` puts it.

    The lines are one [Text][manimgx.Text] (`lines_text`), joined by newlines, so they
    share its grid: their baselines are `1 + line_spacing` ems apart (1.3 unless
    `line_spacing` is given). The paragraph's parts are its lines, from the top, each
    the group of its glyphs.

    Args:
        *text: The lines: each string is one, or several, split at its newlines.
        alignment: "left", "center" or "right" to line the lines up on that side or
            center them; None to start each at the paragraph's start (the left, for
            left-to-right text).

    Examples:
        ```python
        import manimgx as m


        class ParagraphExample(m.Scene):
            def construct(self) -> None:
                lines = ("Twinkle, twinkle,", "little star,", "how I wonder")
                paragraphs = m.VGroup(
                    m.Paragraph(*lines),
                    m.Paragraph(*lines, alignment="center", line_spacing=1),
                    m.Paragraph(*lines, alignment="right"),
                )
                self.add(paragraphs.arrange(buff=0.8).scale(0.85))
        ```
    """

    def __init__(
        self,
        *text: str,
        alignment: Literal["left", "center", "right"] | None = None,
        **kwargs: Unpack[TextOptions],
    ) -> None:
        joined = "\n".join(text)
        if alignment is not None:  # Typst's alignments of these names
            kwargs["typst_preamble"] = f"#set align({alignment})\n" + kwargs.get(
                "typst_preamble", ""
            )
        self.lines_text = whole = Text(joined, **kwargs)
        """The lines as one [Text][manimgx.Text], joined by newlines: the paragraph's
        lines group its glyphs."""
        # the parts are the lines, each the group of its glyphs (CE's structure)
        starts = [0, *(i + 1 for i, ch in enumerate(joined) if ch == "\n")]
        lines: list[list[Mobject]] = [[] for _ in starts]
        for part, chars in zip(whole.submobjects, whole._clusters):
            lines[bisect.bisect_right(starts, chars.start) - 1].append(part)
        super().__init__(*(VGroup(*line) for line in lines))
        self.alignment = alignment


# LaTeX is converted to Typst by mitex, compiled into the engine; the package gives its scope.
# LaTeX sets its text in Computer Modern, as its math (Typst's default text face is Libertinus)
_IMPORT = (
    '#import "@preview/mitex:0.2.7": mitex-scope\n'
    '#set text(font: "New Computer Modern")\n'
)


def _standalone(tex: str) -> str:
    """CE's `_modify_special_strings`: make a lone fragment of a formula typeset on its own.
    Its mends are math's (a trailing `dot` is `\\dot`'s); text is converted as written."""
    tex = tex.strip()
    if tex in ("\\over", "\\overline", "\\sqrt", "\\sqrt{") or tex.endswith(
        ("_", "^", "dot")
    ):
        tex += "{\\quad}"
    if tex in ("\\substack", ""):
        tex = "\\quad"
    if tex.startswith("\\\\"):
        tex = tex.replace("\\\\", "\\quad\\\\")
    lefts, rights = (
        len([s for s in tex.split(k)[1:] if s and s[0] in "(){}[]|.\\"])
        for k in ("\\left", "\\right")
    )
    if lefts != rights:
        tex = tex.replace("\\left", "\\big").replace("\\right", "\\big")
    opens = tex.count("{") - tex.count("\\{") + tex.count("\\\\{")
    closes = tex.count("}") - tex.count("\\}") + tex.count("\\\\}")
    return "{" * max(0, closes - opens) + tex + "}" * max(0, opens - closes)


_BRACES = re.compile("{{(.*?)}}")
_HOLE = 0xE000  # private-use characters: mitex passes them through as they are


def _isolate_braces(strings: list[str], math: bool) -> list[str]:
    """CE's double braces: `{{…}}` sets what it holds apart as a part of its own. In math,
    where spaces mean nothing, once they split anything every part is stripped; text keeps
    its spaces, so its strings still join into the text as written."""
    pieces = [p for s in strings for p in _BRACES.split(s)]
    if math and len(pieces) > len(strings):
        pieces = [p.strip() for p in pieces]
    return [p for p in pieces if p]


_TOKENS = re.compile(r"\\([a-zA-Z]+)|\\.|([{}])")
_DEPTH = {"{": 1, "}": -1, "begin": 1, "end": -1, "left": 1, "right": -1}


def _balanced(tex: str) -> bool:
    """Does the LaTeX stand on its own: every group, environment and delimiter it opens closed
    in it, and none closed that it did not open? (mitex closes what is left open, so a
    piece converting on its own does not tell.)"""
    depth = 0
    for command, brace in _TOKENS.findall(tex):
        depth += _DEPTH.get(command or brace, 0)
        if depth < 0:
            return False
    return depth == 0


def _one_formula(
    pieces: list[str], separator: str, convert: Callable[[str], str]
) -> tuple[str, str, dict[int, str]]:
    """The pieces as one formula, or one text: the Typst code of their joined LaTeX
    (`convert`: mitex's conversion of LaTeX math, or of LaTeX text); its skeleton, the same
    code with each piece that stands on its own (a `hole`) a private-use character; and each
    hole's code. The holes are converted on their own, in the joined LaTeX's skeleton, and the
    skeleton with their code in place is checked to be what the whole converts to: telling
    the pieces apart never changes the code."""
    whole = convert(separator.join(pieces))
    holes: dict[int, str] = {}
    for i, piece in enumerate(pieces):
        if not _balanced(piece) or piece.lstrip()[:1] in ("^", "_", "'", ""):
            continue  # a fragment, or an attachment to what comes before
        try:
            holes[i] = convert(piece)
        except TypstError:
            continue
    apart = ValueError(f"cannot tell these parts apart: {pieces}")
    try:
        skeleton = convert(
            separator.join(
                chr(_HOLE + i) if i in holes else p for i, p in enumerate(pieces)
            )
        )
    except TypstError as error:  # a hole within what converts only whole (math in text)
        raise apart from error
    found = [ord(c) - _HOLE for c in skeleton if _HOLE <= ord(c) < _HOLE + len(pieces)]
    plain = _fill(skeleton, holes)
    if found != sorted(holes) or "".join(plain.split()) != "".join(whole.split()):
        raise apart
    return whole, skeleton, holes


def _fill(skeleton: str, holes: Mapping[int, str]) -> str:
    """The skeleton with each hole's code (or what stands for it) in its place."""
    for i, code in holes.items():
        skeleton = skeleton.replace(chr(_HOLE + i), code)
    return skeleton


def _in_place(skeleton: str, holes: Mapping[int, str]) -> dict[int, str]:
    """Each hole's markup as it reads in the whole. Typst reads a line's first characters
    apart (`- `, `+ `, `= ` and `/ ` begin a list's item, an enumeration's, a heading, a
    term), so a hole that goes on with a line is read after an empty expression, which
    keeps it on the line."""
    read = {}
    for i, code in holes.items():
        before = _fill(skeleton[: skeleton.index(chr(_HOLE + i))], holes)
        read[i] = f"#none;{code}" if before.rsplit("\n", 1)[-1].strip() else code
    return read


_MITEX = 'mode: "math", scope: mitex-scope'
_MARKUP = 'mode: "markup", scope: mitex-scope'


def _math(latex: str) -> str:
    converted = typst_string(_engine.mitex_math(latex))
    return f"eval({converted}, {_MITEX})"


def _text(latex: str) -> str:
    return _markup(_engine.mitex_text(latex))


def _markup(code: str, scope: str = "") -> str:
    """Typst markup (mitex's conversion of LaTeX text) as an expression of its content, in
    mitex's scope and, after it, the bindings `scope` lists ("name: value, ")."""
    within = f"mitex-scope + ({scope})" if scope else "mitex-scope"
    return f'eval({typst_string(code)}, mode: "markup", scope: {within})'


def _bindings(codes: Mapping[int, str]) -> tuple[str, dict[int, int]]:
    """Typst code binding each string's content (its markup, evaluated) to its name, `p{i}`;
    and where in that code each string's markup starts, in bytes, which every glyph the
    markup draws comes from."""
    out, starts, at = [], {}, 0
    for i, code in codes.items():
        head = f"#let p{i} = eval("
        starts[at + len(head.encode())] = i
        binding = f"{head}{typst_string(code)}, {_MARKUP});"
        out.append(binding)
        at += len(binding.encode())
    return "".join(out), starts


def _same(a: Layout, b: Layout) -> bool:
    """Whether two layouts draw the same: the same items, placed and painted alike, wherever
    in the code they came from."""
    return (
        np.array_equal(a.rows[:, : NODE.start], b.rows[:, : NODE.start])
        and len(a.shapes) == len(b.shapes)
        and all(np.array_equal(p, q) for p, q in zip(a.shapes, b.shapes))
    )


@deprecated("use MathTex", category=None)
class SingleStringMathTex(Typst):
    r"""One LaTeX formula, typeset in the engine, whose parts are its glyphs: white
    unless styled.

    The LaTeX is converted to Typst as a [MathTex][manimgx.MathTex]'s is, and set in
    display style; the parts are not grouped by strings, so `formula[i]` is its i-th
    glyph (or shape, such as a fraction's bar), in the order Typst sets them.

    Args:
        tex_string: The formula, in LaTeX.
        organize_left_to_right: Whether to order the parts by their centers, from left
            to right, rather than as Typst sets them.
        tex_environment: Any environment (the default, "align*") sets the string as
            math; None as LaTeX text, math between `$` signs.

    Examples:
        ```python
        import manimgx as m


        class SingleStringMathTexExample(m.Scene):
            def construct(self) -> None:
                formula = m.SingleStringMathTex(r"e^{i\pi} + 1 = 0", font_size=144)
                formula[1:3].set_color(m.YELLOW)
                self.add(formula, m.index_labels(formula, label_height=0.3))
        ```
    """

    @prototype
    def __init__(
        self,
        tex_string: str,
        organize_left_to_right: bool = False,
        tex_environment: str | None = "align*",
        **kwargs: Unpack[TypstOptions],
    ) -> None:
        self.tex_string = tex_string = str(tex_string)
        """The LaTeX the formula was typeset from."""
        self.tex_environment = tex_environment
        body = (
            f"$ #{_math(tex_string)} $" if tex_environment else f"#{_text(tex_string)}"
        )
        kwargs["typst_preamble"] = _IMPORT + kwargs.get("typst_preamble", "")
        super().__init__(body, **kwargs)
        if organize_left_to_right:
            self.submobjects.sort(key=lambda m: m.get_x())


class MathTexPart(VGroup):
    """One of a [MathTex][manimgx.MathTex]'s parts: the glyphs one of its strings adds
    to the formula, as a group that knows the string.

    Args:
        tex_string: The LaTeX it was typeset from.
        *members: Its glyphs.
    """

    def __init__(self, tex_string: str, *members: Mobject) -> None:
        super().__init__(*members)
        self.tex_string = tex_string
        """The LaTeX the part was typeset from."""


class MathTexOptions(_TypstOptions, total=False, closed=True):
    """[MathTex][manimgx.MathTex]'s keywords, for the classes that pass them on:
    [Tex][manimgx.Tex], [BulletedList][manimgx.BulletedList], [Title][manimgx.Title] and
    labels.

    Beyond these, they take the
    [Typst keywords][manimgx.mobjects.text.TypstOptions].
    """

    arg_separator: str
    """What joins the strings into `tex_string`, the formula a MathTex is typeset as,
    or the text a Tex is (default " "; "" for a Tex)."""
    substrings_to_isolate: Iterable[str] | None
    """Substrings to make parts of their own: each string is split around every
    occurrence of each (default None)."""
    tex_to_color_map: Mapping[str, ParsableManimColor] | None
    """A color for each substring, which is made a part of its own, as
    `substrings_to_isolate` makes it, and colored (default None)."""
    tex_environment: str | None
    """How the strings are read: with a name containing "align" ("align*", a MathTex's
    default), as math; with any other ("center", a Tex's default, which also centers the
    lines), or None, as LaTeX text, math between `$` signs."""


class MathTex(Typst):
    r"""LaTeX math, typeset in the engine, a part per string: `MathTex("a^2", "+",
    "b^2")[2]` is the $b^2$, to color, move or match with another formula.

    There is no LaTeX installation: the LaTeX is converted to Typst (by mitex, part of
    the engine) and typeset in display style, in New Computer Modern Math, white unless
    styled. Most of LaTeX's math converts: fractions, roots, sums and integrals,
    matrices (`pmatrix`, `bmatrix`, `array`), `cases` and `aligned`, accents, `\mathbb`
    and the other alphabets, `\text`, `\left` and `\right`, `\color`, `\newcommand`.
    Packages don't — `\usepackage` and their commands, such as `\ce` or `\SI` — nor does
    `\def`: a command mitex doesn't know raises a
    [TypstError][manimgx.drawing.typesetting.TypstError].

    The strings are one formula, joined by `arg_separator` and typeset whole, so parting
    a formula moves none of its glyphs. Each string is a part, a
    [MathTexPart][manimgx.MathTexPart] of the glyphs it adds, and double braces set a
    part apart within a string: `MathTex("{{a^2}} + {{b^2}} = {{c^2}}")` has the five
    parts of the first example below. A string that stands on its own (its braces,
    environments and `\left`…`\right` closed within it) holds exactly its glyphs. The
    rest, such as a fraction's bar or the glyphs of a fragment like `"^2"`, go to the
    first fragment between the standing strings around them: in
    `MathTex(r"\frac{", "a", "}{", "b", "}")` the bar is the closing `"}"`'s, where TeX
    draws it, and in `MathTex(r"e^{i", r"\pi}")`, split inside a term, every glyph is
    the first part's. A formula whose parts can't be told apart raises ValueError.

    `substrings_to_isolate` and `tex_to_color_map` split the strings further;
    [set_color_by_tex][manimgx.MathTex.set_color_by_tex] and
    [get_part_by_tex][manimgx.MathTex.get_part_by_tex] find parts by their LaTeX, and
    [TransformMatchingTex][manimgx.TransformMatchingTex] moves each part to the part
    written the same way in another formula. Read as text (see [Tex][manimgx.Tex]), the
    strings are one text in the same way, spaces and all.

    Args:
        *tex_strings: The formula, in LaTeX: a string per part (a number is written as
            a string), and a part per `{{…}}` within one.
        arg_separator: What joins the strings into `tex_string`, the formula (or text)
            they are typeset as.
        substrings_to_isolate: Substrings to make parts of their own: each string is
            split around every occurrence of each.
        tex_to_color_map: A color for each substring, which is made a part of its own
            and colored.
        tex_environment: How the strings are read: with a name containing "align" (the
            default, "align*"), as math; with any other, or None, as LaTeX text, math
            between `$` signs.

    Examples:
        ```python
        import manimgx as m


        class MathTexExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=144)
                formula[0].set_color(m.BLUE)
                formula[2].set_color(m.GREEN)
                formula[4].set_color(m.YELLOW)
                self.play(m.Write(formula))
        ```

        ```python
        import manimgx as m


        class MathTexLatexExample(m.Scene):
            def construct(self) -> None:
                limit = r"\lim_{n \to \infty} \left(1 + \frac{1}{n}\right)^n = e"
                formulas = m.VGroup(
                    m.MathTex(r"\int_0^1 x^2 \, dx = \frac{1}{3}"),
                    m.MathTex(r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}"),
                    m.MathTex(limit),
                    m.MathTex(r"\sum_{n=1}^\infty \frac{1}{n^2} = \frac{\pi^2}{6}"),
                )
                self.add(formulas.arrange_in_grid(rows=2, buff=1).scale(1.3))
        ```
    """

    @prototype
    def __init__(
        self,
        *tex_strings: str | float,
        arg_separator: str = " ",
        substrings_to_isolate: Iterable[str] | None = None,
        tex_to_color_map: Mapping[str, ParsableManimColor] | None = None,
        tex_environment: str | None = "align*",
        **kwargs: Unpack[TypstOptions],
    ) -> None:
        self.tex_to_color_map = dict(tex_to_color_map or {})
        isolate = list(substrings_to_isolate or []) + list(self.tex_to_color_map)
        math = bool(tex_environment and "align" in tex_environment)
        strings = _isolate_braces([str(s) for s in tex_strings], math)
        self.tex_strings = (
            [p for s in strings for p in _split(s, isolate, math)]
            if isolate
            else strings
        )
        """The strings, a part's each: the arguments, split at `{{…}}` and around the
        isolated substrings."""
        self.arg_separator = arg_separator
        self.tex_string = arg_separator.join(self.tex_strings)
        """The LaTeX of the whole formula, or text: the strings, joined by
        `arg_separator`."""
        self.tex_environment = tex_environment
        preamble = f"{_IMPORT}{_MANIMGRP}\n" if math else _IMPORT
        kwargs["typst_preamble"] = preamble + kwargs.get("typst_preamble", "")

        def layout(source: str) -> Layout:
            return typeset(
                source,
                kwargs["typst_preamble"],
                font_paths=kwargs.get("font_paths"),
                package_path=kwargs.get("package_path"),
            )

        if not math:
            body, starts, whole = self._compose(self.tex_strings, arg_separator)
            owners: dict[int, int] = {}
            if len(self.tex_strings) > 1 and starts:  # which string drew each item
                apart = ValueError(f"cannot tell these parts apart: {self.tex_strings}")
                reference = None if whole is None else layout(whole)
                try:
                    drawn = layout(body)
                except TypstError as error:  # the text is fine, its parting is not
                    if reference is None:
                        raise
                    raise apart from error
                if reference is not None and not _same(drawn, reference):
                    raise apart
                owners = self._owners(drawn, starts)
            super().__init__(body, **kwargs)
            self._regroup(owners, set(starts.values()))
        elif len(self.tex_strings) > 1:  # one formula, its parts told apart
            _, skeleton, holes = _one_formula(
                self.tex_strings, arg_separator, _engine.mitex_math
            )
            plain = typst_string(_fill(skeleton, holes))
            super().__init__(f"$ #eval({plain}, {_MITEX}) $", **kwargs)
            boxed = _fill(
                skeleton,
                {i: f'#manimgrp("p{i}", ${code}$)' for i, code in holes.items()},
            )
            self._regroup_by_twin(
                layout(
                    f"$ #eval({typst_string(boxed)}, {_MITEX} + (manimgrp: manimgrp)) $"
                ),
                set(holes),
            )
        else:  # a part's box would drop to text style; keep display style
            parts = " ".join(
                f'#manimgrp("p{i}", $display(#{_math(_standalone(s))})$)'
                for i, s in enumerate(self.tex_strings)
            )
            super().__init__(f"$ {parts} $", **kwargs)
            self._regroup_by_labels()
        for tex, c in self.tex_to_color_map.items():
            self.set_color_by_tex(tex, c)

    def _compose(
        self, strings: list[str], separator: str
    ) -> tuple[str, dict[int, int], str | None]:
        """The strings as one text, joined by `separator`, set as the document sets it (see
        `_set`): the document's body; where in it the code of each string that stands on its
        own (a hole, see `_one_formula`) starts, and the string's index; and the whole as one
        text, which the body must draw exactly (None if no string is told apart).

        Each hole's code is evaluated on its own and bound to a name, which the code of the
        joined text calls in the hole's place, so every glyph comes from the code of the
        string that drew it, and Typst shapes the text across them as it shapes the whole.
        """
        if len(strings) < 2:  # nothing to tell apart
            return self._set(_text(separator.join(strings))), {}, None
        whole, skeleton, holes = _one_formula(strings, separator, _engine.mitex_text)
        if not holes:
            return self._set(_markup(whole)), {}, None
        bindings, starts = _bindings(_in_place(skeleton, holes))
        called = _fill(skeleton, {i: f"#p{i};" for i in holes})
        text = _markup(called, "".join(f"p{i}: p{i}, " for i in holes))
        return bindings + self._set(text), starts, self._set(_markup(whole))

    def _set(self, text: str) -> str:
        """The text (a Typst expression of its content) as the document sets it: centered
        in the "center" environment."""
        if self.tex_environment == "center":
            return f"#align(center)[#{text}]"
        return f"#{text}"

    def _owners(self, layout: Layout, starts: Mapping[int, int]) -> dict[int, int]:
        """The string each item of the layout came from, if it came from a string's code
        (where it starts in the body, `starts`): a glyph or shape the code drew, or one
        drawn within an element of it (a radical within an equation)."""
        nodes = (layout.rows[:, NODE.start].astype(np.int64) - layout.body).tolist()
        return {k: starts[node] for k, node in enumerate(nodes) if node in starts}

    def _regroup(self, owners: Mapping[int, int], holes: Collection[int]) -> None:
        """The parts: each string's own items (`owners`, the item's index to the string's),
        and every other item to the first string that is not a hole between the strings
        whose items are around it; else to the one before (the first, before any)."""
        count, leaves = len(self.tex_strings), list(self.submobjects)
        if not count:
            return
        groups: list[list[Mobject]] = [[] for _ in range(count)]
        start, before = 0, -1
        for k in range(len(leaves) + 1):
            owner = count if k == len(leaves) else owners.get(k)
            if owner is None:
                continue
            if start < k:  # this run lies between the same two strings' items
                fragment = next(
                    (i for i in range(before + 1, owner) if i not in holes),
                    max(before, 0),
                )
                groups[fragment].extend(leaves[start:k])
            if k < len(leaves):
                groups[owner].append(leaves[k])
            start, before = k + 1, owner
        self.submobjects = [
            MathTexPart(s, *members)
            for s, members in zip(self.tex_strings, groups, strict=True)
        ]

    def _regroup_by_labels(self) -> None:
        groups: list[Mobject] = []
        for i, s in enumerate(self.tex_strings):
            members = self.labels.get(f"p{i}", VGroup())
            groups.append(MathTexPart(s, *members))
        if any(len(g) for g in groups):
            self.submobjects = groups

    def _regroup_by_twin(self, twin: Layout, holes: set[int]) -> None:
        """Parts from the formula's boxed twin, which draws what the formula draws in the same
        order: a hole's glyphs and shapes are labelled; the rest belong to the piece between
        the holes around them (the first, if several are)."""
        rows, leaves = twin.rows, self.submobjects
        if len(rows) != len(leaves) or any(
            (row[KIND] == GLYPH) != isinstance(leaf, TypstGlyph)
            for row, leaf in zip(rows, leaves, strict=True)
        ):
            raise ValueError(f"cannot tell these parts apart: {self.tex_strings}")
        labelled = {
            row: int(label[1:])
            for label, members in twin.labels
            if label.startswith("p") and label[1:].isdigit()
            for row in members
        }
        self._regroup(labelled, holes)

    def get_parts_by_tex(
        self, tex: str, substring: bool = True, case_sensitive: bool = True
    ) -> VGroup:
        """Find the parts whose LaTeX contains `tex`, or is it.

        Args:
            tex: The LaTeX to look for.
            substring: Whether a part whose LaTeX contains `tex` matches; if not, only
                one whose LaTeX is `tex`.
            case_sensitive: Whether upper and lower case differ.

        Returns:
            A new group of the parts themselves, in order.
        """

        def match(s: str) -> bool:
            a, b = (tex, s) if case_sensitive else (tex.lower(), s.lower())
            return a in b if substring else a == b

        return VGroup(
            *(
                m
                for m in self.submobjects
                if isinstance(m, MathTexPart) and match(m.tex_string)
            )
        )

    def get_part_by_tex(
        self, tex: str, substring: bool = True, case_sensitive: bool = True
    ) -> Mobject | None:
        r"""Find the first part whose LaTeX contains `tex`, or is it.

        Args:
            tex: The LaTeX to look for.
            substring: Whether a part whose LaTeX contains `tex` matches; if not, only
                one whose LaTeX is `tex`.
            case_sensitive: Whether upper and lower case differ.

        Returns:
            The part itself, or None if none matches.

        Examples:
            ```python
            import manimgx as m


            class MathTexGetPartByTexExample(m.Scene):
                def construct(self) -> None:
                    formula = m.MathTex(
                        r"\sin^2\theta", "+", r"\cos^2\theta", "=", "1", font_size=120
                    )
                    self.add(formula)
                    self.play(m.Indicate(formula.get_part_by_tex(r"\cos")))
            ```
        """
        parts = self.get_parts_by_tex(tex, substring, case_sensitive)
        return parts[0] if len(parts) else None

    def index_of_part(self, part: Mobject) -> int:
        """Find where a part is among the formula's parts; a mobject that is not one
        raises ValueError.

        Args:
            part: One of the parts.

        Returns:
            Its index, from 0.
        """
        return self.submobjects.index(part)

    def set_color_by_tex(
        self,
        tex: str,
        color: ParsableManimColor,
        substring: bool = True,
        case_sensitive: bool = True,
    ) -> Self:
        """Color the parts whose LaTeX contains `tex`, or is it.

        Args:
            tex: The LaTeX to look for.
            color: Their color.
            substring: Whether a part whose LaTeX contains `tex` matches; if not, only
                one whose LaTeX is `tex`.
            case_sensitive: Whether upper and lower case differ.

        Examples:
            ```python
            import manimgx as m


            class MathTexSetColorByTexExample(m.Scene):
                def construct(self) -> None:
                    formula = m.MathTex(
                        "x + y = y + x", substrings_to_isolate=["x", "y"], font_size=144
                    )
                    formula.set_color_by_tex("x", m.YELLOW)
                    formula.set_color_by_tex("y", m.BLUE)
                    self.add(formula)
            ```
        """
        for part in self.get_parts_by_tex(tex, substring, case_sensitive):
            part.set_color(color)
        return self

    def set_color_by_tex_to_color_map(
        self,
        texs_to_color_map: Mapping[str, ParsableManimColor],
        substring: bool = True,
        case_sensitive: bool = True,
    ) -> Self:
        """Color parts by their LaTeX: for each entry, the parts whose LaTeX contains
        it, or is it.

        Args:
            texs_to_color_map: A color for each piece of LaTeX, applied in order.
            substring: Whether a part whose LaTeX contains a piece matches; if not, only
                one whose LaTeX is the piece.
            case_sensitive: Whether upper and lower case differ.
        """
        for tex, color in texs_to_color_map.items():
            self.set_color_by_tex(tex, color, substring, case_sensitive)
        return self


def _split(s: str, isolate: list[str], math: bool) -> list[str]:
    """The string split around each isolated substring; in math, where spaces mean
    nothing, without the parts that are only spaces."""
    parts = [s]
    for sub in sorted(isolate, key=len, reverse=True):
        out: list[str] = []
        for p in parts:
            if p in isolate:
                out.append(p)
                continue
            pieces = p.split(sub)
            for k, piece in enumerate(pieces):
                if piece:
                    out.append(piece)
                if k < len(pieces) - 1:
                    out.append(sub)
        parts = out
    return [p for p in parts if (p.strip() if math else p)]


class Tex(MathTex):
    r"""LaTeX text, typeset in the engine and centered, a part per string: math goes
    between `$` signs.

    It is a [MathTex][manimgx.MathTex] that reads its strings as LaTeX text: bold
    (`\textbf`), italics (`\emph`, `\textit`), line breaks (`\\`) and inline math
    convert. The text is set in New Computer Modern, as LaTeX sets it, the math in New
    Computer Modern Math; white unless styled. The strings are one text, joined by
    `arg_separator` (nothing, by default) and typeset whole, as a MathTex's are one
    formula: `Tex("Fade", "In")` reads "FadeIn", and parting a text moves none of its
    glyphs. Its parts are told apart as a formula's are; a ligature two strings share is
    the first's.

    Args:
        *tex_strings: The text, in LaTeX: a string per part.
        **kwargs: [MathTex keywords][manimgx.MathTex]:
            the strings are joined by "" and read in a "center" environment unless
            `arg_separator` and `tex_environment` say otherwise.

    Examples:
        ```python
        import manimgx as m


        class TexExample(m.Scene):
            def construct(self) -> None:
                text = m.Tex(
                    r"\textbf{Bold}, \emph{emphasized},\\ and math: $e^{i\pi} = -1$",
                    font_size=96,
                )
                self.play(m.Write(text))
        ```
    """

    def __init__(
        self, *tex_strings: str | float, **kwargs: Unpack[MathTexOptions]
    ) -> None:
        kwargs.setdefault("arg_separator", "")
        kwargs.setdefault("tex_environment", "center")
        super().__init__(*tex_strings, **kwargs)


_BULLET = "bullet"


class BulletedList(Tex):
    r"""A bulleted list: an item per line, each after a bullet, lined up on the left.

    Typst sets the items as a list: each bullet is a centered dot (LaTeX's `\cdot` at
    twice its size), `SMALL_BUFF` from its item, and the items are `buff` apart, in
    scene units at the list's font size. Each item is LaTeX text (math between `$`
    signs) and a part of its own, its bullet first: `items[1]` is the second item.
    `height` and `width` scale the list as set.

    Args:
        *items: The items, in LaTeX.
        buff: The space between items, in scene units.

    Examples:
        ```python
        import manimgx as m


        class BulletedListExample(m.Scene):
            def construct(self) -> None:
                items = m.BulletedList(
                    "Typeset in the engine",
                    "No LaTeX installation",
                    r"Math too: $a^2 + b^2 = c^2$",
                    font_size=72,
                )
                self.add(items)
                self.play(items.animate.fade_all_but(1))
        ```
    """

    # the list's lengths are a set rule of the preamble, so part of what a construction
    # is keyed by; the bullet is CE's (dot_scale_factor 2), and so is the structure

    def __init__(
        self,
        *items: str,
        buff: float = MED_LARGE_BUFF,
        **kwargs: Unpack[MathTexOptions],
    ) -> None:
        self.buff = buff
        pt = 1 / (
            kwargs.get("font_size", DEFAULT_FONT_SIZE) * SCALE_FACTOR_PER_FONT_POINT
        )
        kwargs["typst_preamble"] = (
            f"#set list(marker: [#box(scale(200%, $dot.c$))<{_BULLET}>], indent: 0pt,"
            f" body-indent: {SMALL_BUFF * pt}pt, spacing: {buff * pt}pt)\n"
            + kwargs.get("typst_preamble", "")
        )
        kwargs.setdefault("tex_environment", None)
        super().__init__(*items, **kwargs)

    def _compose(
        self, strings: list[str], separator: str
    ) -> tuple[str, dict[int, int], str | None]:
        """The items as a Typst list, each item's code bound to its name, as a Tex binds a
        string's (see `MathTex._compose`): every glyph comes from its item's code."""
        codes = {i: _engine.mitex_text(s) for i, s in enumerate(strings)}
        bindings, starts = _bindings(codes)
        items = ", ".join(f"p{i}" for i in codes)
        return f"{bindings}#list({items})", starts, None

    def _owners(self, layout: Layout, starts: Mapping[int, int]) -> dict[int, int]:
        """Each item's glyphs, and its bullet: one glyph, in its own labelled box, the
        items' bullets in their order."""
        owners = super()._owners(layout, starts)
        bullets = (rows for label, rows in layout.labels if label == _BULLET)
        for item, rows in enumerate(bullets):
            owners |= dict.fromkeys(rows, item)
        return owners

    def fade_all_but(self, index: int, opacity: float = 0.5) -> Self:
        """Fade every item but one: the others' fill to `opacity`, the one's to 1.

        Args:
            index: The item's index, from 0.
            opacity: The other items' fill opacity, from 0 to 1.
        """
        part = self.submobjects[index]
        for other in self.submobjects:
            other.set_fill(opacity=1 if other is part else opacity)
        return self


class Title(Tex):
    """A title: LaTeX text at the top of the frame, over a line across it.

    The line is the last part, and the title's `underline`; a `color` colors it with
    the text, as [set_color][manimgx.Mobject.set_color] would.

    Args:
        *text_parts: The title, in LaTeX: a string per part.
        include_underline: Whether a line is drawn under the title.
        match_underline_width_to_text: Whether the line is as wide as the title; if
            not, it spans the frame but 1 unit at each side.
        underline_buff: The gap between the title and the line, in scene units.

    Examples:
        ```python
        import manimgx as m


        class TitleExample(m.Scene):
            def construct(self) -> None:
                title = m.Title(r"The Pythagorean theorem: $a^2 + b^2 = c^2$")
                self.play(m.Write(title))
        ```
    """

    def __init__(
        self,
        *text_parts: str,
        include_underline: bool = True,
        match_underline_width_to_text: bool = False,
        underline_buff: float = MED_SMALL_BUFF,
        **kwargs: Unpack[MathTexOptions],
    ) -> None:
        from manimgx.config import config
        from manimgx.constants import DOWN, LEFT, RIGHT, UP
        from manimgx.mobjects.shapes import Line

        super().__init__(*text_parts, **kwargs)
        self.to_edge(UP)
        if include_underline:
            underline = Line(LEFT, RIGHT).next_to(self, DOWN, buff=underline_buff)
            underline.width = (
                self.width if match_underline_width_to_text else config.frame_width - 2
            )
            color = kwargs.get("color")
            if color is not None:  # color= colors the whole title, as set_color does
                underline.set_color(color)
            self.add(underline)
            self.underline = underline
            """The line under the title, its last part (a title made without one has
            none)."""

"""Typst source → its layout, typeset in this process (`_engine.typeset`) and cached on disk.
A layout is one row per item (glyph or shape) in document order, each shape's curves, and each
labelled group's items; the layout owns each glyph's immutable outline and carets."""

import functools
import os
import pickle
import tempfile
from dataclasses import dataclass
from importlib.resources import files
from importlib.util import find_spec
from pathlib import Path

import numpy as np

from manimgx import _engine
from manimgx.caches import Memo, forgets
from manimgx.drawing.geometry import Shape

# The fonts ManimGX ships, its font packages' (Noto): with Typst's own, every face a document is
# set in or falls back to, so text is the same on every machine; a system font only by name. The
# CJK one is not installed in the browser
FONTS = tuple(
    str(files(package))
    for package in ("manimgx_fonts", "manimgx_fonts_cjk")
    if find_spec(package) is not None
)
TYPST_COMPILATION_FONT_SIZE = 10
TYPST_TEMPLATE = (
    "#set page(width: auto, height: auto, margin: 0pt, fill: none)\n#set text(size:"
    " {text_size}pt)\n{preamble}\n"
)
TypstError = _engine.TypstError
"""The error raised when Typst can't typeset a document, or LaTeX can't be converted to
Typst: its message is Typst's (or mitex's), each error with the bytes of the source it
is at, counted from the start of the whole document typeset — a page setup and the
preamble come before the code."""

# a row's columns (see rust/engine/src/typeset.rs): an item's origin is its source node (start,
# end; its own, else the innermost element around it from the source) and the bytes of the
# node's text a glyph's cluster draws (start, end)
KIND, KEY, PLACEMENT, FILL, STROKE, WIDTH, ADVANCE, NODE, DRAWN = (
    0,
    1,
    slice(2, 8),
    slice(8, 12),
    slice(12, 16),
    16,
    17,
    slice(18, 20),
    slice(20, 22),
)
ROW = 23
GLYPH, SHAPE = 0.0, 1.0


type Glyph = tuple[int, Shape | None, bytes]


@dataclass(frozen=True, slots=True)
class Layout:
    """A typeset drawing: `rows` (n × ROW, glyphs with outlines and shapes), `shapes`
    (cubic points, y up), `labels` (a label and its rows, including empty groups),
    `body` (where the body starts in the source, in bytes), and `glyphs` (the
    immutable outline and caret records its rows name)."""

    rows: np.ndarray
    shapes: list[np.ndarray]
    labels: list[tuple[str, list[int]]]
    body: int
    glyphs: dict[int, Glyph]


# Reuse under disjoint native (<2^48) or content (>=2^52) keys. The bound counts
# aliases; either can be forgotten independently. Live layouts own their records.
_GLYPHS: Memo[int, Glyph] = Memo(1 << 12)
_CACHE = (
    Path(directory) / "layouts"
    if (directory := _engine.cache_directory()) is not None
    else None
)
# what made a layout, part of its key: the entry's format, and the engine's own file (a rebuilt
# engine never reads a layout an older one made)
_ENGINE = Path(_engine.__file__).stat()
_VERSION = f"layout 4, engine {_ENGINE.st_size} {_ENGINE.st_mtime_ns}".encode()
_CONTENT = 1 << 52  # glyph keys by content: exact in float64, apart from the engine's
type Stored = tuple[
    np.ndarray,
    list[np.ndarray],
    list[tuple[str, list[int]]],
    int,
    dict[int, tuple[bytes, bytes]],
]


def typst_string(text: str) -> str:
    """Write `text` as a Typst string literal, which Typst reads back as exactly `text`.

    Args:
        text: Any text.

    Returns:
        The literal, its quotes included.
    """
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def typeset(
    body: str,
    preamble: str = "",
    text_size: float = TYPST_COMPILATION_FONT_SIZE,
    font_paths: list[str | Path] | None = None,
    package_path: str | Path | None = None,
) -> Layout:
    """Typeset a Typst document, and read its layout off Typst's frames.

    The document is set in the fonts ManimGX ships (Typst's own and the Noto faces),
    after those in `font_paths`; a system font is read only for a family the document
    names that none of them has. A layout is kept in the current user's cache directory
    (the browser's private filesystem in a page): the same document, with the same fonts
    and packages, is read back, not typeset again, in any process.

    Args:
        body: The document's body: Typst markup.
        preamble: Typst code set before the body.
        text_size: The text's size, in points.
        font_paths: Directories of font files, searched, with their subdirectories,
            before the fonts ManimGX ships.
        package_path: The directory Typst packages are imported from, besides mitex
            (the engine's); None for none but mitex.
    """
    prefix = TYPST_TEMPLATE.format(text_size=text_size, preamble=preamble)
    source = prefix + body + "\n"
    fonts = (*(str(p) for p in font_paths or ()), *FONTS)
    packages = None if package_path is None else str(package_path)
    depends = _files(fonts if packages is None else (*fonts, packages))
    key = _engine.digest(_VERSION, b"\0", source.encode(), b"\0", depends)
    path = None if _CACHE is None else _CACHE / f"{key:016x}.layout"
    stored = None if path is None else _read(path)
    if stored is None:
        stored = _typeset(source, fonts, packages, int.from_bytes(depends, "little"))
        if path is not None:
            _write(path, stored)
    rows, shapes, labels, _, glyphs = stored
    records = {
        key: _glyph(key, points, carets) for key, (points, carets) in glyphs.items()
    }
    return Layout(rows, shapes, labels, len(prefix.encode()), records)


def _glyph(key: int, points: bytes, carets: bytes) -> Glyph:
    """Decode one immutable record, reusing it while remembered."""
    record = _GLYPHS.get(key)
    if record is None:
        array = np.frombuffer(points).reshape(-1, 3)
        record = _GLYPHS.keep(
            key, (key, Shape(array.copy()) if len(array) else None, carets)
        )
    return record


@forgets
@functools.cache
def _files(paths: tuple[str, ...]) -> bytes:
    """The files a layout depends on besides its source (fonts, packages), as paths, sizes and
    times, once per process."""
    found = []
    for root in map(Path, paths):
        found.append(f"{root}\0".encode())
        within = sorted(root.rglob("*")) if root.is_dir() else [root]
        for file in within:
            if file.is_file():
                stat = file.stat()
                found.append(f"{file}\0{stat.st_size}\0{stat.st_mtime_ns}\0".encode())
    return _engine.digest(*found).to_bytes(8, "little")


def _read(path: Path) -> Stored | None:
    """A stored layout, if there is one and the fonts it was set with haven't changed."""
    try:
        stored: Stored = pickle.loads(path.read_bytes())
    except (OSError, pickle.UnpicklingError, EOFError, ValueError):
        return None
    system = stored[3]
    if system and system != _engine.system_fonts_fingerprint():
        return None
    return stored


def _write(path: Path, stored: Stored) -> None:
    """Store a layout: written whole, then renamed, so a reader never sees half of one."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=path.parent) as own:
            partial = Path(own) / "layout"
            partial.write_bytes(pickle.dumps(stored, protocol=5))
            os.replace(partial, path)
    except OSError:
        pass


def _typeset(
    source: str, fonts: tuple[str, ...], packages: str | None, revision: int
) -> Stored:
    """Typeset with Typst; every glyph's key by content, with its outline and carets along."""
    raw, shapes, labels, system = _engine.typeset(
        source, fonts, packages, revision=revision
    )
    rows = np.frombuffer(raw).reshape(-1, ROW).copy()
    glyphs = rows[:, KIND] == GLYPH
    keys = rows[glyphs, KEY].astype(np.int64).tolist()
    held = {k: record for k in set(keys) if (record := _GLYPHS.get(k)) is not None}
    new = sorted(set(keys) - held.keys())
    for k, data in zip(new, _engine.glyph_outlines(new)):
        carets = np.array(_engine.ligature_carets(k), dtype="<f8").tobytes()
        content = _CONTENT | (
            _engine.digest(
                len(data).to_bytes(8, "little"),
                data,
                carets,
            )
            & (_CONTENT - 1)
        )
        held[k] = _GLYPHS.keep(k, _glyph(content, data, carets))
    records = {record[0]: record for record in held.values()}
    rows[glyphs, KEY] = [held[k][0] for k in keys]
    drawn = [
        i
        for i, row in enumerate(rows)
        if row[KIND] != GLYPH or records[int(row[KEY])][1] is not None
    ]
    if len(drawn) != len(rows):
        row_of = {old: new for new, old in enumerate(drawn)}
        rows = rows[drawn]
        labels = [
            (label, [row_of[i] for i in members if i in row_of])
            for label, members in labels
        ]
    glyphs = {
        key: (b"" if shape is None else shape.array.tobytes(), carets)
        for key, shape, carets in records.values()
    }
    return (
        rows,
        [np.frombuffer(s).reshape(-1, 3) for s in shapes],
        labels,
        _engine.system_fonts_fingerprint() if system else 0,
        glyphs,
    )

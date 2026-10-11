"""A document is the same however it was set, and what it holds is its own.

- Set with nothing remembered and no layout on disk, read back from disk, set warm (a copy of
  what was made, or made anew with its glyphs remembered), or set while the glyph memo keeps one
  record at a time, a document draws the same, its groups (its labels, a paragraph's whole text)
  name the same parts, its own, and its glyphs keep their keys and cut the same; so do its copy,
  saved state and target once everything is forgotten, and with their glyphs' keys reassigned.
  A document on disk is read, not set again, and what the engine answered can change afterwards
  without changing a document.
- A glyph cuts at its font's carets, else into equal parts of its advance. (No font ManimGX ships
  has carets: a made-up font has them.)
- Documents share the glyphs they remember: one outline each; cutting and painting one leaves
  the others as they were, and a cut glyph lets its uncut outline go.
- A glyph without an outline is no part, and labels lose it; a paragraph's blank lines are
  empty lines.
- Text is set in the fonts ManimGX ships, the same on every machine: every script finds a face
  there (no .notdef glyph), and a system font is read only for a family a text names.
"""

import gc
import json
import os
import pickle
import re
import shutil
import struct
import subprocess
import sys
import weakref
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import ClassVar, NamedTuple

import numpy as np
import pytest
from tests.oracles import look

import manimgx as m
from manimgx import _engine, caches
from manimgx.drawing import typesetting as tc
from manimgx.drawing.geometry import Shape
from manimgx.mobject import _PROTOTYPES
from manimgx.mobjects.text import TypstGlyph, _cut

type Document = m.Typst | m.Paragraph
type Answer = tuple[bytes, list[bytes], list[tuple[str, list[int]]], bool]


@pytest.mark.parametrize("coordinate", [None, -123, 456])
def test_optional_font_caret_coordinate_is_checked(
    tmp_path: Path, coordinate: int | None
) -> None:
    font = next(
        p for p in Path(tc.FONTS[0]).glob("*.ttf") if p.name.startswith("NotoSans[")
    )
    source = '#set text(font: "Noto Sans")\nA'
    rows, _, _, _ = _engine.typeset(source, [str(font.parent)])
    glyph = int(np.frombuffer(rows).reshape(-1, tc.ROW)[0, tc.KEY]) % 65536
    # A complete font with one optional format-1 caret. Only its coordinate is
    # truncated; the font still loads and shapes normally through the real engine.
    table = struct.pack(">15H", 1, 0, 0, 0, 12, 0, 6, 1, 12, 1, 1, glyph, 1, 4, 1)
    if coordinate is not None:
        table += struct.pack(">h", coordinate)
    data = bytearray(font.read_bytes())
    count = struct.unpack_from(">H", data, 4)[0]
    slot = next(
        12 + 16 * i for i in range(count) if data[12 + 16 * i : 16 + 16 * i] == b"GDEF"
    )
    data.extend(bytes(-len(data) % 4))
    struct.pack_into(">II", data, slot + 8, len(data), len(table))
    data.extend(table)
    (tmp_path / "font.ttf").write_bytes(data)
    rows, _, _, _ = _engine.typeset(source, [str(tmp_path)])
    key = int(np.frombuffer(rows).reshape(-1, tc.ROW)[0, tc.KEY])
    assert _engine.ligature_carets(key) == ([] if coordinate is None else [coordinate])


def test_font_revision_keeps_native_and_persistent_layouts_in_agreement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = next(
        p for p in Path(tc.FONTS[0]).glob("*.ttf") if p.name.startswith("NotoSans[")
    )
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    font = fonts / "font.ttf"
    cache = tmp_path / "cache"
    monkeypatch.setattr(tc, "_CACHE", cache / "layouts")

    def layout() -> tc.Layout:
        return tc.typeset("AB", '#set text(font: "Noto Sans")', font_paths=[fonts])

    before = layout()
    advance = before.rows[0, tc.ADVANCE]
    data = bytearray(source.read_bytes())
    count = struct.unpack_from(">H", data, 4)[0]
    slot = next(
        12 + 16 * i for i in range(count) if data[12 + 16 * i : 16 + 16 * i] == b"hmtx"
    )
    # Install an overriding face after the directory was scanned. The first layout's
    # bundled font stays mapped and immutable, including on Windows.
    # Noto Sans's A is glyph36; change only its advance, keeping family/style.
    at = struct.unpack_from(">I", data, slot + 8)[0] + 36 * 4
    width = struct.unpack_from(">H", data, at)[0]
    struct.pack_into(">H", data, at, width + 500)
    font.write_bytes(data)
    caches.clear()
    after = layout()
    assert after.rows[0, tc.ADVANCE] == advance + 500
    assert before.rows[0, tc.ADVANCE] == advance
    # A new process must read the updated layout from the same cache, not inherit a
    # layout made with old font bytes but published under the new dependency identity.
    program = """
import sys
from manimgx.drawing import typesetting as t
result = t.typeset('AB', '#set text(font: "Noto Sans")', font_paths=[sys.argv[1]])
print(result.rows[0, t.ADVANCE])
"""
    answer = subprocess.check_output(
        [sys.executable, "-c", program, str(fonts)],
        env=dict(
            os.environ,
            MANIMGX_CACHE_DIR=str(cache),
            PYTHONPATH=str(Path(m.__file__).resolve().parent.parent),
        ),
        text=True,
        timeout=30,
    )
    assert float(answer) == advance + 500


def test_package_revision_replaces_cached_native_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packages = tmp_path / "packages"
    package = packages / "preview" / "revision" / "0.1.0"
    package.mkdir(parents=True)
    (package / "typst.toml").write_text(
        '[package]\nname = "revision"\nversion = "0.1.0"\nentrypoint = "lib.typ"\n',
        encoding="utf-8",
    )
    source = package / "lib.typ"
    source.write_text('#let value = "A"', encoding="utf-8")
    monkeypatch.setattr(tc, "_CACHE", tmp_path / "layouts")
    body = '#import "@preview/revision:0.1.0": value\n#value'
    first = tc.typeset(body, package_path=packages)
    source.write_text('#let value = "BB"', encoding="utf-8")
    caches.clear()
    second = tc.typeset(body, package_path=packages)
    assert len(first.rows) == 1
    assert len(second.rows) == 2


def test_shared_temporary_cache_cannot_replace_fonts_or_layouts(tmp_path: Path) -> None:
    """Benign, valid empty entries in the old shared location must have no authority."""
    font = next(
        p for p in Path(tc.FONTS[0]).glob("*.ttf") if p.name.startswith("NotoSans[")
    )
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    shutil.copy2(font, fonts / font.name)
    program = r"""
import hashlib, json, sys, tempfile
from pathlib import Path
import numpy as np
from manimgx import _engine
from manimgx.drawing import typesetting as t
root = getattr(_engine, 'cache_directory', lambda: None)()
scans = Path(tempfile.gettempdir()) / 'manimgx-fonts' if root is None else Path(root) / 'fonts'
layouts = t._CACHE
before_scans = set(scans.glob('*.bin'))
before_layouts = set(layouts.glob('*.layout'))
rows, _, _, system = _engine.typeset('#set text(font:"Noto Sans")\nHello Ω', [sys.argv[1]])
table = np.frombuffer(rows).reshape(-1, 23)
keys = sorted(set(int(row[1]) for row in table if row[0] == 0))
native = hashlib.sha256(rows + b''.join(_engine.glyph_outlines(keys))).hexdigest()
layout = t.typeset('Hello Ω', font_paths=[sys.argv[1]])
print(json.dumps({'native': native, 'layout': hashlib.sha256(layout.rows.tobytes()).hexdigest(),
                  'scans': [p.name for p in set(scans.glob('*.bin')) - before_scans],
                  'layouts': [p.name for p in set(layouts.glob('*.layout')) - before_layouts]}))
"""
    env = dict(
        os.environ,
        TMPDIR=str(tmp_path),
        TMP=str(tmp_path),
        TEMP=str(tmp_path),
        PYTHONPATH=str(Path(m.__file__).resolve().parent.parent),
    )
    env.pop("MANIMGX_CACHE_DIR", None)

    def run() -> dict[str, str | list[str]]:
        result = subprocess.run(
            [sys.executable, "-c", program, str(fonts)],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return json.loads(result.stdout)

    before = run()
    assert before["scans"]
    assert before["layouts"]
    for folder, names, payload in (
        ("manimgx-fonts", before["scans"], bytes(8)),  # bincode's empty Vec
        (
            "manimgx-layouts",
            before["layouts"],
            pickle.dumps((np.empty((0, tc.ROW)), [], [], 0, {}), protocol=5),
        ),
    ):
        target = tmp_path / folder
        target.mkdir(exist_ok=True)
        for name in names:
            (target / name).write_bytes(payload)
    after = run()
    assert (after["native"], after["layout"]) == (
        before["native"],
        before["layout"],
    )


def test_concurrent_cache_writers_publish_complete_owned_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "entry.layout"
    stored: tc.Stored = (np.zeros((100, tc.ROW)), [], [], 0, {})
    expected = pickle.dumps(stored, protocol=5)
    first_written, second_half, published = Event(), Event(), Event()
    write_bytes, replace = Path.write_bytes, os.replace
    observed: list[bytes] = []

    def write(partial: Path, data: bytes) -> int:
        if not first_written.is_set():
            count = write_bytes(partial, data)
            first_written.set()
            assert second_half.wait(3)
            return count
        with partial.open("wb") as stream:
            stream.write(data[: len(data) // 2])
            stream.flush()
            second_half.set()
            assert published.wait(3)
            observed.append(path.read_bytes())
            stream.write(data[len(data) // 2 :])
        return len(data)

    def publish(source: Path, destination: Path) -> None:
        replace(source, destination)
        published.set()

    monkeypatch.setattr(Path, "write_bytes", write)
    monkeypatch.setattr(os, "replace", publish)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(tc._write, path, stored)
        assert first_written.wait(3)
        second = pool.submit(tc._write, path, stored)
        first.result(timeout=5)
        second.result(timeout=5)
    assert observed == [expected]
    assert path.read_bytes() == expected
    assert list(tmp_path.iterdir()) == [path]


class Engine:
    """The engine, counting the documents it is asked to set; or, `made_up`, a font with
    ligature carets: "first", "second" and "missing" are a glyph each, a square 1000 units wide
    (its advance), which the font cuts at 250, at 750, and nowhere."""

    WORDS: ClassVar = {"first": 981, "second": 982, "missing": 983}
    OUTLINE = m.Square(1000).shift([500, 500, 0]).points.tobytes()

    def __init__(self, monkeypatch: pytest.MonkeyPatch, made_up: bool) -> None:
        self.asked = 0
        self.carets = {981: [250.0], 982: [750.0], 983: []}
        real = _engine.typeset

        def typeset(
            source: str,
            fonts: Sequence[str],
            packages: str | None = None,
            *,
            revision: int = 0,
        ) -> Answer:
            self.asked += 1
            return (
                self.made_up(source)
                if made_up
                else real(source, fonts, packages, revision=revision)
            )

        monkeypatch.setattr(_engine, "typeset", typeset)
        if made_up:
            monkeypatch.setattr(
                _engine, "glyph_outlines", lambda keys: [self.OUTLINE for _ in keys]
            )
            monkeypatch.setattr(_engine, "ligature_carets", self.carets.__getitem__)

    def made_up(self, source: str) -> Answer:
        keys = [self.WORDS[word] for word in re.findall("|".join(self.WORDS), source)]
        rows = np.zeros((len(keys), tc.ROW))
        rows[:, tc.KEY] = keys
        rows[:, tc.PLACEMENT] = [0.01, 0, 0, 0.01, 0, 0]
        rows[:, tc.FILL] = [0, 0, 0, 1]
        rows[:, tc.STROKE] = [-1, -1, -1, -1]
        rows[:, tc.ADVANCE] = 1000
        return rows.tobytes(), [], [], False

    def change(self) -> None:
        """Change what it answered: the made-up font's carets."""
        for carets in self.carets.values():
            carets[:] = [900.0] * len(carets)


def test_unavailable_cache_root_typesets_without_disk_reuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = Engine(monkeypatch, made_up=True)
    monkeypatch.setattr(tc, "_CACHE", None)
    first = tc.typeset("first second")
    caches.clear()
    second = tc.typeset("first second")
    assert engine.asked == 2
    assert first.rows.tobytes() == second.rows.tobytes()
    assert first.glyphs.keys() == second.glyphs.keys()


class Case(NamedTuple):
    make: Callable[[], Document]
    named: dict[str, list[int]] | None = None
    """What its groups name, as places in its family, where the case says."""
    cuts: tuple[float, ...] = ()
    """Where the made-up font cuts each glyph, as a fraction of its width; none: the fonts
    manimgx ships."""


DOCUMENTS = {
    "a ligature colored inside": Case(
        lambda: m.Text("office", t2c={"f": m.RED, "i": m.BLUE})
    ),
    "labels, empty and repeated": Case(
        lambda: m.Typst("#box[#box[x ] <same> y] <same> #box[ ] <empty>"),
        # every group of a label, as one: the inner `same` adds x again, after y
        named={"same": [2, 1], "empty": []},
    ),
    "blank lines": Case(lambda: m.Paragraph("", "one", "", "two", "")),
    "math": Case(lambda: m.MathTex(r"\frac{a}{b} = \sqrt{x}")),
    "a font with carets": Case(
        lambda: m.Typst("first second missing"), cuts=(0.25, 0.75, 0.5)
    ),
}


def glyphs(mob: m.Mobject) -> Iterator[TypstGlyph]:
    """Its glyphs, uncut (a cut glyph is the group of its pieces)."""
    for part in mob.submobjects:
        if not isinstance(part, TypstGlyph):
            yield from glyphs(part)
        elif not part.submobjects:
            yield part


def outline(glyph: TypstGlyph) -> Shape:
    ((_, shape),) = glyph._geometry.terms
    return shape


def cut(glyph: TypstGlyph) -> TypstGlyph:
    """A copy of the glyph, cut in two: red, then blue."""
    piece = glyph.copy()
    _cut(piece, [m.RED, m.BLUE])
    return piece


def named(doc: Document) -> dict[str, list[int]]:
    """The parts its groups name, as places in its family (-1: a part not its own)."""
    places = {id(part): k for k, part in enumerate(doc.get_family())}
    groups = (
        {"lines": doc.lines_text}
        if isinstance(doc, m.Paragraph)
        else {label: doc.select(label) for label in doc.labels}
    )
    return {
        name: [places.get(id(part), -1) for part in group.submobjects]
        for name, group in groups.items()
    }


class Seen(NamedTuple):
    """What a document shows, what its groups name, and its glyphs' keys and cuts."""

    look: list[tuple[object, ...]]
    named: dict[str, list[int]]
    keys: list[int]
    cuts: list[list[tuple[object, ...]]]


def seen(doc: Document) -> Seen:
    keys = [glyph.key for glyph in glyphs(doc)]
    return Seen(look(doc), named(doc), keys, [look(cut(g)) for g in glyphs(doc)])


@pytest.mark.cold
@pytest.mark.parametrize("name", DOCUMENTS)
def test_a_document_is_the_same_however_it_was_set(
    name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    case = DOCUMENTS[name]
    engine = Engine(monkeypatch, made_up=bool(case.cuts))
    limit = tc._GLYPHS.limit

    def made(directory: str, *, tight: bool = False, forget: bool = True) -> Document:
        monkeypatch.setattr(tc, "_CACHE", tmp_path / directory)
        monkeypatch.setattr(tc._GLYPHS, "limit", 1 if tight else limit)
        if forget:
            caches.clear()
        return case.make()

    first = made("layouts")  # nothing remembered, nothing on disk
    sets = {"tight": made("tight layouts", tight=True)}
    asked = engine.asked
    engine.change()
    sets["from disk"] = made("layouts")
    sets["warm"] = made("layouts", forget=False)  # a copy of what it made
    _PROTOTYPES.clear()
    sets["glyphs remembered"] = made("layouts", forget=False)  # made anew
    sets["from disk, tight"] = made("layouts", tight=True)
    assert engine.asked == asked, "a document on disk is read, not set again"
    remembered, disk = glyphs(sets["glyphs remembered"]), glyphs(sets["from disk"])
    assert all(outline(a) is outline(b) for a, b in zip(remembered, disk, strict=True))
    replicas = [first.copy(), first.save_state().saved_state, first.generate_target()]
    rekeyed = first.copy()
    for glyph in glyphs(rekeyed):
        glyph.key = -1
    caches.clear()

    expected = seen(first)
    for doc in (*sets.values(), *replicas):
        assert isinstance(doc, (m.Typst, m.Paragraph))
        assert seen(doc) == expected
    assert seen(rekeyed) == expected._replace(keys=[-1] * len(expected.keys))
    if case.named is not None:
        assert named(first) == case.named
    for glyph, at in zip(glyphs(first), case.cuts, strict=bool(case.cuts)):
        left, right = cut(glyph)
        x = glyph.get_left()[0] + at * glyph.width
        assert left.get_right()[0] == pytest.approx(x)
        assert right.get_left()[0] == pytest.approx(x)

    others = [*sets.values(), *replicas, rekeyed]
    before = [look(doc) for doc in others]
    for glyph in glyphs(first):
        _cut(glyph, [m.RED, m.BLUE])
    first.set_color(m.YELLOW)
    assert [look(doc) for doc in others] == before


@pytest.mark.cold
def test_a_cut_glyph_lets_its_uncut_outline_go() -> None:
    (glyph,) = glyphs(m.Text("A"))
    uncut = weakref.ref(outline(glyph).array)
    caches.clear()
    assert uncut() is not None, "a live glyph holds its outline"
    _cut(glyph, [m.RED, m.BLUE])
    caches.clear()
    gc.collect()
    assert uncut() is None


@pytest.mark.cold
def test_a_glyph_without_an_outline_is_no_part_and_labels_lose_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # No outline is the sole omission criterion: advance, opacity and a shape's
    # height must not decide whether the item exists. An image-only font glyph is
    # omitted like a blank, even if it has a large advance.
    rows = np.zeros((8, tc.ROW))
    rows[:, tc.PLACEMENT] = [1, 0, 0, 1, 0, 0]
    rows[:, tc.FILL] = [0, 0, 0, 1]
    rows[:, tc.STROKE] = [-1, -1, -1, -1]
    rows[:, tc.KEY] = [981, 982, 981, 982, 0, 982, 981, 981]
    rows[:, tc.ADVANCE] = [999, 0, 30, 10, 0, 1, 20, 30]
    rows[4, tc.KIND] = tc.SHAPE
    rows[3, tc.FILL] = [1, 1, 1, 0]
    square = np.array([[0.0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]])
    horizontal = np.array([[0.0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]])
    labels = [
        ("empty", [0, 2, 6, 7]),
        ("duplicate", [1, 1, 2, 3]),
        ("same", [4, 5]),
        ("same", [0, 1]),
        ("outer", list(range(8))),
    ]
    raw = rows.tobytes()
    calls = 0

    def typeset(
        source: str,
        fonts: Sequence[str],
        packages: str | None = None,
        *,
        revision: int = 0,
    ) -> Answer:
        nonlocal calls
        calls += 1
        assert calls == 1, "the second construction must read its disk cache"
        return raw, [horizontal.tobytes()], labels, False

    def outlines(keys: Sequence[int]) -> list[bytes]:
        return [b"" if key == 981 else square.tobytes() for key in keys]

    def carets(key: int) -> list[float]:
        return [0.5] if key == 982 else []

    monkeypatch.setattr(tc, "_CACHE", tmp_path)
    monkeypatch.setattr(tc._engine, "typeset", typeset)
    monkeypatch.setattr(tc._engine, "glyph_outlines", outlines)
    monkeypatch.setattr(tc._engine, "ligature_carets", carets)
    expected = rows[[1, 3, 4, 5]].copy()
    for _ in range(2):
        # A new process has no outline or native-key table when it reads the file.
        caches.clear()
        layout = tc.typeset("synthetic drawing")
        key = int(layout.rows[0, tc.KEY])
        expected[[0, 1, 3], tc.KEY] = key
        assert layout.rows.tobytes() == expected.tobytes()
        assert layout.labels == [
            ("empty", []),
            ("duplicate", [0, 0, 1]),
            ("same", [2, 3]),
            ("same", [0]),
            ("outer", [0, 1, 2, 3]),
        ]
        assert layout.shapes[0].tobytes() == horizontal.tobytes()
        _, shape, caret_bytes = layout.glyphs[key]
        assert shape is not None
        assert shape.array.tobytes() == square.tobytes()
        assert tuple(np.frombuffer(caret_bytes, dtype="<f8")) == (0.5,)
    assert rows.tobytes() == raw
    assert calls == 1


def test_marks_a_package_draws_come_from_the_element_around_them() -> None:
    # mitex's radical and fraction bar are drawn in its package's code, which the document
    # doesn't hold: they come from the document's innermost element around them, the
    # equation; what the document writes comes from its own node.
    preamble = (
        '#import "@preview/mitex:0.2.7": mitex-scope\n'
        "#let (mitexsqrt, frac) = (mitex-scope.mitexsqrt, mitex-scope.frac)\n"
    )
    body = "$mitexsqrt(x) + frac(1, 2)$ y"
    layout = tc.typeset(body, preamble)
    origins = [
        (
            "glyph" if row[tc.KIND] == tc.GLYPH else "shape",
            body[
                int(row[tc.NODE][0]) - layout.body : int(row[tc.NODE][1]) - layout.body
            ],
            tuple(row[tc.DRAWN]) == (-1, -1),
        )
        for row in layout.rows
    ]
    equation = body[: body.rindex("$") + 1]
    assert origins == [
        ("glyph", equation, True),  # the radical
        ("shape", equation, True),  # its bar
        ("glyph", "x", False),
        ("glyph", "+", False),
        ("glyph", "1", False),
        ("glyph", "2", False),
        ("shape", equation, True),  # the fraction's bar
        ("glyph", "y", False),
    ]


def test_blank_lines_are_empty_lines() -> None:
    paragraph = m.Paragraph("", "one", "", "two", "")
    assert [len(line) for line in paragraph] == [0, 3, 0, 3, 0]


def _set(text: m.Text) -> tuple[list[int], bool]:
    """The glyph ids the engine set a text in, and whether it read the system's fonts."""
    preamble = tc.TYPST_TEMPLATE.format(
        text_size=tc.TYPST_COMPILATION_FONT_SIZE, preamble=text.typst_preamble
    )
    rows, _, _, system = _engine.typeset(preamble + text.typst_code, tc.FONTS)
    table = np.frombuffer(rows).reshape(-1, tc.ROW)
    keys = table[table[:, tc.KIND] == tc.GLYPH, tc.KEY].astype(np.int64)
    return [int(k) % 65536 for k in keys], system


@pytest.mark.parametrize(
    ("text", "font"),
    [  # multiple_fonts' texts
        ("வணக்கம்", "sans-serif"),
        ("日本へようこそ", ""),
        ("Здравствуйте मस नम म ", "sans-serif"),
        ("नमस्ते", "sans-serif"),
        ("صباح الخير \n تشرفت بمقابلتك", "sans-serif"),
        ("臂猿「黛比」帶著孩子", "sans-serif"),
    ],
)
def test_every_script_is_set_in_a_font_manimgx_ships(text: str, font: str) -> None:
    ids, system = _set(m.Text(text, font=font))
    assert ids
    assert 0 not in ids  # .notdef: a character no font has
    assert not system


def test_a_system_font_is_read_only_by_name() -> None:
    assert _set(m.Text("Hi", font="Open Sans"))[1]

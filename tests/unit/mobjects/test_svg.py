"""An SVG drawing remembered is the drawing made afresh.

Whatever was made before it — the same file in other sizes and looks, the file before an edit
that kept its size and time, a class of the same name, a conversion whose input in its hash
seed or whose XML hook's content has changed since, options changed in place since, settings
equal to the last ones up to their repr — the drawing the cache gives is the one converting
the file anew gives: the same parts, points and paint, and the same named groups of them.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar
from xml.etree import ElementTree as ET

import numpy as np
import pytest
import svgelements as se

import manimgx as m
from manimgx.drawing.paint import Look, Repaint
from manimgx.mobjects.svg import PathOptions

# a row: what is made first (and so remembered), and then the drawing, cached or not
type Row = Callable[[Path], Callable[[bool], m.SVGMobject]]


@pytest.fixture
def drawing(tmp_path: Path) -> Path:
    path = tmp_path / "drawing.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g id="outer"><g id="inner" transform="rotate(15)">'
        '<rect x="2" y="1" width="6" height="3" rx="1" fill="#58c4dd"/>'
        '<circle cx="12" cy="5" r="3" stroke="#ffffff" stroke-width="2"/>'
        '<path d="M1 1 Q3 3 4 1 L4 0 Z" fill="#83c167"/>'
        "</g></g></svg>",
        encoding="utf-8",
    )
    return path


def _sized(height: float | None, width: float | None, centered: bool) -> Row:
    def row(path: Path) -> Callable[[bool], m.SVGMobject]:
        m.SVGMobject(path, sheen_factor=0.2, sheen_direction=m.LEFT)
        look: Look = {
            "sheen_factor": 0.8,
            "sheen_direction": m.UP,
            "background_stroke_color": m.RED,
            "background_stroke_width": 3,
        }
        return lambda cache: m.SVGMobject(
            path,
            height=height,
            width=width,
            should_center=centered,
            use_svg_cache=cache,
            **look,
        )

    return row


def _edited(path: Path) -> Callable[[bool], m.SVGMobject]:
    before = m.SVGMobject(path, height=None)
    stat = path.stat()
    path.write_text(
        path.read_text(encoding="utf-8").replace('width="6"', 'width="9"'),
        encoding="utf-8",
    )
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # (the same size and time)
    assert (
        m.SVGMobject(path, height=None, use_svg_cache=False)[0].width != before[0].width
    )
    return lambda cache: m.SVGMobject(path, height=None, use_svg_cache=cache)


def _same_name(path: Path) -> Callable[[bool], m.SVGMobject]:
    def scaled(factor: float) -> type[m.SVGMobject]:
        class Drawing(m.SVGMobject):
            @staticmethod
            def rect_to_mobject(rect: se.Rect) -> m.Rectangle:
                return m.SVGMobject.rect_to_mobject(rect).scale(factor)

        return Drawing

    scaled(1)(path, height=None)
    large = scaled(2)
    return lambda cache: large(path, height=None, use_svg_cache=cache)


def _reseeded(path: Path) -> Callable[[bool], m.SVGMobject]:
    class Scaled(m.SVGMobject):  # (a conversion's input, in its hash seed)
        factor: ClassVar[float] = 1.0

        @property
        def hash_seed(self) -> tuple[object, ...]:
            return (*super().hash_seed, self.factor)

        @staticmethod
        def rect_to_mobject(rect: se.Rect) -> m.Rectangle:
            return m.SVGMobject.rect_to_mobject(rect).scale(Scaled.factor)

    Scaled(path, height=None)
    Scaled.factor = 2.0
    return lambda cache: Scaled(path, height=None, use_svg_cache=cache)


def _rewritten(path: Path) -> Callable[[bool], m.SVGMobject]:
    class Inked(m.SVGMobject):
        def __init__(self, path: Path, ink: str, use_svg_cache: bool = True) -> None:
            self.ink = ink
            super().__init__(path, use_svg_cache=use_svg_cache)

        def modify_xml_tree(
            self, element_tree: ET.ElementTree[ET.Element]
        ) -> ET.ElementTree[ET.Element]:
            for element in element_tree.iter():
                element.set("fill", self.ink)
            return super().modify_xml_tree(element_tree)

    Inked(path, "#ff0000")
    return lambda cache: Inked(path, "#0000ff", use_svg_cache=cache)


def _changed_in_place(path: Path) -> Callable[[bool], m.SVGMobject]:
    defaults: Repaint = {"stroke_width": 2, "stroke_color": m.RED}
    options: PathOptions = {
        "sheen_factor": 0.2,
        "sheen_direction": np.array([1.0, 2.0, 3.0]),
    }
    m.SVGMobject(path, svg_default=defaults, path_string_config=options)
    defaults["stroke_color"] = m.BLUE
    options["sheen_direction"] = np.array([-1.0, 3.0, 2.0])
    return lambda cache: m.SVGMobject(
        path, svg_default=defaults, path_string_config=options, use_svg_cache=cache
    )


def _precise(path: Path) -> Callable[[bool], m.SVGMobject]:
    first = np.array([1.0, 1.0, 0.0])
    second = np.array([1.0 + 2**-40, 1.0, 0.0])
    assert repr(first) == repr(second)
    m.SVGMobject(path, path_string_config={"sheen_direction": first})
    options: PathOptions = {"sheen_direction": second}
    return lambda cache: m.SVGMobject(
        path, path_string_config=options, use_svg_cache=cache
    )


ROWS: dict[str, Row] = {
    **{
        f"sized {height}×{width}{', centered' if centered else ''}": _sized(
            height, width, centered
        )
        for height, width in ((None, None), (2, None), (None, 4), (3, 2))
        for centered in (False, True)
    },
    "edited, its size and time kept": _edited,
    "a class of the same name": _same_name,
    "a conversion's input in its hash seed changed": _reseeded,
    "a hook's content changed": _rewritten,
    "options changed in place": _changed_in_place,
    "settings equal up to their repr": _precise,
}


def _assert_same(actual: m.SVGMobject, expected: m.SVGMobject) -> None:
    assert len(actual) == len(expected)
    for ours, theirs in zip(actual.get_family(), expected.get_family(), strict=True):
        np.testing.assert_array_equal(ours.points, theirs.points)
        for name in ("fill", "stroke", "background", "sheen_direction"):
            np.testing.assert_array_equal(
                getattr(ours.paint, name), getattr(theirs.paint, name)
            )
        for name in ("stroke_width", "background_width", "sheen_factor"):
            assert getattr(ours.paint, name) == getattr(theirs.paint, name)
    assert actual.id_to_vgroup_dict.keys() == expected.id_to_vgroup_dict.keys()
    for name, group in actual.id_to_vgroup_dict.items():
        assert [actual.submobjects.index(part) for part in group] == [
            expected.submobjects.index(part)
            for part in expected.id_to_vgroup_dict[name]
        ]


@pytest.mark.cold
@pytest.mark.parametrize("row", sorted(ROWS))
def test_a_remembered_drawing_is_the_drawing_made_afresh(
    drawing: Path, row: str
) -> None:
    make = ROWS[row](drawing)
    _assert_same(make(True), make(False))


@pytest.mark.parametrize(
    "transform", ["translate(7 3)", "scale(2 3)", "rotate(35)", "matrix(1 2 3 4 5 6)"]
)
def test_a_root_transform_has_the_same_effect_as_a_group_transform(
    tmp_path: Path, transform: str
) -> None:
    shape = '<rect x="1" y="2" width="3" height="4"/>'
    drawings = []
    for name, body in (
        ("root", f'<svg transform="{transform}">{shape}</svg>'),
        ("group", f'<svg><g transform="{transform}">{shape}</g></svg>'),
    ):
        path = tmp_path / f"{name}.svg"
        path.write_text(body, encoding="utf-8")
        drawings.append(m.SVGMobject(path, height=None, should_center=False))
    np.testing.assert_allclose(drawings[0][0].points, drawings[1][0].points, atol=1e-14)


@pytest.mark.parametrize(
    ("aspect", "size", "center"),
    [
        ("none", (20, 40), (10, 20, 0)),
        ("xMidYMid meet", (20, 20), (10, 20, 0)),
        ("xMinYMin meet", (20, 20), (10, 10, 0)),
        ("xMidYMid slice", (40, 40), (10, 20, 0)),
    ],
)
def test_the_viewbox_maps_user_coordinates_into_the_viewport(
    tmp_path: Path,
    aspect: str,
    size: tuple[float, float],
    center: tuple[float, float, float],
) -> None:
    path = tmp_path / "viewport.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="40" '
        f'viewBox="5 10 10 10" preserveAspectRatio="{aspect}">'
        '<rect x="5" y="10" width="10" height="10"/></svg>',
        encoding="utf-8",
    )
    drawing = m.SVGMobject(path, height=None, should_center=False)
    np.testing.assert_allclose([drawing.width, drawing.height], size)
    # SVGMobject turns SVG's y axis around the drawing's center; that center is kept.
    np.testing.assert_allclose(drawing.get_center(), center, atol=1e-14)


@pytest.mark.parametrize(
    ("root", "child", "expected"),
    [
        ("", "", "#FF0000"),
        ('fill="#0000FF"', "", "#0000FF"),
        ('style="fill:#0000FF"', "", "#0000FF"),
        ('fill="#0000FF"', 'fill="#00FF00"', "#00FF00"),
    ],
)
def test_svg_defaults_fill_only_what_the_document_leaves_unpainted(
    tmp_path: Path, root: str, child: str, expected: str
) -> None:
    path = tmp_path / "paint.svg"
    path.write_text(
        f'<svg {root}><rect width="1" height="1" {child}/></svg>', encoding="utf-8"
    )
    drawing = m.SVGMobject(path, svg_default={"fill_color": "#FF0000"})
    assert drawing[0].get_fill_color().to_hex() == expected


def test_the_document_root_keeps_its_group_identity(tmp_path: Path) -> None:
    path = tmp_path / "identified.svg"
    path.write_text(
        '<svg id="drawing"><g id="shapes"><rect width="1" height="1"/></g></svg>',
        encoding="utf-8",
    )
    drawing = m.SVGMobject(path)
    for name in ("root", "drawing", "shapes"):
        assert list(drawing.id_to_vgroup_dict[name]) == list(drawing)


@pytest.mark.parametrize("scale", [1e-8, 1e-5, 1e-3, 1, 1e5])
def test_closing_a_path_is_independent_of_its_scale(scale: float) -> None:
    path = se.Path(f"M0 0 L{scale} 0 L{scale} {scale} L0 {scale} Z")
    drawing = m.VMobjectFromSVGPath(path)
    assert drawing.get_num_curves() == 4
    np.testing.assert_array_equal(drawing.get_start(), drawing.get_end())
    normalized = m.VMobjectFromSVGPath(se.Path("M0 0 L1 0 L1 1 L0 1 Z"))
    np.testing.assert_allclose(drawing.points / scale, normalized.points, atol=1e-14)


def test_converting_arcs_does_not_edit_the_supplied_path() -> None:
    path = se.Path("M0 0 A1 1 0 0 1 2 0 L2 2 Z")
    segments = [repr(segment) for segment in path]
    identities = [id(segment) for segment in path]
    drawing = m.VMobjectFromSVGPath(path)
    assert [repr(segment) for segment in path] == segments
    assert [id(segment) for segment in path] == identities
    points = drawing.points.copy()
    path *= se.Matrix.scale(2)
    drawing.generate_points()
    np.testing.assert_array_equal(drawing.points, points)

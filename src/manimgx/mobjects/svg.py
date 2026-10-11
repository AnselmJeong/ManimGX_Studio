# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""SVG as mobjects: a file's shapes (`SVGMobject`), and one path's curves (a brace, the logo's
letters). Ported from Manim CE 0.21 (MIT)."""

from __future__ import annotations

import io
import logging
import os
from collections.abc import Sequence
from copy import copy
from pathlib import Path
from typing import TYPE_CHECKING, Self, Unpack
from warnings import deprecated
from xml.etree import ElementTree as ET

import numpy as np

from manimgx.caches import Memo
from manimgx.constants import RIGHT
from manimgx.drawing.geometry import Blend
from manimgx.drawing.paint import BLACK, Colors, Look, Repaint, Style, _Style, key_of
from manimgx.mobject import VGroup, VMobject, copied
from manimgx.mobjects.shapes import Circle, Line, Polygon, Rectangle, RoundedRectangle

if TYPE_CHECKING:  # svgelements loads when an SVG is read (few scenes read one)
    import svgelements as se

__all__ = ["SVGMobject", "VMobjectFromSVGPath"]
logger = logging.getLogger("manimgx")

_DRAWINGS: Memo[tuple[object, ...], tuple[list[VMobject], dict[str, VGroup]]] = Memo(
    1 << 8
)


def _point(point: se.Point | None) -> np.ndarray:
    """A path's point, in 3D (a well-formed path has every point it names)."""
    if point is None:
        raise ValueError("malformed SVG path: a segment without its point")
    return np.array([point.x, point.y, 0.0])


class PathOptions(_Style, total=False):
    """How an SVG path becomes curves: an [SVGMobject][manimgx.SVGMobject]'s
    `path_string_config`, the keywords of each path it reads.

    Beyond these, they take the [style keywords][manimgx.drawing.paint.Style].
    """

    long_lines: bool
    """Accepted for Manim compatibility; ignored (default False)."""
    should_subdivide_sharp_curves: bool
    """Accepted for Manim compatibility; ignored (default False)."""
    should_remove_null_curves: bool
    """Accepted for Manim compatibility; ignored (default False)."""


class SVGMobject(VMobject):
    """A drawing read from an SVG file: each of its shapes a part, painted as the file
    paints it, 2 units tall unless sized.

    Paths, lines, rectangles (rounded too), circles, ellipses, polygons and polylines
    become parts, in the file's order, with the file's fills, strokes and transforms;
    groups and `<use>` are followed, and text is skipped, with a warning. What the file
    leaves unpainted takes SVG's defaults, a black fill and no stroke, unless
    `svg_default` says otherwise. The file's groups are kept by their ids, in
    [id_to_vgroup_dict][manimgx.SVGMobject.id_to_vgroup_dict].

    Args:
        file_name: The SVG file.
        should_center: Whether the drawing is centered on the origin.
        height: The height to scale the drawing to, in scene units; None keeps the
            file's size, a scene unit per SVG unit.
        width: The width to scale the drawing to, in scene units, after `height` (so it
            wins); None: as `height` makes it.
        color: Accepted for Manim compatibility; no effect: the parts keep the file's
            colors (paint over them with `fill_color` and `stroke_color`, or color what
            the file leaves unpainted through `svg_default`).
        opacity: Accepted for Manim compatibility; ignored.
        fill_color: A fill color for every part; None keeps the file's.
        fill_opacity: A fill opacity for every part, from 0 to 1; None keeps the file's.
        stroke_color: A stroke color for every part; None keeps the file's.
        stroke_opacity: A stroke opacity for every part, from 0 to 1; None keeps the
            file's.
        stroke_width: A stroke width for every part, in hundredths of a scene unit;
            None keeps the file's.
        svg_default: [Paint keywords][manimgx.drawing.paint.Repaint] for what the file
            leaves unpainted; None for `{"stroke_width": 0}`: no stroke.
        path_string_config: [SVG path
            keywords][manimgx.mobjects.svg.PathOptions] for every path.
        use_svg_cache: Whether parsed drawings are kept and copied for the same SVG
            content and path settings. The file is always read for changes.
    """

    def __init__(
        self,
        file_name: str | os.PathLike[str] | None = None,
        should_center: bool = True,
        height: float | None = 2,
        width: float | None = None,
        color: Colors | None = None,
        opacity: float | None = None,
        fill_color: Colors | None = None,
        fill_opacity: float | Sequence[float] | None = None,
        stroke_color: Colors | None = None,
        stroke_opacity: float | Sequence[float] | None = None,
        stroke_width: float | None = None,
        svg_default: Repaint | None = None,
        path_string_config: PathOptions | None = None,
        use_svg_cache: bool = True,
        **kwargs: Unpack[Look],
    ):
        super().__init__(stroke_color=None, fill_color=None, **kwargs)
        self.file_name = Path(file_name) if file_name is not None else None
        self.should_center = should_center
        self.svg_height = height
        self.svg_width = width
        self.set_color(BLACK if color is None else color)
        self.opacity = opacity
        self.fill_color = fill_color
        self.fill_opacity = fill_opacity
        self.stroke_color = stroke_color
        self.stroke_opacity = stroke_opacity
        self.stroke_width = 0 if stroke_width is None else stroke_width
        self.id_to_vgroup_dict: dict[str, VGroup] = {}
        """The drawing's groups, by their ids: each `<g>` element's id names a group of
        the shapes inside it, and "root" all of them; an element without an id is named
        "numbered_group_" and a number."""
        self.svg_default: Repaint = (
            {"stroke_width": 0} if svg_default is None else svg_default
        )
        self.path_string_config: PathOptions = (
            {} if path_string_config is None else path_string_config
        )
        self.init_svg_mobject(use_svg_cache=use_svg_cache)
        self.set_style(
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            stroke_color=stroke_color,
            stroke_opacity=stroke_opacity,
            stroke_width=stroke_width,
        )
        self.move_into_position()

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def init_svg_mobject(self, use_svg_cache: bool) -> Self:
        """Build the drawing, reusing parsed parts when caching is enabled."""
        self.use_svg_cache = use_svg_cache
        self.generate_mobject()
        return self

    @property
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def hash_seed(self) -> tuple[object, ...]:
        """The class and path settings that interpret the SVG content. Subclasses can
        extend this tuple with other inputs their conversion uses."""
        return (
            type(self),
            key_of(sorted(self.path_string_config.items())),
        )

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def generate_mobject(self) -> Self:
        """Read the file and add its shapes as parts, flipped so that y points up (SVG's
        points down). Existing geometry turns with the newly read shapes.
        """
        import svgelements as se

        element_tree = ET.parse(self.get_file_path())
        buffer = io.BytesIO()
        self.modify_xml_tree(element_tree).write(buffer)
        buffer.seek(0)
        if self.has_points() or self.submobjects:
            mobjects, self.id_to_vgroup_dict = self.get_mobjects_from(
                se.SVG.parse(buffer)
            )
            self.add(*mobjects)
            return self.flip(RIGHT)
        try:
            key = (buffer.getvalue(), *self.hash_seed) if self.use_svg_cache else None
        except TypeError:
            key = None
        drawing = None if key is None else _DRAWINGS.get(key)
        if drawing is None:
            drawing = self.get_mobjects_from(se.SVG.parse(buffer))
            VGroup(*drawing[0]).flip(RIGHT)
            if key is not None:
                _DRAWINGS.keep(key, copied(drawing))
        else:
            drawing = copied(drawing)
        mobjects, mobject_dict = drawing
        self.flip(RIGHT)
        self.add(*mobjects)
        self.id_to_vgroup_dict = mobject_dict
        return self

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def get_file_path(self) -> Path:
        """Find the SVG file; a mobject made without one raises ValueError.

        Returns:
            The file's path.
        """
        if self.file_name is None:
            raise ValueError("Must specify file for SVGMobject")
        return self.file_name

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def modify_xml_tree(
        self, element_tree: ET.ElementTree[ET.Element]
    ) -> ET.ElementTree[ET.Element]:
        """Give the file's root the defaults its attributes leave unspecified, keeping
        its viewport, transforms, styles and document structure.

        Args:
            element_tree: The file, parsed.

        Returns:
            A new tree.
        """
        root = element_tree.getroot()
        new_root = ET.Element(root.tag, self.generate_config_style_dict() | root.attrib)
        new_root.extend(root)
        return ET.ElementTree(new_root)

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def generate_config_style_dict(self) -> dict[str, str]:
        """The SVG attributes `svg_default` sets: `fill`, `fill-opacity`, `stroke`,
        `stroke-opacity` and `stroke-width`.

        Returns:
            The attributes it gives, as strings, by name.
        """
        keys_converting_dict = {
            "fill": ("color", "fill_color"),
            "fill-opacity": ("opacity", "fill_opacity"),
            "stroke": ("color", "stroke_color"),
            "stroke-opacity": ("opacity", "stroke_opacity"),
            "stroke-width": ("stroke_width",),
        }
        result = {}
        for svg_key, style_keys in keys_converting_dict.items():
            for style_key in style_keys:
                value = self.svg_default.get(style_key)
                if value is not None:
                    result[svg_key] = str(value)
        return result

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def get_mobjects_from(
        self, svg: se.SVG
    ) -> tuple[list[VMobject], dict[str, VGroup]]:
        """Make a part of every shape of the drawing, in document order, and a group of
        the parts of each of its groups, named or not.

        Args:
            svg: The drawing, as svgelements parses it.

        Returns:
            The parts, and the groups by id (an unnamed group numbered; "root" for all
            the parts).
        """
        import svgelements as se

        shapes = (
            se.Path,
            se.SimpleLine,
            se.Rect,
            se.Circle,
            se.Ellipse,
            se.Polygon,
            se.Polyline,
            se.Text,
        )
        result: list[VMobject] = []
        stack: list[tuple[se.SVGElement, int]] = [(svg, 1)]
        group_id_number = 0
        vgroup_stack: list[str] = ["root"]
        vgroups: dict[str, VGroup] = {"root": VGroup()}
        while stack:
            element, depth = stack.pop()
            vgroup_stack = vgroup_stack[0:depth]
            try:
                group_name = str((element.values or {})["id"])
            except Exception:
                group_name = f"numbered_group_{group_id_number}"
                group_id_number += 1
            vgroup_stack.append(group_name)
            vgroups[group_name] = VGroup()
            if isinstance(element, (se.Group, se.Use)):
                stack.extend((subelement, depth + 1) for subelement in element[::-1])
            try:
                if isinstance(element, shapes):
                    mob = self.get_mob_from_shape_element(element)
                    if mob is not None:
                        result.append(mob)
                        for parent_name in vgroup_stack[:-1]:
                            vgroups[parent_name].add(mob)
            except Exception as e:
                logger.error(f"Exception occurred in 'get_mobjects_from'. Details: {e}")
        return (result, vgroups)

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def get_mob_from_shape_element(self, shape: se.SVGElement) -> VMobject | None:
        """Make a part of a shape of the drawing, painted and transformed as the file
        says.

        Args:
            shape: The shape, as svgelements parses it.

        Returns:
            The part; None for an empty shape, or an element that isn't supported (text).
        """
        import svgelements as se

        if isinstance(shape, se.Path):
            mob: VMobject | None = self.path_to_mobject(shape)
        elif isinstance(shape, se.SimpleLine):
            mob = self.line_to_mobject(shape)
        elif isinstance(shape, se.Rect):
            mob = self.rect_to_mobject(shape)
        elif isinstance(shape, (se.Circle, se.Ellipse)):
            mob = self.ellipse_to_mobject(shape)
        elif isinstance(shape, se.Polygon):
            mob = self.polygon_to_mobject(shape)
        elif isinstance(shape, se.Polyline):
            mob = self.polyline_to_mobject(shape)
        elif isinstance(shape, se.Text):
            mob = self.text_to_mobject(shape)
        else:
            logger.warning(f"Unsupported element type: {type(shape)}")
            mob = None
        if mob is None or not mob.has_points():
            return None
        if isinstance(shape, se.GraphicObject):
            self.apply_style_to_mobject(mob, shape)
        if (
            isinstance(shape, se.Transformable)
            and shape.apply
            and shape.transform is not None
        ):
            self.handle_transform(mob, shape.transform)
        return mob

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def handle_transform(mob: VMobject, matrix: se.Matrix) -> VMobject:
        """Apply an SVG transform to a part: its matrix, then its translation.

        Args:
            mob: The part.
            matrix: The transform, as svgelements gives it.

        Returns:
            The part.
        """
        mat = np.array([[matrix.a, matrix.c], [matrix.b, matrix.d]])
        vec = np.array([matrix.e, matrix.f, 0.0])
        mob.apply_matrix(mat)
        mob.shift(vec)
        return mob

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def apply_style_to_mobject(mob: VMobject, shape: se.GraphicObject) -> VMobject:
        """Paint a part as the file paints its shape: its fill, its stroke, their
        opacities and the stroke's width.

        Args:
            mob: The part.
            shape: The shape, as svgelements parses it.

        Returns:
            The part.
        """
        stroke, fill = shape.stroke, shape.fill
        mob.set_style(
            stroke_width=shape.stroke_width,
            stroke_color=None if stroke is None else stroke.hexrgb,
            stroke_opacity=None if stroke is None else stroke.opacity,
            fill_color=None if fill is None else fill.hexrgb,
            fill_opacity=None if fill is None else fill.opacity,
        )
        return mob

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def path_to_mobject(self, path: se.Path) -> VMobjectFromSVGPath:
        """Make a part of a path, with `path_string_config`.

        Args:
            path: The path, as svgelements parses it.

        Returns:
            A new [VMobjectFromSVGPath][manimgx.VMobjectFromSVGPath].
        """
        return VMobjectFromSVGPath(path, **self.path_string_config)

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def line_to_mobject(line: se.SimpleLine) -> Line:
        """Make a part of a line.

        Args:
            line: The line, as svgelements parses it.

        Returns:
            A new [Line][manimgx.Line].
        """
        x1, y1, x2, y2 = (float(v or 0) for v in (line.x1, line.y1, line.x2, line.y2))
        return Line(start=np.array([x1, y1, 0.0]), end=np.array([x2, y2, 0.0]))

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def rect_to_mobject(rect: se.Rect) -> Rectangle:
        """Make a part of a rectangle, its corners rounded if the file rounds them.

        Args:
            rect: The rectangle, as svgelements parses it.

        Returns:
            A new [Rectangle][manimgx.Rectangle] or
            [RoundedRectangle][manimgx.RoundedRectangle].
        """
        x, y, width, height, rx, ry = (
            float(v or 0)
            for v in (rect.x, rect.y, rect.width, rect.height, rect.rx, rect.ry)
        )
        if rx == 0 or ry == 0:
            mob = Rectangle(width=width, height=height)
        else:
            mob = RoundedRectangle(
                width=width, height=height * rx / ry, corner_radius=rx
            )
            mob.stretch_to_fit_height(height)
        mob.shift(np.array([x + width / 2, y + height / 2, 0.0]))
        return mob

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def ellipse_to_mobject(ellipse: se.Ellipse | se.Circle) -> Circle:
        """Make a part of a circle or an ellipse.

        Args:
            ellipse: The circle or ellipse, as svgelements parses it.

        Returns:
            A new [Circle][manimgx.Circle], stretched for an ellipse.
        """
        rx, ry, cx, cy = (
            float(v or 0) for v in (ellipse.rx, ellipse.ry, ellipse.cx, ellipse.cy)
        )
        mob = Circle(radius=rx)
        if rx != ry:
            mob.stretch_to_fit_height(2 * ry)
        mob.shift(np.array([cx, cy, 0.0]))
        return mob

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def polygon_to_mobject(polygon: se.Polygon) -> Polygon:
        """Make a part of a polygon.

        Args:
            polygon: The polygon, as svgelements parses it.

        Returns:
            A new [Polygon][manimgx.Polygon].
        """
        return Polygon(*(np.array([x, y, 0.0]) for x, y in polygon))

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def polyline_to_mobject(self, polyline: se.Polyline) -> VMobject:
        """Make a part of a polyline: an open path through its points.

        Args:
            polyline: The polyline, as svgelements parses it.

        Returns:
            A new VMobject.
        """
        return VMobject().set_points_as_corners([[x, y, 0.0] for x, y in polyline])

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def text_to_mobject(text: se.Text) -> VMobject | None:
        """Skip a text element: SVG text is not supported, and a warning is logged.

        Args:
            text: The text, as svgelements parses it.

        Returns:
            None.
        """
        logger.warning(f"Unsupported element type: {type(text)}")
        return None

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def move_into_position(self) -> Self:
        """Center the drawing and scale it to `height` and `width`, as the constructor
        was asked to.
        """
        if self.should_center:
            self.center()
        if self.svg_height is not None:
            self.set(height=self.svg_height)
        if self.svg_width is not None:
            self.set(width=self.svg_width)
        return self


@deprecated("Manim CE's machinery for SVGMobject: use SVGMobject", category=None)
class VMobjectFromSVGPath(VMobject):
    """A path of an SVG drawing, as a mobject: its lines, quadratic and cubic curves,
    and arcs (approximated by quadratic curves), all made cubic curves.

    An [SVGMobject][manimgx.SVGMobject] makes one of every path in its file. The points
    are in the path's own coordinates, a scene unit per SVG unit, and SVG's y axis
    points down: the path is upside down until flipped, as an SVGMobject flips its
    drawing.

    The supplied path is converted once. Editing it later does not affect the drawing;
    `generate_points` restores the original converted geometry.

    Args:
        path_obj: The path, as svgelements parses it (a `svgelements.Path`).
        long_lines: Accepted for Manim compatibility; ignored.
        should_subdivide_sharp_curves: Accepted for Manim compatibility; ignored.
        should_remove_null_curves: Accepted for Manim compatibility; ignored.
    """

    def __init__(
        self,
        path_obj: se.Path,
        long_lines: bool = False,
        should_subdivide_sharp_curves: bool = False,
        should_remove_null_curves: bool = False,
        **kwargs: Unpack[Style],
    ) -> None:
        import svgelements as se

        path_obj = copy(path_obj)
        path_obj.approximate_arcs_with_quads()
        points: list[np.ndarray] = []
        pen = start = np.zeros(3)
        for segment in path_obj:
            kind = type(segment)
            if kind is se.Move:
                pen = start = _point(segment.end)
            elif kind is se.Line or (
                kind is se.Close and not np.array_equal(pen, start)
            ):
                end = start if kind is se.Close else _point(segment.end)
                points += [pen, (2 * pen + end) / 3, (pen + 2 * end) / 3, end]
                pen = end
            elif isinstance(segment, se.QuadraticBezier):
                control, end = _point(segment.control), _point(segment.end)
                points += [pen, (pen + 2 * control) / 3, (2 * control + end) / 3, end]
                pen = end
            elif isinstance(segment, se.CubicBezier):
                end = _point(segment.end)
                points += [pen, _point(segment.control1), _point(segment.control2), end]
                pen = end
            elif kind is not se.Close:
                raise AssertionError(f"Not implemented: {kind}")
        source = (
            np.array(points, ndmin=2, dtype="float64") if points else np.zeros((0, 3))
        )
        self._source_geometry = Blend.of(source)
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        """Restore the geometry converted from the original SVG path."""
        self._geometry = self._source_geometry
        return self

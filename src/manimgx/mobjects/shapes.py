# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"Geometric figures: cubic paths, planar region operations, arrow tips and sampled point disks."

from __future__ import annotations

import itertools
import warnings
from collections.abc import Iterator, Sequence
from functools import reduce
from math import ceil
from typing import TYPE_CHECKING, ClassVar, Literal, Self, Unpack, cast
from warnings import deprecated

import numpy as np

from manimgx.config import config
from manimgx.constants import (
    DEFAULT_ARROW_TIP_LENGTH,
    DEFAULT_DASH_LENGTH,
    DEFAULT_DOT_RADIUS,
    DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
    DEFAULT_POINT_DENSITY_1D,
    DEGREES,
    DL,
    DOWN,
    DR,
    LARGE_BUFF,
    LEFT,
    MED_SMALL_BUFF,
    ORIGIN,
    OUT,
    PI,
    RIGHT,
    TAU,
    UL,
    UP,
    UR,
)
from manimgx.drawing.geometry import (
    Blend,
    QuickHull,
    _pathops,
    _to_path,
    angle_between_vectors,
    angle_of_vector,
    cartesian_to_spherical,
    defined,
    line_intersection,
    normalize,
    perpendicular_bisector,
    regular_vertices,
    rotation_matrix,
    segment,
    turn_between,
)
from manimgx.drawing.paint import (
    BLUE,
    PURE_YELLOW,
    RED,
    WHITE,
    Colors,
    Style,
    StyleBase,
    _Style,
    _StyleBase,
)
from manimgx.mobject import (
    Mobject,
    Mobject1D,
    Pivot,
    VGroup,
    VMobject,
    _append_path,
    prototype,
    style_defaults,
)
from manimgx.typing import Point3DLike

__all__ = [
    "Angle",
    "AnnotationDot",
    "AnnularSector",
    "Annulus",
    "Arc",
    "ArcBetweenPoints",
    "ArcPolygon",
    "ArcPolygonFromArcs",
    "Arrow",
    "ArrowCircleFilledTip",
    "ArrowCircleTip",
    "ArrowSquareFilledTip",
    "ArrowSquareTip",
    "ArrowTip",
    "ArrowTriangleFilledTip",
    "ArrowTriangleTip",
    "Circle",
    "ConvexHull",
    "CubicBezier",
    "CurvedArrow",
    "CurvedDoubleArrow",
    "CurvesAsSubmobjects",
    "Cutout",
    "DashedLine",
    "DashedVMobject",
    "Difference",
    "Dot",
    "DoubleArrow",
    "Elbow",
    "Ellipse",
    "Exclusion",
    "FullScreenRectangle",
    "Intersection",
    "Line",
    "PointCloudDot",
    "Polygon",
    "Polygram",
    "Rectangle",
    "RegularPolygon",
    "RegularPolygram",
    "RightAngle",
    "RoundedRectangle",
    "ScreenRectangle",
    "Sector",
    "Square",
    "Star",
    "StealthTip",
    "TangentLine",
    "TipableVMobject",
    "Triangle",
    "Union",
    "Vector",
    "adjacent_n_tuples",
    "adjacent_pairs",
]

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Self

    import numpy.typing as npt

    from manimgx.drawing.paint import ParsableManimColor
    from manimgx.mobject import Mobject
    from manimgx.mobjects.grid import Matrix, MatrixOptions
    from manimgx.typing import (
        MatrixMN,
        Point3D,
        Point3D_Array,
        Point3DLike,
        Point3DLike_Array,
        Vector2DLike,
        Vector3D,
        Vector3DLike,
    )

    type AngleQuadrant = tuple[Literal[-1, 1], Literal[-1, 1]]
    "Which way along each of two crossing lines a side of an angle goes from the\n    crossing: a sign for each line, the first line's first; 1 along the line's\n    direction (from its start toward its end), -1 back toward its start."


class _TippedBase(_StyleBase, total=False):
    """TippedBase's keys, open, for the keywords that add to them."""

    tip_length: float
    """The length of the tips [add_tip][manimgx.TipableVMobject.add_tip] makes, in
    scene units (default 0.35; an [Arrow][manimgx.Arrow]'s may be shorter)."""
    normal_vector: Vector3DLike
    """The normal of the plane the path lies in (default OUT). Accepted for Manim
    compatibility; ignored and not retained."""
    tip_style: Style | None
    """Style keywords for the tips the path makes (default None: none). A tip's
    `fill_color` and `stroke_color` are the path's color unless given here."""


class TippedBase(_TippedBase, total=False, closed=True):
    """Every style keyword but `color`, and those of a path that can end in arrow tips
    (see [TipableVMobject][manimgx.TipableVMobject]).

    A class that takes `color` by position declares it itself, and the rest with this.
    """


class _Tipped(_TippedBase, total=False):
    """Tipped's keys, open, for the keywords that add to them."""

    color: Colors | None
    """The color of both fill and stroke (default white; a [Circle][manimgx.Circle]'s is
    red); None for the class's default."""


class Tipped(_Tipped, total=False, closed=True):
    """The style keywords, and those of a path that can end in arrow tips (see
    [TipableVMobject][manimgx.TipableVMobject])."""


class _ArcOptions(_Tipped, total=False):
    """ArcOptions's keys, open, for the keywords that add to them."""

    num_components: int
    """How many anchor points the arc is drawn through: it is one fewer cubic Bézier
    curves (default 9)."""
    arc_center: Point3DLike
    """Where the center of the arc's circle goes, in scene coordinates (default
    ORIGIN)."""


class ArcOptions(_ArcOptions, total=False, closed=True):
    """An arc's keywords, for the classes that build one and pass them on: how finely
    and where it is built, with the style and tip keywords."""


class SectorOptions(_ArcOptions, total=False, closed=True):
    """A [Sector][manimgx.Sector]'s keywords but its radius: its angles, with the arc
    keywords."""

    angle: float
    """The angle the sector spans, in radians: counterclockwise from `start_angle`, or
    clockwise if negative (default TAU / 4: a quarter turn)."""
    start_angle: float
    """The angle of its first edge, in radians, counterclockwise from the positive
    x-axis (default 0)."""


class ArcBetweenOptions(_Tipped, total=False, closed=True):
    """An [ArcBetweenPoints][manimgx.ArcBetweenPoints]'s keywords but its ends: its
    angle or its radius, with the style and tip keywords (for the classes that pass
    them on)."""

    angle: float
    """The angle the arc turns through on its way, in radians: counterclockwise if
    positive, bending it to the right of the straight way; clockwise if negative; a
    straight segment if 0 (default TAU / 4)."""
    radius: float | None
    """The radius of the arc's circle, in scene units, in place of `angle`: the shorter
    arc of that radius, bending right, or left if negative; at least half the distance
    between the ends (default None: set by `angle`)."""


def _similarity(
    a: Point3D, b: Point3D, c: Point3D, d: Point3D
) -> tuple[MatrixMN, MatrixMN]:
    """(the 3×4 map, its rotation) taking segment a→b onto c→d, as CE's `put_start_and_end_on`:
    scale and turn about a, then move."""
    ab, cd = b - a, d - c
    turn = rotation_matrix(*turn_between(ab, cd))
    linear = turn * (np.linalg.norm(cd) / np.linalg.norm(ab))
    return np.hstack([linear, (c - linear @ a)[:, None]]), turn


class TipableVMobject(VMobject):
    """A path that can end in arrow tips: what lines, arcs and arrows have in common.

    A tip is a small shape (an [ArrowTip][manimgx.ArrowTip]) added to the path as a
    submobject, at its end or its start, pointing along it. The tip's point goes where
    the path ended, and the path is fitted to stop at the tip's base. With tips, the
    path's [start][manimgx.TipableVMobject.get_start] and
    [end][manimgx.TipableVMobject.get_end] are the tips' points.

    Args:
        tip_length: The length of the tips [add_tip][manimgx.TipableVMobject.add_tip]
            makes, in scene units (default 0.35).
        normal_vector: The normal of the plane the path lies in. Accepted for Manim
            compatibility; ignored.
        tip_style: Style keywords for the tips the path makes; a tip's `fill_color` and
            `stroke_color` are the path's color unless given here.
    """

    _tip_positioned = False

    tip: ArrowTip
    """The tip at the path's end, once [add_tip][manimgx.TipableVMobject.add_tip] has
    made one."""
    start_tip: ArrowTip
    """The tip at the path's start, once `add_tip(at_start=True)` has made one."""

    def __init__(
        self,
        tip_length: float = DEFAULT_ARROW_TIP_LENGTH,
        normal_vector: Vector3DLike = OUT,
        tip_style: Style | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        self.tip_length: float = tip_length
        self.tip_style: Style = tip_style if tip_style is not None else {}
        super().__init__(**kwargs)

    def add_tip(
        self,
        tip: ArrowTip | None = None,
        tip_shape: type[ArrowTip] | None = None,
        tip_length: float | None = None,
        tip_width: float | None = None,
        at_start: bool = False,
    ) -> Self:
        """Add an arrow tip at the path's end, or its start, pointing along the path
        there.

        The tip's point goes where the path ended, and the path is scaled and turned
        about its other end to stop at the tip's base. The tip is a submobject, named
        [tip][manimgx.TipableVMobject.tip] (or `start_tip`), in the path's color unless
        `tip_style` gives it another.

        Args:
            tip: A tip made beforehand, to turn and move into place; None to make one.
            tip_shape: The class of the tip to make, an [ArrowTip][manimgx.ArrowTip]
                subclass; None for
                [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip].
            tip_length: The length of the tip to make, in scene units; None for the
                path's `tip_length`.
            tip_width: The width of the tip to make, if it is the default filled
                triangle, in scene units; None for the default length. Other shapes take
                no width: they are made at `tip_length` alone.
            at_start: Whether the tip goes at the path's start, pointing back along it.

        Examples:
            ```python
            import manimgx as m


            class TipableVMobjectAddTipExample(m.Scene):
                def construct(self) -> None:
                    line = m.Line(3 * m.LEFT, 3 * m.RIGHT, color=m.BLUE).add_tip()
                    both = m.Line(3 * m.LEFT, 3 * m.RIGHT, color=m.GREEN)
                    both.add_tip(tip_shape=m.StealthTip)
                    both.add_tip(tip_shape=m.ArrowCircleFilledTip, at_start=True)
                    arc = m.Arc(radius=2, angle=m.PI, color=m.YELLOW)
                    arc.add_tip(tip_length=0.5, tip_width=0.5)
                    self.add(m.VGroup(line, both, arc).arrange(m.DOWN, buff=1))
            ```
        """
        if tip is None:
            tip = self.create_tip(tip_shape, tip_length, tip_width, at_start)
        else:
            self.position_tip(tip, at_start)
        self.reset_endpoints_based_on_tip(tip, at_start)
        self.assign_tip_attr(tip, at_start)
        self.add(tip)
        return self

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def create_tip(
        self,
        tip_shape: type[ArrowTip] | None = None,
        tip_length: float | None = None,
        tip_width: float | None = None,
        at_start: bool = False,
    ) -> ArrowTip:
        """Make a tip for the path's end, or its start, pointing along the path there;
        the tip is not added (see [add_tip][manimgx.TipableVMobject.add_tip]).

        Args:
            tip_shape: The class of the tip, an [ArrowTip][manimgx.ArrowTip] subclass;
                None for [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip].
            tip_length: Its length, in scene units; None for the path's
                [default][manimgx.TipableVMobject.get_default_tip_length].
            tip_width: Its width, if it is the default filled triangle, in scene units;
                None for the default length.
            at_start: Whether it is for the path's start, pointing back along it.

        Returns:
            A new tip, in place.
        """
        tip = self.get_unpositioned_tip(tip_shape, tip_length, tip_width)
        self.position_tip(tip, at_start)
        return tip

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def get_unpositioned_tip(
        self,
        tip_shape: type[ArrowTip] | None = None,
        tip_length: float | None = None,
        tip_width: float | None = None,
    ) -> ArrowTip:
        """Make a tip in the path's style, not yet in place: what
        [add_tip][manimgx.TipableVMobject.add_tip] makes before it turns and moves it to
        an end.

        The tip's `fill_color` and `stroke_color` are the path's color, with the path's
        `tip_style` over them. The default filled triangle is made `tip_length` long and
        `tip_width` wide; another shape is made at `tip_length`, as its class makes it.

        Args:
            tip_shape: The class of the tip; None for
                [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip].
            tip_length: Its length, in scene units; None for the path's
                [default][manimgx.TipableVMobject.get_default_tip_length].
            tip_width: The width of the default filled triangle, in scene units; None
                for the default length.

        Returns:
            A new tip.
        """
        # The default tip is given its width too (the default length unless given, as
        # in CE), and a triangle scales with its two sides: it is the unit triangle of
        # their ratio, scaled, one prototype per ratio whatever the size. Another
        # class's shape need not scale with its length (ArrowTriangleTip's width does
        # not), so its tip is made at its size.

        default = self.get_default_tip_length()
        length = default if tip_length is None else tip_length
        color = self.get_color()
        style: Style = {"fill_color": color, "stroke_color": color}
        style.update(self.tip_style)
        if tip_shape is not None and tip_shape is not ArrowTriangleFilledTip:
            return tip_shape(length=length, **style)
        width = default if tip_width is None else tip_width
        if length <= 0:
            return ArrowTriangleFilledTip(length=length, width=width, **style)
        unit = ArrowTriangleFilledTip(length=1.0, width=width / length, **style)
        return unit.scale(length)

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def position_tip(self, tip: ArrowTip, at_start: bool = False) -> ArrowTip:
        """Turn and move a tip onto the path's end, or its start: pointing along the
        path there, its point on the end.

        [add_tip][manimgx.TipableVMobject.add_tip] and
        [create_tip][manimgx.TipableVMobject.create_tip] call it; the path does not
        change.

        Args:
            tip: The tip to place.
            at_start: Whether to place it at the path's start, pointing back along it.

        Returns:
            The tip, in place.
        """
        anchor = self.get_start() if at_start else self.get_end()
        angles = cartesian_to_spherical(self._toward(at_start) - anchor)
        turn = rotation_matrix(angles[1] - PI - tip.tip_angle, OUT)
        if not self._tip_positioned:
            axis = np.array([np.sin(angles[1]), -np.cos(angles[1]), 0])
            turn = rotation_matrix(-angles[2] + PI / 2, axis) @ turn
            self._tip_positioned = True
        # one rigid map, x ↦ R(x − tip point) + anchor: the tip turns to point along the curve,
        # and its tip point, a point of its own, lands on the curve's end (CE's turns about the
        # center and its move are this map)
        point = tip.tip_point
        tip._geometry = tip._geometry.transformed(
            np.hstack([turn, (anchor - turn @ point)[:, None]])
        )
        tip._rotate_direction_state(turn)
        return tip

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def reset_endpoints_based_on_tip(self, tip: ArrowTip, at_start: bool) -> Self:
        """Fit the path to stop at a tip's base: scale and turn it about its other end,
        which stays.

        [add_tip][manimgx.TipableVMobject.add_tip] calls it once the tip is in place. A
        path of no length stays as it is.

        Args:
            tip: The tip, in place at the path's end (or its start).
            at_start: Whether the tip is at the path's start.
        """
        # `put_start_and_end_on`, one map — on the curve alone while no tip is on it yet
        # (a class's own `scale` is not called: it is the curve that is fitted, not the
        # object resized)
        if self.get_length() == 0:
            return self
        start, end = (
            (tip.base, self.get_end()) if at_start else (self.get_start(), tip.base)
        )
        if self.submobjects:  # tips already on it move with it, as CE moves them
            return self.put_start_and_end_on(start, end)
        m, turn = _similarity(*self.get_start_and_end(), start, end)
        self._geometry = self._geometry.transformed(m)
        self._rotate_direction_state(turn)
        return self

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def assign_tip_attr(self, tip: ArrowTip, at_start: bool) -> Self:
        """Name a tip as the path's [tip][manimgx.TipableVMobject.tip], or its
        [start_tip][manimgx.TipableVMobject.start_tip]; the tip is not added.

        [add_tip][manimgx.TipableVMobject.add_tip] calls it.

        Args:
            at_start: Whether it is the tip at the path's start.
        """
        if at_start:
            self.start_tip = tip
        else:
            self.tip = tip
        return self

    def has_tip(self) -> bool:
        """Whether the path has a tip at its end: its
        [tip][manimgx.TipableVMobject.tip], among its submobjects.
        """
        tip = self.__dict__.get("tip")
        return tip is not None and any(m is tip for m in self.submobjects)

    def has_start_tip(self) -> bool:
        """Whether the path has a tip at its start: its
        [start_tip][manimgx.TipableVMobject.start_tip], among its submobjects.
        """
        tip = self.__dict__.get("start_tip")
        return tip is not None and any(m is tip for m in self.submobjects)

    def pop_tips(self) -> VGroup[ArrowTip]:
        """Remove the path's tips, and fit the path back between its start and its end
        as they were: the tips' points.

        Returns:
            The tips removed, the end tip first, in a new group (empty if there were
            none).
        """

        start, end = self.get_start_and_end()
        result = VGroup[ArrowTip]()
        if self.has_tip():
            result.add(self.tip)
            self.remove(self.tip)
        if self.has_start_tip():
            result.add(self.start_tip)
            self.remove(self.start_tip)
        if result.submobjects:
            self.put_start_and_end_on(start, end)
        return result

    def get_tips(self) -> VGroup[ArrowTip]:
        """The tips the path has been given: its [tip][manimgx.TipableVMobject.tip] and
        its [start_tip][manimgx.TipableVMobject.start_tip], those it has had.

        A tip [pop_tips][manimgx.TipableVMobject.pop_tips] removed is still named, and
        listed here; [has_tip][manimgx.TipableVMobject.has_tip] tells whether it is on
        the path.

        Returns:
            The tips, the end tip first, in a new group.
        """

        result = VGroup[ArrowTip]()
        if hasattr(self, "tip"):
            result.add(self.tip)
        if hasattr(self, "start_tip"):
            result.add(self.start_tip)
        return result

    def get_tip(self) -> ArrowTip:
        """The path's tip: the one at its end, or the one at its start if it has none
        there.

        It is the first of [get_tips][manimgx.TipableVMobject.get_tips]; a path never
        given a tip raises an exception.
        """
        tips = self.get_tips()
        if not tips.submobjects:
            raise Exception("tip not found")
        return tips[0]

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def get_default_tip_length(self) -> float:
        """The length of the tips the path makes unless given one: its `tip_length`.

        Returns:
            The length, in scene units.
        """
        return self.tip_length

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def get_first_handle(self) -> Point3D:
        """The path's first handle: the control point after its first point, toward
        which it leaves its start.

        Returns:
            The point, in scene coordinates.
        """
        first_handle: Point3D = self.points[1]
        return first_handle

    def _toward(self, at_start: bool) -> Point3D:
        """The point the path leaves its start toward, or comes into its end from: the
        nearest of the end curve's control points apart from its end, so a tip points
        along the path where a handle has no length (a curve arrives along P3 − P1 when
        P2 = P3)."""
        curve = self.points[:4] if at_start else self.points[-4:][::-1]
        end = curve[0]
        for point in curve[1:]:
            if np.linalg.norm(point - end) > 1e-9 * (1 + np.abs(end).max()):
                return point
        return curve[1]

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def get_last_handle(self) -> Point3D:
        """The path's last handle: the control point before its last point, from which
        it comes into its end.

        Returns:
            The point, in scene coordinates.
        """
        last_handle: Point3D = self.points[-2]
        return last_handle

    def get_end(self) -> Point3D:
        """Where the path ends: its end tip's point, if it has an end tip, and otherwise
        its last point.

        Returns:
            The point, in scene coordinates.
        """
        if self.has_tip():
            return np.array(self.tip.tip_point)
        else:
            return super().get_end()

    def get_start(self) -> Point3D:
        """Where the path starts: its start tip's point, if it has a start tip, and
        otherwise its first point.

        Returns:
            The point, in scene coordinates.
        """
        if self.has_start_tip():
            return np.array(self.start_tip.tip_point)
        else:
            return super().get_start()

    def get_length(self) -> float:
        """The distance from the path's start to its end, tips included: straight
        across, so an arc's chord, not the length along it.

        Returns:
            The distance, in scene units.
        """
        start, end = self.get_start_and_end()
        return float(np.linalg.norm(start - end))


def _unit_arc(start: float, angle: float, n: int) -> np.ndarray:
    """CE's arc on the unit circle: n anchors, handles along the tangents."""
    a = np.linspace(start, start + angle, n)
    anchors = np.stack([np.cos(a), np.sin(a), np.zeros(n)], axis=1)
    tangents = np.stack([-anchors[:, 1], anchors[:, 0], np.zeros(n)], axis=1)
    factor = 4 / 3 * np.tan(angle / (n - 1.0) / 4)
    curves = np.empty((n - 1, 4, 3))
    curves[:, 0], curves[:, 3] = anchors[:-1], anchors[1:]
    curves[:, 1] = anchors[:-1] + factor * tangents[:-1]
    curves[:, 2] = anchors[1:] - factor * tangents[1:]
    return curves.reshape(-1, 3)


class Arc(TipableVMobject):
    r"""An arc of a circle: from the angle `start_angle` through `angle`,
    counterclockwise if `angle` is positive; white unless styled.

    Angles are in radians, about the arc's center, counterclockwise from the positive
    x-axis. The arc is drawn through `num_components` points spaced evenly along it,
    joined by cubic Bézier curves.

    Args:
        radius: The radius, in scene units; None for 1.
        start_angle: The angle of the arc's first point.
        angle: How far the arc goes: counterclockwise if positive, clockwise if
            negative; TAU for a whole circle.
        num_components: How many anchor points it is drawn through: the arc is one
            fewer cubic Bézier curves.
        arc_center: Where the center of its circle goes.

    Examples:
        ```python
        import manimgx as m


        class ArcExample(m.Scene):
            def construct(self) -> None:
                arcs = m.VGroup(
                    m.Arc(radius=1.5, angle=m.PI, color=m.BLUE),
                    m.Arc(radius=1.5, start_angle=m.PI / 2, angle=3 * m.PI / 2),
                    m.Arc(radius=1.5, angle=-m.PI / 2, color=m.YELLOW),
                ).arrange(buff=1.5)
                labels = ("angle=PI", "start_angle=PI/2\nangle=3*PI/2", "angle=-PI/2")
                for arc, label in zip(arcs, labels):
                    self.add(m.Text(label, font_size=28).next_to(arc, m.DOWN))
                self.play(m.Create(arcs, run_time=3))
        ```
    """

    def __init__(
        self,
        radius: float | None = 1.0,
        start_angle: float = 0,
        angle: float = TAU / 4,
        num_components: int = 9,
        arc_center: Point3DLike = ORIGIN,
        **kwargs: Unpack[Tipped],
    ):
        if radius is None:
            radius = 1.0
        self.radius = radius
        self.num_components = num_components
        self.arc_center: Point3D = np.asarray(arc_center)
        self.start_angle = start_angle
        self.angle = angle
        self._failed_to_get_center: bool = False
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        # the unit arc of this start, angle and number of pieces (a defined shape),
        # placed by radius and center
        start, angle, n = self.start_angle, self.angle, self.num_components
        shape = defined(("arc", start, angle, n), lambda: _unit_arc(start, angle, n))
        m = np.zeros((3, 4))
        m[0, 0] = m[1, 1] = m[2, 2] = self.radius
        m[:, 3] = self.arc_center
        self._geometry = Blend(((m, shape),), len(shape.array))
        return self

    def get_arc_center(self, warning: bool = True) -> Point3D:
        """The center of the arc's circle, where it is now, in whatever plane it lies:
        the center of the circle through its first curve's ends and middle.

        If there is none (a straight path), it is the origin, with a warning.

        Args:
            warning: Whether to warn when the center cannot be found.

        Returns:
            The point, in scene coordinates.
        """
        a1, h1, h2, a2 = self.points[:4]
        if np.all(a1 == a2):
            return np.copy(a1)
        middle = (a1 + 3 * (h1 + h2) + a2) / 8  # on the circle, as an arc's curve is
        u, v = a1 - middle, a2 - middle
        normal = np.cross(u, v)
        if np.linalg.norm(normal) <= 1e-12 * max(u @ u, v @ v):
            if warning:
                warnings.warn(
                    "Can't find Arc center, using ORIGIN instead", stacklevel=1
                )
            self._failed_to_get_center = True
            return np.array(ORIGIN)
        return middle + np.cross((u @ u) * v - (v @ v) * u, normal) / (
            2 * normal @ normal
        )

    def move_arc_center_to(self, point: Point3DLike) -> Self:
        """Move the arc so the center of its circle is at a point.

        Args:
            point: Where the center goes, in scene coordinates.
        """
        self.shift(point - self.get_arc_center())
        return self

    def stop_angle(self) -> float:
        """The angle at which the arc ends: the angle of its last point about its
        [center][manimgx.Arc.get_arc_center].

        Returns:
            The angle, in radians, counterclockwise from the positive x-axis, from 0 up
            to TAU.
        """
        return angle_of_vector(self.points[-1] - self.get_arc_center()) % TAU


class ArcBetweenPoints(Arc):
    """An arc from one point to another, through an angle or of a radius; white unless
    styled.

    Going from `start` to `end`, a positive angle turns counterclockwise, bending the
    arc to the right of the straight way; a negative angle bends it to the left, and 0
    makes it a straight segment.

    Args:
        start: Where the arc starts.
        end: Where it ends.
        angle: The angle it turns through on its way, in radians.
        radius: The radius of its circle, in scene units, in place of `angle`: the
            shorter arc of that radius, bending right, or left if negative. It must be
            at least half the distance between the ends. None to use `angle`.
        **kwargs: [Arc keywords][manimgx.mobjects.shapes.ArcOptions]; `arc_center`
            has no effect, as the ends place the arc.

    Examples:
        ```python
        import manimgx as m


        class ArcBetweenPointsExample(m.Scene):
            def construct(self) -> None:
                start, end = 3 * m.LEFT + m.DOWN, 3 * m.RIGHT + m.DOWN
                arcs = m.VGroup(
                    m.ArcBetweenPoints(start, end, color=m.BLUE),
                    m.ArcBetweenPoints(start, end, radius=-4, color=m.GREEN),
                    m.ArcBetweenPoints(start, end, angle=-m.PI, color=m.YELLOW),
                )
                self.add(m.Dot(start, radius=0.12), m.Dot(end, radius=0.12))
                self.play(m.Create(arcs, run_time=3))
        ```
    """

    def __init__(
        self,
        start: Point3DLike,
        end: Point3DLike,
        angle: float = TAU / 4,
        radius: float | None = None,
        **kwargs: Unpack[ArcOptions],
    ) -> None:
        if radius is not None:
            self.radius = radius
            if radius < 0:
                sign = -2
                radius *= -1
            else:
                sign = 2
            halfdist = np.linalg.norm(np.array(start) - np.array(end)) / 2
            if radius < halfdist:
                raise ValueError(
                    "ArcBetweenPoints called with a radius that is\n                   "
                    "         smaller than half the distance between the points."
                )
            arc_height = radius - np.sqrt(radius**2 - halfdist**2)
            angle = np.arccos((radius - arc_height) / radius) * sign
        super().__init__(radius=radius, angle=angle, **kwargs)
        if angle == 0:
            self.set_points_as_corners(np.array([LEFT, RIGHT]))
        self.put_start_and_end_on(start, end)
        if radius is None:
            center = self.get_arc_center(warning=False)
            if not self._failed_to_get_center:
                self.radius = cast(
                    float, np.linalg.norm(np.array(start) - np.array(center))
                )
            else:
                self.radius = np.inf


class CurvedArrow(ArcBetweenPoints):
    """An arrow along an arc: an [ArcBetweenPoints][manimgx.ArcBetweenPoints] with a tip
    at its end, bending right on its way by default; white unless styled.

    Args:
        start_point: Where the arrow starts.
        end_point: Where it points to: its tip's point.
        tip_shape: The class of its tip; None for
            [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip].
        **kwargs:
            [ArcBetweenPoints keywords][manimgx.ArcBetweenPoints]:
            its angle (a quarter turn unless given) or its radius, style and tips.

    Examples:
        ```python
        import manimgx as m


        class CurvedArrowExample(m.Scene):
            def construct(self) -> None:
                start, end = 3 * m.LEFT + 0.5 * m.UP, 3 * m.RIGHT + 0.5 * m.UP
                arrows = m.VGroup(
                    m.CurvedArrow(start, end, color=m.BLUE),
                    m.CurvedArrow(start, end, angle=m.PI, color=m.YELLOW),
                    m.CurvedArrow(end, start, color=m.GREEN),
                    m.CurvedArrow(end, start, radius=3.2, tip_shape=m.StealthTip),
                )
                self.add(m.Dot(start, radius=0.12), m.Dot(end, radius=0.12))
                self.play(m.Create(arrows, run_time=4))
        ```
    """

    def __init__(
        self,
        start_point: Point3DLike,
        end_point: Point3DLike,
        *,
        tip_shape: type[ArrowTip] | None = None,
        **kwargs: Unpack[ArcBetweenOptions],
    ) -> None:

        super().__init__(start_point, end_point, **kwargs)
        self.add_tip(tip_shape=tip_shape or ArrowTriangleFilledTip)


class CurvedDoubleArrow(CurvedArrow):
    """An arrow along an arc with a tip at each end: an
    [ArcBetweenPoints][manimgx.ArcBetweenPoints] with two tips, bending right on its way
    by default; white unless styled.

    Args:
        start_point: Where the arrow starts: its start tip's point.
        end_point: Where it ends: its end tip's point.
        tip_shape_start: The class of the tip at its start; None for
            [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip].
        tip_shape_end: The class of the tip at its end; None for
            [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip].
        **kwargs:
            [ArcBetweenPoints keywords][manimgx.ArcBetweenPoints]:
            its angle (a quarter turn unless given) or its radius, style and tips.

    Examples:
        ```python
        import manimgx as m


        class CurvedDoubleArrowExample(m.Scene):
            def construct(self) -> None:
                left = m.Circle(radius=1, color=m.BLUE).shift(4 * m.LEFT)
                right = m.Square(side_length=2, color=m.GREEN).shift(4 * m.RIGHT)
                top = left.get_top(), right.get_top()
                arrows = m.VGroup(
                    m.CurvedDoubleArrow(*top, angle=-m.PI / 3),
                    m.CurvedDoubleArrow(
                        left.get_bottom(),
                        right.get_bottom(),
                        tip_shape_start=m.ArrowCircleFilledTip,
                        tip_shape_end=m.StealthTip,
                        color=m.YELLOW,
                    ),
                )
                self.add(left, right)
                self.play(m.Create(arrows, run_time=2))
        ```
    """

    def __init__(
        self,
        start_point: Point3DLike,
        end_point: Point3DLike,
        *,
        tip_shape_start: type[ArrowTip] | None = None,
        tip_shape_end: type[ArrowTip] | None = None,
        **kwargs: Unpack[ArcBetweenOptions],
    ) -> None:

        super().__init__(start_point, end_point, tip_shape=tip_shape_end, **kwargs)
        self.add_tip(at_start=True, tip_shape=tip_shape_start or ArrowTriangleFilledTip)


class Circle(Arc):
    """A circle: drawn counterclockwise from its rightmost point, red unless styled.

    Args:
        radius: The radius, in scene units; None for 1.
        color: The color, which may be given by position (`Circle(1, BLUE)`); None for
            red.
        num_components: How many anchor points it is drawn through: the circle is one
            fewer cubic Bézier arcs.
        arc_center: Where its center goes.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style].

    Examples:
        ```python
        import manimgx as m


        class CircleExample(m.Scene):
            def construct(self) -> None:
                circles = m.VGroup(
                    m.Circle(color=m.BLUE),
                    m.Circle(radius=1.5, color=m.GREEN, fill_opacity=0.5),
                    m.Circle(radius=2, color=m.YELLOW, stroke_width=12),
                ).arrange(buff=1)
                self.play(m.Create(circles))
        ```
    """

    defaults: ClassVar[Style] = {"color": RED}

    def __init__(
        self,
        radius: float | None = None,
        color: Colors | None = None,
        *,
        num_components: int = 9,
        arc_center: Point3DLike = ORIGIN,
        **kwargs: Unpack[TippedBase],
    ) -> None:
        style = Tipped(**kwargs) if color is None else Tipped(**kwargs, color=color)
        super().__init__(
            radius=radius,
            start_angle=0,
            angle=TAU,
            num_components=num_components,
            arc_center=arc_center,
            **style,
        )

    def surround(
        self,
        mobject: Mobject,
        dim_to_match: int = 0,
        stretch: bool = False,
        buff: float = 0,
        *,
        buffer_factor: float = 1.2,
    ) -> Self:
        """Fit the circle around a mobject: through the corners of its bounding box, enlarged
        by `buffer_factor`, then `buff` farther out.

        Args:
            mobject: The mobject to surround.
            dim_to_match: The dimension (0, 1 or 2) of `mobject` the circle is first fitted
                to, before it grows to the corners.
            stretch: Whether that first fit stretches the circle into an ellipse matching the
                bounding box.
            buff: How much farther out the circle goes, in scene units.
            buffer_factor: How much larger than through the corners the circle is.

        Examples:
            ```python
            import manimgx as m


            class CircleSurroundExample(m.Scene):
                def construct(self) -> None:
                    word = m.Text("manimgx", font_size=120)
                    ring = m.Circle(color=m.YELLOW).surround(word)
                    self.add(word)
                    self.play(m.Create(ring))
            ```
        """
        self.replace(mobject, dim_to_match, stretch)
        self.width = np.sqrt(mobject.width**2 + mobject.height**2)
        self.scale(buffer_factor)
        return self.scale((self.width / 2 + buff) / (self.width / 2)) if buff else self

    def point_at_angle(self, angle: float) -> Point3D:
        """The point of the circle at an angle from its start, its rightmost point.

        Args:
            angle: The angle, in radians, counterclockwise; any angle wraps around.

        Returns:
            The point, in scene coordinates.
        """
        proportion = angle / TAU
        proportion -= np.floor(proportion)
        return self.point_from_proportion(proportion)

    @staticmethod
    def from_three_points(
        p1: Point3DLike, p2: Point3DLike, p3: Point3DLike, **kwargs: Unpack[Tipped]
    ) -> Circle:
        """The circle through three points.

        Args:
            p1: A point on the circle.
            p2: A second point on it.
            p3: A third point on it, not on the line through the other two.
            **kwargs: [Style keywords][manimgx.drawing.paint.Style].

        Returns:
            A new circle.
        """
        center = line_intersection(
            perpendicular_bisector([np.asarray(p1), np.asarray(p2)]),
            perpendicular_bisector([np.asarray(p2), np.asarray(p3)]),
        )
        radius = float(np.linalg.norm(np.asarray(p1, dtype=float) - center))
        return Circle(radius=radius, **kwargs).shift(center)


class Dot(Circle):
    """A dot: a small filled disc, white and without an outline unless styled.

    Args:
        point: Where its center goes.
        radius: Its radius, in scene units (default 0.08).

    Examples:
        ```python
        import manimgx as m


        class DotExample(m.Scene):
            def construct(self) -> None:
                self.add(
                    m.Dot([-5, 0, 0]),
                    m.Dot([-3.5, 0, 0], radius=0.2, color=m.BLUE),
                    m.Dot([-1, 0, 0], radius=0.6, color=m.YELLOW),
                    m.Dot([3, 0, 0], radius=1.5, color=m.GREEN, fill_opacity=0.5),
                )
        ```
    """

    defaults: ClassVar[Style] = {"stroke_width": 0, "fill_opacity": 1.0, "color": WHITE}

    def __init__(
        self,
        point: Point3DLike = ORIGIN,
        radius: float = DEFAULT_DOT_RADIUS,
        **kwargs: Unpack[Tipped],
    ) -> None:
        super().__init__(radius=radius, arc_center=point, **kwargs)


class AnnotationDot(Dot):
    """A dot to mark a point with: a little larger than a [Dot][manimgx.Dot], blue with
    a thick white outline unless styled.

    Its colors are its `fill_color` and its `stroke_color`, which `color` does not
    change.

    Args:
        radius: Its radius, in scene units (default 0.104, 1.3 times a dot's).
        point: Where its center goes.

    Examples:
        ```python
        import manimgx as m


        class AnnotationDotExample(m.Scene):
            def construct(self) -> None:
                arc = m.Arc(radius=3, angle=m.PI, color=m.GREY).shift(1.5 * m.DOWN)
                start = m.AnnotationDot(point=arc.get_start())
                end = m.AnnotationDot(point=arc.get_end())
                top = m.AnnotationDot(
                    0.25, point=arc.get_top(), fill_color=m.YELLOW, stroke_color=m.RED
                )
                self.add(arc, start, end, top)
        ```
    """

    defaults: ClassVar[Style] = {
        "stroke_width": 5,
        "stroke_color": WHITE,
        "fill_color": BLUE,
    }

    def __init__(
        self,
        radius: float = DEFAULT_DOT_RADIUS * 1.3,
        *,
        point: Point3DLike = ORIGIN,
        **kwargs: Unpack[Tipped],
    ) -> None:
        super().__init__(point=point, radius=radius, **kwargs)


class Ellipse(Circle):
    """An ellipse: a circle stretched to a width and a height, red unless styled.

    Like a circle, it is drawn counterclockwise from its rightmost point.

    Args:
        width: Its width, in scene units: its extent along x.
        height: Its height, in scene units: its extent along y.

    Examples:
        ```python
        import manimgx as m


        class EllipseExample(m.Scene):
            def construct(self) -> None:
                ellipses = m.VGroup(
                    m.Ellipse(),
                    m.Ellipse(width=2, height=4, color=m.BLUE),
                    m.Ellipse(width=5, height=2, color=m.YELLOW, fill_opacity=0.5),
                ).arrange(buff=1)
                self.add(ellipses)
        ```
    """

    def __init__(
        self, width: float = 2, height: float = 1, **kwargs: Unpack[ArcOptions]
    ) -> None:
        super().__init__(**kwargs)
        self.stretch_to_fit_width(width)
        self.stretch_to_fit_height(height)


class AnnularSector(Arc):
    """A sector of a ring: the region between two arcs of one center, over one angle;
    white and filled, without an outline, unless styled.

    Args:
        inner_radius: The inner arc's radius, in scene units.
        outer_radius: The outer arc's radius, in scene units.
        angle: The angle it spans, in radians: counterclockwise from `start_angle`, or
            clockwise if negative.
        start_angle: The angle of its first edge, in radians, counterclockwise from the
            positive x-axis.
        **kwargs: [Arc keywords][manimgx.mobjects.shapes.ArcOptions];
            `num_components` has no effect.

    Examples:
        ```python
        import manimgx as m


        class AnnularSectorExample(m.Scene):
            def construct(self) -> None:
                sectors = m.VGroup(
                    m.AnnularSector(),
                    m.AnnularSector(1.5, 2, angle=m.PI, color=m.BLUE),
                    m.AnnularSector(
                        0.5, 2, angle=-3 * m.PI / 2, start_angle=m.PI, color=m.YELLOW
                    ),
                ).arrange(buff=1)
                self.add(sectors)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 0, "color": WHITE}

    def __init__(
        self,
        inner_radius: float = 1,
        outer_radius: float = 2,
        angle: float = TAU / 4,
        start_angle: float = 0,
        **kwargs: Unpack[ArcOptions],
    ) -> None:
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        super().__init__(start_angle=start_angle, angle=angle, **kwargs)

    def generate_points(self) -> Self:
        arc = _unit_arc(self.start_angle, self.angle, 9)
        inner = arc * self.inner_radius + self.arc_center
        outer = arc[::-1] * self.outer_radius + self.arc_center
        self.append_points(inner)
        self.add_line_to(outer[0])
        self.append_points(outer)
        self.add_line_to(inner[0])
        return self


class Sector(AnnularSector):
    """A sector of a disc, a slice of pie: the region between two radii and the arc
    joining them; white and filled, without an outline, unless styled.

    Args:
        radius: Its radius, in scene units.
        **kwargs: [Sector keywords][manimgx.mobjects.shapes.SectorOptions]: its
            angles (a quarter turn from the positive x-axis unless given), style and
            center; `num_components` has no effect.

    Examples:
        ```python
        import manimgx as m


        class SectorExample(m.Scene):
            def construct(self) -> None:
                sectors = m.VGroup(
                    m.Sector(radius=2),
                    m.Sector(radius=2, angle=m.PI / 3, start_angle=m.PI, color=m.BLUE),
                    m.Sector(radius=2, angle=-5 * m.PI / 3, color=m.YELLOW),
                ).arrange(buff=1)
                self.add(sectors)
        ```
    """

    def __init__(self, radius: float = 1, **kwargs: Unpack[SectorOptions]) -> None:
        super().__init__(inner_radius=0, outer_radius=radius, **kwargs)


class Annulus(Circle):
    """A ring: the region between two circles of one center; white and filled, without
    an outline, unless styled.

    The inner circle runs clockwise, the other way around from the outer one, so it is
    a hole in the fill.

    Args:
        inner_radius: The inner circle's radius, in scene units.
        outer_radius: The outer circle's radius, in scene units.
        mark_paths_closed: Accepted for Manim compatibility; ignored.
        **kwargs: [Arc keywords][manimgx.mobjects.shapes.ArcOptions];
            `num_components` has no effect.

    Examples:
        ```python
        import manimgx as m


        class AnnulusExample(m.Scene):
            def construct(self) -> None:
                rings = m.VGroup(
                    m.Annulus(),
                    m.Annulus(inner_radius=1.5, outer_radius=2, color=m.BLUE),
                    m.Annulus(inner_radius=0.5, outer_radius=1.5, color=m.YELLOW),
                ).arrange(buff=1)
                self.add(rings)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 0, "color": WHITE}

    def __init__(
        self,
        inner_radius: float = 1,
        outer_radius: float = 2,
        mark_paths_closed: bool = False,
        **kwargs: Unpack[ArcOptions],
    ) -> None:
        self.mark_paths_closed = mark_paths_closed
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        self.radius = self.outer_radius
        arc = _unit_arc(0, TAU, 9)
        self.append_points(arc * self.outer_radius)
        self.append_points(arc[::-1] * self.inner_radius)
        self.shift(self.arc_center)
        return self


class CubicBezier(VMobject):
    """A cubic Bézier curve: from one anchor to another, pulled toward two handles;
    white unless styled.

    The curve leaves its start heading toward `start_handle` and comes into its end
    from the direction of `end_handle`; the farther a handle, the longer the curve
    keeps to its direction. It passes through neither handle.

    Args:
        start_anchor: Where the curve starts.
        start_handle: The handle of its start.
        end_handle: The handle of its end.
        end_anchor: Where the curve ends.

    Examples:
        ```python
        import manimgx as m


        class CubicBezierExample(m.Scene):
            def construct(self) -> None:
                start, end = [-5, -2, 0], [5, -2, 0]
                handle1, handle2 = [-3, 3, 0], [6, 3, 0]
                curve = m.CubicBezier(start, handle1, handle2, end, color=m.YELLOW)
                levers = m.VGroup(m.Line(start, handle1), m.Line(end, handle2))
                levers.set_stroke(m.GREY, width=2)
                anchors = m.VGroup(m.Dot(start), m.Dot(end)).set_color(m.BLUE)
                handles = m.VGroup(m.Dot(handle1), m.Dot(handle2)).set_color(m.RED)
                self.add(levers, anchors, handles)
                self.play(m.Create(curve, run_time=2))
        ```
    """

    def __init__(
        self,
        start_anchor: Point3DLike,
        start_handle: Point3DLike,
        end_handle: Point3DLike,
        end_anchor: Point3DLike,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(**kwargs)
        self.add_cubic_bezier_curve(start_anchor, start_handle, end_handle, end_anchor)


class ArcPolygon(VMobject):
    """A polygon whose sides are arcs: an [ArcBetweenPoints][manimgx.ArcBetweenPoints]
    from each vertex to the next, and from the last back to the first; white unless
    styled.

    Going around the vertices counterclockwise, arcs of a positive angle bulge out, and
    arcs of a negative one bend in. Its outline runs along the arcs, and is filled and
    stroked in its style. The arcs are also its submobjects, its
    [arcs][manimgx.ArcPolygon.arcs], drawn over its outline in their own style (white
    unless `arc_config` styles them): to color the whole, style them too, as a family
    method such as [set_color][manimgx.Mobject.set_color] does.

    Args:
        *vertices: The vertices, in order around it.
        angle: The angle every arc turns through, in radians, unless `radius` or
            `arc_config` is given.
        radius: The radius of every arc, in scene units, in place of `angle`, unless
            `arc_config` is given; None (or 0) to use `angle`.
        arc_config: The arcs' [ArcBetweenPoints
            keywords][manimgx.ArcBetweenPoints], in place of
            `angle` and `radius`: one set for every arc, or a list of one per side, the
            first vertex's side first.

    Examples:
        ```python
        import manimgx as m


        class ArcPolygonExample(m.Scene):
            def construct(self) -> None:
                a, b, c = [0, 0, 0], [2.5, 0, 0], [0, 2.5, 0]
                sides = [{"radius": 2, "color": m.RED}, {"angle": 0}, {"angle": 1}]
                shapes = m.VGroup(
                    m.ArcPolygon(a, b, c),
                    m.ArcPolygon(a, b, c, radius=2, fill_opacity=0.5).set_color(m.BLUE),
                    m.ArcPolygon(a, b, c, angle=-m.PI / 3).set_color(m.GREEN),
                    m.ArcPolygon(a, b, c, arc_config=sides),
                ).arrange(buff=0.6)
                self.play(m.Create(shapes, run_time=4))
        ```
    """

    def __init__(
        self,
        *vertices: Point3DLike,
        angle: float = PI / 4,
        radius: float | None = None,
        arc_config: ArcBetweenOptions | list[ArcBetweenOptions] | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        n = len(vertices)
        point_pairs = [(vertices[k], vertices[(k + 1) % n]) for k in range(n)]
        all_arc_configs: Iterable[ArcBetweenOptions]
        if not arc_config:
            config_: ArcBetweenOptions = (
                {"radius": radius} if radius else {"angle": angle}
            )
            all_arc_configs = itertools.repeat(config_, len(point_pairs))
        elif isinstance(arc_config, list):
            assert len(arc_config) == n
            all_arc_configs = arc_config
        else:
            all_arc_configs = itertools.repeat(arc_config, len(point_pairs))
        arcs = [
            ArcBetweenPoints(*pair, **conf)
            for pair, conf in zip(point_pairs, all_arc_configs, strict=True)
        ]
        super().__init__(**kwargs)
        self.add(*arcs)
        for arc in arcs:
            self.append_points(arc.points)
        self.arcs = arcs
        """The arcs, one per side, the first vertex's side first; they are also its
        submobjects."""


class ArcPolygonFromArcs(VMobject):
    """A closed shape made of arcs: each arc in turn, joined to the next by a straight
    line where they do not meet, and the last to the first; white unless styled.

    Its outline is filled and stroked in its style. The arcs are also its submobjects,
    its [arcs][manimgx.ArcPolygonFromArcs.arcs], drawn over its outline in their own
    style: to color the whole, style them too, as a family method such as
    [set_color][manimgx.Mobject.set_color] does.

    Args:
        *arcs: The arcs, in order around it: [Arc][manimgx.Arc]s, or
            [ArcBetweenPoints][manimgx.ArcBetweenPoints].

    Examples:
        ```python
        import manimgx as m


        class ArcPolygonFromArcsExample(m.Scene):
            def construct(self) -> None:
                a, b, c = [-5.5, -1.3, 0], [-2.5, -1.3, 0], [-4, 1.3, 0]
                pairs = (a, b), (b, c), (c, a)
                sides = [m.ArcBetweenPoints(p, q, radius=3) for p, q in pairs]
                reuleaux = m.ArcPolygonFromArcs(*sides, fill_opacity=0.5)
                left = m.Arc(start_angle=m.PI / 2, angle=m.PI).shift(1.5 * m.RIGHT)
                right = m.Arc(start_angle=-m.PI / 2, angle=m.PI).shift(4.5 * m.RIGHT)
                stadium = m.ArcPolygonFromArcs(left, right, fill_opacity=0.5)
                reuleaux.set_color(m.BLUE)
                stadium.set_color(m.GREEN)
                self.play(m.Create(reuleaux), m.Create(stadium))
        ```
    """

    def __init__(self, *arcs: Arc | ArcBetweenPoints, **kwargs: Unpack[Style]) -> None:
        if not all(isinstance(m, (Arc, ArcBetweenPoints)) for m in arcs):
            raise ValueError(
                "All ArcPolygon submobjects must be of type Arc/ArcBetweenPoints"
            )
        super().__init__(**kwargs)
        self.add(*arcs)
        self.arcs = [*arcs]
        """The arcs, in order; they are also its submobjects."""

        for arc1, arc2 in adjacent_pairs(arcs):
            self.append_points(arc1.points)
            # the joining line is divided into curves about as long as the arc's, so
            # the outline's points are spread evenly along it
            line = Line(arc1.get_end(), arc2.get_start())
            len_ratio = line.get_length() / arc1.get_arc_length()
            if np.isnan(len_ratio) or np.isinf(len_ratio):
                continue
            line.insert_n_curves(int(arc1.get_num_curves() * len_ratio))
            self.append_points(line.points)


class Polygram(VMobject):
    """A shape of straight sides through groups of vertices: each group a closed path,
    from vertex to vertex and back to its first; blue unless styled.

    The groups make one mobject, filled and stroked together. Where they overlap, the
    fill counts how many times its paths wind around each point: a group inside another
    that runs the other way around is a hole.

    The vertices are taken as they are given: changing their arrays afterwards changes
    no shape.

    Args:
        *vertex_groups: The groups of vertices, each in order around its path.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class PolygramExample(m.Scene):
            def construct(self) -> None:
                r = np.sqrt(3)
                hexagram = m.Polygram(
                    [[0, 2, 0], [-r, -1, 0], [r, -1, 0]],
                    [[-r, 1, 0], [0, -2, 0], [r, 1, 0]],
                )
                framed = m.Polygram(
                    [[-2, -2, 0], [2, -2, 0], [2, 2, 0], [-2, 2, 0]],
                    [[-1, -1, 0], [-1, 1, 0], [1, 1, 0], [1, -1, 0]],
                    color=m.YELLOW,
                    fill_opacity=0.5,
                )
                self.play(m.Create(m.VGroup(hexagram, framed).arrange(buff=2)))
        ```
    """

    defaults: ClassVar[Style] = {"color": BLUE}

    def __init__(
        self, *vertex_groups: Point3DLike_Array, **kwargs: Unpack[Style]
    ) -> None:
        super().__init__(**kwargs)
        for vertices in vertex_groups:
            first_vertex, *vertices = vertices
            first_vertex = np.array(first_vertex)
            self.start_new_path(first_vertex)
            self.add_points_as_corners(np.array([*vertices, first_vertex]))

    def get_vertices(self) -> Point3D_Array:
        """The polygram's vertices, group after group: where each of its curves starts
        (the arcs and sides too, once its corners are rounded).

        Returns:
            An (n, 3) array of points, in scene coordinates.
        """
        return self.get_start_anchors()

    def get_vertex_groups(self) -> list[Point3D_Array]:
        """The polygram's vertices, grouped by the closed paths they are on.

        Returns:
            A list of (n, 3) arrays of points, one per closed path.
        """
        vertex_groups = []
        group = []
        for start, end in zip(
            self.get_start_anchors(), self.get_end_anchors(), strict=True
        ):
            group.append(start)
            if self.consider_points_equals(end, group[0]):
                vertex_groups.append(np.array(group))
                group = []
        return vertex_groups

    def round_corners(
        self,
        radius: float | list[float] = 0.5,
        evenly_distribute_anchors: bool = False,
        components_per_rounded_corner: int = 2,
    ) -> Self:
        """Round the polygram's corners: replace each with an arc of `radius` tangent to
        its two sides.

        An arc touches each side at most halfway along it: a radius too large for a
        corner is made smaller. A negative radius rounds a corner the other way,
        cutting a concave arc into it.

        Args:
            radius: The arcs' radius, in scene units; or a list of radii, one per
                corner of each group, from its second vertex's on (its first vertex's
                last), repeated over the corners: its length must divide their number.
            evenly_distribute_anchors: Whether to divide the straight sides into curves
                about as long as the arcs' curves, so the outline's points are spread
                evenly along it (a transform then moves them more evenly).
            components_per_rounded_corner: How many anchor points each arc is drawn
                through: 2 for one cubic Bézier curve.

        Examples:
            ```python
            import manimgx as m


            class PolygramRoundCornersExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(2.8, color=m.YELLOW)
                    shapes = m.VGroup(
                        m.Star(outer_radius=1.5),
                        m.Star(outer_radius=1.5).round_corners(0.25),
                        square.round_corners([0.1, 0.4, 0.8, 1.2]),
                        m.Triangle(radius=1.6, color=m.GREEN).round_corners(-0.5),
                    ).arrange(buff=0.5)
                    self.add(shapes)
            ```
        """
        if radius == 0:
            return self
        new_points: list[Point3D_Array] = []
        for vertex_group in self.get_vertex_groups():
            arcs = []
            if isinstance(radius, (int, float)):
                radius_list = [radius] * len(vertex_group)
            else:
                radius_list = radius * ceil(len(vertex_group) / len(radius))
            for current_radius, (v1, v2, v3) in zip(
                radius_list, adjacent_n_tuples(list(vertex_group), 3), strict=True
            ):
                vect1 = v2 - v1
                vect2 = v3 - v2
                unit_vect1 = normalize(vect1)
                unit_vect2 = normalize(vect2)
                angle = angle_between_vectors(vect1, vect2)
                angle *= np.sign(current_radius)
                cut_off_length = current_radius * np.tan(angle / 2)
                max_cut_off = min(np.linalg.norm(vect1), np.linalg.norm(vect2)) / 2
                cut_off_length = np.clip(cut_off_length, -max_cut_off, max_cut_off)
                sign = np.sign(np.cross(vect1, vect2)[2])
                arc = ArcBetweenPoints(
                    v2 - unit_vect1 * cut_off_length,
                    v2 + unit_vect2 * cut_off_length,
                    angle=sign * angle,
                    num_components=components_per_rounded_corner,
                )
                arcs.append(arc)
            average_arc_length = 1.0
            if evenly_distribute_anchors:
                nonzero_length_arcs = [arc for arc in arcs if len(arc.points) > 4]
                if len(nonzero_length_arcs) > 0:
                    total_arc_length = sum(
                        [arc.get_arc_length() for arc in nonzero_length_arcs]
                    )
                    num_curves = (
                        sum([len(arc.points) for arc in nonzero_length_arcs]) / 4
                    )
                    average_arc_length = total_arc_length / num_curves
            arcs = [arcs[-1], *arcs[:-1]]

            for arc1, arc2 in adjacent_pairs(arcs):
                new_points.append(arc1.points)
                line = Line(arc1.get_end(), arc2.get_start())
                if evenly_distribute_anchors:
                    line.insert_n_curves(ceil(line.get_length() / average_arc_length))
                new_points.append(line.points)
        self.set_points(np.concatenate(new_points) if new_points else np.array([]))
        return self


class Polygon(Polygram):
    """A polygon: straight sides from each vertex to the next, and from the last back to
    the first; blue unless styled.

    Args:
        *vertices: The vertices, in order around it.

    Examples:
        ```python
        import manimgx as m


        class PolygonExample(m.Scene):
            def construct(self) -> None:
                triangle = m.Polygon([-6, -2, 0], [-1.5, -2, 0], [-3.5, 2.5, 0])
                arrowhead = m.Polygon(
                    [1, -2.5, 0],
                    [6, 0, 0],
                    [1, 2.5, 0],
                    [2.5, 0, 0],
                    color=m.YELLOW,
                    fill_opacity=0.5,
                )
                self.play(m.Create(triangle), m.Create(arrowhead))
        ```
    """

    def __init__(self, *vertices: Point3DLike, **kwargs: Unpack[Style]) -> None:
        super().__init__(vertices, **kwargs)


class RegularPolygonOptions(_Style, total=False, closed=True):
    """A [RegularPolygon][manimgx.RegularPolygon]'s keywords but its number of vertices,
    for the classes that pass them on: its size and turn, with the style keywords."""

    radius: float
    """The radius of the circle its vertices are on, in scene units (default 1)."""
    start_angle: float | None
    """The angle of its first vertex, in radians, counterclockwise from the positive
    x-axis (default None: a vertex straight up if their number is odd, to the right if
    it is even)."""


class RegularPolygram(Polygram):
    """A regular star polygon: points evenly spaced on a circle, each joined to the one
    `density` steps on; blue unless styled.

    With a density of 1 it is a regular polygon; five points at density 2 make a
    pentagram. When the number of points and the density share a factor, the points
    make that many polygrams, each turned from the last: six points at density 2 make
    two triangles, a hexagram.

    Args:
        num_vertices: How many points there are on the circle.
        density: How many steps on each point is joined to: 1 for a polygon.
        radius: The radius of the circle, in scene units.
        start_angle: The angle of the first point, in radians, counterclockwise from
            the positive x-axis; None for a point straight up if each polygram has an
            odd number of points, to the right if even.

    Examples:
        ```python
        import manimgx as m


        class RegularPolygramExample(m.Scene):
            def construct(self) -> None:
                polygrams = m.VGroup(
                    m.RegularPolygram(5, radius=2),
                    m.RegularPolygram(7, density=3, radius=2, color=m.YELLOW),
                    m.RegularPolygram(6, radius=2, color=m.GREEN),
                ).arrange(buff=1)
                self.play(m.Create(polygrams, run_time=3))
        ```
    """

    def __init__(
        self,
        num_vertices: int,
        *,
        density: int = 2,
        radius: float = 1,
        start_angle: float | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        num_gons = np.gcd(num_vertices, density)
        num_vertices //= num_gons
        density //= num_gons

        vertices, self.start_angle = regular_vertices(
            num_vertices, radius=radius, start_angle=start_angle
        )
        order = np.arange(num_vertices) * (density % num_vertices) % num_vertices
        vertex_groups = [vertices[order]]
        for i in range(1, num_gons):
            start_angle = self.start_angle + i / num_gons * TAU / num_vertices
            vertices, _ = regular_vertices(
                num_vertices, radius=radius, start_angle=start_angle
            )
            vertex_groups.append(vertices[order])
        super().__init__(*vertex_groups, **kwargs)


class RegularPolygon(RegularPolygram):
    """A regular polygon: `n` vertices evenly spaced on a circle, joined in turn; blue
    unless styled.

    Args:
        n: How many vertices, and sides, it has.
        **kwargs: [Regular polygon
            keywords][manimgx.mobjects.shapes.RegularPolygonOptions]: its
            radius (1 unless given), its turn and its style.

    Examples:
        ```python
        import manimgx as m


        class RegularPolygonExample(m.Scene):
            def construct(self) -> None:
                polygons = m.VGroup(
                    m.RegularPolygon(radius=1.5),
                    m.RegularPolygon(radius=1.5, start_angle=m.PI / 6, color=m.GREEN),
                    m.RegularPolygon(5, radius=1.5, color=m.YELLOW),
                    m.RegularPolygon(10, radius=1.5, color=m.RED),
                ).arrange(buff=0.5)
                self.add(polygons)
        ```
    """

    def __init__(self, n: int = 6, **kwargs: Unpack[RegularPolygonOptions]) -> None:
        super().__init__(n, density=1, **kwargs)


class Star(Polygon):
    """A star: `n` points on a circle, and between each two a vertex on a smaller
    circle; blue unless styled.

    Unless given, the inner radius is the one that makes the star the outline of the
    [RegularPolygram][manimgx.RegularPolygram] of its `n` points at `density`: its
    edges lie along the polygram's lines.

    Args:
        n: How many points it has.
        outer_radius: The radius of the circle its points are on, in scene units.
        inner_radius: The radius of the circle its inner vertices are on, in scene
            units; None to set it by `density`.
        density: Without `inner_radius`, the density of the polygram whose outline it
            is: the higher, the thinner its points. It must be above 0 and below
            `n / 2`.
        start_angle: The angle of its first point, in radians, counterclockwise from
            the positive x-axis (default a quarter turn: straight up); None for a
            point straight up if `n` is odd, to the right if even.

    Examples:
        ```python
        import manimgx as m


        class StarExample(m.Scene):
            def construct(self) -> None:
                stars = m.VGroup(
                    m.Star(outer_radius=1.5),
                    m.Star(7, outer_radius=1.5, color=m.YELLOW),
                    m.Star(7, outer_radius=1.5, density=3, color=m.RED),
                    m.Star(12, outer_radius=1.5, inner_radius=1, color=m.GREEN),
                ).arrange(buff=0.5)
                self.play(m.Create(stars, run_time=3))
        ```
    """

    def __init__(
        self,
        n: int = 5,
        *,
        outer_radius: float = 1,
        inner_radius: float | None = None,
        density: int = 2,
        start_angle: float | None = TAU / 4,
        **kwargs: Unpack[Style],
    ) -> None:
        inner_angle = TAU / (2 * n)
        if (
            inner_radius is None
        ):  # the radius that makes the star's edges lines through `density` points
            if density <= 0 or density >= n / 2:
                raise ValueError(
                    f"Incompatible density {density} for number of points {n}"
                )
            outer_angle = TAU * density / n
            inverse_x = 1 - np.tan(inner_angle) * (
                (np.cos(outer_angle) - 1) / np.sin(outer_angle)
            )
            inner_radius = float(outer_radius / (np.cos(inner_angle) * inverse_x))
        outer_vertices, self.start_angle = regular_vertices(
            n, radius=outer_radius, start_angle=start_angle
        )
        inner_vertices, _ = regular_vertices(
            n, radius=inner_radius, start_angle=self.start_angle + inner_angle
        )
        vertices: list[npt.NDArray] = []
        for pair in zip(outer_vertices, inner_vertices, strict=True):
            vertices.extend(pair)
        super().__init__(*vertices, **kwargs)


class Triangle(RegularPolygon):
    """An equilateral triangle, pointing up, its vertices on a circle of radius 1 unless
    given another; blue unless styled.

    Args:
        **kwargs: [Regular polygon
            keywords][manimgx.mobjects.shapes.RegularPolygonOptions]: its
            radius, its turn and its style.

    Examples:
        ```python
        import manimgx as m


        class TriangleExample(m.Scene):
            def construct(self) -> None:
                triangles = m.VGroup(
                    m.Triangle(),
                    m.Triangle(radius=2, color=m.YELLOW, fill_opacity=0.5),
                    m.Triangle(radius=2, start_angle=-m.PI / 2, color=m.GREEN),
                ).arrange(buff=1)
                self.add(triangles)
        ```
    """

    def __init__(self, **kwargs: Unpack[RegularPolygonOptions]) -> None:
        super().__init__(n=3, **kwargs)


class _GridOptions(_Style, total=False):
    """GridOptions's keys, open, for the keywords that add to them."""

    grid_xstep: float | None
    """The distance between the vertical lines of its grid, from its left edge, in
    scene units (default None: no vertical lines)."""
    grid_ystep: float | None
    """The distance between the horizontal lines of its grid, from its top edge, in
    scene units (default None: no horizontal lines)."""
    mark_paths_closed: bool
    """Accepted for Manim compatibility; ignored."""


class GridOptions(_GridOptions, total=False, closed=True):
    """A [Rectangle][manimgx.Rectangle]'s grid, with the style keywords (for the classes
    that pass them on)."""


class RectangleOptions(_GridOptions, total=False, closed=True):
    """A [Rectangle][manimgx.Rectangle]'s keywords, for the classes that pass them on:
    its size and its grid, with the style keywords."""

    height: float
    """Its height, in scene units (default 2)."""
    width: float
    """Its width, in scene units (default 4)."""


class Rectangle(Polygon):
    """A rectangle, 4 wide and 2 tall unless sized, centered at the origin; white unless
    styled.

    Its vertices run counterclockwise from its top right corner. With `grid_xstep` or
    `grid_ystep` it is ruled into a grid: lines across it, its
    [grid_lines][manimgx.Rectangle.grid_lines], in its `color`.

    Args:
        color: Its color, which may be given by position (`Rectangle(BLUE)`); None for
            white.
        height: Its height, in scene units.
        width: Its width, in scene units.
        grid_xstep: The distance between the vertical lines of its grid, from its left
            edge, in scene units; None for none.
        grid_ystep: The distance between the horizontal lines of its grid, from its top
            edge, in scene units; None for none.
        mark_paths_closed: Accepted for Manim compatibility; ignored.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style].

    Examples:
        ```python
        import manimgx as m


        class RectangleExample(m.Scene):
            def construct(self) -> None:
                grid = m.Rectangle(
                    m.YELLOW, height=3, width=4, grid_xstep=1, grid_ystep=0.5
                )
                rectangles = m.VGroup(
                    m.Rectangle(),
                    m.Rectangle(m.BLUE, height=4, width=1.5, fill_opacity=0.5),
                    grid,
                ).arrange(buff=1)
                self.add(rectangles)
        ```
    """

    defaults: ClassVar[Style] = {"color": WHITE}

    def __init__(
        self,
        color: Colors | None = None,
        height: float = 2.0,
        width: float = 4.0,
        grid_xstep: float | None = None,
        grid_ystep: float | None = None,
        mark_paths_closed: bool = False,
        **kwargs: Unpack[StyleBase],
    ) -> None:
        style = Style(**kwargs) if color is None else Style(**kwargs, color=color)
        color = (style_defaults(type(self)) | style).get("color", WHITE)
        super().__init__(UR, UL, DL, DR, **style)
        self.stretch_to_fit_width(width)
        self.stretch_to_fit_height(height)

        v = self.get_vertices()
        line_color = color or WHITE
        self.grid_lines = VGroup()
        """The lines of its grid: a group of the vertical lines, then one of the
        horizontal lines, those it has; a submobject, unless it is empty (without a
        grid)."""
        if grid_xstep:
            grid_xstep = abs(grid_xstep)
            count = int(width / grid_xstep)
            grid = VGroup(
                *(
                    Line(
                        v[1] + i * grid_xstep * RIGHT,
                        v[1] + i * grid_xstep * RIGHT + height * DOWN,
                        color=line_color,
                    )
                    for i in range(1, count)
                )
            )
            self.grid_lines.add(grid)
        if grid_ystep:
            grid_ystep = abs(grid_ystep)
            count = int(height / grid_ystep)
            grid = VGroup(
                *(
                    Line(
                        v[1] + i * grid_ystep * DOWN,
                        v[1] + i * grid_ystep * DOWN + width * RIGHT,
                        color=line_color,
                    )
                    for i in range(1, count)
                )
            )
            self.grid_lines.add(grid)
        if self.grid_lines:
            self.add(self.grid_lines)


class ScreenOptions(_Style, total=False, closed=True):
    """A [ScreenRectangle][manimgx.ScreenRectangle]'s keywords, for the rectangles that
    pass them on: its proportions and its height, with the style keywords."""

    aspect_ratio: float
    """Its width over its height (default 16 / 9)."""
    height: float
    """Its height, in scene units (default 4)."""


class ScreenRectangle(Rectangle):
    """A rectangle with a screen's proportions, 16:9 and 4 tall unless given others,
    centered at the origin; white unless styled.

    Args:
        aspect_ratio: Its width over its height.
        height: Its height, in scene units.

    Examples:
        ```python
        import manimgx as m


        class ScreenRectangleExample(m.Scene):
            def construct(self) -> None:
                screens = m.VGroup(
                    m.ScreenRectangle(),
                    m.ScreenRectangle(aspect_ratio=4 / 3, height=3, color=m.BLUE),
                ).arrange(buff=1)
                self.add(screens)
        ```
    """

    def __init__(
        self,
        aspect_ratio: float = 16.0 / 9.0,
        height: float = 4,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(width=aspect_ratio * height, height=height, **kwargs)

    @property
    def aspect_ratio(self) -> float:
        """The rectangle's width over its height. Set it to stretch the rectangle's
        width to that proportion, about its center; its height stays."""
        return self.width / self.height

    @aspect_ratio.setter
    def aspect_ratio(self, value: float) -> None:
        self.stretch_to_fit_width(value * self.height)


class FullScreenRectangle(ScreenRectangle):
    """A screen rectangle as tall as the frame, centered at the origin: with the 16:9
    proportions it has unless given others, the frame's own outline; white unless
    styled.

    Its height is the frame's (8 units unless configured otherwise), whatever `height`
    is given.

    Args:
        **kwargs: [Screen rectangle keywords][manimgx.mobjects.shapes.ScreenOptions];
            `height` has no effect.

    Examples:
        ```python
        import manimgx as m


        class FullScreenRectangleExample(m.Scene):
            def construct(self) -> None:
                backdrop = m.FullScreenRectangle(
                    fill_color=m.DARK_BLUE, fill_opacity=1, stroke_color=m.YELLOW
                )
                self.add(backdrop, m.Text("A backdrop", font_size=96))
        ```
    """

    def __init__(self, **kwargs: Unpack[ScreenOptions]) -> None:
        super().__init__(**kwargs)
        self.height = config.frame_height


class Square(Rectangle):
    """A square, 2 on a side unless sized, centered at the origin; white unless styled.

    Args:
        side_length: The length of its sides, in scene units.

    Examples:
        ```python
        import manimgx as m


        class SquareExample(m.Scene):
            def construct(self) -> None:
                squares = m.VGroup(
                    m.Square(),
                    m.Square(3, color=m.BLUE, fill_opacity=0.5),
                    m.Square(4, color=m.YELLOW, grid_xstep=1, grid_ystep=1),
                ).arrange(buff=1)
                self.add(squares)
        ```
    """

    def __init__(self, side_length: float = 2.0, **kwargs: Unpack[GridOptions]) -> None:
        super().__init__(height=side_length, width=side_length, **kwargs)

    @property
    def side_length(self) -> float:
        """The length of the square's sides, in scene units: the distance between its
        first two vertices. Set it to scale the square to that side, about its
        center."""
        return float(np.linalg.norm(self.get_vertices()[0] - self.get_vertices()[1]))

    @side_length.setter
    def side_length(self, value: float) -> None:
        self.scale(value / self.side_length)


class RoundedRectangle(Rectangle):
    """A rectangle with rounded corners, 4 wide and 2 tall unless sized; white unless
    styled.

    Args:
        corner_radius: The radius of its corners, in scene units; or a list of radii
            for its top left, bottom left, bottom right and top right corners, in that
            order, repeated if there are one or two (see
            [round_corners][manimgx.Polygram.round_corners]).
        **kwargs: [Rectangle
            keywords][manimgx.mobjects.shapes.RectangleOptions]: its size,
            its grid and its style.

    Examples:
        ```python
        import manimgx as m


        class RoundedRectangleExample(m.Scene):
            def construct(self) -> None:
                leaf = m.RoundedRectangle([0, 1.2, 0, 1.2], height=3, width=3)
                rectangles = m.VGroup(
                    m.RoundedRectangle(),
                    m.RoundedRectangle(1.5, height=4, width=4, color=m.BLUE),
                    leaf.set_color(m.YELLOW),
                ).arrange(buff=1)
                self.add(rectangles)
        ```
    """

    def __init__(
        self,
        corner_radius: float | list[float] = 0.5,
        **kwargs: Unpack[RectangleOptions],
    ) -> None:
        super().__init__(**kwargs)
        self.corner_radius = corner_radius
        self.round_corners(self.corner_radius)


class Cutout(VMobject):
    """A shape with holes cut out of it: the main shape's outline, with the other
    shapes' outlines as holes; white unless styled.

    Each hole's path runs the other way around from the main shape's, so the fill
    leaves it out: the shapes given as holes are turned to run that way, in place. Only
    the shapes' own paths are used, not their submobjects', and the cutout has a style
    of its own.

    Args:
        main_shape: The shape to cut the holes out of.
        *mobjects: The shapes of the holes, inside it.

    Examples:
        ```python
        import manimgx as m


        class CutoutExample(m.Scene):
            def construct(self) -> None:
                holes = [
                    m.Circle(0.7).shift(1.3 * m.UL),
                    m.Square(1.4).shift(1.3 * m.UR),
                    m.Triangle(radius=0.8).shift(1.3 * m.DL),
                    m.Star(outer_radius=0.8).shift(1.3 * m.DR),
                ]
                card = m.Cutout(m.Square(5), *holes, color=m.BLUE, fill_opacity=1)
                behind = m.Circle(radius=2.2, color=m.YELLOW, fill_opacity=1)
                self.add(behind, card)
        ```
    """

    def __init__(
        self, main_shape: VMobject, *mobjects: VMobject, **kwargs: Unpack[Style]
    ) -> None:
        super().__init__(**kwargs)
        self.append_points(main_shape.points)
        sub_direction: Literal["CCW", "CW"] = (
            "CCW" if main_shape.get_direction() == "CW" else "CW"
        )
        for mobject in mobjects:
            self.append_points(mobject.force_direction(sub_direction).points)


class ConvexHull(Polygram):
    """The convex hull of points: the smallest convex polygon around them all, its
    vertices among them; blue unless styled.

    It is found in the plane of the screen: the points' z coordinates are ignored.

    Args:
        *points: The points: at least three, not all on one line.
        tolerance: How far outside the hull a point may be and still not be made a
            vertex of it, in scene units.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ConvexHullExample(m.Scene):
            def construct(self) -> None:
                points = np.random.default_rng(7).uniform(-3, 3, (20, 3)) * [1.5, 1, 0]
                hull = m.ConvexHull(*points, color=m.YELLOW, fill_opacity=0.3)
                self.add(hull, *(m.Dot(point, radius=0.1) for point in points))
        ```
    """

    def __init__(
        self, *points: Point3DLike, tolerance: float = 1e-05, **kwargs: Unpack[Style]
    ) -> None:
        array = np.array(points)[:, :2]
        hull = QuickHull(tolerance)
        hull.build(array)
        facets = set(hull.facets) - hull.removed
        facet = facets.pop()
        subfacets = list(facet.subfacets)
        while len(subfacets) <= len(facets):
            sf = subfacets[-1]
            (facet,) = hull.neighbors[sf] - {facet}
            (sf,) = facet.subfacets - {sf}
            subfacets.append(sf)
        coordinates = np.vstack([sf.coordinates for sf in subfacets])
        vertices = np.hstack((coordinates, np.zeros((len(coordinates), 1))))
        super().__init__(vertices, **kwargs)


class ArrowTip(VMobject):
    """The base of arrow tips: a small shape with two points of its own, its
    [tip_point][manimgx.ArrowTip.tip_point], where the path it ends points to, and its
    [base][manimgx.ArrowTip.base], where the path stops.

    A path makes its tip as `tip_shape(length=…, **style)` (see
    [add_tip][manimgx.TipableVMobject.add_tip]), then turns and moves it into place: the
    tip is what its class makes at that length. It is not made itself: its subclasses
    are the tips. To make a tip of your own, subclass it and a shape, made at the length
    given: the shape's first point is the tip point, and the point halfway around its
    outline is the base. Both are read from its points, so they move with it; a
    subclass that names other points of its shape does so as properties, never stored.

    Args:
        length: The tip's length, in scene units.
    """

    @prototype
    def __init__(
        self, length: float = DEFAULT_ARROW_TIP_LENGTH, **kwargs: Unpack[Style]
    ) -> None:
        raise NotImplementedError("Has to be implemented in inheriting subclasses.")

    @property
    def base(self) -> Point3D:
        """The point where the path meets the tip, and stops: halfway around the tip's
        outline from its tip point."""
        return self.point_from_proportion(0.5)

    @property
    def tip_point(self) -> Point3D:
        """The tip's point, where the path points to: the first point of its
        outline."""
        tip_point: Point3D = self.points[0]
        return tip_point

    @property
    def vector(self) -> Vector3D:
        """The vector from the tip's base to its tip point: the way it points."""
        return self.tip_point - self.base

    @property
    def tip_angle(self) -> float:
        """The direction the tip points in: the angle of its
        [vector][manimgx.ArrowTip.vector], in radians, counterclockwise from the
        positive x-axis."""
        return angle_of_vector(self.vector)

    @property
    def length(self) -> float:
        """The tip's length, in scene units: the distance from its base to its tip
        point."""
        return float(np.linalg.norm(self.vector))


class StealthTip(ArrowTip):
    """A dart-shaped tip: a sharp point with two barbs swept back from it and a notch
    between them, where the path stops; filled, with a stroke 3 wide.

    Its length runs from its barbs to its point; the notch is 5/8 of the way back from
    the point. It is half as long as the other tips unless given a length.

    Args:
        length: Its length, from its barbs to its point, in scene units (default
            0.175).
        start_angle: Accepted for Manim compatibility; ignored.

    Examples:
        ```python
        import manimgx as m


        class StealthTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.StealthTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 3}

    @prototype
    def __init__(
        self,
        length: float = DEFAULT_ARROW_TIP_LENGTH / 2,
        start_angle: float = PI,
        **kwargs: Unpack[Style],
    ):
        self.start_angle = start_angle
        VMobject.__init__(self, **kwargs)
        self.set_points_as_corners(
            np.array([[2, 0, 0], [-1.2, 1.6, 0], [0, 0, 0], [-1.2, -1.6, 0], [2, 0, 0]])
        )
        self.scale(length / self.length)

    @property
    def length(self) -> float:
        """The tip's whole length, in scene units: from its barbs to its point, 1.6
        times the distance from its notch to its point."""
        return float(np.linalg.norm(self.vector) * 1.6)


class ArrowTriangleTip(ArrowTip, Triangle):
    """A triangular tip, outlined: an isosceles triangle `length` long and `width` wide,
    its outline 3 wide and not filled.

    Args:
        length: Its length, from its base to its point, in scene units.
        width: Its width, across its base, in scene units.
        start_angle: The direction its point faces as made, in radians (default PI:
            left); a path turns the tip to point along itself.

    Examples:
        ```python
        import manimgx as m


        class ArrowTriangleTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowTriangleTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 0.0, "stroke_width": 3}

    @prototype
    def __init__(
        self,
        length: float = DEFAULT_ARROW_TIP_LENGTH,
        width: float = DEFAULT_ARROW_TIP_LENGTH,
        start_angle: float = PI,
        **kwargs: Unpack[Style],
    ) -> None:
        Triangle.__init__(self, start_angle=start_angle, **kwargs)
        self.width = width
        self.stretch_to_fit_width(length)
        self.stretch_to_fit_height(width)


class ArrowTriangleFilledTip(ArrowTriangleTip):
    """A triangular tip, filled and without an outline: the default tip of lines, arcs
    and arrows.

    Args:
        length: Its length, from its base to its point, in scene units.
        width: Its width, across its base, in scene units.
        start_angle: The direction its point faces as made, in radians (default PI:
            left); a path turns the tip to point along itself.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style].

    Examples:
        ```python
        import manimgx as m


        class ArrowTriangleFilledTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowTriangleFilledTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 0}


class ArrowCircleTip(ArrowTip, Circle):
    """A round tip, outlined: a circle `length` across, from where the path stops to
    where it ended; its outline 3 wide and not filled.

    Args:
        length: Its diameter, in scene units.
        start_angle: Accepted for Manim compatibility; ignored.

    Examples:
        ```python
        import manimgx as m


        class ArrowCircleTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowCircleTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 0.0, "stroke_width": 3}

    @prototype
    def __init__(
        self,
        length: float = DEFAULT_ARROW_TIP_LENGTH,
        start_angle: float = PI,
        **kwargs: Unpack[Style],
    ) -> None:
        self.start_angle = start_angle
        Circle.__init__(self, **kwargs)
        self.width = length
        self.stretch_to_fit_height(length)


class ArrowCircleFilledTip(ArrowCircleTip):
    """A round tip, filled and without an outline: a disc `length` across, from where
    the path stops to where it ended.

    Args:
        length: Its diameter, in scene units.
        start_angle: Accepted for Manim compatibility; ignored.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style].

    Examples:
        ```python
        import manimgx as m


        class ArrowCircleFilledTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowCircleFilledTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 0}


class ArrowSquareTip(ArrowTip, Square):
    """A square tip, outlined: a square `length` on a side, set on a corner, its
    diagonal along the path from where the path stops to where it ended; its outline 3
    wide and not filled.

    Its [length][manimgx.ArrowTip.length] is that diagonal's.

    Args:
        length: The length of its sides, in scene units.
        start_angle: Accepted for Manim compatibility; ignored.

    Examples:
        ```python
        import manimgx as m


        class ArrowSquareTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowSquareTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 0.0, "stroke_width": 3}

    @prototype
    def __init__(
        self,
        length: float = DEFAULT_ARROW_TIP_LENGTH,
        start_angle: float = PI,
        **kwargs: Unpack[Style],
    ) -> None:
        self.start_angle = start_angle
        Square.__init__(self, side_length=length, **kwargs)
        self.width = length
        self.stretch_to_fit_height(length)


class ArrowSquareFilledTip(ArrowSquareTip):
    """A square tip, filled and without an outline: a square `length` on a side, set on
    a corner, its diagonal along the path from where the path stops to where it ended.

    Its [length][manimgx.ArrowTip.length] is that diagonal's.

    Args:
        length: The length of its sides, in scene units.
        start_angle: Accepted for Manim compatibility; ignored.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style].

    Examples:
        ```python
        import manimgx as m


        class ArrowSquareFilledTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowSquareFilledTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 0}


class ArcedBase(_TippedBase, total=False):
    """A line's bend, with the tip keywords and every style keyword but `color`."""

    path_arc: float
    """The angle the line bends through, in radians: 0 for straight; otherwise it is an
    arc from its start to its end, turning counterclockwise if positive (bending right
    on its way), clockwise if negative (default 0)."""


class _Arced(ArcedBase, _Tipped, total=False):
    """Arced's keys, open, for the keywords that add to them."""

    pass


class Arced(_Arced, total=False, closed=True):
    """A line's bend, with the style and tip keywords (for the lines that set the buffer
    themselves)."""


class _LineOptions(_Arced, total=False):
    """LineOptions's keys, open, for the keywords that add to them."""

    buff: float
    """How far the line stops short of each end, in scene units; a line shorter than
    twice it keeps its ends (default 0)."""


class LineOptions(_LineOptions, total=False, closed=True):
    """A [Line][manimgx.Line]'s keywords but its ends, for the classes that pass them
    on: its buffer and its bend, with the style and tip keywords."""


class DashedLineOptions(_LineOptions, total=False):
    """A [DashedLine][manimgx.DashedLine]'s keywords but its ends: its dashes, with the
    line keywords."""

    dash_length: float
    """The length of each dash, in scene units: about it, as a whole number of dashes
    spans the line (default 0.05)."""
    dashed_ratio: float
    """The fraction of the line the dashes cover, from 0 to 1; the rest is gaps
    (default 0.5: dashes and gaps as long)."""


class _ArrowTipsBase(ArcedBase, total=False):
    """ArrowTipsBase's keys, open, for the keywords that add to them."""

    max_tip_length_to_length_ratio: float
    """The longest its tip may be, as a fraction of its length: a short arrow's tip is
    shorter (default 0.25)."""
    max_stroke_width_to_length_ratio: float
    """The widest its stroke may be, in hundredths of a scene unit, per scene unit of
    its length: a short arrow is thinner (default 5)."""
    tip_shape: type[ArrowTip]
    """The class of its tip (default
    [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip])."""


class ArrowTipsBase(_ArrowTipsBase, total=False, closed=True):
    """An [Arrow][manimgx.Arrow]'s keywords but its ends, its buffer and its color (for
    the methods that set those): its tip, how it shrinks when short, and its bend."""


class _ArrowTips(_ArrowTipsBase, _Tipped, total=False):
    """ArrowTips's keys, open, for the keywords that add to them."""

    pass


class ArrowTips(_ArrowTips, total=False, closed=True):
    """An [Arrow][manimgx.Arrow]'s keywords but its ends and its buffer (for the arrows
    that set it: vectors)."""


class ArrowOptions(_ArrowTips, total=False, closed=True):
    """An [Arrow][manimgx.Arrow]'s keywords but its ends, for the classes that pass them
    on."""

    buff: float
    """How far the arrow stops short of each end, in scene units (default 0.25)."""


class Line(TipableVMobject):
    """A straight line from one point to another, white unless styled; or an arc
    between them, bent through `path_arc`.

    An end may be a mobject: the line then starts (or ends) at its point farthest
    toward the other end (see [get_boundary_point][manimgx.Mobject.get_boundary_point]),
    so a line between two shapes runs from outline to outline. The line is placed when
    it is made, and does not follow the mobjects afterwards.

    Args:
        start: Where the line starts: a point, or a mobject.
        end: Where it ends: a point, or a mobject.
        buff: How far it stops short of each end, in scene units (along it, if bent);
            a line shorter than twice it keeps its ends.
        path_arc: The angle it bends through, in radians: 0 for straight; otherwise it
            is an arc, turning counterclockwise if positive, bending right on its way
            (see [ArcBetweenPoints][manimgx.ArcBetweenPoints]).

    Examples:
        ```python
        import manimgx as m


        class LineExample(m.Scene):
            def construct(self) -> None:
                straight = m.Line(4 * m.LEFT, 4 * m.RIGHT, color=m.BLUE)
                bent = m.Line(4 * m.LEFT, 4 * m.RIGHT, path_arc=-m.PI / 3)
                m.VGroup(straight, bent).arrange(m.DOWN, buff=1).shift(m.UP)
                left = m.Circle(radius=1, color=m.GREEN).move_to([-4.5, -2, 0])
                right = m.Circle(radius=0.5, color=m.RED).move_to([4.5, -2.5, 0])
                link = m.Line(left, right, buff=0.2, color=m.YELLOW)
                self.add(straight, bent, left, right, link)
        ```
    """

    def __init__(
        self,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        buff: float = 0,
        path_arc: float = 0,
        **kwargs: Unpack[Tipped],
    ) -> None:
        self.dim = 3
        self.buff = buff
        self.path_arc = path_arc
        self._set_start_and_end_attrs(start, end)
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        self.set_points_by_ends(
            start=self.start, end=self.end, buff=self.buff, path_arc=self.path_arc
        )
        return self

    @deprecated("use put_start_and_end_on", category=None)
    def set_points_by_ends(
        self,
        start: Point3DLike | Mobject,
        end: Point3DLike | Mobject,
        buff: float = 0,
        path_arc: float = 0,
    ) -> Self:
        """Rebuild the line between two ends, straight or bent.

        Its tips, if it has any, stay where they are.

        Args:
            start: Where it starts: a point, or a mobject (see [Line][manimgx.Line]).
            end: Where it ends: a point, or a mobject.
            buff: How far it stops short of each end, in scene units.
            path_arc: 0 for straight; otherwise the line is bent through its own
                `path_arc` (see [set_path_arc][manimgx.Line.set_path_arc]).
        """
        self._set_start_and_end_attrs(start, end)
        if path_arc:
            arc = ArcBetweenPoints(self.start, self.end, angle=self.path_arc)
            self.set_points(arc.points)
        else:
            self._geometry = segment(self.start, self.end)
        self._account_for_buff(buff)
        return self

    def _account_for_buff(self, buff: float) -> None:
        if buff <= 0:
            return
        length = self.get_length() if self.path_arc == 0 else self.get_arc_length()
        if length < 2 * buff:
            return
        if self.path_arc == 0:  # straight: the segment between the ends brought in
            start, end = self.get_start_and_end()
            inward = (end - start) * (buff / length)
            self._geometry = segment(start + inward, end - inward)
            return
        buff_proportion = buff / length
        self.pointwise_become_partial(self, buff_proportion, 1 - buff_proportion)

    def _set_start_and_end_attrs(
        self, start: Point3DLike | Mobject, end: Point3DLike | Mobject
    ) -> None:
        rough_start = self._pointify(start)
        rough_end = self._pointify(end)
        vect = normalize(rough_end - rough_start)
        self.start = self._pointify(start, vect)
        self.end = self._pointify(end, -vect)

    def _pointify(
        self, mob_or_point: Mobject | Point3DLike, direction: Vector3DLike | None = None
    ) -> Point3D:
        if isinstance(mob_or_point, Mobject):
            mob = mob_or_point
            if direction is None:
                return mob.get_center()
            else:
                return mob.get_boundary_point(direction)
        return np.array(mob_or_point)

    def set_path_arc(self, new_value: float) -> Self:
        """Bend the line through a new angle: rebuild it, straight or as an arc, between
        the ends it was made with.

        It is rebuilt where it was made (or last rebuilt), wherever it has moved since,
        and keeps its buffer.

        Args:
            new_value: The angle, in radians: 0 for straight; otherwise an arc, turning
                counterclockwise if positive.
        """
        self.path_arc = new_value
        self.init_points()
        return self

    def put_start_and_end_on(self, start: Point3DLike, end: Point3DLike) -> Self:
        """Move, turn and scale the line so it runs from `start` to `end`, tips
        included; its shape stays, scaled in proportion (an arrow's tips keep their
        size).

        A line whose ends coincide is rebuilt between the new ends.

        Args:
            start: Where its start goes: its start tip's point, if it has one.
            end: Where its end goes: its end tip's point, if it has one.

        Examples:
            ```python
            import manimgx as m


            class LinePutStartAndEndOnExample(m.Scene):
                def construct(self) -> None:
                    a, b, c = [-4, -2, 0], [0, 2.5, 0], [4, -2, 0]
                    dots = m.VGroup(*(m.Dot(p, radius=0.12) for p in (a, b, c)))
                    line = m.Line(a, b, color=m.BLUE)
                    self.add(dots, line)
                    self.play(line.animate.put_start_and_end_on(b, c))
                    self.play(line.animate.put_start_and_end_on(c, a))
            ```
        """
        curr_start, curr_end = self.get_start_and_end()
        if np.all(curr_start == curr_end):
            self.start = np.asarray(start)
            self.end = np.asarray(end)
            self.generate_points()
        return super().put_start_and_end_on(start, end)

    def get_vector(self) -> Vector3D:
        """The vector from the line's start to its end, tips included.

        Returns:
            The vector, in scene units.
        """
        return self.get_end() - self.get_start()

    def get_unit_vector(self) -> Vector3D:
        """The line's direction: the unit vector from its start toward its end.

        Returns:
            A vector of length 1; zero for a line of no length.
        """
        return normalize(self.get_vector())

    def get_angle(self) -> float:
        """The line's angle: the direction from its start to its end, counterclockwise
        from the positive x-axis.

        Returns:
            The angle, in radians, from -PI to PI.
        """
        return angle_of_vector(self.get_vector())

    def get_projection(self, point: Point3DLike) -> Point3D:
        """The point of the line nearest a point: the point's orthogonal projection onto
        the line, extended past its ends.

        Args:
            point: The point to project.

        Returns:
            The point on the line, in scene coordinates.
        """
        start = self.get_start()
        end = self.get_end()
        unit_vect = normalize(end - start)
        return start + float(np.dot(point - start, unit_vect)) * unit_vect

    def get_slope(self) -> float:
        """The line's slope: how far it rises for each unit it runs to the right, the
        tangent of its [angle][manimgx.Line.get_angle].

        Returns:
            The slope; very large for a line nearly upright.
        """
        return float(np.tan(self.get_angle()))

    def set_angle(self, angle: float, about_point: Point3DLike | None = None) -> Self:
        """Turn the line so its [angle][manimgx.Line.get_angle] is `angle`: about its
        start, unless given another point.

        Args:
            angle: The new angle, in radians, counterclockwise from the positive x-axis.
            about_point: The point it turns about; None for its start.
        """
        if about_point is None:
            about_point = self.get_start()
        self.rotate(angle - self.get_angle(), about_point=about_point)
        return self

    def set_length(self, length: float) -> Self:
        """Scale the line about its center to a length, tips included (an arrow's tips
        keep their size).

        Args:
            length: The new length, from its start to its end, in scene units.

        Examples:
            ```python
            import manimgx as m


            class LineSetLengthExample(m.Scene):
                def construct(self) -> None:
                    line = m.Line(m.LEFT, m.RIGHT, color=m.BLUE).shift(m.UP)
                    arrow = m.Arrow(m.LEFT, m.RIGHT, color=m.YELLOW).shift(m.DOWN)
                    self.add(line, arrow)
                    self.play(line.animate.set_length(10), arrow.animate.set_length(10))
                    self.play(line.animate.set_length(4), arrow.animate.set_length(4))
            ```
        """
        scale_factor: float = length / self.get_length()
        return self.scale(scale_factor)


class CurvesAsSubmobjects(VGroup[VMobject]):
    """A path split into its curves: a group of one path per curve, each styled as the
    path is.

    Each part can then be styled or animated on its own: a gradient across the parts
    colors the path along its length. Only the path's own curves are taken, not its
    submobjects'.

    Args:
        vmobject: The path to split.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] of the group itself: as it
            has no points, they do not restyle its parts, which take the path's style.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class CurvesAsSubmobjectsExample(m.Scene):
            def construct(self) -> None:
                curve = m.ParametricFunction(
                    lambda t: [2 * t, 2 * np.sin(t), 0], t_range=(-3, 3, 0.1)
                )
                parts = m.CurvesAsSubmobjects(curve.set_stroke(width=12))
                parts.set_color_by_gradient(m.BLUE, m.YELLOW, m.RED)
                self.play(m.Create(parts, run_time=2))
        ```
    """

    def __init__(self, vmobject: VMobject, **kwargs: Unpack[Style]) -> None:
        super().__init__(**kwargs)
        for tup in vmobject.get_cubic_bezier_tuples():
            part = VMobject()
            part.set_points(tup)
            part.match_style(vmobject)
            self.add(part)


def dash_pattern(
    n: int, ratio: float, offset: float, closed: bool
) -> tuple[float, float, float]:
    """CE's dashes as a periodic window over the path (period, duty, phase — fractions of it): an
    open path starts and ends with a dash; a closed one repeats every 1/n."""
    dash = ratio / n
    void = (
        (1 - ratio) / n if closed else (1 - ratio if n == 1 else (1 - ratio) / (n - 1))
    )
    period = dash + void
    return period, dash / period, offset % 1 * period


def _even(vmobject: VMobject) -> bool:
    """Whether a path's curves are all one length (so its parameter measures its length: a
    dash window over it has equal dashes)."""
    lengths = vmobject._geometry.curve_lengths()
    return len(lengths) > 0 and float(np.ptp(lengths)) <= 1e-3 * float(lengths.max())


class DashedVMobject(VMobject):
    """A path drawn in dashes: evenly spaced dashes along another path, in its style.

    An open path starts and ends with a dash; a closed one has as many gaps as dashes,
    all the way around. Each dash ends as the path's `cap_style` says, and an arrow's
    tips are drawn whole.

    Args:
        vmobject: The path to draw in dashes.
        num_dashes: How many dashes; 0 draws none.
        dashed_ratio: The fraction of the path the dashes cover, from 0 to 1; the gaps
            take the rest.
        dash_offset: How far the dashes are moved along the path, toward its end, as a
            fraction of a dash and the gap after it.
        equal_lengths: Whether the dashes are equally long; if False they are equal
            stretches of the path's parameter, longer where the path runs faster.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]; the dashes take the path's
            paint over them.

    Examples:
        ```python
        import manimgx as m


        class DashedVMobjectExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=1.5, color=m.BLUE, stroke_width=6)
                square = m.Square(side_length=3, color=m.GREEN, stroke_width=6)
                arc = m.Arc(radius=2, angle=m.PI, color=m.YELLOW, stroke_width=6)
                shapes = m.VGroup(
                    m.DashedVMobject(circle, num_dashes=12),
                    m.DashedVMobject(square, num_dashes=16, dashed_ratio=0.7),
                    m.DashedVMobject(arc, num_dashes=7, dashed_ratio=0.3),
                ).arrange(buff=1)
                self.play(m.Create(shapes, run_time=2))
        ```
    """

    defaults: ClassVar[Style] = {"color": WHITE}

    def __init__(
        self,
        vmobject: VMobject,
        num_dashes: int = 15,
        dashed_ratio: float = 0.5,
        dash_offset: float = 0,
        equal_lengths: bool = True,
        **kwargs: Unpack[Style],
    ) -> None:
        self.dashed_ratio = dashed_ratio
        self.num_dashes = num_dashes
        super().__init__(**kwargs)
        base = vmobject

        tips = base.get_tips().submobjects if isinstance(base, TipableVMobject) else []
        whole = all(any(m is t for t in tips) for m in base.submobjects)
        # the path itself, drawn in dashes (a window over it; its tips drawn whole)
        if (
            num_dashes > 0
            and whole
            and base.has_points()
            and (not equal_lengths or _even(base))
        ):
            self._geometry = base._geometry
            self.match_style(base, family=False)
            self.paint = self.paint.but(
                dash=dash_pattern(
                    num_dashes, dashed_ratio, dash_offset, base.is_closed()
                )
            )
            self.add(*(tip.copy() for tip in tips))
            return
        vmobject = base.copy()

        tips = vmobject.pop_tips() if isinstance(vmobject, TipableVMobject) else None
        r, n = dashed_ratio, num_dashes
        if n > 0:
            closed = vmobject.is_closed()
            dash_len = r / n
            void_len = (
                (1 - r) / n if closed else (1 - r if n == 1 else (1 - r) / (n - 1))
            )
            period = dash_len + void_len
            phase = dash_offset % 1 * period
            pattern_len = 1 if closed else 1 + void_len
            starts = [(i * period + phase) % pattern_len for i in range(n)]
            ends = [(i * period + dash_len + phase) % pattern_len for i in range(n)]
            if not closed:
                if ends[-1] > 1 and starts[-1] > 1:
                    ends.pop()
                    starts.pop()
                elif ends[-1] < dash_len:
                    if starts[-1] < 1:
                        starts.append(0)
                        ends.append(ends[-1])
                        ends[-2] = 1
                    else:
                        starts[-1] = 0
                elif starts[-1] > 1 - dash_len:
                    ends[-1] = 1
            if equal_lengths:
                lengths = np.cumsum(
                    np.r_[0.0, vmobject._geometry.piece_lengths().ravel()]
                )
                refs = np.linspace(0, 1, lengths.size)
                total = lengths[-1]
                self.add(
                    *(
                        vmobject.get_subcurve(
                            np.interp(s * total, lengths, refs),
                            np.interp(e * total, lengths, refs),
                        )
                        for s, e in zip(starts, ends, strict=True)
                    )
                )
            else:
                self.add(
                    *(
                        vmobject.get_subcurve(s, e)
                        for s, e in zip(starts, ends, strict=True)
                    )
                )
        self.match_style(base, family=False)
        if tips is not None and tips.submobjects:
            self.add(*tips.submobjects)


class DashedLine(Line):
    """A line drawn in dashes, white unless styled.

    The dashes are the line's stroke drawn in pieces: a whole number of them, at least
    two, spread evenly from end to end, each about `dash_length` long, each ended as
    the line's `cap_style` says. It stays one path, placed, bent and tipped as a
    [Line][manimgx.Line] is, and starts and ends where the line does; its handles are
    its dashes', the first dash's and the last's. Its dashes are counted when it is
    made, and scale with it.

    Args:
        start: Where the line starts: a point, or a mobject (see [Line][manimgx.Line]).
        end: Where it ends: a point, or a mobject.
        buff: How far it stops short of each end, in scene units.
        path_arc: The angle it bends through, in radians: 0 for straight.
        dash_length: The length of each dash, in scene units (default 0.05): about it,
            as a whole number of dashes spans the line.
        dashed_ratio: The fraction of the line the dashes cover, from 0 to 1; the rest
            is gaps.

    Examples:
        ```python
        import manimgx as m


        class DashedLineExample(m.Scene):
            def construct(self) -> None:
                start, end = 5 * m.LEFT, 5 * m.RIGHT
                lines = m.VGroup(
                    m.DashedLine(start, end),
                    m.DashedLine(start, end, dash_length=0.4, color=m.BLUE),
                    m.DashedLine(start, end, dash_length=0.4, dashed_ratio=0.2),
                    m.DashedLine(start, end, path_arc=m.PI / 4, color=m.YELLOW),
                ).arrange(m.DOWN, buff=1)
                lines[2].set_color(m.GREEN)
                self.add(lines)
        ```
    """

    def __init__(
        self,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        buff: float = 0,
        path_arc: float = 0,
        *,
        dash_length: float = DEFAULT_DASH_LENGTH,
        dashed_ratio: float = 0.5,
        **kwargs: Unpack[Tipped],
    ) -> None:
        self.dash_length = dash_length
        self.dashed_ratio = dashed_ratio
        super().__init__(start, end, buff, path_arc, **kwargs)
        self.paint = self.paint.but(  # a line drawn in dashes: one path, a dash window
            dash=dash_pattern(self._calculate_num_dashes(), dashed_ratio, 0, False)
        )

    def _calculate_num_dashes(self) -> int:
        return max(
            2, int(np.ceil(self.get_length() / self.dash_length * self.dashed_ratio))
        )

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_first_handle(self) -> Point3D:
        """The line's first handle: its first dash's, the control point after the
        line's start toward which that dash leaves it (a third of the way into the
        dash, on a straight line).

        Returns:
            The point, in scene coordinates.
        """
        start, handle = self.points[:2]
        return start + self._dash_cut() * (handle - start)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_last_handle(self) -> Point3D:
        """The line's last handle: its last dash's, the control point before the
        line's end from which that dash comes into it (a third of the way back into
        the dash, on a straight line).

        Returns:
            The point, in scene coordinates.
        """
        handle, end = self.points[-2:]
        return end + self._dash_cut() * (handle - end)

    def _dash_cut(self) -> float:
        """How far into the curve at each end of the line the dash there reaches, in
        that curve's parameter from the end: the dash is the curve cut there, which
        keeps the end and brings its handle in by as much (de Casteljau). The first
        dash starts the line and the last ends it, each period × duty of its parameter;
        drawn solid, the line is one piece, each end curve whole."""
        if self.paint.dash is None:
            return 1.0
        period, duty, _ = self.paint.dash
        return min(1.0, period * duty * self.get_num_curves())


class TangentLine(Line):
    """A line tangent to a path at a point along it, `length` long and centered on the
    point; white unless styled.

    Its direction is that of the chord between the points `d_alpha` before and after
    the point.

    Args:
        vmob: The path.
        alpha: Where along the path, as a proportion of its length: 0 at its start, 1
            at its end.
        length: The line's length, in scene units.
        d_alpha: The proportion of the path's length before and after the point whose
            chord sets the direction.

    Examples:
        ```python
        import manimgx as m


        class TangentLineExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=2.5, color=m.BLUE)
                self.add(circle)
                for alpha in (0, 0.2, 0.45, 0.7):
                    self.add(m.TangentLine(circle, alpha, length=4, color=m.YELLOW))
                    self.add(m.Dot(circle.point_from_proportion(alpha)))
        ```
    """

    def __init__(
        self,
        vmob: VMobject,
        alpha: float,
        length: float = 1,
        d_alpha: float = 1e-06,
        **kwargs: Unpack[LineOptions],
    ) -> None:
        self.length = length
        self.d_alpha = d_alpha
        da = self.d_alpha
        a1 = np.clip(alpha - da, 0, 1)
        a2 = np.clip(alpha + da, 0, 1)
        super().__init__(
            vmob.point_from_proportion(a1), vmob.point_from_proportion(a2), **kwargs
        )
        self.scale(self.length / self.get_length())


class Elbow(VMobject):
    """The mark of a right angle: two segments `width` long meeting at a square corner;
    white unless styled.

    Made at the origin, it marks the right angle between the positive x and y axes:
    from (0, `width`) across to its corner at (`width`, `width`), and down to
    (`width`, 0); `angle` turns it about the origin. To mark the angle between two
    lines, see [RightAngle][manimgx.RightAngle].

    Args:
        width: The length of each segment, in scene units.
        angle: The angle it is turned through about the origin, in radians,
            counterclockwise.

    Examples:
        ```python
        import manimgx as m


        class ElbowExample(m.Scene):
            def construct(self) -> None:
                elbows = m.VGroup(
                    m.Elbow(),
                    m.Elbow(width=1.5, color=m.BLUE),
                    m.Elbow(width=2, angle=5 * m.PI / 4, color=m.YELLOW),
                ).arrange(buff=1.5)
                self.add(elbows)
        ```
    """

    def __init__(
        self, width: float = 0.2, angle: float = 0, **kwargs: Unpack[Style]
    ) -> None:
        self.angle = angle
        super().__init__(**kwargs)
        self.set_points_as_corners(np.array([UP, UP + RIGHT, RIGHT]))
        self.scale_to_fit_width(width, about_point=ORIGIN)
        self.rotate(self.angle, about_point=ORIGIN)


class Arrow(Line):
    """An arrow: a line with a tip at its end, stopping `buff` short of the two points
    it joins; white, with a stroke 6 wide, unless styled.

    A short arrow is drawn in proportion: its tip is at most
    `max_tip_length_to_length_ratio` of its length, and its stroke at most
    `max_stroke_width_to_length_ratio` wide per unit of its length. Scaled, it keeps
    its tip's size (see [scale][manimgx.Arrow.scale]).

    Args:
        start: Where the arrow starts: a point, or a mobject (see [Line][manimgx.Line]).
        end: Where it points to: a point, or a mobject.
        buff: How far it stops short of each end, in scene units (default 0.25): an
            arrow between two mobjects leaves a gap at each.
        max_tip_length_to_length_ratio: The longest its tip may be, as a fraction of
            its length.
        max_stroke_width_to_length_ratio: The widest its stroke may be, in hundredths
            of a scene unit, per scene unit of its length.
        tip_shape: The class of its tip.
        **kwargs: [Style, tip and bend keywords][manimgx.mobjects.shapes.Arced]:
            its `path_arc` bends it.

    Examples:
        ```python
        import manimgx as m


        class ArrowExample(m.Scene):
            def construct(self) -> None:
                a, b = 2.5 * m.LEFT, 2.5 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b),
                    m.Arrow(a, b, buff=0, color=m.BLUE),
                    m.Arrow(a, b, path_arc=-m.PI / 3, color=m.GREEN),
                    m.Arrow(a, b, tip_shape=m.StealthTip, color=m.YELLOW),
                ).arrange(m.DOWN, buff=0.8, aligned_edge=m.LEFT)
                shorts = m.VGroup()
                for length in (0.5, 1, 2, 4, 6):
                    shorts.add(m.Arrow(m.ORIGIN, length * m.UP, buff=0, color=m.RED))
                shorts.arrange(aligned_edge=m.DOWN)
                self.add(m.VGroup(arrows, shorts).arrange(buff=1.5))
        ```
    """

    defaults: ClassVar[Style] = {"stroke_width": 6}

    def __init__(
        self,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        *,
        buff: float = MED_SMALL_BUFF,
        max_tip_length_to_length_ratio: float = 0.25,
        max_stroke_width_to_length_ratio: float = 5,
        tip_shape: type[ArrowTip] = ArrowTriangleFilledTip,
        **kwargs: Unpack[Arced],
    ) -> None:
        self.max_tip_length_to_length_ratio = max_tip_length_to_length_ratio
        self.max_stroke_width_to_length_ratio = max_stroke_width_to_length_ratio
        super().__init__(start, end, buff=buff, **kwargs)
        self.initial_stroke_width = self.stroke_width
        self.add_tip(tip_shape=tip_shape)
        self._set_stroke_width_from_length()

    def scale(
        self,
        scale_factor: float | Vector3DLike,
        scale_stroke: bool = False,
        scale_tips: bool = False,
        **kwargs: Unpack[Pivot],
    ) -> Self:
        """Scale the arrow, keeping its tips' size unless `scale_tips`.

        The shaft is scaled, and the tips are put back on its ends. Then the shaft's
        stroke width is set from its new length, as when the arrow was made: the smaller
        of the width it was made with and `max_stroke_width_to_length_ratio` times its
        length. An arrow of no length stays as it is.

        Args:
            scale_factor: The factor: one, or one per axis (see
                [Mobject.scale][manimgx.Mobject.scale]).
            scale_stroke: Whether stroke widths scale too; the shaft's is then set from
                its length all the same.
            scale_tips: Whether the tips scale with the shaft.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).

        Examples:
            ```python
            import manimgx as m


            class ArrowScaleExample(m.Scene):
                def construct(self) -> None:
                    kept = m.Arrow(m.LEFT, m.RIGHT, color=m.BLUE).shift(1.5 * m.UP)
                    scaled = m.Arrow(m.LEFT, m.RIGHT, color=m.YELLOW).shift(m.DOWN)
                    top = m.Text("scale(3)").move_to(2.8 * m.UP)
                    bottom = m.Text("scale(3, scale_tips=True)").move_to(2.5 * m.DOWN)
                    self.add(top, bottom, kept, scaled)
                    self.play(
                        kept.animate.scale(3), scaled.animate.scale(3, scale_tips=True)
                    )
            ```
        """
        if self.get_length() == 0:
            return self
        if scale_tips:
            super().scale(scale_factor, scale_stroke, **kwargs)
            self._set_stroke_width_from_length()
            return self
        has_tip = self.has_tip()
        order = list(self.submobjects)  # the tips come back to their places among them
        old_tips = self.pop_tips()
        super().scale(scale_factor, scale_stroke, **kwargs)
        self._set_stroke_width_from_length()
        for tip, at_start in zip(
            old_tips, (False, True) if has_tip else (True,), strict=False
        ):
            self.add_tip(tip=tip, at_start=at_start)
        place = {id(m): i for i, m in enumerate(order)}
        self.submobjects.sort(key=lambda m: place.get(id(m), len(order)))
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_normal_vector(self) -> Vector3D:
        """The normal of the plane the arrow's tip lies in, from its first three
        anchors.

        Returns:
            A unit vector: IN for an arrow in the plane of the screen.
        """
        p0, p1, p2 = self.tip.get_start_anchors()[:3]
        return normalize(np.cross(p2 - p1, p1 - p0))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def reset_normal_vector(self) -> Self:
        """Set the arrow's `normal_vector` to its
        [tip's normal][manimgx.Arrow.get_normal_vector].

        Kept for Manim compatibility: nothing reads `normal_vector`.
        """
        self.normal_vector = self.get_normal_vector()
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_default_tip_length(self) -> float:
        """The length of the tips the arrow makes unless given one: its `tip_length`,
        or `max_tip_length_to_length_ratio` times its length if that is shorter.

        Returns:
            The length, in scene units.
        """
        max_ratio = self.max_tip_length_to_length_ratio
        return min(self.tip_length, max_ratio * self.get_length())

    def _set_stroke_width_from_length(self) -> Self:
        max_ratio = self.max_stroke_width_to_length_ratio
        self.set_stroke(
            width=min(self.initial_stroke_width, max_ratio * self.get_length()),
            family=False,
        )
        return self


class Vector(Arrow):
    """A vector: an arrow from the origin to a point; white unless styled.

    Args:
        direction: Where it points to, from the origin: two coordinates, or three.
        buff: How far it stops short of the origin and of its end, in scene units.

    Examples:
        ```python
        import manimgx as m


        class VectorExample(m.Scene):
            def construct(self) -> None:
                vectors = m.VGroup(
                    m.Vector([2, 1], color=m.YELLOW),
                    m.Vector([-3, 2], color=m.BLUE),
                    m.Vector([1, -3, 0], color=m.GREEN),
                )
                self.add(m.NumberPlane(), vectors)
        ```
    """

    def __init__(
        self,
        direction: Vector2DLike | Vector3DLike = RIGHT,
        buff: float = 0,
        **kwargs: Unpack[ArrowTips],
    ) -> None:
        self.buff = buff
        end = np.asarray(direction, dtype=float)
        if len(end) == 2:
            end = np.hstack([end, 0])
        super().__init__(ORIGIN, end, buff=buff, **kwargs)

    def coordinate_label(
        self,
        integer_labels: bool = True,
        n_dim: int = 2,
        **kwargs: Unpack[MatrixOptions],
    ) -> Matrix:
        """Make a label of the vector's coordinates: a column matrix beside its tip.

        The label, at 0.8 of a matrix's size, is placed 0.25 beyond the vector's end,
        centered on it vertically: to its right if the vector points right (or straight
        up or down), to its left otherwise. It is not added to the vector.

        Args:
            integer_labels: Whether to round the coordinates to integers.
            n_dim: How many coordinates to show: 2 for x and y, 3 for z too.
            **kwargs: [Matrix keywords][manimgx.mobjects.grid.MatrixOptions]; `color`
                colors the whole label.

        Returns:
            A new matrix.

        Examples:
            ```python
            import manimgx as m


            class VectorCoordinateLabelExample(m.Scene):
                def construct(self) -> None:
                    right = m.Vector([3, 2], color=m.YELLOW)
                    left = m.Vector([-4, -2], color=m.BLUE)
                    self.add(m.NumberPlane(), right, left)
                    self.add(right.coordinate_label())
                    self.add(left.coordinate_label(color=m.BLUE))
            ```
        """
        from manimgx.mobjects.grid import Matrix

        vect = np.array(self.get_end())
        if integer_labels:
            vect = np.round(vect).astype(int)
        vect = vect[:n_dim]
        vect = vect.reshape((n_dim, 1))
        color = kwargs.pop("color", None)
        label = Matrix(vect, **kwargs)
        label.scale(LARGE_BUFF - 0.2)
        shift_dir = np.array(self.get_end())
        if shift_dir[0] >= 0:
            shift_dir -= label.get_left() + DEFAULT_MOBJECT_TO_MOBJECT_BUFFER * LEFT
        else:
            shift_dir -= label.get_right() + DEFAULT_MOBJECT_TO_MOBJECT_BUFFER * RIGHT
        label.shift(shift_dir)
        if color is not None:
            label.set_color(color)
        return label


class DoubleArrow(Arrow):
    """An arrow with a tip at each end; white, with a stroke 6 wide, unless styled.

    Its tips and its stroke are sized from its length, tip to tip, as an
    [Arrow][manimgx.Arrow]'s are.

    Args:
        start: Where it starts: a point, or a mobject (see [Line][manimgx.Line]).
        end: Where it ends: a point, or a mobject.
        tip_shape_start: The class of the tip at its start.
        tip_shape_end: The class of the tip at its end; None for the `tip_shape`
            keyword's, or else [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip].

    Examples:
        ```python
        import manimgx as m


        class DoubleArrowExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=2, color=m.BLUE).shift(3 * m.LEFT)
                diameter = m.DoubleArrow(circle.get_left(), circle.get_right(), buff=0)
                mixed = m.DoubleArrow(
                    m.RIGHT,
                    6 * m.RIGHT,
                    tip_shape_start=m.ArrowCircleFilledTip,
                    tip_shape_end=m.StealthTip,
                    color=m.YELLOW,
                )
                self.add(circle, diameter, mixed)
        ```
    """

    def __init__(
        self,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        *,
        tip_shape_start: type[ArrowTip] = ArrowTriangleFilledTip,
        tip_shape_end: type[ArrowTip] | None = None,
        **kwargs: Unpack[ArrowOptions],
    ) -> None:
        if tip_shape_end is not None:
            kwargs["tip_shape"] = tip_shape_end
        super().__init__(start, end, **kwargs)
        self.add_tip(at_start=True, tip_shape=tip_shape_start)
        self._set_stroke_width_from_length()  # as an arrow's: by its length, tip to tip


class _AngleShape(_Style, total=False):
    """AngleShape's keys, open, for the keywords that add to them."""

    quadrant: AngleQuadrant
    """Which way each side of the angle goes from the crossing: a sign for each line,
    the first line's first; 1 along the line's direction (from its start toward its
    end), -1 back toward its start (default (1, 1))."""
    other_angle: bool
    """Whether the arc runs clockwise from the first side to the second, instead of
    counterclockwise: it then marks the rest of the full turn (default False)."""
    dot: bool
    """Whether to put a dot inside the arc, as a right angle is sometimes marked
    (default False; an elbow has none)."""
    dot_radius: float | None
    """The dot's radius, in scene units (default None: a tenth of the arc's radius)."""
    dot_distance: float
    """How far the dot is from the crossing, as a fraction of the arc's radius (default
    0.55)."""
    dot_color: ParsableManimColor
    """The dot's color (default white)."""


class AngleShape(_AngleShape, total=False, closed=True):
    """An [Angle][manimgx.Angle]'s keywords but its radius and its elbow (for right
    angles, which set them): which angle it marks, and its dot, with the style
    keywords."""


class AngleOptions(_AngleShape, total=False, closed=True):
    """An [Angle][manimgx.Angle]'s keywords but its lines (for the methods that make
    one)."""

    radius: float | None
    """The arc's radius, or the elbow's side, in scene units (default None: 0.4, or
    for short lines two thirds of the distance from the crossing to the nearer of the
    line ends the sides point to, when that is less than 0.6)."""
    elbow: bool
    """Whether to mark the angle with an elbow, two segments making a corner between
    its sides, instead of an arc (default False)."""


class Angle(VMobject):
    """The mark of an angle between two lines: an arc about the point where they cross,
    counterclockwise from a side along the first line to a side along the second; white
    unless styled.

    The lines are taken as infinite, so they need not reach the point where they cross.
    From there, `quadrant` picks the way each side goes along its line, and
    `other_angle` turns the arc clockwise instead, marking the rest of the full turn:
    together they pick the angle marked, which may be more than half a turn. With
    `elbow`, the mark is two segments instead, making a corner between the two sides,
    as a right angle is marked. Parallel lines in the plane of the screen make an empty
    mark, of value 0.

    Args:
        line1: The line the angle is measured from.
        line2: The line it is measured to.
        radius: The arc's radius, or the elbow's side, in scene units; None for 0.4, or
            for short lines two thirds of the distance from the crossing to the nearer
            of the line ends the sides point to, when that is less than 0.6.
        quadrant: Which way each side goes from the crossing: a sign for each line,
            `line1`'s first; 1 along the line's direction (from its start toward its
            end), -1 back toward its start.
        other_angle: Whether the arc runs clockwise from the first side to the second
            instead, marking the rest of the full turn.
        dot: Whether to put a dot inside the arc (an elbow has none).
        dot_radius: The dot's radius, in scene units; None for a tenth of the arc's
            radius.
        dot_distance: How far the dot is from the crossing, as a fraction of the arc's
            radius.
        dot_color: The dot's color.
        elbow: Whether to mark the angle with an elbow instead of an arc.

    Examples:
        ```python
        import manimgx as m


        class AngleExample(m.Scene):
            def construct(self) -> None:
                line1 = m.Line(1.2 * m.LEFT, 1.2 * m.RIGHT)
                line2 = m.Line(1.2 * m.DOWN, 1.2 * m.UP).rotate(-30 * m.DEGREES)
                angles = [
                    m.Angle(line1, line2, color=m.YELLOW),
                    m.Angle(line1, line2, quadrant=(-1, 1), color=m.BLUE),
                    m.Angle(line1, line2, other_angle=True, color=m.GREEN),
                    m.Angle(line1, line2, dot=True, color=m.RED),
                ]
                labels = ["default", "quadrant=(-1, 1)", "other_angle=True", "dot=True"]
                panels = m.VGroup()
                for angle in angles:
                    panels.add(m.VGroup(line1.copy(), line2.copy(), angle))
                panels.arrange(buff=1)
                for panel, label in zip(panels, labels):
                    text = m.Text(label, font_size=24).next_to(panel, m.DOWN)
                    self.add(panel, text)
        ```
    """

    def __init__(
        self,
        line1: Line,
        line2: Line,
        radius: float | None = None,
        quadrant: AngleQuadrant = (1, 1),
        other_angle: bool = False,
        dot: bool = False,
        dot_radius: float | None = None,
        dot_distance: float = 0.55,
        dot_color: ParsableManimColor = WHITE,
        elbow: bool = False,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(**kwargs)
        self.lines = (line1, line2)
        self.quadrant = quadrant
        self.dot_distance = dot_distance
        self.elbow = elbow
        try:
            inter = line_intersection(
                [line1.get_start(), line1.get_end()],
                [line2.get_start(), line2.get_end()],
            )
        except ValueError:
            lines_are_in_xy_plane = all(
                point[2] == 0
                for line in (line1, line2)
                for point in (line.get_start(), line.get_end())
            )
            directions_are_parallel = (
                np.cross(line1.get_vector(), line2.get_vector())[2] == 0
            )
            if not (lines_are_in_xy_plane and directions_are_parallel):
                raise
            self.angle_value = 0.0
            return
        if radius is None:
            if quadrant[0] == 1:
                dist_1 = np.linalg.norm(line1.get_end() - inter)
            else:
                dist_1 = np.linalg.norm(line1.get_start() - inter)
            if quadrant[1] == 1:
                dist_2 = np.linalg.norm(line2.get_end() - inter)
            else:
                dist_2 = np.linalg.norm(line2.get_start() - inter)
            radius = (
                float(2 / 3 * min(dist_1, dist_2)) if min(dist_1, dist_2) < 0.6 else 0.4
            )
        else:
            self.radius = radius
        anchor_angle_1 = inter + quadrant[0] * radius * line1.get_unit_vector()
        anchor_angle_2 = inter + quadrant[1] * radius * line2.get_unit_vector()
        if elbow:
            anchor_middle = (
                inter
                + quadrant[0] * radius * line1.get_unit_vector()
                + quadrant[1] * radius * line2.get_unit_vector()
            )
            angle_mobject: VMobject = Elbow(**kwargs)
            angle_mobject.set_points_as_corners(
                np.array([anchor_angle_1, anchor_middle, anchor_angle_2])
            )
        else:
            angle_1 = angle_of_vector(anchor_angle_1 - inter)
            angle_2 = angle_of_vector(anchor_angle_2 - inter)
            if not other_angle:
                start_angle = angle_1
                if angle_2 > angle_1:
                    angle_fin = angle_2 - angle_1
                else:
                    angle_fin = 2 * np.pi - (angle_1 - angle_2)
            else:
                start_angle = angle_1
                if angle_2 < angle_1:
                    angle_fin = -angle_1 + angle_2
                else:
                    angle_fin = -2 * np.pi + (angle_2 - angle_1)
            self.angle_value = angle_fin
            angle_mobject = Arc(
                radius=radius,
                angle=self.angle_value,
                start_angle=start_angle,
                arc_center=inter,
                **kwargs,
            )
            if dot:
                if dot_radius is None:
                    dot_radius = radius / 10
                else:
                    self.dot_radius = dot_radius
                right_dot = Dot(ORIGIN, radius=dot_radius, color=dot_color)
                dot_anchor = (
                    inter
                    + (angle_mobject.get_center() - inter)
                    / np.linalg.norm(angle_mobject.get_center() - inter)
                    * radius
                    * dot_distance
                )
                right_dot.move_to(dot_anchor)
                self.add(right_dot)
        self.set_points(angle_mobject.points)

    def get_lines(self) -> VGroup:
        """The two lines the angle is between.

        Returns:
            A new group of the two lines, `line1` first.
        """
        return VGroup(*self.lines)

    def get_value(self, degrees: bool = False) -> float:
        """The size of the angle marked: counterclockwise from its first side to its
        second, or clockwise, and negative, with `other_angle`.

        An angle marked with an elbow has no value: asking for it raises an exception.

        Args:
            degrees: Whether to give it in degrees instead of radians.

        Returns:
            The angle, in radians (or degrees), from -TAU to TAU.
        """
        return self.angle_value / DEGREES if degrees else self.angle_value

    @staticmethod
    def from_three_points(
        A: Point3DLike, B: Point3DLike, C: Point3DLike, **kwargs: Unpack[AngleOptions]
    ) -> Angle:
        """The mark of the angle ABC: at `B`, from the line toward `A` counterclockwise
        to the line toward `C`.

        Args:
            A: A point on the first side.
            B: The vertex.
            C: A point on the second side.
            **kwargs: [Angle keywords][manimgx.mobjects.shapes.AngleOptions].

        Returns:
            A new angle.

        Examples:
            ```python
            import manimgx as m


            class AngleFromThreePointsExample(m.Scene):
                def construct(self) -> None:
                    a, b, c = [-4, -2, 0], [3, -2, 0], [-1, 2.5, 0]
                    angles = m.VGroup(
                        m.Angle.from_three_points(b, a, c, radius=0.8, color=m.YELLOW),
                        m.Angle.from_three_points(c, b, a, radius=0.8, color=m.BLUE),
                        m.Angle.from_three_points(a, c, b, radius=0.8, color=m.GREEN),
                    )
                    self.add(m.Polygon(a, b, c, color=m.WHITE), angles)
            ```
        """
        return Angle(Line(B, A), Line(B, C), **kwargs)


class RightAngle(Angle):
    """The mark of a right angle between two lines: an [Angle][manimgx.Angle] marked
    with an elbow; white unless styled.

    The lines need not be perpendicular: the elbow is then a corner of a
    parallelogram.

    Args:
        line1: The first line.
        line2: The second line.
        length: The length of the elbow's sides, in scene units; None for 0.4, or less
            for short lines (see [Angle][manimgx.Angle]).
        **kwargs: [Angle keywords][manimgx.mobjects.shapes.AngleShape]; the dot
            keywords have no effect.

    Examples:
        ```python
        import manimgx as m


        class RightAngleExample(m.Scene):
            def construct(self) -> None:
                a, b, c = [-6, -2, 0], [-1, -2, 0], [-6, 2, 0]
                triangle = m.Polygon(a, b, c, color=m.BLUE)
                corner = m.RightAngle(m.Line(a, b), m.Line(a, c), color=m.YELLOW)
                line1 = m.Line([1, -2, 0], [6, 3, 0])
                line2 = m.Line([1, 3, 0], [6, -2, 0])
                marks = m.VGroup(
                    m.RightAngle(line1, line2),
                    m.RightAngle(line1, line2, length=0.7, quadrant=(-1, -1)),
                ).set_color(m.GREEN)
                self.add(triangle, corner, line1, line2, marks)
        ```
    """

    def __init__(
        self,
        line1: Line,
        line2: Line,
        length: float | None = None,
        **kwargs: Unpack[AngleShape],
    ) -> None:
        super().__init__(line1, line2, radius=length, elbow=True, **kwargs)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def adjacent_n_tuples[T](objects: Sequence[T], n: int) -> Iterator[tuple[T, ...]]:
    """Each run of `n` items in a row, wrapping around at the end: for `[a, b, c]` and
    2, `(a, b)`, `(b, c)` and `(c, a)`.

    Args:
        objects: The items.
        n: How many items each run has.

    Returns:
        The runs, as tuples, one starting at each item.
    """
    return zip(*(list(objects[k:]) + list(objects[:k]) for k in range(n)), strict=True)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def adjacent_pairs[T](objects: Sequence[T]) -> Iterator[tuple[T, ...]]:
    """Each item with the next, wrapping around at the end (see
    [adjacent_n_tuples][manimgx.adjacent_n_tuples]).

    Args:
        objects: The items.

    Returns:
        The pairs, as tuples, one starting at each item.
    """
    return adjacent_n_tuples(objects, 2)


if TYPE_CHECKING:
    from pathops import Path as SkiaPath
    from pathops import PathOp

    from manimgx.typing import Point3D_Array


def _combine(operation: PathOp, *vmobjects: VMobject) -> SkiaPath:
    """Fold an operation over the operands' own outlines, left to right."""
    paths = [_to_path(m.points, m.tolerance_for_point_equality) for m in vmobjects]
    return reduce(lambda a, b: _pathops().op(a, b, operation), paths)


class Union(VMobject):
    """The union of shapes: the region any of them covers, as a new path; white unless
    styled.

    It is found from the shapes' own paths (not their submobjects'), each the region
    its fill covers, in the plane of the screen: their z coordinates are dropped. The
    shapes stay as they are.

    Args:
        *vmobjects: The shapes: at least two.

    Examples:
        ```python
        import manimgx as m


        class UnionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(3, color=m.RED, fill_opacity=0.5).shift(4.5 * m.LEFT)
                circle = m.Circle(1.5, color=m.BLUE, fill_opacity=0.5)
                circle.shift(3 * m.LEFT + m.UP)
                union = m.Union(square, circle, color=m.GREEN, fill_opacity=0.8)
                self.add(square, circle, union.shift(7 * m.RIGHT))
        ```
    """

    def __init__(self, *vmobjects: VMobject, **kwargs: Unpack[Style]) -> None:
        if len(vmobjects) < 2:
            raise ValueError("At least 2 mobjects needed for Union.")
        super().__init__(**kwargs)
        outpen = _pathops().Path()
        _pathops().union(
            [
                _to_path(vmobject.points, vmobject.tolerance_for_point_equality)
                for vmobject in vmobjects
            ],
            outpen.getPen(),
        )
        _append_path(self, outpen)


class Difference(VMobject):
    """The difference of two shapes: the region the first covers and the second does
    not, as a new path; white unless styled.

    It is found from the shapes' own paths (not their submobjects'), each the region
    its fill covers, in the plane of the screen: their z coordinates are dropped. The
    shapes stay as they are.

    Args:
        subject: The shape to take a part of.
        clip: The shape whose region is left out of it.

    Examples:
        ```python
        import manimgx as m


        class DifferenceExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(3, color=m.RED, fill_opacity=0.5).shift(4.5 * m.LEFT)
                circle = m.Circle(1.5, color=m.BLUE, fill_opacity=0.5)
                circle.shift(3 * m.LEFT + m.UP)
                cut = m.Difference(square, circle, color=m.GREEN, fill_opacity=0.8)
                self.add(square, circle, cut.shift(7 * m.RIGHT))
        ```
    """

    def __init__(
        self, subject: VMobject, clip: VMobject, **kwargs: Unpack[Style]
    ) -> None:
        super().__init__(**kwargs)
        _append_path(self, _combine(_pathops().PathOp.DIFFERENCE, subject, clip))


class Intersection(VMobject):
    """The intersection of shapes: the region all of them cover, as a new path; white
    unless styled.

    It is found from the shapes' own paths (not their submobjects'), each the region
    its fill covers, in the plane of the screen: their z coordinates are dropped. The
    shapes stay as they are.

    Args:
        *vmobjects: The shapes: at least two.

    Examples:
        ```python
        import manimgx as m


        class IntersectionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(3, color=m.RED, fill_opacity=0.5).shift(4.5 * m.LEFT)
                circle = m.Circle(1.5, color=m.BLUE, fill_opacity=0.5)
                circle.shift(3 * m.LEFT + m.UP)
                common = m.Intersection(square, circle, color=m.GREEN, fill_opacity=0.8)
                self.add(square, circle, common.shift(7 * m.RIGHT))
        ```
    """

    def __init__(self, *vmobjects: VMobject, **kwargs: Unpack[Style]) -> None:
        if len(vmobjects) < 2:
            raise ValueError("At least 2 mobjects needed for Intersection.")
        super().__init__(**kwargs)
        _append_path(self, _combine(_pathops().PathOp.INTERSECTION, *vmobjects))


class Exclusion(VMobject):
    """The exclusive or of two shapes: the region one of them covers but not both, as a
    new path; white unless styled.

    It is found from the shapes' own paths (not their submobjects'), each the region
    its fill covers, in the plane of the screen: their z coordinates are dropped. The
    shapes stay as they are.

    Args:
        subject: The first shape.
        clip: The second shape.

    Examples:
        ```python
        import manimgx as m


        class ExclusionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(3, color=m.RED, fill_opacity=0.5).shift(4.5 * m.LEFT)
                circle = m.Circle(1.5, color=m.BLUE, fill_opacity=0.5)
                circle.shift(3 * m.LEFT + m.UP)
                either = m.Exclusion(square, circle, color=m.GREEN, fill_opacity=0.8)
                self.add(square, circle, either.shift(7 * m.RIGHT))
        ```
    """

    def __init__(
        self, subject: VMobject, clip: VMobject, **kwargs: Unpack[Style]
    ) -> None:
        super().__init__(**kwargs)
        _append_path(self, _combine(_pathops().PathOp.XOR, subject, clip))


class PointCloudDot(Mobject1D):
    """A disk of points: rings of points around a center, pure yellow unless styled.

    The rings are 1/`density` scene units apart, from that far from the center out to
    just inside `radius`, and the points along each ring about as far apart. Its points
    are small: `stroke_width` 2.

    Args:
        center: Where its center is, in scene coordinates.
        radius: How far out its points reach, in scene units.
        density: How many rings, and points along a ring, per scene unit.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]: `color` colors its points,
            and `stroke_width` sizes them.

    Examples:
        ```python
        import manimgx as m


        class PointCloudDotExample(m.Scene):
            def construct(self) -> None:
                clouds = m.Group(
                    m.PointCloudDot(),
                    m.PointCloudDot(density=5, stroke_width=8, color=m.BLUE),
                    m.PointCloudDot(density=15, stroke_width=4, color=m.RED),
                ).arrange(buff=0.6)
                self.add(clouds)
        ```
    """

    defaults: ClassVar[Style] = {"stroke_width": 2, "color": PURE_YELLOW}

    def __init__(
        self,
        center: Point3DLike = ORIGIN,
        radius: float = 2.0,
        *,
        density: int = DEFAULT_POINT_DENSITY_1D,
        **kwargs: Unpack[Style],
    ) -> None:
        self.radius = radius
        self.epsilon = 1.0 / density
        super().__init__(density=density, **kwargs)
        self.shift(center)

    def generate_points(self) -> Self:
        rings = []
        for r in np.arange(self.epsilon, self.radius, self.epsilon):
            theta = np.linspace(
                0,
                2 * np.pi,
                num=int(2 * np.pi * (r + self.epsilon) / self.epsilon),
            )[:, None]
            rings.append(r * (np.cos(theta) * RIGHT + np.sin(theta) * UP))
        return self.add_points(np.concatenate(rings) if rings else np.empty((0, 3)))

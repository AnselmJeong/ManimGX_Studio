# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"Mutable scene objects: one family graph, shared geometry and paint, and path, point and mesh leaf rules."

import copy
import functools
import inspect
import itertools as it
import math
import pathlib
import random
import types
import weakref
from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping, Sequence
from fractions import Fraction
from functools import reduce
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Concatenate,
    Final,
    Literal,
    Never,
    Self,
    TypeIs,
    Unpack,
    cast,
    overload,
)
from warnings import deprecated

import numpy as np
import numpy.typing as npt
from typing_extensions import TypedDict

from manimgx import caches
from manimgx.animation import clock
from manimgx.caches import Memo, unchanged
from manimgx.config import config
from manimgx.constants import (
    DEFAULT_MOBJECT_TO_EDGE_BUFFER,
    DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
    DEFAULT_POINT_DENSITY_1D,
    DEFAULT_STROKE_WIDTH,
    DL,
    DOWN,
    IN,
    LEFT,
    MED_SMALL_BUFF,
    ORIGIN,
    OUT,
    RIGHT,
    TAU,
    UL,
    UP,
    CapStyleType,
    LineJointType,
)
from manimgx.drawing.geometry import (
    _NPPCC,
    EMPTY,
    Blend,
    Lattice,
    Path,
    _pathops,
    bezier,
    bezier_remap,
    get_smooth_cubic_bezier_handle_points,
    integer_interpolate,
    interpolate,
    linear_about,
    normalize,
    partial_bezier_points,
    rotation_matrix,
    segment,
    shoelace_direction,
    straight_path,
    subpath_ranges,
    turn_between,
)
from manimgx.drawing.paint import (
    BLACK,
    WHITE,
    Colors,
    ManimColor,
    Material,
    Paint,
    PaintAttribute,
    ParsableManimColor,
    SimpleStyle,
    Style,
    StyleBase,
    StyleSnapshot,
    _Look,
    color_gradient,
    frozen,
    interpolate_color,
    key_of,
    parse_colors,
    stretch_array,
)
from manimgx.typing import (
    MatrixMN,
    PathFunc,
    Point3D,
    Point3D_Array,
    Point3DLike,
    Point3DLike_Array,
    PointsFunc,
    RGBA_Array,
    Vector3D,
    Vector3DLike,
)

__all__ = [
    "ComplexValueTracker",
    "Group",
    "MeshMobject",
    "Mobject",
    "Mobject1D",
    "PGroup",
    "PMobject",
    "Point",
    "VDict",
    "VGroup",
    "VMobject",
    "ValueTracker",
    "VectorizedPoint",
    "override_animate",
    "override_animation",
    "remove_list_redundancies",
]

if TYPE_CHECKING:
    from manimgx.animation.timeline import Animation
    from manimgx.animation.transform import Always, Animate

type Updater[M] = Callable[[M], object] | Callable[[M, float], object]
"""A function that keeps a mobject updated: called with the mobject once a frame, or, if
it has a parameter named `dt`, with the mobject and the seconds since it last ran. What
it returns is ignored; see [add_updater][manimgx.Mobject.add_updater]."""

type _Recorder = tuple[
    "Mobject", Callable[..., object], Sequence[Callable[..., object]]
]


def axis_factors(factor: float | Vector3DLike) -> np.ndarray:
    """A scale's factors along x, y and z.

    Args:
        factor: One factor for every axis, or one per axis.

    Returns:
        The three factors.
    """
    return np.broadcast_to(np.asarray(factor, dtype=float), 3)


def length_factor(factor: float | Vector3DLike) -> float:
    """How a scale changes a length that has no direction, such as a stroke's width or a
    font's size.

    Args:
        factor: The scale's factor, or its factors along x, y and z.

    Returns:
        The factor itself; for one factor per axis, the geometric mean of the sizes of
        x's and y's.
    """
    x, y, _ = np.abs(axis_factors(factor))
    return float(np.sqrt(x * y))


# CE's override decorators, as data: a mobject method → the animation class it plays instead
# (`override_animation`), and a mobject method → the method whose animation its `.animate`
# call plays (`override_animate`)
_plays_instead: dict[Callable[..., object], type["Animation"]] = {}
_animate_plays: dict[Callable[..., object], Callable[..., "Animation"]] = {}

# What an updater is, known per function (a method's is its function's) and held weakly:
# a function outlives no scene for being an updater, nor a method's object
_TIME_BASED: "weakref.WeakKeyDictionary[Callable[..., object], bool]" = (
    weakref.WeakKeyDictionary()
)
_FLOWS: "weakref.WeakSet[Callable[..., object]]" = weakref.WeakSet()


def _has_updater(
    updaters: Iterable[Callable[..., object]], updater: Callable[..., object]
) -> bool:
    """Whether this exact callable remains in the active updater list."""
    return any(active is updater for active in updaters)


def _function(updater: Callable[..., object]) -> Callable[..., object]:
    """The function an updater runs: a method's function, else the updater itself."""
    return getattr(updater, "__func__", updater)


def _per_frame[M](updater: Updater[M]) -> TypeIs[Callable[[M], object]]:
    """Does the updater take the mobject alone (no `dt`)? CE inspects the signature on every
    call; the answer is kept per function."""
    function = _function(updater)
    try:
        known = _TIME_BASED.get(function)
    except TypeError:  # held by no weak reference (a builtin): asked each time
        return "dt" not in inspect.signature(updater).parameters
    if known is None:
        known = _TIME_BASED[function] = "dt" in inspect.signature(updater).parameters
    return not known


def _flows(updater: Callable[..., object]) -> bool:
    """Is the updater a [flow][manimgx.mobject.flow] (or a method whose function is)?"""
    return _function(updater) in _FLOWS


def flow[U: Callable[..., object]](updater: U) -> U:
    """Declare a time-based updater a flow: one that does the same over some time
    however that time is split into steps.

    A time-based updater is handed `dt`, the seconds since it last ran. Most compose:
    one that moves the mobject at a rate (`mob.shift(dt * velocity)`), or sets it by a
    function of the time it has run, does the same in one step of `dt` as in two of
    `dt / 2`. A flow runs at every instant the scene computes — each frame, and the end
    of each play and wait — handed exactly the time since, so every frame shows it at
    that frame's instant.

    Any other time-based updater is simulated, since what it does may depend on its
    steps (an integrator, a ball that bounces): it steps on a clock of its own,
    `config.simulation_rate` ticks a second (60) and the end of each play and wait, so
    it takes the same steps at any frame rate, and a frame shows it as its last tick
    left it. While one is in the scene, the scene computes every tick, between frames
    too. Declare an updater that composes a flow to make it exact at every frame and to
    spare those ticks; [always_shift][manimgx.always_shift] and
    [always_rotate][manimgx.always_rotate] add flows. An updater that only reads the
    world, as a traced path's does, is a [recorder][manimgx.mobject.record].

    Args:
        updater: A time-based updater: a function of the mobject and `dt`.

    Returns:
        The same updater, declared a flow, to add with
        [add_updater][manimgx.Mobject.add_updater].

    Examples:
        ```python
        import manimgx as m
        from manimgx.mobject import flow


        @flow
        def orbit(dot: m.Mobject, dt: float) -> None:
            dot.rotate(dt * m.PI / 2, about_point=m.ORIGIN)  # a quarter turn a second


        class FlowExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(3 * m.RIGHT, radius=0.25, color=m.YELLOW)
                dot.add_updater(orbit)
                self.add(m.Circle(radius=3, color=m.BLUE), dot)
                self.wait(3)
        ```
    """
    _FLOWS.add(_function(updater))
    return updater


_RECORDERS: "weakref.WeakSet[Callable[..., object]]" = weakref.WeakSet()


def record[U: Callable[..., object]](updater: U) -> U:
    """Declare a time-based updater a recorder: one that reads the world and changes
    only its own mobject, as a [TracedPath][manimgx.TracedPath]'s does.

    The scene runs a recorder at every instant it computes — each tick of the
    simulation clock, each frame, and the end of each play and wait — once everything
    else is there: the animations playing, the mobjects' updaters and the scene's. At a
    frame or at the end of a play or wait, it runs twice: first on the world as time
    alone brought it there, as a tick sees it, then once the per-frame updaters have
    run, so it can tell their change apart (a traced path spreads it over the frame
    that ends there). A recorder is simulated (see [flow][manimgx.mobject.flow]):
    while one is in the scene, the scene computes the simulation clock's ticks.

    Args:
        updater: A time-based updater: a function of the mobject and `dt`, or such a
            method, decorated where its class defines it.

    Returns:
        The same updater, declared a recorder, to add with
        [add_updater][manimgx.Mobject.add_updater].
    """
    # the scene computes a frame or an event in two passes (`Scene._instant`) only while
    # a recorder is in it; the second pass is `clock.framing`
    _RECORDERS.add(_function(updater))
    return updater


def records(updater: Callable[..., object]) -> bool:
    """Whether an updater is a [recorder][manimgx.mobject.record].

    The scene asks, to know whether it must compute each frame in two passes.

    Args:
        updater: An updater; a method is a recorder if its function is.
    """
    return _function(updater) in _RECORDERS


def simulated(updater: Updater[Never]) -> bool:
    """Whether an updater steps on the simulation clock: it is time-based and not a
    [flow][manimgx.mobject.flow].

    The scene asks, to know whether it must compute the ticks of its simulation clock.

    Args:
        updater: An updater, of a mobject or of a scene.
    """
    return not _per_frame(updater) and not _flows(updater)


_SHARED: frozenset[type] = frozenset(
    {
        int,
        float,
        bool,
        str,
        bytes,
        Blend,
        Paint,
        ManimColor,
        np.float64,
        np.int64,
        np.bool_,
        types.FunctionType,  # a function (not a bound method: that is rebound to the copy)
        pathlib.PosixPath,
        pathlib.WindowsPath,
    }
)


def copied[T](value: T) -> T:
    """A deep copy of a value that holds mobjects.

    Lists, tuples and dicts are rebuilt, each mobject is copied once (so two references
    to one mobject refer to one copy), and plain values are shared.

    Args:
        value: A mobject, or a container of mobjects and plain values.
    """
    # see `_copied`
    return cast("T", _copied(value, {}))


def _copied(value: object, memo: dict[int, object]) -> object:
    """A deep copy that knows the common shapes: values shared, containers rebuilt, mobjects
    copied through the memo (aliases stay aliases)."""
    kind = type(value)
    if value is None or kind in _SHARED:
        return value
    if kind is list:
        return [_copied(v, memo) for v in cast("list[object]", value)]
    if kind is dict:
        return {
            k: _copied(v, memo) for k, v in cast("dict[object, object]", value).items()
        }
    if kind is tuple:
        return tuple(_copied(v, memo) for v in cast("tuple[object, ...]", value))
    if isinstance(value, Mobject):
        known = memo.get(id(value))
        return known if known is not None else value.__deepcopy__(memo)
    if kind is np.ndarray:  # read-only, an array is a value: shared
        array = cast("np.ndarray", value)
        return array.copy() if array.flags.writeable else array
    return copy.deepcopy(value, memo)


_CASCADES: Memo[type, Style] = Memo(1 << 12)
_UNPAINTED: Final = Paint()  # every mobject's paint until its style is applied
_PAINT_STYLE: Final = (
    "color",
    "fill_color",
    "fill_opacity",
    "stroke_color",
    "stroke_width",
    "stroke_opacity",
    "background_stroke_color",
    "background_stroke_width",
    "background_stroke_opacity",
    "sheen_factor",
    "sheen_direction",
    "joint_type",
    "cap_style",
    "shade_in_3d",
    "material",
)
# a style's paint, as the first `init_colors` makes it: (the mobject's, a fresh member's)
_STYLED: Memo[tuple[object, ...], tuple[Paint, Paint | None]] = Memo(1 << 12)
_PROTOTYPES: Memo[tuple[object, ...], "Mobject"] = Memo(1 << 12)


def _copy_state(source: "Mobject", target: "Mobject", memo: dict[int, object]) -> None:
    """Copy fields in order, with active clock stamps owned by the copied updaters."""
    shared = type(source).shared
    copied = target.__dict__
    for name, value in source.__dict__.items():
        if value is None or type(value) in _SHARED or name in shared:
            copied[name] = value
        elif name == "_since_":
            stamps = cast("dict[object, Fraction]", value)
            copied[name] = {
                (updater if "updaters" in shared else _copied(updater, memo)): stamps[
                    updater
                ]
                for updater in source.updaters
                if updater in stamps
            }
        else:
            copied[name] = _copied(value, memo)


def prototype[S: "Mobject", **P](
    init: Callable[Concatenate[S, P], None],
) -> Callable[Concatenate[S, P], None]:
    """Make a mobject class's construction run once per distinct call: a decorator for
    its `__init__`.

    Construction is a value: an `__init__` given the same arguments (and the same
    configuration) makes the same mobject. So it runs once per distinct call, and every
    later construction takes a copy of what it made; an expensive mobject (typeset text,
    an arrow tip) is made once. A call with an argument that is not a plain value (a
    mobject, a function) constructs as usual.

    Args:
        init: The class's `__init__`.

    Returns:
        The `__init__`, remembering what it makes.
    """

    # a later construction adopts the made mobject's attributes: whatever named the made
    # mobject names the new one

    @functools.wraps(init)
    def construct(self: S, *args: P.args, **kwargs: P.kwargs) -> None:
        if self.__dict__:
            init(self, *args, **kwargs)
            return
        try:
            key = (
                init,
                type(self),
                key_of(args),
                key_of(sorted(kwargs.items())),
                key_of(tuple(vars(config).values())),
            )
        except TypeError:
            init(self, *args, **kwargs)
            return
        made = _PROTOTYPES.get(key)
        if made is None:
            init(self, *args, **kwargs)
            _PROTOTYPES.keep(key, self.copy())
            return
        _copy_state(made, self, {id(made): self})

    return construct


def _anchors(points: Point3D_Array) -> Point3D_Array:
    """A path's anchors: the first and last point of every cubic curve."""
    if len(points) < 4:
        return points
    return points[np.r_[0 : len(points) : 4, 3 : len(points) : 4]]


def _style_key(style: Style) -> tuple[object, ...] | None:
    try:
        key = tuple(key_of(style.get(name)) for name in _PAINT_STYLE)
    except TypeError:
        return None
    return key


_STRAIGHT = straight_path()  # a default (paths are immutable)


class GridArrangement(TypedDict, total=False):
    """How [arrange_in_grid][manimgx.Mobject.arrange_in_grid] lays mobjects out: its
    keywords, for the classes that pass them on (tables)."""

    rows: int | None
    """How many rows (default None: as many as `row_alignments` or `row_heights` lists,
    else as many as the mobjects need; with neither `rows` nor `cols`, a grid as square
    as it can be)."""
    cols: int | None
    """How many columns (default None: as many as `col_alignments` or `col_widths`
    lists, else as many as the mobjects need; with neither `rows` nor `cols`, a grid as
    square as it can be)."""
    buff: float | tuple[float, float]
    """The gap between cells, in scene units: one for both directions, or (horizontal,
    vertical) (default 0.25)."""
    cell_alignment: Vector3DLike
    """Where each mobject sits in its cell, as a direction: UL for its top left corner
    (default ORIGIN: centered)."""
    row_alignments: str | None
    """Each row's vertical alignment, top to bottom: a letter per row, "u" (up), "c"
    (center) or "d" (down) (default None: as `cell_alignment`'s vertical part says)."""
    col_alignments: str | None
    """Each column's horizontal alignment, left to right: a letter per column, "l"
    (left), "c" (center) or "r" (right) (default None: as `cell_alignment`'s horizontal
    part says)."""
    row_heights: Iterable[float | None] | None
    """Each row's height, top to bottom, in scene units; None for the height of its
    tallest mobject (default None: all measured)."""
    col_widths: Iterable[float | None] | None
    """Each column's width, left to right, in scene units; None for the width of its
    widest mobject (default None: all measured)."""
    flow_order: str
    """The order the cells are filled in: two letters, the direction a line of cells
    fills and then the direction the lines follow each other — "r" (right), "l" (left),
    "u" (up) or "d" (down) (default "rd": rows left to right, from the top down; "dr"
    fills columns top to bottom, from the left)."""


class _Beside(TypedDict, total=False):
    """Beside's keys, open, for the keywords that add to them."""

    aligned_edge: Vector3DLike
    """The edge, as a direction, along which the two line up besides the side they meet
    at: with the direction RIGHT and UP here, their tops line up (default ORIGIN:
    centered)."""
    submobject_to_align: "Mobject | None"
    """A part of the mobject to put beside the other in its place; the rest moves with
    it (default None: the whole mobject)."""
    index_of_submobject_to_align: int | None
    """The index of the part of each mobject to line up: this one's part goes beside the
    other's (default None: the whole of each)."""
    coor_mask: Vector3DLike
    """Which coordinates may change: 1 for each axis the mobject moves along, 0 for one
    it keeps (default (1, 1, 1))."""


class Beside(_Beside, total=False, closed=True):
    """How [next_to][manimgx.Mobject.next_to] aligns a mobject beside another: its
    keywords but the direction and the gap, for the methods that pass them on
    ([arrange][manimgx.Mobject.arrange])."""


class Placement(_Beside, total=False, closed=True):
    """How [next_to][manimgx.Mobject.next_to] places a mobject beside another: its
    keywords but the direction, for the methods that pass them on."""

    buff: float
    """The gap between the two, in scene units (default 0.25)."""


class BackgroundOptions(_Look, total=False, closed=True):
    """A background rectangle's keywords but its color and opacity: those of
    [add_background_rectangle][manimgx.Mobject.add_background_rectangle] and its
    variants."""

    buff: float | tuple[float, float]
    """The margin around the mobject, in scene units: one for both directions, or
    (horizontal, vertical) (default 0)."""
    corner_radius: float
    """The radius of the rectangle's corners, in scene units (default 0: square
    corners)."""
    stroke_width: float
    """The width of the rectangle's outline, in hundredths of a scene unit (default 0:
    none)."""
    stroke_opacity: float
    """The outline's opacity, from 0 to 1 (default 0)."""
    stroke_color: Colors | None
    """The outline's color (default: the rectangle's color)."""


class Pivot(TypedDict, total=False, closed=True):
    """The point a transformation keeps fixed: given, or a point of the mobject's
    bounding box.

    With neither keyword, a scale, a rotation or a stretch keeps the mobject's center
    fixed, and a function or a matrix is applied about the origin.
    """

    about_point: Point3DLike | None
    """The point that stays fixed, in scene coordinates; it takes precedence over
    `about_edge`."""
    about_edge: Vector3DLike | None
    """The point of the mobject's bounding box that stays fixed, named by a direction:
    UP for the middle of its top edge, UR for its top right corner, ORIGIN for its
    center."""


def style_defaults(cls: "type[Mobject]") -> Style:
    """A mobject class's style defaults: the [defaults][manimgx.Mobject.defaults] of
    every class in its hierarchy, each class's over its parents'.

    Args:
        cls: A mobject class.

    Returns:
        The defaults of its style keywords.
    """
    # each class in the hierarchy adds only what it changes; cached per class
    cached = _CASCADES.get(cls)
    if cached is None:
        cached = Style()
        for klass in reversed(cls.__mro__):
            if issubclass(klass, Mobject) and "defaults" in vars(klass):
                cached = cached | klass.defaults
        _CASCADES.keep(cls, cached)
    return cached


@deprecated("use list(dict.fromkeys(items))", category=None)
def remove_list_redundancies[T](items: Sequence[T]) -> list[T]:
    """The items without repeats: each one once, where it last occurs.

    Items are the same when they are the same object.

    Args:
        items: The items, in order.

    Returns:
        A new list.
    """
    # the last occurrence of each is kept (CE semantics)
    seen: set[int] = set()
    out: list[T] = []
    for x in reversed(items):
        if id(x) not in seen:
            seen.add(id(x))
            out.append(x)
    out.reverse()
    return out


def _family(roots: Iterable["Mobject"]) -> list["Mobject"]:
    """Preorder from these roots, each member once at its last occurrence."""
    # Right-to-left postorder is reversed preorder. Keep its first occurrences,
    # skipping already visited subtrees, then reverse to keep preorder's last ones.
    family: list[Mobject] = []
    seen: set[int] = set()
    pending: list[Mobject | tuple[Mobject]] = list(roots)
    while pending:
        item = pending.pop()
        if isinstance(item, tuple):
            family.append(item[0])
        elif id(item) not in seen:
            seen.add(id(item))
            if item.submobjects:
                pending.append((item,))
                pending.extend(item.submobjects)
            else:
                family.append(item)
    family.reverse()
    return family


def _family_box(family: Iterable["Mobject"]) -> np.ndarray | None:
    """Combine the selected family's own geometry boxes without constructing a group."""
    # A member's box is what it draws (`_box`); paths use their curves' tight bounds.
    boxes = [b for m in family if m._geometry.n and (b := m._box()) is not None]
    if len(boxes) < 2:
        return boxes[0] if boxes else None
    stacked = np.array(boxes)
    return np.array([stacked[:, 0].min(axis=0), stacked[:, 1].max(axis=0)])


class Mobject:
    """The object everything in a scene is made of: shapes, text, groups, trackers.

    A mobject has points in scene coordinates (x to the right, y up, z out of the
    screen; the frame is 8 units on its short side, about 14.2 × 8 at 16:9, centered
    on the origin);
    submobjects, a tree drawn and moved with it; a style: its fill, its stroke and their
    colors; updaters, which change it as time passes; and a z-index, its place in the
    drawing order. You make one through its subclasses — [`Circle`][manimgx.Circle],
    [`Text`][manimgx.Text], [`VGroup`][manimgx.VGroup] and the rest — and they all share
    the methods here: to transform it ([`shift`][manimgx.Mobject.shift],
    [`scale`][manimgx.Mobject.scale], [`rotate`][manimgx.Mobject.rotate]), lay it out
    ([`next_to`][manimgx.Mobject.next_to], [`arrange`][manimgx.Mobject.arrange]), style
    it ([`set_color`][manimgx.Mobject.set_color]), keep it updated
    ([`add_updater`][manimgx.Mobject.add_updater]), and animate any of that
    ([`animate`][manimgx.Mobject.animate]).

    A transformation or a style acts on the mobject's whole family — the mobject, its
    submobjects, theirs, and so on — and returns the mobject, so calls chain:
    `Square().scale(2).set_color(BLUE)`. Size and layout go by the mobject's
    [bounding box][manimgx.Mobject.boundary_box]: the smallest box, aligned with the
    axes, around what it draws.
    """

    animation_overrides: ClassVar[
        dict[type["Animation"], Callable[..., "Animation"]]
    ] = {}
    # The animations the class plays another in place of: each animation class, with the
    # function that makes the one played instead (see `override_animation`).
    defaults: ClassVar[Style] = {}
    """The style keywords whose defaults the class changes: a subclass lists only what
    it changes (`defaults = {"color": BLUE}`), and takes the rest from its parents (see
    [style_defaults][manimgx.mobject.style_defaults])."""
    shared: ClassVar[frozenset[str]] = frozenset(
        {"style", "__orig_class__", "_film_record"}
    )
    """The attributes a copy shares with its original instead of copying them: values
    that are never changed in place."""

    # CE's style attributes, kept in the paint: each reads and sets the mobject's own,
    # not its family's
    joint_type = PaintAttribute[LineJointType]("joint")
    """How the mobject's own stroke is joined where its path turns: round, beveled or
    mitered (see [LineJointType][manimgx.LineJointType])."""
    cap_style = PaintAttribute[CapStyleType]("cap")
    """How the mobject's own stroke ends, at each end it shows: round, butt or square
    (see [CapStyleType][manimgx.CapStyleType])."""
    shade_in_3d = PaintAttribute[bool]("shade_in_3d")
    """Whether a three-dimensional scene's light shades the mobject's own paint."""
    material = PaintAttribute[Material | None]("material")
    """How the mobject's own surface reflects the scene's lights (see
    [Material][manimgx.Material]); None: Manim's shading."""
    sheen_factor = PaintAttribute[float]("sheen_factor")
    """How much the mobject's own colors lighten toward its `sheen_direction`, from -1
    to 1 (0: none; negative: they darken); see
    [set_sheen][manimgx.Mobject.set_sheen]."""
    sheen_direction = PaintAttribute[Vector3D, Vector3DLike]("sheen_direction")
    """The direction the mobject's own colors lighten toward, which its color gradients
    run along too."""
    fill_rgbas = PaintAttribute[RGBA_Array, npt.ArrayLike]("fill")
    """The mobject's own fill colors, as rows of red, green, blue and opacity, from 0 to
    1: one row per gradient stop."""
    stroke_rgbas = PaintAttribute[RGBA_Array, npt.ArrayLike]("stroke")
    """The mobject's own stroke colors, as rows of red, green, blue and opacity, from 0
    to 1."""
    background_stroke_rgbas = PaintAttribute[RGBA_Array, npt.ArrayLike]("background")
    """The colors of the mobject's own background stroke (an outline drawn behind its
    fill), as rows of red, green, blue and opacity, from 0 to 1."""
    background_stroke_width = PaintAttribute[float]("background_width")
    """The width of the mobject's own background stroke, in hundredths of a scene
    unit."""
    z_index_group: "Mobject | None" = None
    """The group the mobject is ordered with in a three-dimensional scene, if any: set
    by `set_shade_in_3d(z_index_as_group=True)`. Kept for Manim compatibility: the
    renderer draws a three-dimensional scene by depth."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        own = {
            _plays_instead[f]: f
            for f in vars(cls).values()
            if inspect.isfunction(f) and f in _plays_instead
        }
        if own:  # a class's overrides are its bases' and its own
            cls.animation_overrides = cls.animation_overrides | own

    def __init__(self, **kwargs: Unpack[Style]) -> None:
        if (
            "color" in kwargs and kwargs["color"] is None
        ):  # not given: the class's default
            del kwargs["color"]
        self.style = style_defaults(type(self)) | kwargs
        """Pending constructor style, including the class's defaults. Base color
        initialization consumes this instance entry; current appearance is kept in
        [paint][manimgx.Mobject.paint]. Point clouds retain their defaults for later points."""
        name = self.style.get("name")
        self.name = type(self).__name__ if name is None else name
        """The mobject's name: its class's name, unless it was made with one."""
        self.dim = 3
        """How many coordinates each of its points has: 3."""
        self.target: Mobject | None = self.style.get("target")
        """The state [MoveToTarget][manimgx.MoveToTarget] moves the mobject to: made by
        [generate_target][manimgx.Mobject.generate_target], or given when the mobject
        was made; None if neither."""
        self.z_index = self.style.get("z_index", 0.0)
        """The mobject's place in the drawing order: a higher index is drawn over a
        lower one (default 0); see [set_z_index][manimgx.Mobject.set_z_index]."""
        self.submobjects: list[Mobject] = []
        """The mobject's children, in drawing order: each is drawn over those before it,
        at an equal z-index."""
        self.updaters: list[Updater[Self]] = []
        """The mobject's own updaters, in the order they run; see
        [add_updater][manimgx.Mobject.add_updater]."""
        self.updating_suspended = False
        """Whether the mobject's updaters are suspended; see
        [suspend_updating][manimgx.Mobject.suspend_updating]."""
        self.paint = _UNPAINTED
        """The mobject's own style as it is now, as one value: its colors, opacities,
        stroke widths and sheen. The style methods replace it; it is never changed in
        place."""
        self.reset_points()
        self.generate_points()
        self.init_colors()

    # ── kind hooks ─────────────────────────────────────────────────────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def generate_points(self) -> Self:
        """Build the mobject's points: its shape.

        The constructor calls it. A class with a shape of its own overrides it; a plain
        mobject has no points.
        """
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def init_points(self) -> Self:
        """Build the mobject's points: the same as
        [generate_points][manimgx.Mobject.generate_points], by another name.
        """
        # CE's other name for `generate_points`
        self.generate_points()
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def init_colors(self, propagate_colors: bool = True) -> Self:
        """Paint the mobject with its style.

        The constructor calls it once its points are built: the first call paints the
        style keywords the mobject was made with, then consumes those inputs. A later
        call paints its present style again — its first fill and stroke colors, their
        opacities, its stroke widths and its sheen. A subclass can read its instance's
        pending `style` before delegating; successful initialization removes that entry.

        Args:
            propagate_colors: Whether its whole family is painted (so the parts
                [generate_points][manimgx.Mobject.generate_points] made), or the mobject
                alone.
        """
        # CE semantics: the first call paints the constructor style onto the family,
        # later calls re-apply the current style to it
        family = propagate_colors
        p = self.paint
        s: Style | None = self.__dict__.get("style")
        if s is None:
            self.set_fill(self.get_fill_color(), p.fill[0, 3], family)
            self.set_stroke(
                self.get_stroke_color(), p.stroke_width, p.stroke[0, 3], family=family
            )
            self.set_stroke(
                self.get_stroke_color(background=True),
                p.background_width,
                p.background[0, 3],
                background=True,
                family=family,
            )
            return self.set_sheen(p.sheen_factor, p.sheen_direction, family)
        members = self._each(family)
        key = _style_key(s)
        if key is not None and any(m.paint is not _UNPAINTED for m in members):
            key = None  # a family painted already is painted over, not looked up
        if key is not None:  # the paint a style makes is a value: made once, shared
            styled = _STYLED.get(key)
            if styled is not None and (len(members) == 1 or styled[1] is not None):
                self.paint, rest = styled
                if rest is not None:
                    for m in members[1:]:
                        m.paint = rest
                del self.style
                return self
        color = s.get("color", WHITE)
        fill, stroke, joint = (
            s.get("fill_color"),
            s.get("stroke_color"),
            s.get("joint_type"),
        )
        self.paint = p.but(
            joint=LineJointType.AUTO if joint is None else joint,
            cap=s.get("cap_style", CapStyleType.AUTO),
            shade_in_3d=s.get("shade_in_3d", False),
            material=s.get("material"),
        )
        self.set_fill(
            color if fill is None else fill, s.get("fill_opacity", 0.0), family
        )
        self.set_stroke(
            color if stroke is None else stroke,
            s.get("stroke_width", DEFAULT_STROKE_WIDTH),
            s.get("stroke_opacity", 1.0),
            family=family,
        )
        self.set_stroke(
            s.get("background_stroke_color", BLACK),
            s.get("background_stroke_width", 0.0),
            s.get("background_stroke_opacity", 1.0),
            background=True,
            family=family,
        )
        self.set_sheen(s.get("sheen_factor", 0.0), s.get("sheen_direction", UL), family)
        del self.style
        if key is not None:
            _STYLED.keep(
                key, (self.paint, members[1].paint if len(members) > 1 else None)
            )
        return self

    # its points are cubic curves' control points (a path): its box is its curves' tight box
    _curves: ClassVar[bool] = False

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_points_defining_boundary(self) -> Point3D_Array:
        """The points [get_boundary_point][manimgx.Mobject.get_boundary_point] chooses
        among: every point of the mobject's family — or, for a path, its members'
        anchors, the ends of its curves (a path's handles need not lie on it).

        The mobject's bounding box is not made from them: it is
        [boundary_box][manimgx.Mobject.boundary_box], around what the family draws.

        Returns:
            The points, as an (n, 3) array.
        """
        if not self._curves:
            return self.get_all_points()
        arrays = [
            _anchors(m.points)
            for m in self.get_family()
            if m._curves and m.has_points()
        ]
        return np.concatenate(arrays) if arrays else np.zeros((0, 3))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def align_points_with_larger(self, larger: "Mobject") -> Self:
        """Give the mobject as many points as `larger`, its shape unchanged, so the two
        can be blended point by point.

        [align_points][manimgx.Mobject.align_points] calls it on the one of two mobjects
        with fewer points. Each kind implements it (a path divides its curves); a
        mobject of no kind cannot.

        Args:
            larger: The mobject with more points.
        """
        raise NotImplementedError(f"{type(self).__name__} cannot align points")

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_point_mobject(self, center: Point3DLike | None = None) -> "Mobject":
        """The mobject shrunk to a point: what it grows from, or shrinks to, when a
        transform makes it appear or disappear.

        A kind returns a point of its own kind and style; a mobject of no kind, the
        group of its members' points.

        Args:
            center: Where the point is; None for the mobject's center.

        Returns:
            A new mobject.
        """
        c = self.get_center() if center is None else center
        return Group(*(m.get_point_mobject(c) for m in self.submobjects))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def pointwise_become_partial(self, mobject: "Mobject", a: float, b: float) -> Self:
        """Become a part of another mobject: its points from proportion `a` of the way
        along it to proportion `b`, as a reveal over that stretch shows it: a path's
        curves, cut where `a` and `b` fall; a cloud's points, a mesh's triangles and a
        surface's faces whole, every one the stretch reaches into.

        [get_pieces][manimgx.Mobject.get_pieces] calls it. Each kind implements it; a
        mobject of no kind stays as it is.

        Args:
            mobject: The mobject to take a part of (this one, or one of its kind).
            a: Where the part starts, from 0 to 1.
            b: Where the part ends, from `a` to 1.
        """
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def reveal_pace(self) -> tuple[np.ndarray, np.ndarray] | None:
        """How a reveal ([Create][manimgx.Create], [Write][manimgx.Write], …) moves
        through the mobject: evenly by its parts, or, for a path, by arc length, so it
        is drawn at a steady speed.

        The reveal animations read it for each drawn member.

        Returns:
            None for evenly by step (points, triangles, or a surface's faces, in order,
            each whole with all it draws); for a path, fractions of its length and the
            curve parameters where they are reached.
        """
        return None

    # ── points ────────────────────────────────────────────────────────────
    @property
    def points(self) -> Point3D_Array:
        """The mobject's own points, in scene coordinates: an (n, 3) array, read-only.

        A path's are the control points of its cubic Bézier curves, four per curve.
        Assign an array to reshape the mobject; its submobjects keep theirs. Assigning the
        points it has changes nothing (it keeps its geometry, and all that was derived from
        it), unless they are a blend of shapes, as mid-morph, which become one; assigning
        them with more after them grows it.
        """
        # the geometry blend, materialized (cached, hence read-only)
        return self._geometry.points()

    @points.setter
    def points(self, value: Point3DLike_Array) -> None:
        array = np.asarray(value, dtype=float).reshape(-1, self.dim)
        g = self.__dict__.get("_geometry", EMPTY)  # (none yet, while constructing)
        # one shape: the points it was given again, or more after them, compared as the
        # geometry holds them (their last point first: points that changed are told at once),
        # are unchanged, or grown; so are the points it was read as (never read for this: a
        # change would pay for it). A blend of more shapes becomes one again, which the
        # player draws directly.
        if 0 < g.n <= len(array) and len(g.terms) == 1:
            m, shape = g.terms[0]
            if (
                np.array_equal(m[:, :3], np.eye(3))
                and np.array_equal(array[g.n - 1] - m[:, 3], shape.array[-1])
                and np.array_equal(array[: g.n] - m[:, 3], shape.array)
            ):
                if len(array) > g.n:
                    self._geometry = Blend(
                        ((m, shape.extended(array[g.n :] - m[:, 3])),), len(array)
                    )
                return
            if g.n == len(array) and unchanged(array, g.cached):
                return
        self._geometry = Blend.of(array, self.dim)

    def reset_points(self) -> Self:
        """Remove the mobject's own points; its submobjects keep theirs."""
        self._geometry: Blend = EMPTY
        return self

    def set_points(self, points: Point3DLike_Array) -> Self:
        """Give the mobject new points of its own, in place of its present ones.

        Args:
            points: The points, in scene coordinates: an (n, 3) array.
        """
        self.points = np.array(points, dtype=float)
        return self

    @deprecated("get_points() is points: use it", category=None)
    def get_points(self) -> Point3D_Array:
        """The mobject's own [points][manimgx.Mobject.points].

        Returns:
            An (n, 3) array, read-only.
        """
        return self.points

    def has_points(self) -> bool:
        """Whether the mobject has points of its own (a group has none: its members do)."""
        return self._geometry.n > 0

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def has_no_points(self) -> bool:
        """Whether the mobject has no points of its own."""
        return self._geometry.n == 0

    @deprecated("use len(mobject.points)", category=None)
    def get_num_points(self) -> int:
        """How many points of its own the mobject has.

        Returns:
            The number of points.
        """
        return self._geometry.n

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_all_points(self) -> Point3D_Array:
        """Every point of the mobject's family, member after member.

        Returns:
            An (n, 3) array.
        """
        arrays = [m.points for m in self.get_family()]
        return np.concatenate(arrays) if arrays else np.zeros((0, 3))

    def get_start(self) -> Point3D:
        """The mobject's first point: where a path starts.

        Raises an exception if the mobject has no points of its own.

        Returns:
            The point, in scene coordinates.
        """
        self._require_points()
        return np.array(self.points[0])

    def get_end(self) -> Point3D:
        """The mobject's last point: where a path ends.

        Raises an exception if the mobject has no points of its own.

        Returns:
            The point, in scene coordinates.
        """
        self._require_points()
        return np.array(self.points[-1])

    @deprecated("use get_start() and get_end()", category=None)
    def get_start_and_end(self) -> tuple[Point3D, Point3D]:
        """The mobject's first and last points.

        Returns:
            Its [start][manimgx.Mobject.get_start] and its
            [end][manimgx.Mobject.get_end], in scene coordinates.
        """
        return self.get_start(), self.get_end()

    def _require_points(self) -> None:
        if self.has_no_points():
            raise Exception(
                f"Cannot call this method on a {type(self).__name__} with no points"
            )

    # ── family ────────────────────────────────────────────────────────────
    def add(self, *mobjects: "Mobject") -> Self:
        """Add submobjects after the ones the mobject has: they move with it, and are
        drawn over those before them (at an equal z-index).

        A mobject that is a submobject already moves to the end. Adding anything but a
        mobject, or the mobject itself or one that holds it, raises an exception (a
        mobject cannot hold itself).

        Args:
            *mobjects: The mobjects to add, in order.
        """
        return self._place(None, mobjects)

    def add_to_back(self, *mobjects: "Mobject") -> Self:
        """Add submobjects before the ones the mobject has: they are drawn under them
        (at an equal z-index).

        A mobject that is a submobject already moves to the front; what `add` refuses,
        this refuses too.

        Args:
            *mobjects: The mobjects to add, in order.
        """
        return self._place(0, mobjects)

    def insert(self, index: int, mobject: "Mobject") -> Self:
        """Insert a submobject at a place among the mobject's other submobjects.

        A mobject that is a submobject already moves there; what `add` refuses, this
        refuses too.

        Args:
            index: Its place in the list of the other submobjects, as `list.insert`
                takes it.
            mobject: The mobject to insert.
        """
        return self._place(index, (mobject,))

    def _place(self, index: int | None, mobjects: Sequence["Mobject"]) -> Self:
        """The one way submobjects join: each a mobject that neither is this one nor holds
        it, once (where it last occurs), at `index` among the others (None: last)."""
        for i, m in enumerate(mobjects):
            if not isinstance(m, Mobject):
                raise TypeError(
                    f"Only Mobjects can be added to {type(self).__name__}, got"
                    f" {type(m).__name__} at index {i}"
                )
            if m is self or (
                m.submobjects and any(member is self for member in m.get_family())
            ):
                raise ValueError(
                    f"Cannot add {type(m).__name__} to {type(self).__name__}: a"
                    " mobject cannot hold itself"
                )
        new = remove_list_redundancies(list(mobjects))
        joining = {id(m) for m in new}
        others = [m for m in self.submobjects if id(m) not in joining]
        at = len(others) if index is None else index
        self.submobjects = others[:at] + new + others[at:]
        return self

    def remove(self, *mobjects: "Mobject") -> Self:
        """Remove submobjects: those given that are among the mobject's own submobjects
        (not its submobjects' submobjects); the rest are ignored.

        Args:
            *mobjects: The mobjects to remove.
        """
        for m in mobjects:
            if m in self.submobjects:
                self.submobjects.remove(m)
        return self

    def get_family(self) -> list["Mobject"]:
        """The mobject and all its descendants: itself, then each submobject's family in
        turn, each member once (where it last occurs, if the tree holds it twice).

        Returns:
            A new list.
        """
        if not self.submobjects:
            return [self]
        return _family((self,))

    def family_members_with_points(self) -> list["Mobject"]:
        """The members of the mobject's family that have points of their own: the ones
        that are drawn.

        Returns:
            A new list, in family order.
        """
        return [m for m in self.get_family() if m.has_points()]

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def split(self) -> list["Mobject"]:
        """The mobject's parts: itself, if it has points of its own, then its
        submobjects.

        Indexing the mobject (`mobject[0]`), slicing it, iterating over it and its `len`
        go through the same parts.

        Returns:
            A new list.
        """
        return list(self)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_group_class(self) -> type["Group"]:
        """The class of the groups the mobject's parts are gathered in: slicing it
        (`mobject[1:3]`) makes one.

        Returns:
            [Group][manimgx.Group].
        """
        return Group

    def __iter__(self) -> Iterator["Mobject"]:
        return it.chain([self] if self.has_points() else [], self.submobjects)

    def __len__(self) -> int:
        return len(self.submobjects) + (1 if self.has_points() else 0)

    @overload
    def __getitem__(self, value: int) -> "Mobject": ...
    @overload
    def __getitem__(self, value: slice) -> "Mobject": ...
    def __getitem__(self, value: int | slice) -> "Mobject":
        items = list(self)
        if isinstance(value, slice):
            return self.get_group_class()(*items[value])
        return items[value]

    # ── copying ───────────────────────────────────────────────────────────
    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        """A copy shares what cannot change (geometry and paint are values, and what the class
        names in `shared`) and deep-copies the rest."""
        cls = type(self)
        result = cls.__new__(cls)
        memo[id(self)] = result
        _copy_state(self, result, memo)
        return result

    def copy(self) -> Self:
        """A copy of the mobject, with its whole family.

        Every mobject its attributes refer to is copied once, so an attribute that
        refers to one of its members refers to the copy's member. The copy runs the same
        updater functions, on itself, and is not in the scene. Copying is cheap: the
        copy shares the original's points and style until either one changes them.
        """
        return copy.deepcopy(self)

    def generate_target(self) -> Self:
        """Make the mobject's [target][manimgx.Mobject.target]: a copy of it, which you
        change into the state [MoveToTarget][manimgx.MoveToTarget] then animates the
        mobject to.

        Using [animate][manimgx.Mobject.animate] makes a new target too, in place of
        this one.

        Returns:
            The target.

        Examples:
            ```python
            import manimgx as m


            class MobjectGenerateTargetExample(m.Scene):
                def construct(self) -> None:
                    circle = m.Circle(radius=1.5, color=m.BLUE).shift(3 * m.LEFT)
                    target = circle.generate_target()
                    target.set_fill(m.GREEN, opacity=0.5).shift(6 * m.RIGHT + m.UP)
                    target.scale(0.5)
                    self.add(circle)
                    self.play(m.MoveToTarget(circle))
            ```
        """
        self.target = None  # not copied into the new target
        self.target = self.copy()
        return self.target

    def save_state(self) -> Self:
        """Keep a copy of the mobject as it is now, to return to with
        [restore][manimgx.Mobject.restore] or the [Restore][manimgx.Restore] animation.

        The copy is the mobject's `saved_state`; saving again replaces it.

        Examples:
            ```python
            import manimgx as m


            class MobjectSaveStateExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(color=m.BLUE, fill_opacity=0.5)
                    square.save_state()
                    self.add(square)
                    self.play(square.animate.set_color(m.YELLOW).shift(3 * m.LEFT))
                    self.play(square.animate.rotate(m.PI / 4).scale(2))
                    self.play(m.Restore(square))
            ```
        """
        self.saved_state = None  # not copied into the new saved state
        self.saved_state = self.copy()
        return self

    def restore(self) -> Self:
        """Make the mobject what it was when [save_state][manimgx.Mobject.save_state]
        last kept it: its points and its style, member by member (see
        [become][manimgx.Mobject.become]).

        Raises an exception if its state was never saved.
        """
        saved = getattr(self, "saved_state", None)
        if saved is None:
            raise Exception("Trying to restore without having saved")
        self.become(saved)
        return self

    # ── updaters ──────────────────────────────────────────────────────────
    # A time-based updater integrates the time it is live: `advance(t)` hands it the time since
    # it was last brought forward — or attached, joined the scene, or resumed — on its clock:
    # scene time, unless the updater carries a `clock` (ChangeSpeed's do).
    def update(self, dt: float = 0, recursive: bool = True) -> Self:
        """Run each of the mobject's updaters once, now; nothing runs while its updating
        is suspended.

        The scene runs updaters itself, at every frame: this runs them by hand, now.

        Args:
            dt: The seconds handed to its time-based updaters.
            recursive: Whether its submobjects' updaters run too, after its own.
        """
        # CE's; the scene uses `advance`
        if self.updating_suspended:
            return self
        updaters = self.updaters
        for updater in updaters:
            if updaters is not self.updaters and not _has_updater(
                self.updaters, updater
            ):
                continue
            if _per_frame(updater):
                updater(self)
            else:
                cast("Callable[[Self, float], object]", updater)(self, dt)
        if recursive:
            for sub in self.submobjects:
                sub.update(dt, recursive)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def advance(
        self,
        t: Fraction,
        recursive: bool = True,
        recorders: "list[_Recorder] | None" = None,
    ) -> Self:
        """Bring the mobject's updaters to scene time `t`.

        An engine hook: the scene calls it on each of its mobjects at every instant it
        computes, and an animation on the copy of its mobject that the updaters run on
        while it plays. Each time-based updater is handed the time since it last ran —
        on its own clock, if it has one (as [ChangeSpeed][manimgx.ChangeSpeed]'s
        updaters do). A simulated one (time-based, not a
        [flow][manimgx.mobject.flow]) runs only at the ticks of the simulation
        clock and at the ends of plays and waits; a per-frame one only at frames and
        those ends. Nothing runs while the mobject's updating is suspended.

        Args:
            t: The scene time, in seconds, exact.
            recursive: Whether its submobjects' updaters are brought there too, after
                its own.
            recorders: Where the scene collects the
                [recorders][manimgx.mobject.record], each with its mobject
                and the updater list it came from, to run them once everything
                else is at `t`; None: they run here, as the
                simulated updaters they are.
        """
        # a simulated updater runs only where it steps (`clock.stepping`: between the
        # simulation clock's ticks it stays where it was); a per-frame one only at a
        # frame or an event (`clock.framing`)
        if self.updating_suspended:
            return self
        updaters = self.updaters
        for updater in updaters:
            if updaters is not self.updaters and not _has_updater(
                self.updaters, updater
            ):
                continue
            if _per_frame(updater):
                if clock.framing:
                    updater(self)
            elif recorders is not None and records(updater):
                recorders.append((self, updater, updaters))
            elif clock.stepping or _flows(updater):
                self._bring(updater, t)
        if recursive:
            for sub in self.submobjects:
                sub.advance(t, recursive, recorders)
        return self

    def _bring(self, updater: Callable[..., object], t: Fraction) -> None:
        """Run a time-based updater with the time its clock ran since it was last brought
        forward."""
        since = self._since
        start = since.get(updater, t)
        since[updater] = t
        on = cast("clock.Clock | None", getattr(updater, "clock", None))
        dt = float(t - start) if on is None else on.at(float(t)) - on.at(float(start))
        updater(self, dt)

    @property
    def _since(self) -> dict[object, Fraction]:
        """When each time-based updater was last brought forward (made on first use)."""
        since = self.__dict__.get("_since_")
        if since is None:
            since = self.__dict__["_since_"] = {}
        return since

    def _stamp(self, t: Fraction, recursive: bool = True) -> None:
        """The time-based updaters start (again) from `t`: they joined the scene, or resumed."""
        for updater in self.updaters:
            if not _per_frame(updater):
                self._since[updater] = t
        if recursive:
            for sub in self.submobjects:
                sub._stamp(t, recursive)

    @overload
    def add_updater(
        self,
        update_function: Callable[[Self], object],
        index: int | None = None,
        call_updater: bool = False,
    ) -> Self: ...
    @overload
    def add_updater(
        self,
        update_function: Callable[[Self, float], object],
        index: int | None = None,
        call_updater: bool = False,
    ) -> Self: ...
    def add_updater(
        self,
        update_function: Updater[Self],
        index: int | None = None,
        call_updater: bool = False,
    ) -> Self:
        """Add an updater: a function that keeps the mobject updated as time passes.

        An updater is a function of the mobject, run once a frame — to keep a relation,
        such as a label beside a dot — or, if it has a parameter named `dt`, of the
        mobject and `dt`: the seconds of scene time since it last ran, or since it was
        added, the mobject joined the scene, or its updating resumed. A time-based
        updater moves the mobject by the time that passed:
        `lambda mob, dt: mob.rotate(dt * PI)` turns it half a turn a second, at any
        frame rate. What an updater returns is ignored.

        The scene runs the updaters of the mobjects in it at every frame, after the
        animations playing have moved them to the frame's instant, and at the end of
        each play and wait: mobject by mobject in the order they were added to the
        scene, a mobject's own before its submobjects', and a
        [recorder][manimgx.mobject.record] after all the rest. So add a mobject
        that follows another after it, or it sees where the other's updaters left it at
        the instant before. Updaters keep running while an animation plays the mobject,
        beneath the animation (see `suspend_mobject_updating` among the
        [animation options][manimgx.animation.timeline.AnimationOptions]). A time-based
        updater steps on the scene's simulation clock, `config.simulation_rate` ticks a
        second, so it takes the same steps at any frame rate; declare one that does the
        same however its time is split a [flow][manimgx.mobject.flow], and it runs
        exactly at every frame instead.

        Args:
            update_function: The updater: a function of the mobject, or of the mobject
                and `dt`.
            index: Where it goes among the mobject's updaters, which run in order; None
                for last.
            call_updater: Whether to run it once right away; a time-based one is handed
                a `dt` of 0.

        Examples:
            ```python
            import manimgx as m


            class MobjectAddUpdaterExample(m.Scene):
                def construct(self) -> None:
                    hand = m.Line(m.ORIGIN, 3 * m.RIGHT, color=m.BLUE)
                    # time-based: a quarter turn about the origin every second
                    hand.add_updater(
                        lambda mob, dt: mob.rotate(dt * m.PI / 2, about_point=m.ORIGIN)
                    )
                    dot = m.Dot(radius=0.2, color=m.YELLOW)
                    # per frame: at the hand's end, wherever it is
                    dot.add_updater(lambda mob: mob.move_to(hand.get_end()))
                    self.add(hand, dot)
                    self.wait(3)
            ```
        """
        if index is None:
            self.updaters.append(update_function)
        else:
            self.updaters.insert(index, update_function)
        if not _per_frame(update_function):
            self._since[update_function] = clock.now  # it integrates from now
        if call_updater:
            if _per_frame(update_function):
                update_function(self)
            else:
                cast("Callable[[Self, float], object]", update_function)(self, 0)
        return self

    def remove_updater(self, update_function: Updater[Never]) -> Self:
        """Remove an updater from the mobject, every time it was added.

        This also cancels calls that have not yet run in the current update,
        including a recorder waiting for the other updaters to finish.

        Args:
            update_function: The updater to remove.
        """
        self.updaters = [u for u in self.updaters if u is not update_function]
        since = self.__dict__.get("_since_")
        if since is not None and update_function not in self.updaters:
            since.pop(update_function, None)
        return self

    def clear_updaters(self, recursive: bool = True) -> Self:
        """Remove every updater of the mobject, including calls still waiting
        to run in the current update.

        Args:
            recursive: Whether its whole family's updaters are removed too.
        """
        self.updaters = []
        self.__dict__.pop("_since_", None)
        if recursive:
            for sub in self.submobjects:
                sub.clear_updaters()
        return self

    def get_updaters(self) -> tuple[Updater[Self], ...]:
        """The mobject's own updaters, in the order they run.

        Change them with [add_updater][manimgx.Mobject.add_updater],
        [remove_updater][manimgx.Mobject.remove_updater] and
        [clear_updaters][manimgx.Mobject.clear_updaters], which keep their clocks with
        them.

        Returns:
            A snapshot of them.
        """
        return tuple(self.updaters)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_family_updaters(self) -> list[Updater[Never]]:  # each of its own kind
        """Every updater of the mobject's family: its own, then its descendants', in
        family order.

        Returns:
            A new list.
        """
        return [u for m in self.get_family() for u in m.updaters]

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def has_time_based_updater(self) -> bool:
        """Whether any of the mobject's own updaters is time-based: it takes `dt`."""
        return not all(_per_frame(u) for u in self.updaters)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_time_based_updaters(self) -> list[Updater[Self]]:
        """The mobject's own time-based updaters: those that take `dt`.

        Returns:
            A new list, in the order they run.
        """
        return [u for u in self.updaters if not _per_frame(u)]

    @property
    def always(self) -> "Always[Self]":
        """A proxy that turns each method call made on it into an updater: the call is
        made again every frame.

        `label.always.next_to(dot, UP)` keeps the label above the dot, wherever the dot
        goes. Each call is also made right away, and adds one per-frame updater (see
        [add_updater][manimgx.Mobject.add_updater]); the proxy returns itself, so calls
        chain. The arguments are taken once, as written: pass the mobject to follow
        (`dot`), not its position (`dot.get_center()`), which stays where it was.

        Examples:
            ```python
            import manimgx as m


            class MobjectAlwaysExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(color=m.BLUE, fill_opacity=0.5).shift(4 * m.LEFT)
                    label = m.Text("always above")
                    label.always.next_to(square, m.UP)
                    self.add(square, label)
                    self.play(square.animate.shift(8 * m.RIGHT), run_time=2)
            ```
        """
        # CE's
        from manimgx.animation.transform import Always

        return Always(self)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def match_updaters(self, mobject: "Mobject") -> Self:
        """Give the mobject another's updaters in place of its own, and clear its
        submobjects'.

        They are the same functions, now run on this mobject too; the time-based ones
        start from now.

        Args:
            mobject: The mobject whose updaters to take (its own, not its family's).
        """
        self.clear_updaters()
        self.updaters.extend(
            mobject.get_updaters()  # ty: ignore[invalid-argument-type]  # CE: another mobject's updaters, applied to this one
        )
        self._stamp(clock.now, recursive=False)
        return self

    def suspend_updating(self, recursive: bool = True) -> Self:
        """Stop the mobject's updaters from running, and its family's beneath it, until
        [resume_updating][manimgx.Mobject.resume_updating]: nothing updated through a
        suspended mobject runs.

        An animation suspends the updating of the mobject it plays while it plays, and
        runs the updaters beneath it instead (see
        [add_updater][manimgx.Mobject.add_updater]).

        Args:
            recursive: Whether each member of its family is suspended too, so that it stays
                stopped where it is updated apart from the mobject (a member the scene
                also holds by itself), and when the mobject alone resumes.
        """
        self.updating_suspended = True
        if recursive:
            for sub in self.submobjects:
                sub.suspend_updating(recursive)
        return self

    def resume_updating(self, recursive: bool = True) -> Self:
        """Let the mobject's updaters run again, from now: the time they were suspended
        is not made up.

        They are not run here: the scene runs them where it next brings the world — at
        the instant it is computing, when an animation resumes them as it finishes,
        else at the next one, such as the next frame.

        Args:
            recursive: Whether its whole family's updaters resume too: resumed alone, the
                mobject runs again, and the members beneath it that are not suspended
                themselves.
        """
        # not run here as well: the instant's own pass runs them, and a per-frame
        # updater would run twice at one instant
        self.updating_suspended = False
        if recursive:
            for sub in self.submobjects:
                sub.resume_updating(recursive)
        self._stamp(clock.now, recursive)
        return self

    # ── the one transform primitive ────────────────────────────────────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def apply_points_function_about_point(
        self,
        func: PointsFunc,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Apply a function to the points of the mobject's whole family, about a point:
        each drawn member's points become `func(points - about_point) + about_point`.

        It moves the points alone, and a path's curves follow its control points: they
        are exactly their image under an affine map (a move, a scale, a rotation, a
        matrix), but stray from it under a function that bends them.
        [apply_function][manimgx.Mobject.apply_function] maps a path's curves
        themselves, cutting them where a function bends them.

        Args:
            func: A function of an (n, 3) array of points, relative to the point, that
                returns their new places.
            about_point: The point the function is applied about; None: see
                `about_edge`.
            about_edge: The point of the mobject's bounding box it is applied about,
                named by a direction (UL for its top left corner); None for its center.
        """
        if about_point is None:
            about_point = self.get_critical_point(
                ORIGIN if about_edge is None else about_edge
            )
        about = np.array(about_point, dtype=float)
        for mob in self.family_members_with_points():
            mob.points = func(mob.points - about) + about
        return self

    def shift(self, *vectors: Vector3DLike) -> Self:
        """Move the mobject and its whole family by a vector.

        Args:
            *vectors: The vector, in scene units (`2 * RIGHT` moves it two units right);
                several are added into one.

        Examples:
            ```python
            import manimgx as m


            class MobjectShiftExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(color=m.BLUE, fill_opacity=0.5)
                    self.add(square)
                    self.play(square.animate.shift(4 * m.LEFT))
                    self.play(square.animate.shift(2 * m.UP, 8 * m.RIGHT))
            ```
        """
        # one vector (a (1, 3) array too, as CE takes it)
        vector = vectors[0] if len(vectors) == 1 else reduce(np.add, vectors)
        total = np.asarray(vector, dtype=float).reshape(-1)
        for mob in self.family_members_with_points():
            mob._geometry = mob._geometry.translated(total)
        return self

    def _apply_linear(
        self,
        linear: MatrixMN,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """x ↦ L(x − about) + about on every member: a matrix composed into the geometry."""
        if about_point is None:
            about_point = self.get_critical_point(
                ORIGIN if about_edge is None else about_edge
            )
        m = linear_about(
            np.asarray(linear, dtype=float), np.array(about_point, dtype=float)
        )
        for mob in self.family_members_with_points():
            mob._geometry = mob._geometry.transformed(m)
        return self

    def scale(
        self,
        scale_factor: float | Vector3DLike,
        scale_stroke: bool = False,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Scale the mobject and its whole family about a point: by one factor, or by
        one per axis.

        Stroke widths stay as they are, unless `scale_stroke`.

        Args:
            scale_factor: The factor: 2 doubles the mobject's size, 0.5 halves it, and a
                negative factor also reflects it through the point; or its factors along
                x, y and z.
            scale_stroke: Whether stroke widths scale too, by the factor (for factors
                per axis, the geometric mean of the sizes of x's and y's).
            about_point: The point that stays fixed; None: see `about_edge`.
            about_edge: The point of the mobject's bounding box that stays fixed, named
                by a direction (DL for its bottom left corner); None for its center.

        Examples:
            ```python
            import manimgx as m


            class MobjectScaleExample(m.Scene):
                def construct(self) -> None:
                    a = m.Square(color=m.BLUE, fill_opacity=0.5)
                    b, c = a.copy(), a.copy()
                    m.VGroup(a, b, c).arrange(buff=2.5)
                    for square, text in zip(
                        (a, b, c), ("scale(2)", "about_edge=DL", "[0.5, 1.5, 1]")
                    ):
                        self.add(m.Text(text, font_size=32).next_to(square, m.DOWN, 2))
                    self.add(a, b, c)
                    self.play(
                        a.animate.scale(2),
                        b.animate.scale(2, about_edge=m.DL),
                        c.animate.scale([0.5, 1.5, 1]),
                    )
            ```
        """
        if scale_stroke:
            length = length_factor(scale_factor)
            for mob in self.get_family():
                mob.paint = mob.paint.but(
                    stroke_width=length * mob.get_stroke_width(),
                    background_width=length * mob.get_stroke_width(background=True),
                )
        if isinstance(scale_factor, (int, float)):  # one factor: a scale about a point
            if about_point is None:
                edge = ORIGIN if about_edge is None else about_edge
                about_point = self.get_critical_point(edge)
            about = np.array(about_point, dtype=float)
            for mob in self.family_members_with_points():
                mob._geometry = mob._geometry.scaled(float(scale_factor), about)
            return self
        return self._apply_linear(
            np.diag(axis_factors(scale_factor)), about_point, about_edge
        )

    def rotate(
        self,
        angle: float,
        axis: Vector3DLike = OUT,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Rotate the mobject and its whole family by an angle, about an axis through a
        point.

        Its sheen direction turns with it. Through [animate][manimgx.Mobject.animate],
        the mobject turns rigidly through the whole angle.

        Args:
            angle: The angle, in radians: counterclockwise as seen from where `axis`
                points (on the screen, for the default axis).
            axis: The axis's direction (default OUT, out of the screen: a turn in the
                plane).
            about_point: The point the axis goes through; None: see `about_edge`.
            about_edge: The point of the mobject's bounding box the axis goes through,
                named by a direction (DL for its bottom left corner); None for its
                center.

        Examples:
            ```python
            import manimgx as m


            class MobjectRotateExample(m.Scene):
                def construct(self) -> None:
                    a = m.Square(side_length=2.5, color=m.BLUE, fill_opacity=0.5)
                    b = m.Square(side_length=2.5, color=m.YELLOW, fill_opacity=0.5)
                    m.VGroup(a, b).arrange(buff=4)
                    pivot = m.Dot(b.get_corner(m.DL), radius=0.12, color=m.RED)
                    self.add(a, b, pivot)
                    self.play(
                        a.animate.rotate(m.PI / 4),
                        b.animate.rotate(m.PI / 2, about_edge=m.DL),
                    )
            ```
        """
        rot = rotation_matrix(angle, axis)
        self._rotate_direction_state(rot)
        return self._apply_linear(rot, about_point, about_edge)

    def _rotate_direction_state(self, rot: MatrixMN) -> None:
        for mob in self.get_family():
            mob.paint = mob.paint.but(sheen_direction=rot @ mob.paint.sheen_direction)

    @deprecated(
        "rotate_about_origin(angle, axis) is rotate(angle, axis, about_point=ORIGIN)",
        category=None,
    )
    def rotate_about_origin(self, angle: float, axis: Vector3DLike = OUT) -> Self:
        """Rotate the mobject and its whole family by an angle, about an axis through
        the origin: `rotate(angle, axis, about_point=ORIGIN)`.

        Args:
            angle: The angle, in radians: counterclockwise as seen from where `axis`
                points.
            axis: The axis's direction (default OUT: a turn in the plane of the screen).
        """
        return self.rotate(angle, axis, about_point=ORIGIN)

    def flip(
        self,
        axis: Vector3DLike = UP,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Flip the mobject and its whole family over: turn it half around an axis
        through a point, which mirrors it across that axis.

        About the default UP axis, it is mirrored left to right; about RIGHT, upside
        down. Through [animate][manimgx.Mobject.animate], it turns over, through space.

        Args:
            axis: The axis's direction (default UP).
            about_point: The point the axis goes through; None: see `about_edge`.
            about_edge: The point of the mobject's bounding box the axis goes through,
                named by a direction; None for its center.

        Examples:
            ```python
            import manimgx as m


            class MobjectFlipExample(m.Scene):
                def construct(self) -> None:
                    word = m.Text("flip", font_size=160, color=m.YELLOW)
                    self.add(word)
                    self.play(word.animate.flip())
                    self.play(word.animate.flip(m.RIGHT))
            ```
        """
        return self.rotate(
            TAU / 2, axis, about_point=about_point, about_edge=about_edge
        )

    @deprecated(
        "stretch_about_point(factor, dim, point) is stretch(factor, dim, about_point=point): use it",
        category=None,
    )
    def stretch_about_point(self, factor: float, dim: int, point: Point3DLike) -> Self:
        """Stretch the mobject and its whole family along one axis, keeping a point
        fixed (see [stretch][manimgx.Mobject.stretch]).

        Args:
            factor: The factor along the axis.
            dim: The axis: 0 for x, 1 for y, 2 for z.
            point: The point that stays fixed.
        """
        return self.stretch(factor, dim, about_point=point)

    def stretch(
        self,
        factor: float,
        dim: int,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Stretch the mobject and its whole family along one axis: scale that
        coordinate of every point, about a point, and keep the others.

        Stroke widths stay as they are.

        Args:
            factor: The factor: 2 makes the mobject twice as long along the axis.
            dim: The axis: 0 for x (its width), 1 for y (its height), 2 for z.
            about_point: The point that stays fixed; None: see `about_edge`.
            about_edge: The point of the mobject's bounding box that stays fixed, named
                by a direction (DOWN for the middle of its bottom edge); None for its
                center.

        Examples:
            ```python
            import manimgx as m


            class MobjectStretchExample(m.Scene):
                def construct(self) -> None:
                    circle = m.Circle(radius=1.5, color=m.BLUE, fill_opacity=0.5)
                    self.add(circle)
                    self.play(circle.animate.stretch(3, 0))
                    self.play(circle.animate.stretch(0.5, 1, about_edge=m.DOWN))
            ```
        """
        linear = np.eye(3)
        linear[dim, dim] = factor
        return self._apply_linear(linear, about_point, about_edge)

    def apply_matrix(
        self,
        matrix: MatrixMN,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Transform the mobject and its whole family by a matrix: each point, taken
        relative to a fixed point, is multiplied by it.

        Args:
            matrix: A 3 × 3 matrix, or a smaller one (2 × 2) that acts on the first
                coordinates and keeps the rest.
            about_point: The point that stays fixed; with neither this nor `about_edge`,
                the origin.
            about_edge: The point of the mobject's bounding box that stays fixed, named
                by a direction.

        Examples:
            ```python
            import manimgx as m


            class MobjectApplyMatrixExample(m.Scene):
                def construct(self) -> None:
                    grid = m.NumberPlane()
                    square = m.Square(color=m.YELLOW, fill_opacity=0.5).shift(m.UR)
                    shear = [[1, 1], [0, 1]]
                    self.add(grid, square)
                    self.play(
                        grid.animate.apply_matrix(shear),
                        square.animate.apply_matrix(shear),
                        run_time=2,
                    )
            ```
        """
        if about_point is None and about_edge is None:
            about_point = ORIGIN
        full = np.identity(self.dim)
        m = np.array(matrix)
        full[: m.shape[0], : m.shape[1]] = m
        return self._apply_linear(full, about_point, about_edge)

    def apply_function(
        self,
        function: Callable[[Point3D], Point3D],
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """Move the mobject's whole family through a function, about a point: each
        drawn member becomes its image under the function.

        A path's curves are mapped to the curves of their image. Each curve is mapped to
        the curve through the images of its ends, along the images of its directions
        there; where one strays from the true image halfway along it by more than 0.001
        scene units (a quarter of a pixel at 4K), every curve of the path is cut into 2,
        4, 8, … equal pieces (at most 256 each), and the pieces are mapped instead. Any
        other kind maps its points. Through [animate][manimgx.Mobject.animate], each
        point of the path, cut the same way, moves straight to its image.

        Args:
            function: A function of a point, relative to the fixed point, that returns
                its new place.
            about_point: The point the function is applied about; with neither this nor
                `about_edge`, the origin, so the function sees scene coordinates.
            about_edge: The point of the mobject's bounding box it is applied about,
                named by a direction.

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            def wave(p: np.ndarray) -> np.ndarray:
                return p + 0.5 * np.array([np.sin(p[1]), np.sin(p[0]), 0])


            class MobjectApplyFunctionExample(m.Scene):
                def construct(self) -> None:
                    grid = m.NumberPlane()
                    grid.prepare_for_nonlinear_transform()
                    self.add(grid)
                    self.play(grid.animate.apply_function(wave), run_time=2)
            ```
        """
        # each leaf becomes its image its own way (`_map_points`): a mobject's points
        # map; a path's curves become the curves of their image (`VMobject._map_points`)
        if about_point is None:
            about_point = (
                ORIGIN if about_edge is None else self.get_critical_point(about_edge)
            )
        about = np.array(about_point, dtype=float)
        for mob in self.family_members_with_points():
            mob._map_points(function, about)
        return self

    def _map_points(
        self, function: Callable[[Point3D], Point3D], about: np.ndarray
    ) -> None:
        """This leaf's image under `function`, about `about`: each point mapped."""
        self.points = np.apply_along_axis(function, 1, self.points - about) + about

    def apply_complex_function(
        self, function: Callable[[complex], complex], **kwargs: Unpack[Pivot]
    ) -> Self:
        """Move the mobject's whole family through a function of a complex number: the
        point (x, y, z) is x + iy, and goes where `function` sends it, keeping its z.

        A path's curves are mapped as [apply_function][manimgx.Mobject.apply_function]
        maps them.

        Args:
            function: A function of a complex number, returning one.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point the
                function is applied about (default: the origin).

        Examples:
            ```python
            import manimgx as m


            class MobjectApplyComplexFunctionExample(m.Scene):
                def construct(self) -> None:
                    grid = m.ComplexPlane(x_range=(-4, 4, 0.5), y_range=(-4, 4, 0.5))
                    grid.prepare_for_nonlinear_transform()
                    self.add(grid)
                    self.play(
                        grid.animate.apply_complex_function(lambda z: z**2 / 4),
                        run_time=2,
                    )
            ```
        """

        def r3(point: Point3D) -> Point3D:
            z = function(complex(point[0], point[1]))
            return np.array([z.real, z.imag, point[2]])

        return self.apply_function(r3, **kwargs)

    @deprecated("use move_to(function(mobject.get_center()))", category=None)
    def apply_function_to_position(
        self, function: Callable[[Point3D], Point3D]
    ) -> Self:
        """Move the mobject so its center goes where a function sends it; its shape
        stays.

        Args:
            function: A function of a point, in scene coordinates, that returns its new
                place.
        """
        return self.move_to(function(self.get_center()))

    @deprecated("use move_to(function(mobject.get_center()))", category=None)
    def apply_function_to_submobject_positions(
        self, function: Callable[[Point3D], Point3D]
    ) -> Self:
        """Move each submobject so its center goes where a function sends it; their
        shapes stay.

        Args:
            function: A function of a point, in scene coordinates, that returns its new
                place.
        """
        for sub in self.submobjects:
            sub.apply_function_to_position(function)
        return self

    @deprecated("use reverse_direction", category=None)
    def reverse_points(self) -> Self:
        """Reverse the order of the points of each drawn member of the family: a path
        then runs the other way, from its end to its start.
        """
        for mob in self.family_members_with_points():
            mob.points = mob.points[::-1].copy()
        return self

    # ── bounds: one box, what the family draws ───────────────────────────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def length_over_dim(self, dim: int) -> float:
        """The mobject's extent along one axis, in scene units: its
        [bounding box][manimgx.Mobject.boundary_box]'s, from its lowest coordinate to
        its highest.

        Args:
            dim: The axis: 0 for x (its width), 1 for y (its height), 2 for z (its
                depth).

        Returns:
            The extent; 0 if it has no points.
        """
        box = self.boundary_box()
        return 0 if box is None else float(box[1, dim] - box[0, dim])

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_extremum_along_dim(
        self, points: Point3D_Array | None = None, dim: int = 0, key: float = 0
    ) -> float:
        """The lowest, the middle or the highest coordinate along one axis, of some
        points or of the mobject's [bounding box][manimgx.Mobject.boundary_box].

        Args:
            points: The points, as an (n, 3) array; None for the mobject's bounding box.
            dim: The axis: 0 for x, 1 for y, 2 for z.
            key: Which: negative for the lowest, 0 for the middle of the range, positive
                for the highest.

        Returns:
            The coordinate; 0 for the box of a mobject with no points.
        """
        if points is None:
            box = self.boundary_box()
            lo, hi = (0.0, 0.0) if box is None else (box[0, dim], box[1, dim])
        else:
            lo, hi = np.min(points[:, dim]), np.max(points[:, dim])
        return float(lo if key < 0 else hi if key > 0 else (lo + hi) / 2)

    def _box(self) -> np.ndarray | None:
        """The (2, 3) box of what this member draws, alone: its geometry's (a path's,
        its curves' tight box); None when it draws nothing."""
        return self._geometry.box(self._curves)

    def boundary_box(self) -> np.ndarray | None:
        """The mobject's bounding box: the smallest box, aligned with the axes, around
        what its family draws.

        A path is measured by its curves themselves, not by their control points (a
        curve bulges past its anchors where it turns, and its handles reach past the
        curve); any other kind by its points. A stroke's width is not counted. It is
        the one box every measure reads: [width][manimgx.Mobject.width] and
        [height][manimgx.Mobject.height], the corners, edges and center
        ([get_critical_point][manimgx.Mobject.get_critical_point]), `get_x` and `get_y`,
        alignment and layout, and the extent of a color gradient. It joins the boxes of
        the family's members, so a member spans the same in whatever group holds it.

        Returns:
            A 2 × 3 array, the lowest (x, y, z) then the highest; None if the family has
            no points.
        """
        return _family_box(self.get_family())

    def get_critical_point(self, direction: Vector3DLike) -> Point3D:
        """A point of the mobject's bounding box, named by a direction: its center, the
        middle of an edge, or a corner.

        Each coordinate is the box's lowest where the direction's is negative, its
        highest where it is positive, and its middle where it is 0: UR names the top
        right corner, UP the middle of the top edge, ORIGIN the center. The box is
        [boundary_box][manimgx.Mobject.boundary_box], around what the mobject draws: a
        path's curves themselves, not their control points.

        Args:
            direction: The direction, such as UP, UR or ORIGIN.

        Returns:
            The point, in scene coordinates; the origin if the mobject has no points.
        """
        box = self.boundary_box()
        if box is None:
            return np.zeros(self.dim)
        lo, hi = box.tolist()
        return np.array(
            [
                lo[k] if d < 0 else hi[k] if d > 0 else (lo[k] + hi[k]) / 2
                for k, d in enumerate(np.asarray(direction).tolist()[: self.dim])
            ]
        )

    @deprecated(
        "get_edge_center is get_critical_point: use it, or get_top, get_bottom,"
        " get_left and get_right",
        category=None,
    )
    def get_edge_center(self, direction: Vector3DLike) -> Point3D:
        """The middle of an edge of the mobject's bounding box, named by a direction:
        [get_critical_point][manimgx.Mobject.get_critical_point], by another name."""
        return self.get_critical_point(direction)

    get_corner = get_critical_point
    """A corner of the mobject's bounding box, named by a direction (`get_corner(UR)`):
    another name for [get_critical_point][manimgx.Mobject.get_critical_point]."""

    def get_center(self) -> Point3D:
        """The center of the mobject's bounding box.

        Returns:
            The point, in scene coordinates.
        """
        return self.get_critical_point(np.zeros(self.dim))

    @deprecated("use get_center", category=None)
    def get_center_of_mass(self) -> Point3D:
        """The mean of all the points of the mobject's family: every control point of a
        path, its handles too.

        Returns:
            The point, in scene coordinates.
        """
        return np.mean(self.get_all_points(), axis=0)

    def get_boundary_point(self, direction: Vector3DLike) -> Point3D:
        """The point of the mobject farthest in a direction: of the points it is drawn
        through, the one farthest along `direction`.

        Unlike [get_critical_point][manimgx.Mobject.get_critical_point], it is one of
        those points (for a path, an end of one of its curves), not a point of the
        mobject's bounding box.

        Returns:
            The point, in scene coordinates.
        """
        points = self.get_points_defining_boundary()
        return points[np.argmax(points @ np.asarray(direction))]

    def get_top(self) -> Point3D:
        """The middle of the top edge of the mobject's bounding box.

        Returns:
            The point, in scene coordinates.
        """
        return self.get_critical_point(UP)

    def get_bottom(self) -> Point3D:
        """The middle of the bottom edge of the mobject's bounding box.

        Returns:
            The point, in scene coordinates.
        """
        return self.get_critical_point(DOWN)

    def get_right(self) -> Point3D:
        """The middle of the right edge of the mobject's bounding box.

        Returns:
            The point, in scene coordinates.
        """
        return self.get_critical_point(RIGHT)

    def get_left(self) -> Point3D:
        """The middle of the left edge of the mobject's bounding box.

        Returns:
            The point, in scene coordinates.
        """
        return self.get_critical_point(LEFT)

    @deprecated("use get_critical_point(OUT), or get_critical_point(IN)", category=None)
    def get_zenith(self) -> Point3D:
        """The middle of the face of the mobject's bounding box farthest out of the
        screen (toward OUT: its highest z).

        Returns:
            The point, in scene coordinates.
        """
        return self.get_critical_point(OUT)

    @deprecated("use get_critical_point(OUT), or get_critical_point(IN)", category=None)
    def get_nadir(self) -> Point3D:
        """The middle of the face of the mobject's bounding box farthest into the screen
        (toward IN: its lowest z).

        Returns:
            The point, in scene coordinates.
        """
        return self.get_critical_point(IN)

    @deprecated("use get_x, get_y or get_z", category=None)
    def get_coord(self, dim: int, direction: Vector3DLike = ORIGIN) -> float:
        """One coordinate of a point of the mobject's bounding box: along axis `dim`,
        its lowest, middle or highest, as `direction`'s coordinate there is negative, 0
        or positive.

        Args:
            dim: The axis: 0 for x, 1 for y, 2 for z.
            direction: A direction such as LEFT, ORIGIN or RIGHT (default ORIGIN: the
                middle).
        """
        return self.get_extremum_along_dim(dim=dim, key=np.asarray(direction)[dim])

    def get_x(self, direction: Vector3DLike = ORIGIN) -> float:
        """The x coordinate of the mobject's center, or of an edge of its bounding box.

        Args:
            direction: LEFT for its left edge, RIGHT for its right edge; ORIGIN
                (default) for its center.
        """
        return self.get_coord(0, direction)

    def get_y(self, direction: Vector3DLike = ORIGIN) -> float:
        """The y coordinate of the mobject's center, or of an edge of its bounding box.

        Args:
            direction: DOWN for its bottom edge, UP for its top edge; ORIGIN (default)
                for its center.
        """
        return self.get_coord(1, direction)

    def get_z(self, direction: Vector3DLike = ORIGIN) -> float:
        """The z coordinate of the mobject's center, or of a face of its bounding box.

        Args:
            direction: IN for its lowest z, OUT for its highest; ORIGIN (default) for
                its center.
        """
        return self.get_coord(2, direction)

    def get_midpoint(self) -> Point3D:
        """The point halfway along the mobject: for a path, half its length from its
        start.

        Returns:
            The point, in scene coordinates.
        """
        return self.point_from_proportion(0.5)

    def point_from_proportion(self, alpha: float) -> Point3D:
        """The point a proportion of the way along the mobject, from its start (0) to
        its end (1): for a path, by its length.

        Each kind implements it; a mobject of no kind has no way along it, and raises an
        exception.

        Args:
            alpha: The proportion, from 0 to 1.

        Returns:
            The point, in scene coordinates.
        """
        raise NotImplementedError(f"{type(self).__name__} has no parametrization")

    @property
    def width(self) -> float:
        """The mobject's width, in scene units: its
        [bounding box][manimgx.Mobject.boundary_box]'s extent along x, from the leftmost
        of what it draws to the rightmost. Set it to scale the mobject to that width, in
        proportion, about its center."""
        return self.length_over_dim(0)

    @width.setter
    def width(self, value: float) -> None:
        self.scale_to_fit_width(value)

    @property
    def height(self) -> float:
        """The mobject's height, in scene units: its
        [bounding box][manimgx.Mobject.boundary_box]'s extent along y, from the lowest
        of what it draws to the highest. Set it to scale the mobject to that height, in
        proportion, about its center."""
        return self.length_over_dim(1)

    @height.setter
    def height(self, value: float) -> None:
        self.scale_to_fit_height(value)

    @deprecated("get_width() is width: use it", category=None)
    def get_width(self) -> float:
        """The mobject's [width][manimgx.Mobject.width].

        Returns:
            The width, in scene units.
        """
        return self.width

    # ── layout ────────────────────────────────────────────────────────────
    def center(self) -> Self:
        """Move the mobject so the center of its bounding box is at the origin."""
        return self.shift(-self.get_center())

    def move_to(
        self,
        point_or_mobject: "Point3DLike | Mobject",
        aligned_edge: Vector3DLike = ORIGIN,
        coor_mask: Vector3DLike = (1, 1, 1),
    ) -> Self:
        """Move the mobject to a point, or onto another mobject: its center, or the
        point of its bounding box `aligned_edge` names, goes there.

        Args:
            point_or_mobject: A point, in scene coordinates, or a mobject: then the
                point of its bounding box `aligned_edge` names (its center, by default).
            aligned_edge: The point of the mobject that goes there, named by a
                direction: ORIGIN (default) for its center, DL for its bottom left
                corner.
            coor_mask: Which coordinates change: 1 for each axis the mobject moves
                along, 0 for one it keeps (`(1, 0, 0)` moves it horizontally only).

        Examples:
            ```python
            import manimgx as m


            class MobjectMoveToExample(m.Scene):
                def construct(self) -> None:
                    dot = m.Dot([3, 1.5, 0], radius=0.15, color=m.YELLOW)
                    origin = m.Dot(radius=0.15, color=m.RED)
                    square = m.Square(color=m.BLUE, fill_opacity=0.5).shift(4 * m.LEFT)
                    self.add(dot, origin, square)
                    self.play(square.animate.move_to(dot))
                    self.play(square.animate.move_to(m.ORIGIN, aligned_edge=m.DL))
            ```
        """
        if isinstance(point_or_mobject, Mobject):
            target = point_or_mobject.get_critical_point(aligned_edge)
        else:
            target = np.asarray(point_or_mobject, dtype=float)
        return self.shift(
            (target - self.get_critical_point(aligned_edge)) * np.asarray(coor_mask)
        )

    def next_to(
        self,
        mobject_or_point: "Mobject | Point3DLike",
        direction: Vector3DLike = RIGHT,
        buff: float = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
        aligned_edge: Vector3DLike = ORIGIN,
        submobject_to_align: "Mobject | None" = None,
        index_of_submobject_to_align: int | None = None,
        coor_mask: Vector3DLike = (1, 1, 1),
    ) -> Self:
        """Put the mobject beside another, or beside a point, `buff` away in a
        direction.

        The side of the mobject facing back along `direction` goes to the other's side
        facing along it, `buff` farther on: with RIGHT, the middle of its left edge goes
        `buff` to the right of the middle of the other's right edge. A diagonal
        direction (UR) puts corner to corner.

        Args:
            mobject_or_point: The mobject (its bounding box) or the point to put it
                beside.
            direction: The side: RIGHT (default), UP, DL, …
            buff: The gap, in scene units, along `direction` (default 0.25).
            aligned_edge: The edge along which the two line up besides the side they
                meet at, named by a direction: with the direction RIGHT and UP here,
                their tops line up (default ORIGIN: centered).
            submobject_to_align: A part of the mobject to put beside the other in its
                place; the rest moves with it.
            index_of_submobject_to_align: The index of the part of each mobject to line
                up: this one's part goes beside the other's.
            coor_mask: Which coordinates change: 1 for each axis the mobject moves
                along, 0 for one it keeps.

        Examples:
            ```python
            import manimgx as m


            class MobjectNextToExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                    right = m.Text("RIGHT").next_to(square, m.RIGHT)
                    up = m.Text("UP, aligned LEFT").next_to(
                        square, m.UP, aligned_edge=m.LEFT
                    )
                    down = m.Text("DOWN, buff=1").next_to(square, m.DOWN, buff=1)
                    dot = m.Dot(radius=0.2, color=m.YELLOW)
                    dot.next_to(square, m.UL, buff=0)
                    self.add(square, right, up, down, dot)
            ```
        """
        d, edge = (
            np.asarray(direction, dtype=float),
            np.asarray(aligned_edge, dtype=float),
        )
        if isinstance(mobject_or_point, Mobject):
            target_aligner = (
                mobject_or_point
                if index_of_submobject_to_align is None
                else mobject_or_point[index_of_submobject_to_align]
            )
            target = target_aligner.get_critical_point(edge + d)
        else:
            target = np.asarray(mobject_or_point, dtype=float)
        if submobject_to_align is not None:
            aligner: Mobject = submobject_to_align
        elif index_of_submobject_to_align is not None:
            aligner = self[index_of_submobject_to_align]
        else:
            aligner = self
        point_to_align = aligner.get_critical_point(edge - d)
        return self.shift((target - point_to_align + buff * d) * np.asarray(coor_mask))

    @deprecated("use to_edge or to_corner", category=None)
    def align_on_border(
        self, direction: Vector3DLike, buff: float = DEFAULT_MOBJECT_TO_EDGE_BUFFER
    ) -> Self:
        """Move the mobject to an edge or a corner of the frame, `buff` in from it.

        Only the coordinates along which `direction` points change: sent to the top
        edge, the mobject moves up or down only. The frame is the configured one,
        centered on the origin, wherever the camera looks.

        Args:
            direction: The edge (UP, LEFT, …) or the corner (UR, DL, …) of the frame.
            buff: The margin between the mobject and the frame's edge, in scene units
                (default 0.5).
        """
        d = np.asarray(direction, dtype=float)
        target = np.sign(d) * (config.frame_x_radius, config.frame_y_radius, 0)
        shift = (target - self.get_critical_point(d) - buff * d) * np.abs(np.sign(d))
        return self.shift(shift)

    def to_corner(
        self, corner: Vector3DLike = DL, buff: float = DEFAULT_MOBJECT_TO_EDGE_BUFFER
    ) -> Self:
        """Move the mobject into a corner of the frame, `buff` in from both its edges.

        The frame is the configured one, centered on the origin, wherever the camera
        looks.

        Args:
            corner: The corner: UL, UR, DL (default) or DR.
            buff: The margin between the mobject and each edge of the frame, in scene
                units (default 0.5).

        Examples:
            ```python
            import manimgx as m


            class MobjectToCornerExample(m.Scene):
                def construct(self) -> None:
                    self.add(m.Text("UL").to_corner(m.UL))
                    self.add(m.Text("UR, buff=0").to_corner(m.UR, buff=0))
                    self.add(m.Circle(color=m.BLUE).to_corner(m.DL))
                    self.add(m.Square(color=m.YELLOW).to_corner(m.DR, buff=1))
            ```
        """
        return self.align_on_border(corner, buff)

    def to_edge(
        self, edge: Vector3DLike = LEFT, buff: float = DEFAULT_MOBJECT_TO_EDGE_BUFFER
    ) -> Self:
        """Move the mobject to an edge of the frame, `buff` in from it; along the edge,
        it stays where it is.

        The frame is the configured one, centered on the origin, wherever the camera
        looks.

        Args:
            edge: The edge: UP, DOWN, LEFT (default) or RIGHT.
            buff: The margin between the mobject and the edge, in scene units (default
                0.5).

        Examples:
            ```python
            import manimgx as m


            class MobjectToEdgeExample(m.Scene):
                def construct(self) -> None:
                    top = m.Text("to_edge(UP)").to_edge(m.UP)
                    left = m.Text("to_edge(LEFT)").to_edge(m.LEFT)
                    circle = m.Circle(color=m.BLUE).shift(2 * m.DOWN)
                    circle.to_edge(m.RIGHT, buff=0)
                    self.add(top, left, circle)
            ```
        """
        return self.align_on_border(edge, buff)

    def is_off_screen(self) -> bool:
        """Whether the mobject is wholly outside the frame: the configured one, centered
        on the origin.

        Returns:
            True if its bounding box lies wholly past an edge of the frame.
        """
        x, y = config.frame_x_radius, config.frame_y_radius
        return bool(
            self.get_left()[0] > x
            or self.get_right()[0] < -x
            or self.get_bottom()[1] > y
            or self.get_top()[1] < -y
        )

    def shift_onto_screen(self, buff: float = DEFAULT_MOBJECT_TO_EDGE_BUFFER) -> Self:
        """Move the mobject back into the frame where it reaches past an edge, or nearer
        to it than `buff`: to that edge, `buff` in (see
        [to_edge][manimgx.Mobject.to_edge]).

        Args:
            buff: The margin to keep from the frame's edges, in scene units (default
                0.5).
        """
        radii = (config.frame_x_radius, config.frame_y_radius)
        for vect in (UP, DOWN, LEFT, RIGHT):
            dim = int(np.argmax(np.abs(vect)))
            if np.dot(self.get_critical_point(vect), vect) > radii[dim] - buff:
                self.to_edge(vect, buff=buff)
        return self

    background_rectangle: "Mobject | None" = None
    """The rectangle last put behind the mobject (see
    [add_background_rectangle][manimgx.Mobject.add_background_rectangle]); None if
    none."""

    def add_background_rectangle(
        self,
        color: ParsableManimColor | None = None,
        opacity: float = 0.75,
        **kwargs: Unpack[BackgroundOptions],
    ) -> Self:
        """Put a rectangle behind the mobject, to set it off from whatever is behind it:
        a [BackgroundRectangle][manimgx.BackgroundRectangle] around it, added as its
        first submobject.

        The rectangle moves with the mobject; it is the mobject's
        [background_rectangle][manimgx.Mobject.background_rectangle].

        Args:
            color: The rectangle's color; None for the scene's background color.
            opacity: The rectangle's opacity, from 0 to 1 (default 0.75).
            **kwargs: [Background keywords][manimgx.mobject.BackgroundOptions]: its
                margin, corners and outline.

        Examples:
            ```python
            import manimgx as m


            class MobjectAddBackgroundRectangleExample(m.Scene):
                def construct(self) -> None:
                    label = m.Text("set off from the grid", font_size=64)
                    label.add_background_rectangle(color=m.BLACK, opacity=0.9, buff=0.2)
                    self.add(m.NumberPlane(), label)
            ```
        """
        from manimgx.mobjects.annotations import BackgroundRectangle

        self.background_rectangle = BackgroundRectangle(
            self, color=color, fill_opacity=opacity, **kwargs
        )
        return self.add_to_back(self.background_rectangle)

    def align_to(
        self,
        mobject_or_point: "Mobject | Point3DLike",
        direction: Vector3DLike = ORIGIN,
    ) -> Self:
        """Move the mobject so a side of it lines up with another's: along each axis on
        which `direction` is not 0, the side of its bounding box in that direction goes
        where the other's is.

        `align_to(other, UP)` puts its top at the height of the other's top, moving it
        up or down only; `align_to(other, UL)` lines up both tops and both left sides.
        With the default ORIGIN, nothing moves.

        Args:
            mobject_or_point: The mobject to line up with (the side of its bounding box
                `direction` names), or a point.
            direction: The side, named by a direction: UP, DL, …

        Examples:
            ```python
            import manimgx as m


            class MobjectAlignToExample(m.Scene):
                def construct(self) -> None:
                    floor = m.Line(6 * m.LEFT, 6 * m.RIGHT).shift(3 * m.DOWN)
                    shapes = m.VGroup(
                        m.Circle(color=m.BLUE),
                        m.Square(side_length=3, color=m.GREEN),
                        m.Triangle(color=m.YELLOW),
                        m.Star(color=m.RED),
                    ).arrange(buff=1)
                    self.add(floor, shapes)
                    self.play(*(s.animate.align_to(floor, m.DOWN) for s in shapes))
            ```
        """
        point = (
            mobject_or_point.get_critical_point(direction)
            if isinstance(mobject_or_point, Mobject)
            else np.asarray(mobject_or_point)
        )
        for dim in range(self.dim):
            if direction[dim] != 0:
                self.set_coord(point[dim], dim, direction)
        return self

    @deprecated("use set_x, set_y or set_z", category=None)
    def set_coord(
        self, value: float, dim: int, direction: Vector3DLike = ORIGIN
    ) -> Self:
        """Move the mobject along one axis so a coordinate of its bounding box is
        `value`: its lowest, middle or highest, as `direction`'s coordinate there is
        negative, 0 or positive.

        Args:
            value: The coordinate, in scene units.
            dim: The axis: 0 for x, 1 for y, 2 for z.
            direction: A direction such as LEFT, ORIGIN or RIGHT (default ORIGIN: the
                center).
        """
        shift = np.zeros(self.dim)
        shift[dim] = value - self.get_coord(dim, direction)
        return self.shift(shift)

    def set_x(self, x: float, direction: Vector3DLike = ORIGIN) -> Self:
        """Move the mobject left or right so its center, or an edge of its bounding box,
        is at `x`.

        Args:
            x: The x coordinate, in scene units.
            direction: LEFT to place its left edge, RIGHT its right edge; ORIGIN
                (default) its center.
        """
        return self.set_coord(x, 0, direction)

    def set_y(self, y: float, direction: Vector3DLike = ORIGIN) -> Self:
        """Move the mobject up or down so its center, or an edge of its bounding box, is
        at `y`.

        Args:
            y: The y coordinate, in scene units.
            direction: DOWN to place its bottom edge, UP its top edge; ORIGIN (default)
                its center.
        """
        return self.set_coord(y, 1, direction)

    def set_z(self, z: float, direction: Vector3DLike = ORIGIN) -> Self:
        """Move the mobject in or out so its center, or a face of its bounding box, is
        at `z`.

        Args:
            z: The z coordinate, in scene units.
            direction: IN to place its lowest z, OUT its highest; ORIGIN (default) its
                center.
        """
        return self.set_coord(z, 2, direction)

    @deprecated("use scale_to_fit_width or scale_to_fit_height", category=None)
    def rescale_to_fit(
        self, length: float, dim: int, stretch: bool = False, **kwargs: Unpack[Pivot]
    ) -> Self:
        """Scale the mobject so its extent along one axis is `length`: in proportion, or
        along that axis only.

        A mobject with no extent along the axis stays as it is.

        Args:
            length: The extent, in scene units.
            dim: The axis: 0 for x (its width), 1 for y (its height), 2 for z (its
                depth).
            stretch: Whether to stretch it along that axis only, instead of scaling it
                in proportion.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).
        """
        old = self.length_over_dim(dim)
        if old == 0:
            return self
        return (
            self.stretch(length / old, dim, **kwargs)
            if stretch
            else self.scale(length / old, **kwargs)
        )

    def scale_to_fit_width(self, width: float, **kwargs: Unpack[Pivot]) -> Self:
        """Scale the mobject in proportion to a width.

        Args:
            width: The width, in scene units.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).
        """
        return self.rescale_to_fit(width, 0, stretch=False, **kwargs)

    def stretch_to_fit_width(self, width: float, **kwargs: Unpack[Pivot]) -> Self:
        """Stretch the mobject horizontally to a width; its height stays.

        Args:
            width: The width, in scene units.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).
        """
        return self.rescale_to_fit(width, 0, stretch=True, **kwargs)

    def scale_to_fit_height(self, height: float, **kwargs: Unpack[Pivot]) -> Self:
        """Scale the mobject in proportion to a height.

        Args:
            height: The height, in scene units.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).
        """
        return self.rescale_to_fit(height, 1, stretch=False, **kwargs)

    def stretch_to_fit_height(self, height: float, **kwargs: Unpack[Pivot]) -> Self:
        """Stretch the mobject vertically to a height; its width stays.

        Args:
            height: The height, in scene units.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).
        """
        return self.rescale_to_fit(height, 1, stretch=True, **kwargs)

    @deprecated("use match_width or match_height", category=None)
    def match_dim_size(
        self, mobject: "Mobject", dim: int, **kwargs: Unpack[Pivot]
    ) -> Self:
        """Scale the mobject in proportion so its extent along one axis is another's.

        Args:
            mobject: The mobject to match.
            dim: The axis: 0 for x (width), 1 for y (height), 2 for z (depth).
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).
        """
        return self.rescale_to_fit(mobject.length_over_dim(dim), dim, **kwargs)

    def match_width(self, mobject: "Mobject", **kwargs: Unpack[Pivot]) -> Self:
        """Scale the mobject in proportion to another's width.

        Args:
            mobject: The mobject to match.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).
        """
        return self.match_dim_size(mobject, 0, **kwargs)

    def match_height(self, mobject: "Mobject", **kwargs: Unpack[Pivot]) -> Self:
        """Scale the mobject in proportion to another's height.

        Args:
            mobject: The mobject to match.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).
        """
        return self.match_dim_size(mobject, 1, **kwargs)

    @deprecated("use scale", category=None)
    def match_depth(self, mobject: "Mobject", **kwargs: Unpack[Pivot]) -> Self:
        """Scale the mobject in proportion to another's depth, its extent along z.

        Args:
            mobject: The mobject to match.
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).
        """
        return self.match_dim_size(mobject, 2, **kwargs)

    @deprecated("use match_x, match_y or match_z", category=None)
    def match_coord(
        self, mobject: "Mobject", dim: int, direction: Vector3DLike = ORIGIN
    ) -> Self:
        """Move the mobject along one axis to another's coordinate there: the same point
        of each one's bounding box, as `direction` names it, gets the same coordinate.

        Args:
            mobject: The mobject to match.
            dim: The axis: 0 for x, 1 for y, 2 for z.
            direction: Which point along the axis: the lowest, the middle (ORIGIN,
                default) or the highest, as its coordinate there is negative, 0 or
                positive.
        """
        return self.set_coord(mobject.get_coord(dim, direction), dim, direction)

    def match_x(self, mobject: "Mobject", direction: Vector3DLike = ORIGIN) -> Self:
        """Move the mobject left or right to another's x: centers, or left or right
        edges, lined up.

        Args:
            mobject: The mobject to match.
            direction: LEFT to line up the left edges, RIGHT the right ones; ORIGIN
                (default) the centers.
        """
        return self.match_coord(mobject, 0, direction)

    def match_y(self, mobject: "Mobject", direction: Vector3DLike = ORIGIN) -> Self:
        """Move the mobject up or down to another's y: centers, or top or bottom edges,
        lined up.

        Args:
            mobject: The mobject to match.
            direction: DOWN to line up the bottom edges, UP the top ones; ORIGIN
                (default) the centers.
        """
        return self.match_coord(mobject, 1, direction)

    def match_z(self, mobject: "Mobject", direction: Vector3DLike = ORIGIN) -> Self:
        """Move the mobject in or out to another's z: centers, or faces, lined up.

        Args:
            mobject: The mobject to match.
            direction: IN to line up the lowest z, OUT the highest; ORIGIN (default) the
                centers.
        """
        return self.match_coord(mobject, 2, direction)

    def replace(
        self, mobject: "Mobject", dim_to_match: int = 0, stretch: bool = False
    ) -> Self:
        """Put the mobject in another's place: scaled to its extent along one axis (or
        stretched to its width and height), and centered on it.

        The other mobject stays where it is.

        Args:
            mobject: The mobject whose place it takes.
            dim_to_match: The axis whose extent it takes, in proportion: 0 for x (the
                width), 1 for y (the height), 2 for z.
            stretch: Whether to stretch it to the other's width and height instead.
        """
        if stretch:
            self.stretch_to_fit_width(mobject.width)
            self.stretch_to_fit_height(mobject.height)
        else:
            self.rescale_to_fit(mobject.length_over_dim(dim_to_match), dim_to_match)
        return self.shift(mobject.get_center() - self.get_center())

    def put_start_and_end_on(self, start: Point3DLike, end: Point3DLike) -> Self:
        """Move, turn and scale the mobject so its first point is at `start` and its
        last at `end`; its shape stays, scaled in proportion.

        A mobject whose first and last points coincide is only moved.

        Args:
            start: Where its first point goes.
            end: Where its last point goes.
        """
        cur_start, cur_end = self.get_start_and_end()
        cur_vec = cur_end - cur_start
        if np.all(cur_vec == 0):
            return self.shift(np.asarray(start) - cur_start)
        target_vec = np.asarray(end) - np.asarray(start)
        angle, axis = turn_between(cur_vec, target_vec)
        self.scale(
            np.linalg.norm(target_vec) / np.linalg.norm(cur_vec), about_point=cur_start
        )
        self.rotate(angle, about_point=cur_start, axis=axis)
        return self.shift(np.asarray(start) - cur_start)

    def arrange(
        self,
        direction: Vector3DLike = RIGHT,
        buff: float = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
        center: bool = True,
        **kwargs: Unpack[Beside],
    ) -> Self:
        """Lay the submobjects out in a row: each one beside the one before it (see
        [next_to][manimgx.Mobject.next_to]), `buff` apart; then center the whole at the
        origin.

        Args:
            direction: The way the row goes: RIGHT (default), DOWN for a column, …
            buff: The gap between neighbours, in scene units (default 0.25).
            center: Whether to center the mobject at the origin afterwards; if not, the
                first submobject stays where it was.
            **kwargs: [Beside keywords][manimgx.mobject.Beside]: how neighbours
                line up (`aligned_edge=DOWN` puts their bottoms on one line).

        Examples:
            ```python
            import manimgx as m


            class MobjectArrangeExample(m.Scene):
                def construct(self) -> None:
                    sizes = (0.5, 1, 2)
                    squares = m.VGroup(*(m.Square(s, color=m.BLUE) for s in sizes))
                    squares.arrange(buff=0.5, aligned_edge=m.DOWN)
                    words = m.VGroup(m.Text("one"), m.Text("three"), m.Text("eleven"))
                    words.arrange(m.DOWN, aligned_edge=m.LEFT)
                    self.add(m.VGroup(squares, words).arrange(buff=1.5))
            ```
        """
        for m1, m2 in zip(self.submobjects[:-1], self.submobjects[1:], strict=True):
            m2.next_to(m1, direction, buff, **kwargs)
        return self.center() if center else self

    @deprecated("arrange_submobjects is arrange: use it", category=None)
    def arrange_submobjects(
        self,
        direction: Vector3DLike = RIGHT,
        buff: float = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
        center: bool = True,
        **kwargs: Unpack[Beside],
    ) -> Self:
        """[arrange][manimgx.Mobject.arrange], by another name."""
        return self.arrange(direction, buff, center, **kwargs)

    def arrange_in_grid(
        self,
        rows: int | None = None,
        cols: int | None = None,
        buff: float | tuple[float, float] = MED_SMALL_BUFF,
        cell_alignment: Vector3DLike = ORIGIN,
        row_alignments: str | None = None,
        col_alignments: str | None = None,
        row_heights: Iterable[float | None] | None = None,
        col_widths: Iterable[float | None] | None = None,
        flow_order: str = "rd",
    ) -> Self:
        """Lay the submobjects out in a grid of rows and columns, centered where the
        mobject was.

        Each row is as tall as its tallest mobject and each column as wide as its
        widest, unless given. Each mobject sits in its cell as `cell_alignment` says,
        but vertically as `row_alignments` says for its row and horizontally as
        `col_alignments` says for its column, where they are given. Too few rows and
        columns for the submobjects raise an exception.

        Args:
            rows: How many rows; None for as many as `row_alignments` or `row_heights`
                lists, else as many as the submobjects need. With neither `rows` nor
                `cols`, the grid is as square as it can be.
            cols: How many columns; None for as many as `col_alignments` or `col_widths`
                lists, else as many as the submobjects need.
            buff: The gap between cells, in scene units: one for both directions, or
                (horizontal, vertical) (default 0.25).
            cell_alignment: Where each mobject sits in its cell, named by a direction:
                UL for its top left corner (default ORIGIN: centered).
            row_alignments: Each row's vertical alignment, top to bottom: a letter per
                row, "u" (up), "c" (center) or "d" (down); None: as the vertical part of
                `cell_alignment` says (UL: up).
            col_alignments: Each column's horizontal alignment, left to right: a letter
                per column, "l" (left), "c" (center) or "r" (right); None: as the
                horizontal part of `cell_alignment` says (UL: left).
            row_heights: Each row's height, top to bottom, in scene units; None (for the
                grid or a row) for the height of the row's tallest mobject.
            col_widths: Each column's width, left to right, in scene units; None (for
                the grid or a column) for the width of the column's widest mobject.
            flow_order: The order the cells are filled in: two letters, the direction a
                line of cells fills and then the direction the lines follow each other,
                "r" (right), "l" (left), "u" (up) or "d" (down). The default "rd" fills
                rows left to right, from the top down; "dr" fills columns top to bottom,
                from the left.

        Examples:
            ```python
            import manimgx as m


            def cells() -> m.VGroup:
                return m.VGroup(
                    *(
                        m.Square(0.9, color=m.BLUE).add(m.Text(str(i), font_size=36))
                        for i in range(1, 11)
                    )
                )


            class MobjectArrangeInGridExample(m.Scene):
                def construct(self) -> None:
                    by_rows = cells().arrange_in_grid(rows=3, buff=0.2)
                    by_cols = cells().arrange_in_grid(rows=3, buff=0.2, flow_order="dr")
                    self.add(m.VGroup(by_rows, by_cols).arrange(buff=1.5))
            ```
        """
        mobs = list(self.submobjects)
        start_pos = self.get_center()
        heights_in = list(row_heights) if row_heights is not None else None
        widths_in = list(col_widths) if col_widths is not None else None
        cols = cols or (
            len(col_alignments)
            if col_alignments
            else len(widths_in)
            if widths_in
            else None
        )
        rows = rows or (
            len(row_alignments)
            if row_alignments
            else len(heights_in)
            if heights_in
            else None
        )
        if rows is None:
            cols = math.ceil(math.sqrt(len(mobs))) if cols is None else cols
            rows = math.ceil(len(mobs) / cols)
        elif cols is None:
            cols = math.ceil(len(mobs) / rows)
        if rows * cols < len(mobs):
            raise ValueError("Too few rows and columns to fit all submobjetcs.")
        bx, by = buff if isinstance(buff, tuple) else (buff, buff)
        cell = np.asarray(cell_alignment, dtype=float)
        rdirs = (  # a row aligns its cells vertically, a column horizontally
            [cell * UP] * rows
            if row_alignments is None
            else [{"u": UP, "c": ORIGIN, "d": DOWN}[c] for c in row_alignments]
        )
        cdirs = (
            [cell * RIGHT] * cols
            if col_alignments is None
            else [{"l": LEFT, "c": ORIGIN, "r": RIGHT}[c] for c in col_alignments]
        )
        index = {
            "dr": lambda r, c: rows - r - 1 + c * rows,
            "dl": lambda r, c: rows - r - 1 + (cols - c - 1) * rows,
            "ur": lambda r, c: r + c * rows,
            "ul": lambda r, c: r + (cols - c - 1) * rows,
            "rd": lambda r, c: (rows - r - 1) * cols + c,
            "ld": lambda r, c: (rows - r - 1) * cols + (cols - c - 1),
            "ru": lambda r, c: r * cols + c,
            "lu": lambda r, c: r * cols + (cols - c - 1),
        }[flow_order]
        rdirs.reverse()
        heights_given = list(reversed(heights_in)) if heights_in else [None] * rows
        placeholder = Mobject()
        mobs.extend([placeholder] * (rows * cols - len(mobs)))
        grid = [[mobs[index(r, c)] for c in range(cols)] for r in range(rows)]
        heights = [
            h if h is not None else max(grid[r][c].height for c in range(cols))
            for r, h in enumerate(heights_given)
        ]
        widths = [
            w if w is not None else max(grid[r][c].width for r in range(rows))
            for c, w in enumerate(widths_in or [None] * cols)
        ]
        y = 0.0
        for r in range(rows):
            x = 0.0
            for c in range(cols):
                if grid[r][c] is not placeholder:
                    lo, hi = (
                        np.array([x, y, 0.0]),
                        np.array([x + widths[c], y + heights[r], 0.0]),
                    )
                    align = rdirs[r] + cdirs[c]
                    corner = np.where(
                        align < 0, lo, np.where(align > 0, hi, (lo + hi) / 2)
                    )
                    grid[r][c].move_to(corner, align)
                x += widths[c] + bx
            y += heights[r] + by
        return self.move_to(start_pos)

    def sort(
        self,
        point_to_num_func: Callable[[Point3D], float] = lambda p: p[0],
        submob_func: Callable[["Mobject"], float] | None = None,
    ) -> Self:
        """Sort the submobjects by a number: one computed from each one's center (by
        default its x coordinate, so left to right), or from each one itself.

        Their order is the order they are drawn in (at an equal z-index), and the order
        a `lag_ratio` staggers their animation in.

        Args:
            point_to_num_func: A function of a submobject's center, giving the number to
                sort it by.
            submob_func: A function of a submobject, giving the number to sort it by, in
                place of `point_to_num_func`.
        """
        key = submob_func or (lambda m: point_to_num_func(m.get_center()))
        self.submobjects.sort(key=key)
        return self

    def shuffle(self, recursive: bool = False) -> Self:
        """Put the submobjects in a random order, drawn from Python's `random`.

        Args:
            recursive: Whether each submobject's submobjects are shuffled too, and
                theirs.
        """
        if recursive:
            for sub in self.submobjects:
                sub.shuffle(recursive=True)
        random.shuffle(self.submobjects)
        return self

    def invert(self, recursive: bool = False) -> Self:
        """Reverse the order of the submobjects.

        Args:
            recursive: Whether each submobject's submobjects are reversed too, and
                theirs.
        """
        if recursive:
            for sub in self.submobjects:
                sub.invert(recursive=True)
        self.submobjects.reverse()
        return self

    @deprecated("use arrange, with buff", category=None)
    def space_out_submobjects(
        self, factor: float = 1.5, **kwargs: Unpack[Pivot]
    ) -> Self:
        """Spread the submobjects apart, each keeping its size: the mobject is scaled by
        `factor`, then each submobject back by 1 / `factor`, about its own center.

        Args:
            factor: How much farther apart their centers go (1.5: half as far again).
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point they
                spread out from (default: the mobject's center).
        """
        self.scale(factor, **kwargs)
        for sub in self.submobjects:
            sub.scale(1.0 / factor)
        return self

    def set_z_index(self, z_index_value: float, family: bool = True) -> Self:
        """Set the mobject's place in the drawing order: a higher z-index is drawn over
        a lower one, anywhere in the scene.

        Mobjects of an equal z-index are drawn in the scene's order: the ones added
        later over the ones added earlier, and a mobject's submobjects each over those
        before it. Every mobject's z-index is 0 unless set.

        Args:
            z_index_value: The z-index.
            family: Whether its whole family gets it, or the mobject alone (which orders
                only its own points).

        Examples:
            ```python
            import manimgx as m


            class MobjectSetZIndexExample(m.Scene):
                def construct(self) -> None:
                    red = m.Square(3, color=m.RED, fill_opacity=1).shift(m.LEFT + m.UP)
                    blue = m.Square(3, color=m.BLUE, fill_opacity=1)
                    green = m.Square(3, color=m.GREEN, fill_opacity=1)
                    green.shift(m.RIGHT + m.DOWN)
                    red.set_z_index(1)  # added first, drawn on top
                    self.add(red, blue, green)
            ```
        """
        if family:
            for sub in self.submobjects:
                sub.set_z_index(z_index_value, family)
        self.z_index = z_index_value
        return self

    # ── style: written once for every kind, through Paint ──────────────────
    def _each(self, family: bool) -> list["Mobject"]:
        return self.get_family() if family else [self]

    def set_fill(
        self,
        color: ParsableManimColor | Iterable[ParsableManimColor] | None = None,
        opacity: float | Iterable[float] | None = None,
        family: bool = True,
    ) -> Self:
        """Set the mobject's fill: its color, its opacity, or both.

        Args:
            color: The color; several make a gradient across the mobject, from the first
                to the last toward its sheen direction (UL unless set). None keeps the
                present one.
            opacity: The opacity, from 0 (no fill) to 1 (opaque); several make a
                gradient of opacities. None keeps the present one.
            family: Whether its whole family is filled, or the mobject alone.

        Examples:
            ```python
            import manimgx as m


            class MobjectSetFillExample(m.Scene):
                def construct(self) -> None:
                    a, b, c = (m.Square(side_length=2.5) for _ in range(3))
                    m.VGroup(a, b, c).arrange(buff=1)
                    a.set_fill(m.BLUE, opacity=1)
                    b.set_fill(m.GREEN, opacity=0.4)
                    c.set_fill([m.YELLOW, m.RED], opacity=1)
                    self.add(a, b, c)
            ```
        """
        for mob in reversed(self._each(family)):
            mob.paint = mob.paint.updated("fill", color, opacity)
        return self

    def set_stroke(
        self,
        color: ParsableManimColor | Iterable[ParsableManimColor] | None = None,
        width: float | None = None,
        opacity: float | Iterable[float] | None = None,
        background: bool = False,
        family: bool = True,
    ) -> Self:
        """Set the mobject's stroke, its outline: its color, width and opacity, any of
        them.

        Args:
            color: The color; several make a gradient, from the first to the last toward
                the mobject's sheen direction (UL unless set). None keeps the present
                one.
            width: The width, in hundredths of a scene unit (4 unless styled; 0: no
                stroke); None keeps the present one.
            opacity: The opacity, from 0 to 1; several make a gradient of opacities.
                None keeps the present one.
            background: Whether to set the background stroke instead: an outline drawn
                behind the fill.
            family: Whether its whole family is stroked, or the mobject alone.

        Examples:
            ```python
            import manimgx as m


            class MobjectSetStrokeExample(m.Scene):
                def construct(self) -> None:
                    a = m.Circle(radius=1.5, color=m.BLUE, fill_opacity=0.3)
                    b, c = a.copy(), a.copy()
                    m.VGroup(a, b, c).arrange(buff=1)
                    a.set_stroke(m.YELLOW, width=2)
                    b.set_stroke(m.YELLOW, width=16)
                    c.set_stroke(m.YELLOW, width=16, opacity=0.3)
                    self.add(a, b, c)
            ```
        """
        channel = "background" if background else "stroke"
        for mob in reversed(self._each(family)):
            paint = mob.paint.updated(channel, color, opacity)
            if width is not None:
                paint = (
                    paint.but(background_width=width)
                    if background
                    else paint.but(stroke_width=width)
                )
            mob.paint = paint
        return self

    def set_style(
        self,
        fill_color: ParsableManimColor | Iterable[ParsableManimColor] | None = None,
        fill_opacity: float | Iterable[float] | None = None,
        stroke_color: ParsableManimColor | Iterable[ParsableManimColor] | None = None,
        stroke_width: float | None = None,
        stroke_opacity: float | Iterable[float] | None = None,
        background_stroke_color: (
            ParsableManimColor | Iterable[ParsableManimColor] | None
        ) = None,
        background_stroke_width: float | None = None,
        background_stroke_opacity: float | Iterable[float] | None = None,
        sheen_factor: float | None = None,
        sheen_direction: Vector3DLike | None = None,
        family: bool = True,
    ) -> Self:
        """Set any of the mobject's style at once: what is None stays as it is.

        See [set_fill][manimgx.Mobject.set_fill],
        [set_stroke][manimgx.Mobject.set_stroke] and
        [set_sheen][manimgx.Mobject.set_sheen]; the sheen changes only with a nonzero
        `sheen_factor`.

        Args:
            fill_color: The fill's color; several make a gradient.
            fill_opacity: The fill's opacity, from 0 to 1.
            stroke_color: The stroke's color; several make a gradient.
            stroke_width: The stroke's width, in hundredths of a scene unit.
            stroke_opacity: The stroke's opacity, from 0 to 1.
            background_stroke_color: The color of the outline drawn behind the fill.
            background_stroke_width: That outline's width, in hundredths of a scene
                unit.
            background_stroke_opacity: That outline's opacity, from 0 to 1.
            sheen_factor: How much the colors lighten toward `sheen_direction`, from -1
                to 1; None or 0 leaves the sheen as it is.
            sheen_direction: The direction they lighten toward, set with `sheen_factor`.
            family: Whether its whole family is styled, or the mobject alone.
        """
        self.set_fill(fill_color, fill_opacity, family)
        self.set_stroke(stroke_color, stroke_width, stroke_opacity, family=family)
        self.set_stroke(
            background_stroke_color,
            background_stroke_width,
            background_stroke_opacity,
            background=True,
            family=family,
        )
        if sheen_factor:
            self.set_sheen(sheen_factor, sheen_direction, family)
        return self

    def set_material(self, material: Material | None, family: bool = True) -> Self:
        """Give the mobject a surface the scene's lights reflect from, in a three-dimensional
        scene: its fill color is the surface's base color.

        Args:
            material: How the surface reflects light (see [Material][manimgx.Material]); None
                for Manim's shading.
            family: Whether its whole family takes the material, or the mobject alone.

        Returns:
            This mobject, for chaining.

        Examples:
            ```python
            import manimgx as m


            class MobjectSetMaterialExample(m.ThreeDScene):
                def construct(self) -> None:
                    self.set_camera_orientation(
                        phi=65 * m.DEGREES, theta=-50 * m.DEGREES
                    )
                    self.add(
                        m.SunLight(4 * m.LEFT + 6 * m.OUT),
                        m.AmbientLight(intensity=0.15),
                    )
                    torus = m.Torus(resolution=(48, 24)).set_color(m.TEAL)
                    self.add(torus.set_material(m.Material(roughness=0.25)))
                    self.play(
                        torus.animate.set_material(
                            m.Material(metallic=1, roughness=0.6)
                        )
                    )
            ```
        """
        for mob in self.get_family() if family else [self]:
            mob.paint = mob.paint.but(material=material)
        return self

    def set_color(
        self,
        color: ParsableManimColor | Iterable[ParsableManimColor],
        family: bool = True,
    ) -> Self:
        """Color the mobject: its fill and its stroke, which keep their opacities (an
        unfilled shape stays unfilled).

        Args:
            color: The color; several make a gradient across the mobject, from the first
                to the last toward its sheen direction (UL unless set).
            family: Whether its whole family is colored, or the mobject alone.

        Examples:
            ```python
            import manimgx as m


            class MobjectSetColorExample(m.Scene):
                def construct(self) -> None:
                    circle = m.Circle(radius=1.5)
                    square = m.Square(side_length=3, fill_opacity=0.5)
                    shapes = m.VGroup(circle, square).arrange(buff=2)
                    self.add(shapes)
                    self.play(shapes.animate.set_color(m.YELLOW))
                    self.play(square.animate.set_color([m.BLUE, m.GREEN]))
            ```
        """
        self.set_fill(color, family=family)
        return self.set_stroke(color, family=family)

    def set_opacity(self, opacity: float, family: bool = True) -> Self:
        """Set the opacity of the mobject's fill, stroke and background stroke alike —
        so an unfilled shape gets a fill of that opacity.

        Args:
            opacity: The opacity, from 0 (invisible) to 1 (opaque).
            family: Whether its whole family gets it, or the mobject alone.

        Examples:
            ```python
            import manimgx as m


            class MobjectSetOpacityExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(side_length=3, color=m.BLUE, fill_opacity=1)
                    circle = m.Circle(radius=1.5, color=m.YELLOW, fill_opacity=1)
                    square.shift(m.LEFT)
                    circle.shift(m.RIGHT)
                    self.add(square, circle)
                    self.play(circle.animate.set_opacity(0.3))
            ```
        """
        self.set_fill(opacity=opacity, family=family)
        self.set_stroke(opacity=opacity, family=family)
        return self.set_stroke(opacity=opacity, background=True, family=family)

    def fade(self, darkness: float = 0.5, family: bool = True) -> Self:
        """Make the mobject fainter: its fill's, stroke's and background stroke's
        opacities each times 1 − `darkness`.

        Args:
            darkness: How much fainter, from 0 (as it is) to 1 (invisible).
            family: Whether its whole family fades, or the mobject alone.
        """
        factor = 1.0 - darkness
        if factor == 1.0:
            return self
        for mob in self._each(family):
            p, faded = mob.paint, {}
            for name in ("fill", "stroke", "background"):  # every row: stops, points
                rows = getattr(p, name)
                if len(rows):
                    faded[name] = rows * [1.0, 1.0, 1.0, factor]
            mob.paint = p.but(**faded)
        return self

    def set_sheen(
        self, factor: float, direction: Vector3DLike | None = None, family: bool = True
    ) -> Self:
        """Give the mobject a sheen: its colors lighten across it, toward a direction.

        With a nonzero factor, its fill and its stroke each become a gradient from their
        color to that color lightened by the factor.

        Args:
            factor: How much the colors lighten, from -1 to 1: 0 for no sheen, a
                negative factor darkens.
            direction: The direction they lighten toward, copied as a value; None
                keeps the present one (UL unless styled). The caller's array is
                unchanged.
            family: Whether its whole family gets it, or the mobject alone.
        """
        if direction is not None:
            direction = frozen(np.array(direction, dtype=float, copy=True))
        for mob in self._each(family):
            mob.paint = (
                mob.paint.but(sheen_factor=factor)
                if direction is None
                else mob.paint.but(sheen_factor=factor, sheen_direction=direction)
            )
            if factor != 0:
                mob.paint = mob.paint.updated("stroke", mob.get_stroke_color(), None)
                mob.paint = mob.paint.updated("fill", mob.get_fill_color(), None)
        return self

    def set_sheen_direction(self, direction: Vector3DLike, family: bool = True) -> Self:
        """Set the direction the mobject's colors lighten toward, which its gradients
        run along too.

        Args:
            direction: The direction, copied as a value without changing the
                caller's array.
            family: Whether its whole family gets it, or the mobject alone.
        """
        direction = frozen(np.array(direction, dtype=float, copy=True))
        for mob in self._each(family):
            mob.paint = mob.paint.but(sheen_direction=direction)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_stroke_rgbas(self, background: bool = False) -> np.ndarray:
        """The mobject's own stroke colors, one row per gradient stop.

        Args:
            background: Whether to read the background stroke's instead.

        Returns:
            An (n, 4) array of red, green, blue and opacity, from 0 to 1.
        """
        return self.paint.background if background else self.paint.stroke

    @deprecated("get_fill_color() is fill_color: use it", category=None)
    def get_fill_color(self) -> ManimColor:
        """The mobject's own fill color (for a gradient, its first)."""
        return ManimColor(self.paint.fill[0, :3])

    @deprecated("get_fill_opacity() is fill_opacity: use it", category=None)
    def get_fill_opacity(self) -> float:
        """The opacity of the mobject's own fill (for a gradient, its first color's).

        Returns:
            The opacity, from 0 to 1.
        """
        return float(self.paint.fill[0, 3])

    @deprecated("get_stroke_color() is stroke_color: use it", category=None)
    def get_stroke_color(self, background: bool = False) -> ManimColor:
        """The mobject's own stroke color (for a gradient, its first).

        Args:
            background: Whether to read the background stroke's instead.
        """
        return ManimColor(self.get_stroke_rgbas(background)[0, :3])

    @deprecated("get_stroke_width() is stroke_width: use it", category=None)
    def get_stroke_width(self, background: bool = False) -> float:
        """The width of the mobject's own stroke.

        Args:
            background: Whether to read the background stroke's instead.

        Returns:
            The width, in hundredths of a scene unit.
        """
        return max(
            0.0, self.paint.background_width if background else self.paint.stroke_width
        )

    @deprecated("get_stroke_opacity() is stroke_opacity: use it", category=None)
    def get_stroke_opacity(self, background: bool = False) -> float:
        """The opacity of the mobject's own stroke (for a gradient, its first color's).

        Args:
            background: Whether to read the background stroke's instead.

        Returns:
            The opacity, from 0 to 1.
        """
        return float(self.get_stroke_rgbas(background)[0, 3])

    @deprecated("get_color() is color: use it", category=None)
    def get_color(self) -> ManimColor:
        """The mobject's own color: its fill's, or its stroke's if it has no fill (its
        fill wholly transparent).
        """
        if np.all(self.paint.fill[:, 3] == 0):
            return self.get_stroke_color()
        return self.get_fill_color()

    @property
    def color(self) -> ManimColor:
        """The mobject's own color: its fill's, or its stroke's if it has no fill. Set
        it to color the whole family (see [set_color][manimgx.Mobject.set_color])."""
        return self.get_color()

    @color.setter
    def color(self, value: ParsableManimColor) -> None:
        self.set_color(value)

    fill_color = property(get_fill_color, lambda self, c: self.set_fill(c))
    """The mobject's own fill color (for a gradient, its first). Set it to fill the
    whole family with a color (see [set_fill][manimgx.Mobject.set_fill])."""
    stroke_color = property(get_stroke_color, lambda self, c: self.set_stroke(c))
    """The mobject's own stroke color (for a gradient, its first). Set it to stroke the
    whole family with a color (see [set_stroke][manimgx.Mobject.set_stroke])."""
    fill_opacity = property(get_fill_opacity, lambda self, o: self.set_fill(opacity=o))
    """The opacity of the mobject's own fill, from 0 to 1. Set it to set the whole
    family's."""
    stroke_opacity = property(
        get_stroke_opacity, lambda self, o: self.set_stroke(opacity=o)
    )
    """The opacity of the mobject's own stroke, from 0 to 1. Set it to set the whole
    family's."""
    stroke_width = property(get_stroke_width, lambda self, w: self.set_stroke(width=w))
    """The width of the mobject's own stroke, in hundredths of a scene unit. Set it to
    set the whole family's."""

    def match_style(self, mobject: "Mobject", family: bool = True) -> Self:
        """Give the mobject another's style: its colors, opacities, stroke widths, sheen
        and the rest of its look, all but how much of it a reveal shows.

        Args:
            mobject: The mobject whose style to take.
            family: Whether the submobjects take the style of the other's too, in order:
                paired evenly when their numbers differ, and each taking the other
                mobject's own if it has none.
        """
        self.paint = mobject.paint.but(trim=self.paint.trim)
        if family:
            subs1, subs2 = self.submobjects, mobject.submobjects
            if subs1:
                subs2 = subs2 or [mobject]
                n = max(len(subs1), len(subs2))
                for i in range(n):
                    subs1[i * len(subs1) // n].match_style(subs2[i * len(subs2) // n])
        return self

    def match_color(self, mobject: "Mobject") -> Self:
        """Color the mobject and its whole family with another's
        [color][manimgx.Mobject.color].

        Args:
            mobject: The mobject whose color to take.
        """
        return self.set_color(mobject.get_color())

    def set_color_by_gradient(self, *colors: ParsableManimColor) -> Self:
        """Color the drawn members of the family along a gradient: in family order, each
        one solid, from the first color to the last.

        One color colors them all; none raises an exception.

        Args:
            *colors: The colors the gradient runs through, evenly.

        Examples:
            ```python
            import manimgx as m


            class MobjectSetColorByGradientExample(m.Scene):
                def construct(self) -> None:
                    dots = m.VGroup(*(m.Dot(radius=0.35) for _ in range(9)))
                    dots.arrange(buff=0.5)
                    dots.set_color_by_gradient(m.BLUE, m.GREEN, m.YELLOW)
                    word = m.Text("gradient", font_size=120)
                    word.set_color_by_gradient(m.RED, m.YELLOW)
                    self.add(m.VGroup(dots, word).arrange(m.DOWN, buff=1))
            ```
        """
        return self.set_submobject_colors_by_gradient(*colors)

    def set_submobject_colors_by_radial_gradient(
        self,
        center: Point3DLike | None = None,
        radius: float = 1,
        inner_color: ParsableManimColor = WHITE,
        outer_color: ParsableManimColor = "#000000",
    ) -> Self:
        """Color the drawn members of the family by how far their centers are from a
        point: `inner_color` there, blending to `outer_color` at `radius` and beyond;
        each member one solid color.

        Args:
            center: The point; None for the mobject's center.
            radius: The distance at which the color is `outer_color`, in scene units.
            inner_color: The color at the point.
            outer_color: The color at `radius` and beyond.
        """
        c = self.get_center() if center is None else np.asarray(center)
        for mob in self.family_members_with_points():
            t = min(float(np.linalg.norm(mob.get_center() - c)) / radius, 1.0)
            mob.set_color(
                interpolate_color(ManimColor(inner_color), ManimColor(outer_color), t),
                family=False,
            )
        return self

    @deprecated("sort_submobjects is sort: use it", category=None)
    def sort_submobjects(
        self,
        point_to_num_func: Callable[[Point3D], float] = lambda p: p[0],
        submob_func: "Callable[[Mobject], float] | None" = None,
    ) -> Self:
        """Sort the submobjects by a number: the same as [sort][manimgx.Mobject.sort].

        Args:
            point_to_num_func: A function of a submobject's center, giving the number to
                sort it by (default: its x coordinate).
            submob_func: A function of a submobject, giving the number to sort it by, in
                place of `point_to_num_func`.
        """
        return self.sort(point_to_num_func, submob_func)

    @deprecated("use set_color(mobject.color)", category=None)
    def to_original_color(self) -> Self:
        """Color the whole family with the mobject's own [color][manimgx.Mobject.color]."""
        return self.set_color(self.color)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def apply_to_family(self, func: Callable[["Mobject"], object]) -> None:
        """Call a function on each drawn member of the family, in family order.

        Args:
            func: A function of a mobject; what it returns is ignored.
        """
        for mob in self.family_members_with_points():
            func(mob)

    @deprecated(
        "set_submobject_colors_by_gradient is set_color_by_gradient: use it",
        category=None,
    )
    def set_submobject_colors_by_gradient(self, *colors: ParsableManimColor) -> Self:
        """Color the drawn members of the family along a gradient: the same as
        [set_color_by_gradient][manimgx.Mobject.set_color_by_gradient].

        Args:
            *colors: The colors the gradient runs through, evenly.
        """
        if len(colors) == 0:
            raise ValueError("Need at least one color")
        if len(colors) == 1:
            return self.set_color(colors[0])
        mobs = self.family_members_with_points()
        for mob, color in zip(mobs, color_gradient(colors, len(mobs)), strict=True):
            mob.set_color(color, family=False)
        return self

    def set_colors_by_radial_gradient(
        self,
        center: Point3DLike | None = None,
        radius: float = 1,
        inner_color: ParsableManimColor = WHITE,
        outer_color: ParsableManimColor = "#000000",
    ) -> Self:
        """Color the mobject by distance from a point: `inner_color` there, blending to
        `outer_color` at `radius` and beyond.

        Each drawn member of the family is one solid color, by its center's distance.

        Args:
            center: The point; None for the mobject's center.
            radius: The distance at which the color is `outer_color`, in scene units.
            inner_color: The color at the point.
            outer_color: The color at `radius` and beyond.
        """
        c = self.get_center() if center is None else np.asarray(center)
        for mob in self.family_members_with_points():
            t = min(float(np.linalg.norm(mob.get_center() - c)) / radius, 1)
            mob.set_color(
                interpolate_color(ManimColor(inner_color), ManimColor(outer_color), t),
                family=False,
            )
        return self

    def fade_to(
        self, color: ParsableManimColor, alpha: float, family: bool = True
    ) -> Self:
        """Blend the mobject's color toward another: each drawn member's own color,
        mixed `alpha` of the way to `color`.

        Args:
            color: The color to blend toward.
            alpha: How far, from 0 (as it is) to 1 (`color`).
            family: Whether its whole family blends, or the mobject alone.
        """
        if self.has_points():
            self.set_color(
                interpolate_color(self.get_color(), ManimColor(color), alpha),
                family=False,
            )
        if family:
            for sub in self.submobjects:
                sub.fade_to(color, alpha)
        return self

    # ── structural alignment + interpolation (the Transform engine) ─────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def align_data(
        self, mobject: "Mobject", skip_point_alignment: bool = False
    ) -> Self:
        """Give this mobject's family and another's the same structure, so the two can
        be blended member by member: the same number of members, level by level, and,
        unless skipped, the same number of points in each pair.

        A transform calls it on its keyframes; both mobjects change, but neither's look
        does.

        Args:
            mobject: The other mobject.
            skip_point_alignment: Whether to leave the numbers of points as they are
                ([become][manimgx.Mobject.become] does: it takes the other's points as
                they are).
        """
        self.null_point_align(mobject)
        self.align_submobjects(mobject)
        if not skip_point_alignment:
            self.align_points(mobject)
        for m1, m2 in zip(self.submobjects, mobject.submobjects, strict=True):
            m1.align_data(m2, skip_point_alignment)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def align_points(self, mobject: "Mobject") -> Self:
        """Give this mobject and another the same number of points of their own, and of
        color rows: the one with fewer is refined, its shape and look unchanged (see
        [align_points_with_larger][manimgx.Mobject.align_points_with_larger]).

        Args:
            mobject: The other mobject.
        """
        self.paint, mobject.paint = Paint.aligned(self.paint, mobject.paint)
        n1, n2 = self.get_num_points(), mobject.get_num_points()
        if n1 < n2:
            self.align_points_with_larger(mobject)
        elif n2 < n1:
            mobject.align_points_with_larger(self)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def align_submobjects(self, mobject: "Mobject") -> Self:
        """Give this mobject and another the same number of submobjects.

        The one with fewer repeats its own (see
        [add_n_more_submobjects][manimgx.Mobject.add_n_more_submobjects]); one with none
        grows, at its center, the point of each of the other's — of that one's kind and
        style, so what appears from nothing appears as itself.

        Args:
            mobject: The other mobject.
        """
        # (CE's VGroup lent a grown point the group's own, never-drawn style)
        for a, b in ((self, mobject), (mobject, self)):
            if not a.submobjects and b.submobjects:
                center = a.get_center()
                a.submobjects = [m.get_point_mobject(center) for m in b.submobjects]
            else:
                a.add_n_more_submobjects(
                    max(0, len(b.submobjects) - len(a.submobjects))
                )
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def null_point_align(self, mobject: "Mobject") -> Self:
        """If one of this mobject and another has no points of its own and the other
        has, move the other's points into a submobject of its own, so the two families
        line up (see
        [push_self_into_submobjects][manimgx.Mobject.push_self_into_submobjects]).

        Args:
            mobject: The other mobject.
        """
        for m1, m2 in ((self, mobject), (mobject, self)):
            if m1.has_no_points() and m2.has_points():
                m2.push_self_into_submobjects()
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def push_self_into_submobjects(self) -> Self:
        """Move the mobject's own points into a new submobject, added last: a copy of it
        without submobjects. The mobject keeps its submobjects, and has no points of its
        own.
        """
        clone = self.copy()
        clone.submobjects = []
        self.reset_points()
        return self.add(clone)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def add_n_more_submobjects(self, n: int) -> Self:
        """Add `n` submobjects, for a transform that splits parts: a mobject with none
        gets `n` points of itself, at its center (see
        [get_point_mobject][manimgx.Mobject.get_point_mobject]); otherwise each
        submobject is followed by invisible copies of itself, spread as evenly as can
        be.

        Args:
            n: How many to add.
        """
        if n == 0:
            return self
        cur = len(self.submobjects)
        if cur == 0:
            self.submobjects = [self.get_point_mobject() for _ in range(n)]
            return self
        target = cur + n
        # Count the integer indices in each child's interval.
        split = [
            int(((i + 1) * target + cur - 1) // cur - (i * target + cur - 1) // cur)
            for i in range(cur)
        ]
        new: list[Mobject] = []
        for sub, sf in zip(self.submobjects, split, strict=True):
            new.append(sub)
            new.extend(sub.copy().fade(1) for _ in range(1, sf))
        self.submobjects = new
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def interpolate(
        self,
        mobject1: "Mobject",
        mobject2: "Mobject",
        alpha: float,
        path_func: PathFunc = _STRAIGHT,
    ) -> Self:
        """Make the mobject a blend of two others: `mobject1` at 0, `mobject2` at 1.

        Its own points go from the first's to the second's along `path_func`, and its
        style blends from the first's to the second's; its submobjects are left as they
        are. A transform calls it on each drawn member, with its aligned keyframes (see
        [align_data][manimgx.Mobject.align_data]), which have as many points as each
        other.

        Args:
            mobject1: The mobject it is at 0.
            mobject2: The mobject it is at 1.
            alpha: How far from the first to the second, from 0 to 1.
            path_func: The path each point takes (default: straight).
        """
        g1, g2 = mobject1._geometry, mobject2._geometry
        if (
            isinstance(path_func, Path) and g1.n == g2.n
        ):  # a linear path moves shapes, not points
            self._geometry = Blend.mix(g1, g2, path_func.coefficients(alpha))
        else:
            self.points = path_func(mobject1.points, mobject2.points, alpha)
        self.paint = self.paint.mixed(mobject1.paint, mobject2.paint, alpha)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def interpolate_color(
        self, mobject1: "Mobject", mobject2: "Mobject", alpha: float
    ) -> Self:
        """Make the mobject's own style a blend of two others': `mobject1`'s at 0,
        `mobject2`'s at 1; its points stay.

        Args:
            mobject1: The mobject whose style it has at 0.
            mobject2: The mobject whose style it has at 1.
            alpha: How far from the first to the second, from 0 to 1.
        """
        self.paint = self.paint.mixed(mobject1.paint, mobject2.paint, alpha)
        return self

    def become(
        self,
        mobject: "Mobject",
        match_height: bool = False,
        match_width: bool = False,
        match_depth: bool = False,
        match_center: bool = False,
        stretch: bool = False,
    ) -> Self:
        """Make the mobject look like another, at once, while staying itself: the same
        object in the scene, with its updaters.

        The two families are first given the same structure; then each member takes its
        counterpart's points and its colors, opacities, stroke widths, sheen and
        texture (its joint and cap styles and 3D shading stay its own, unless they are
        the same). With a `match_*` flag or `stretch`, a copy of `mobject` is first
        fitted to this mobject.

        Args:
            mobject: The mobject to look like.
            match_height: Whether the copy is first scaled, in proportion, to this
                mobject's height.
            match_width: Whether it is first scaled to this mobject's width.
            match_depth: Whether it is first scaled to this mobject's depth.
            match_center: Whether it is first moved to this mobject's center.
            stretch: Whether it is first stretched to this mobject's width, height and
                depth, in place of the `match_*` scalings.

        Examples:
            ```python
            import manimgx as m


            class MobjectBecomeExample(m.Scene):
                def construct(self) -> None:
                    shape = m.Circle(radius=2, color=m.RED, fill_opacity=0.8)
                    shape.add_updater(lambda mob, dt: mob.rotate(dt))
                    self.add(shape)
                    self.wait()
                    square = m.Square(side_length=4, color=m.BLUE, fill_opacity=0.8)
                    shape.become(square)
                    self.wait(2)  # the same mobject: its updater still turns it
            ```
        """
        if stretch or match_height or match_width or match_depth or match_center:
            mobject = mobject.copy()
            for dim, match in ((1, match_height), (0, match_width), (2, match_depth)):
                if stretch or match:
                    mobject.rescale_to_fit(self.length_over_dim(dim), dim, stretch)
            if match_center:
                mobject.move_to(self.get_center())
        self.align_data(mobject, skip_point_alignment=True)
        for sm1, sm2 in zip(self.get_family(), mobject.get_family(), strict=True):
            sm1._geometry = sm2._geometry  # immutable: shared, not copied
            sm1._take_shape(sm2)
            a, b = sm1.paint, sm2.paint
            # (the rest — colors, widths, windows, dashes — `mixed` takes from b at 1); a
            # picture is what the mobject shows, so it becomes b's too (a texture is an array
            # or a camera: compared by identity)
            same = (a.joint, a.cap, a.shade_in_3d) == (b.joint, b.cap, b.shade_in_3d)
            sm1.paint = (  # a value: shared, not copied
                b
                if same and a.texture is b.texture
                else a.mixed(a, b, 1).but(texture=b.texture)
            )
        return self

    def match_points(self, mobject: "Mobject") -> Self:
        """Take another mobject's shape: its points, member by member in family order;
        this mobject's style stays its own.

        Members past the end of the shorter family stay as they are.

        Args:
            mobject: The mobject whose shape to take.
        """
        for sm1, sm2 in zip(self.get_family(), mobject.get_family(), strict=False):
            sm1._geometry = sm2._geometry
            sm1._take_shape(sm2)
        return self

    def _take_shape(self, mobject: "Mobject") -> None:
        """What goes with another mobject's points when this one takes them (a kind whose
        shape is more than points — a mesh's triangles — takes that too)."""

    @classmethod
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def add_animation_override(
        cls,
        animation_class: type["Animation"],
        override_func: Callable[..., "Animation"],
    ) -> None:
        """Make the class play another animation in place of one: playing
        `animation_class(mobject, …)` on a mobject of the class plays what
        `override_func` returns instead.

        [override_animation][manimgx.override_animation] does this for a method of the
        class. Overriding one animation twice raises an exception.

        Args:
            animation_class: The animation to play another in place of.
            override_func: A function of the mobject, then the animation's other
                arguments and keywords, that returns the animation to play.
        """
        if animation_class in cls.animation_overrides:
            raise Exception(
                f"The animation {animation_class.__name__} for {cls.__name__} is"
                " overridden by more than one method"
            )
        cls.animation_overrides = cls.animation_overrides | {
            animation_class: override_func
        }

    @classmethod
    def set_default(cls, **kwargs: object) -> None:
        """Change the defaults of the class's constructor keywords, for every mobject of
        the class made from then on; with none given, restore them.

        After `Text.set_default(font_size=100)`, a `Text` is 100 points unless it is
        made with another size. The keywords are checked when a mobject is made.

        Changing or restoring defaults discards remembered constructions. Existing
        mobjects keep their state; later construction reads the current defaults.

        Repeated calls replace this class's keyword defaults. Reset restores its
        original constructor, or normal inheritance if it had no constructor of its own.
        The defaults are applied when a mobject is made, to the constructor then in
        force: the class's own, or the next one in the made mobject's class's order (so a
        parent's later defaults reach a configured child, and a configured mixin calls the
        class after it in a subclass's order).

        Args:
            **kwargs: Keywords of the class's constructor, with their new defaults.
        """
        if kwargs:
            original = cls.__dict__.get(
                "_original__init__", cls.__dict__.get("__init__")
            )
            defaults = dict(kwargs)

            # The constructor checks the keywords when it runs: defaults applied to a
            # signature have no static type
            def init(self: Mobject, *args: object, **given: object) -> None:
                merged = defaults | given
                if original is not None:
                    original(self, *args, **merged)
                else:
                    super(cls, self).__init__(*args, **merged)

            setattr(cls, "_original__init__", original)  # noqa: B010
            setattr(cls, "__init__", init)  # noqa: B010
        elif "_original__init__" in cls.__dict__:
            original = cls.__dict__["_original__init__"]
            delattr(cls, "_original__init__")
            if original is None:
                delattr(cls, "__init__")
            else:
                setattr(cls, "__init__", original)  # noqa: B010
        caches.clear()

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_pieces(self, n_pieces: int) -> "Group":
        """Split the mobject into pieces: copies of it, each an equal part of it in
        turn, from its start to its end (a path's, by its curves).

        Only the mobject's own points are split; its submobjects are left out.

        Args:
            n_pieces: How many pieces.

        Returns:
            A new group of the pieces, in order.
        """
        template = self.copy()
        template.submobjects = []
        alphas = np.linspace(0, 1, n_pieces + 1)
        return Group(
            *(
                template.copy().pointwise_become_partial(self, a1, a2)
                for a1, a2 in it.pairwise(alphas)
            )
        )

    # ── animation hooks ───────────────────────────────────────────────────
    @property
    def animate(self) -> "Animate[Self]":
        """An animation of the mobject, built from the method calls made on it.

        `square.animate.shift(RIGHT).scale(2)` is an animation that moves the square
        right and doubles its size: pass it to [Scene.play][manimgx.Scene.play]. Each
        call is recorded — and tried at once on a copy, so a wrong call fails where it
        is written — and returns the animation, so calls chain. The calls are carried
        out on the mobject as it is when the animation begins, and the animation tweens
        it from that state to the result: in
        `Succession(square.animate.shift(RIGHT), square.animate.rotate(PI / 2))`, the
        square turns about its center where the shift left it. When the animation
        finishes, the calls are carried out on the mobject itself.

        The motion follows the calls: a turn among them (`rotate`, `flip`) turns the
        mobject rigidly about its pivot, through its whole angle (`rotate(TAU)` is a full turn); every other call moves its center
        straight; and the rest of the change (a size, a color, a new shape) blends along
        the way. Call `animate` with options before any method —
        `square.animate(run_time=2, rate_func=linear).shift(UP)` — to set the
        animation's [Transform options][manimgx.animation.transform.TransformOptions]; a
        `path_arc` or a `path_func` among them replaces the motion. Call it with a
        function — `square.animate(lambda s: s.shift(UP))` — to record that function as
        a call. Call a method of your own class so: through `animate`, a type checker
        knows only ManimGX's methods, but it checks a function against the mobject's
        class.

        Examples:
            ```python
            import manimgx as m


            class MobjectAnimateExample(m.Scene):
                def construct(self) -> None:
                    triangle = m.Triangle(color=m.BLUE, fill_opacity=0.5)
                    self.add(triangle)
                    self.play(triangle.animate.shift(3 * m.LEFT).scale(1.5))
                    self.play(triangle.animate.rotate(m.PI).set_color(m.YELLOW))
                    self.play(triangle.animate(path_arc=m.PI).move_to(3 * m.RIGHT))
            ```
        """
        from manimgx.animation.transform import Animate

        return Animate(self)

    @classmethod
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def animation_override_for(
        cls, animation_class: type["Animation"]
    ) -> Callable[..., "Animation"] | None:
        """The function that makes the animation the class plays in place of
        `animation_class` (see [override_animation][manimgx.override_animation]).

        An animation asks, when it is played.

        Returns:
            The function; None if the class plays `animation_class` itself.
        """
        return cls.animation_overrides.get(animation_class)

    def set(self, **kwargs: object) -> Self:
        """Set attributes of the mobject by name: its properties, such as `width`,
        `height` or `color` (or a text's `font_size`), or any other attribute.

        Through [animate][manimgx.Mobject.animate] it animates the change:
        `mobject.animate.set(width=4)`.

        Args:
            **kwargs: The attributes' names, with their values.
        """
        # CE's
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return self

    def __repr__(self) -> str:
        return str(self.name)


def _members(items: Iterable[Mobject | Iterable[Mobject]]) -> list[Mobject]:
    """Mobjects and iterables of mobjects, flattened one level."""
    flat: list[Mobject] = []
    for i, m in enumerate(items):
        if isinstance(m, Mobject):
            flat.append(m)
        elif isinstance(m, Iterable):
            flat.extend(m)
        else:
            raise TypeError(
                f"Only mobjects can be grouped, got {type(m).__name__} at index {i}"
            )
    return flat


class Group[T: Mobject = Mobject](Mobject):
    """Mobjects together, of any kinds: paths, text, images, point clouds, other groups.

    A group has no points of its own: its members are its submobjects, and whatever is
    done to the group — moving, scaling, styling, animating — is done to them all.
    [VGroup][manimgx.VGroup] is another name for it. A group can be indexed (`group[0]`), sliced (`group[1:3]` is a new group of those
    members) and iterated over, and `group + mobject`, `group - mobject`, `+=` and `-=`
    add and remove members.

    Its member type is inferred from what it is made with; a group meant to hold several
    kinds says so once, as `Group[Mobject](…)`, and `Group[Integer](…)` holds integers
    only, so `group[0]` is an [Integer][manimgx.Integer] to a type checker.

    Args:
        *mobjects: The members, in drawing order: mobjects, or iterables of mobjects
            (each of their mobjects a member).
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] of the group itself: as it
            has no points, they do not restyle its members (the style methods do).

    Examples:
        ```python
        import manimgx as m


        class GroupExample(m.Scene):
            def construct(self) -> None:
                shapes = m.Group(
                    m.Circle(color=m.BLUE), m.Square(color=m.GREEN), m.Triangle()
                ).arrange(buff=1)
                self.play(m.Create(shapes))
                self.play(shapes.animate.scale(1.5).set_fill(opacity=0.5))
                self.play(shapes[1].animate.shift(m.UP))
        ```
    """

    # a kind (path, points, mesh) belongs to a leaf, never to a container — so CE's
    # Group, VGroup and PGroup are this one class

    # a Group[T] only ever adds T
    submobjects: list[T]  # pyright: ignore[reportIncompatibleVariableOverride]
    """The group's members, in drawing order."""

    @overload  # `Group(a, b)`: members of any kinds
    def __init__(
        self: "Group[Mobject]",
        *mobjects: Mobject | Iterable[Mobject],
        **kwargs: Unpack[Style],
    ) -> None: ...
    @overload  # `Group[Integer](a, b)`: declared, so checked on the way in and precise on the way out
    def __init__(self, *mobjects: T | Iterable[T], **kwargs: Unpack[Style]) -> None: ...
    def __init__(
        self, *mobjects: Mobject | Iterable[Mobject], **kwargs: Unpack[Style]
    ) -> None:
        super().__init__(**kwargs)
        Mobject.add(self, *_members(mobjects))

    def add(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # a Group[T] adds T
        self, *mobjects: T | Iterable[T]
    ) -> Self:
        """Add members after the ones the group has: mobjects, or iterables of mobjects
        (each of their mobjects a member).

        A member already in the group moves to the end. Adding anything but mobjects, or
        the group to itself, raises an exception.

        Args:
            *mobjects: The members to add, in order.
        """
        return super().add(*_members(mobjects))

    def __iter__(self) -> Iterator[T]:
        return iter(self.submobjects)

    @overload
    def __getitem__(self, value: int) -> T: ...
    @overload
    def __getitem__(self, value: slice) -> "Group[T]": ...
    def __getitem__(self, value: int | slice) -> "T | Group[T]":
        if isinstance(value, slice):
            return self._group(self.submobjects[value])
        return self.submobjects[value]

    def __add__(self, mobject: T) -> "Group[T]":
        return self._group([*self.submobjects, mobject])

    def __iadd__(self, mobject: T) -> Self:
        return self.add(mobject)

    def __sub__(self, mobject: T) -> "Group[T]":
        rest = self._group(self.submobjects)
        rest.remove(mobject)
        return rest

    def __isub__(self, mobject: T) -> Self:
        return self.remove(mobject)

    def _group(self, members: Iterable[T]) -> "Group[T]":
        """A plain group of members of this group's type (`Group(…)` alone would say Mobject)."""
        return cast("Group[T]", Group(*members))


@deprecated(
    "Manim CE's way to change the animation a class plays: ManimGX doesn't document it",
    category=None,
)
def override_animate[F: Callable[..., "Animation"]](
    method: Callable[..., object],
) -> Callable[[F], F]:
    """Decorate a mobject class's method that makes the animation to play when another
    method is called through [animate][manimgx.Mobject.animate].

    Then `mobject.animate.method(*args, **kwargs)` is the animation the decorated method
    returns, called with the mobject, the same arguments, and `anim_args`: the options
    given to `animate(...)` (an empty dict if none). It is made when the call is
    written, and cannot be chained with other calls.

    Args:
        method: The method whose `animate` call plays the decorated method's animation.

    Returns:
        The decorator, which returns the decorated method as it is.

    Examples:
        ```python
        import manimgx as m
        from manimgx.animation.motion import TransformOptions


        class Tally(m.VGroup):
            def add_mark(self) -> "Tally":
                mark = m.Line(1.5 * m.UP, 1.5 * m.DOWN, stroke_width=12)
                return self.add(mark.shift(0.7 * (len(self) - 2) * m.RIGHT))

            @m.override_animate(add_mark)
            def _add_mark_animation(self, anim_args: TransformOptions) -> m.Animation:
                self.add_mark()
                return m.GrowFromCenter(self[-1], **anim_args)


        class OverrideAnimateExample(m.Scene):
            def construct(self) -> None:
                tally = Tally().add_mark()
                self.add(tally)
                for _ in range(4):
                    self.play(tally.animate(run_time=0.5).add_mark())
        ```
    """
    # CE's decorator

    def decorator(animation_method: F) -> F:
        _animate_plays[method] = animation_method
        return animation_method

    return decorator


@deprecated(
    "Manim CE's way to change the animation a class plays: ManimGX doesn't document it",
    category=None,
)
def override_animation[F: Callable[..., "Animation"]](
    animation_class: type["Animation"],
) -> Callable[[F], F]:
    """Decorate a mobject class's method that makes the animation to play in place of
    `animation_class`.

    Then playing `animation_class(mobject, *args, **kwargs)` on a mobject of the class,
    or of a subclass, plays what the decorated method returns, called with the mobject
    and the same arguments. An animation made with `use_override=False` plays itself.

    Args:
        animation_class: The animation to play another in place of.

    Returns:
        The decorator, which returns the decorated method as it is.

    Examples:
        ```python
        from typing import Unpack

        import manimgx as m
        from manimgx.animation.timeline import AnimationOptions


        class DrawnSquare(m.Square):
            @m.override_animation(m.FadeIn)
            def _fade_in(self, **kwargs: Unpack[AnimationOptions]) -> m.Animation:
                return m.Create(self, **kwargs)


        class OverrideAnimationExample(m.Scene):
            def construct(self) -> None:
                square = DrawnSquare(side_length=4, color=m.BLUE, fill_opacity=0.5)
                self.play(m.FadeIn(square, run_time=2))  # drawn, not faded in
        ```
    """
    # CE's decorator

    def decorator(func: F) -> F:
        _plays_instead[func] = animation_class
        return func

    return decorator


class ValueTracker[V: (float, complex) = float](Mobject):
    """A number that animations can change and updaters can read.

    The number is kept as the x coordinate of the tracker's one point, so whatever moves
    a mobject changes it: `tracker.animate.set_value(5)` takes it to 5 at the pace of
    the animation's rate function, and the updaters of other mobjects read it with
    [`get_value`][manimgx.ValueTracker.get_value]. A tracker is never drawn; add it to
    the scene only if it has updaters of its own. `tracker += 1` and `tracker -= 1`
    change the number at once.

    Args:
        value: The real number it starts with; use
            [ComplexValueTracker][manimgx.ComplexValueTracker] for complex numbers.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style], as any mobject takes (a
            tracker is not drawn).

    Examples:
        ```python
        import manimgx as m


        class ValueTrackerExample(m.Scene):
            def construct(self) -> None:
                x = m.ValueTracker(-4)
                line = m.NumberLine(x_range=(-6, 6, 1), length=12).add_numbers()
                pointer = m.Vector(1.5 * m.DOWN, color=m.YELLOW)
                pointer.add_updater(lambda p: p.next_to(line.n2p(x.get_value()), m.UP))
                label = m.MathTex("x", font_size=72, color=m.YELLOW)
                label.add_updater(lambda t: t.next_to(pointer, m.UP))
                self.add(line, pointer, label)
                self.play(x.animate.set_value(5), run_time=2)
                x -= 3
                self.wait(0.5)
                self.play(x.animate.increment_value(-5))
        ```
    """

    @overload
    def __init__(
        self: "ValueTracker[float]", value: float = 0, **kwargs: Unpack[Style]
    ) -> None: ...
    @overload
    def __init__(
        self: "ComplexValueTracker", value: complex = 0, **kwargs: Unpack[Style]
    ) -> None: ...
    def __init__(self, value: V = 0, **kwargs: Unpack[Style]) -> None:
        super().__init__(**kwargs)
        self.points = np.zeros((1, 3))
        self.set_value(value)

    def get_value(self) -> V:
        """The number the tracker holds."""
        return float(self.points[0, 0])  # pyright: ignore[reportReturnType]  # V is float here

    def set_value(self, value: V) -> Self:
        """Set the number the tracker holds; through
        [`animate`][manimgx.Mobject.animate], animate it there.

        Args:
            value: The new number.
        """
        points = np.array(self.points)
        points[0, 0] = value
        self.points = points
        return self

    def increment_value(self, d_value: V) -> Self:
        """Add to the number the tracker holds; through
        [`animate`][manimgx.Mobject.animate], animate the change.

        Args:
            d_value: The amount to add; a negative one subtracts.
        """
        return self.set_value(self.get_value() + d_value)

    def __iadd__(self, d_value: V) -> Self:
        return self.increment_value(d_value)

    def __isub__(self, d_value: V) -> Self:
        return self.increment_value(-d_value)


class ComplexValueTracker(ValueTracker[complex]):
    """A complex number that animations can change and updaters can read.

    The number is kept as the tracker's one point, its real part as x and its imaginary
    part as y, so an animation takes it along a straight line of the complex plane:
    `tracker.animate.set_value(3 + 2j)`. `+=` and `-=` change it at once, in complex
    arithmetic.

    Args:
        value: The number it starts with.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style], as any mobject takes (a
            tracker is not drawn).

    Examples:
        ```python
        import manimgx as m


        class ComplexValueTrackerExample(m.Scene):
            def construct(self) -> None:
                plane = m.ComplexPlane().add_coordinates()
                z = m.ComplexValueTracker(2 + 1j)
                dot = m.Dot(radius=0.15, color=m.YELLOW)
                dot.add_updater(lambda d: d.move_to(plane.n2p(z.get_value())))
                self.add(plane, dot)
                self.play(z.animate.set_value(-3 + 2j))
                self.play(z.animate.set_value(z.get_value() * 1j))
                self.play(z.animate.set_value(z.get_value() / (1 + 1j)))
        ```
    """

    def get_value(self) -> complex:
        """The complex number the tracker holds."""
        return complex(*self.points[0, :2])

    def set_value(self, value: complex) -> Self:
        """Set the complex number the tracker holds; through
        [`animate`][manimgx.Mobject.animate], animate it there, in a straight line.

        Args:
            value: The new number; a real one is taken as complex.
        """
        z = complex(value)
        points = np.array(self.points)
        points[0, :2] = (z.real, z.imag)
        self.points = points
        return self


_T_VALUES = np.linspace(0, 1, _NPPCC)
_IMAGE_TOLERANCE = 1e-3
"""How far a curve's image may stray from the true image of the curve at a third and two
thirds of each piece (scene units): a quarter of a pixel at 4K."""
_IMAGE_MAX_DEPTH = 8
"""At most 2**8 pieces per curve for an image (a map that blows up somewhere stops there)."""
_CHECKS = np.array([1 / 3, 2 / 3])[:, None]
# where an image is checked, in each piece: the middle alone passes an image that strays both
# ways about it (a wave, a curve of no handles); with its ends, two points inside pin a cubic
_AT_CHECKS = np.hstack(
    [
        (1 - _CHECKS) ** 3,
        3 * (1 - _CHECKS) ** 2 * _CHECKS,
        3 * (1 - _CHECKS) * _CHECKS**2,
        _CHECKS**3,
    ]
)


def _checked(curves: np.ndarray) -> np.ndarray:
    """Each cubic's points at a third and two thirds of its parameter: (curves, 2, dim)."""
    return np.einsum("tk,ckd->ctd", _AT_CHECKS, curves)


class VMobject(Mobject):
    """A path: cubic Bézier curves, stroked in white and unfilled unless styled.

    Each curve has four control points: it starts at an anchor, bends toward two handles
    and ends at the next anchor. The path's [points][manimgx.Mobject.points] are its
    curves' control points, four by four, and a new subpath starts wherever a curve does
    not begin where the one before it ends. The stroke follows the curves; the fill
    closes each subpath with a straight line back to its start, and where subpaths
    overlap, a point is filled unless their windings around it cancel: a subpath inside
    another that runs the other way cuts a hole.

    Circles, polygons, text and graphs are all paths. A plain `VMobject` has no points
    until it is given a shape: set its points as corners, or start it at a point and add
    lines and curves.

    Args:
        **kwargs: [Style keywords][manimgx.drawing.paint.Style].

    Examples:
        ```python
        import manimgx as m


        class VMobjectExample(m.Scene):
            def construct(self) -> None:
                path = m.VMobject(color=m.BLUE, fill_opacity=0.5, stroke_width=8)
                path.set_points_as_corners([[-3, -2, 0], [-3, 2, 0], [0, 2, 0]])
                path.add_cubic_bezier_curve_to([3, 2, 0], [3, -2, 0], [0, -2, 0])
                path.close_path()
                self.play(m.Create(path, run_time=2))
        ```
    """

    _curves = True  # a path: its box is its curves' tight box
    # CE's per-instance options, which no scene sets: constants a subclass may override.
    pre_function_handle_to_anchor_scale_factor: float = 0.01
    """Where along each handle [apply_function][manimgx.Mobject.apply_function] samples
    the function, as a fraction of the handle's length (default 0.01): the handle then
    follows how the function stretches the path at its anchor, so the curves stay
    smooth."""
    make_smooth_after_applying_functions: bool = False
    """Whether [apply_function][manimgx.Mobject.apply_function] makes the path smooth
    after mapping its curves (default False; see
    [make_smooth][manimgx.VMobject.make_smooth])."""
    tolerance_for_point_equality: float = 1e-6
    """How far apart, in scene units, two points of the path may be and still count as
    one, where a subpath ends and whether the path is closed (default 1e-6, plus 1e-5 of
    their coordinates)."""

    @property
    def n_points_per_curve(self) -> int:
        """The number of control points of each of the path's curves: 4."""
        return _NPPCC

    def set_cap_style(self, cap_style: CapStyleType) -> Self:
        """Set how the strokes of the path and its family end, at each end they show:
        an open path's ends, a reveal's moving end, each dash's ends.

        A two-dimensional scene draws the caps; a three-dimensional scene ends every
        stroke flat (see [CapStyleType][manimgx.CapStyleType]).

        Args:
            cap_style: The cap: round, butt or square.
        """
        for mob in self.get_family():
            mob.paint = mob.paint.but(cap=cap_style)
        return self

    def set_shade_in_3d(
        self, value: bool = True, z_index_as_group: bool = False
    ) -> Self:
        """Set whether a three-dimensional scene's light shades the path and its family.

        Args:
            value: Whether the light shades them.
            z_index_as_group: Whether each member of the family also takes the path as
                its z-index group, which is kept for
                Manim compatibility (the renderer draws a three-dimensional scene by
                depth).
        """
        for mob in self.get_family():
            mob.paint = mob.paint.but(shade_in_3d=value)
            if z_index_as_group:
                mob.z_index_group = self
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_sheen_direction(self) -> np.ndarray:
        """The direction the path's own colors lighten toward, which its gradients run
        along too (see [set_sheen][manimgx.Mobject.set_sheen]).

        Returns:
            A copy of the direction.
        """
        return np.array(self.paint.sheen_direction)

    gradient_frame: Mobject | None = None
    """The mobject whose bounding box the path's color gradients span; None for the
    path's own. Parts that share one show a single gradient across them all."""

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_gradient_start_and_end_points(self) -> tuple[Point3D, Point3D]:
        """Where the path's color gradients start and end: a gradient spans its
        [bounding box][manimgx.Mobject.boundary_box], along its sheen direction.

        They are the box's center, less and plus the sheen direction scaled by half the
        box's size along each axis: with the default direction, [UL][manimgx.UL], the
        box's lower right and upper left corners. The box is the
        [gradient_frame][manimgx.VMobject.gradient_frame]'s, if the path has one. The
        renderer reads them for a path whose fill or stroke has several colors.

        Returns:
            The start and the end, in scene coordinates; the origin twice if the box has
            no points.
        """
        box = (self.gradient_frame or self).boundary_box()
        if box is None:
            return np.zeros(3), np.zeros(3)
        lo, hi = box
        center, offset = (lo + hi) / 2, (hi - lo) / 2 * self.get_sheen_direction()
        return center - offset, center + offset

    # ── path building ─────────────────────────────────────────────────────
    @deprecated("use add_cubic_bezier_curve, and get_anchors", category=None)
    def set_anchors_and_handles(
        self,
        anchors1: Point3D_Array,
        handles1: Point3D_Array,
        handles2: Point3D_Array,
        anchors2: Point3D_Array,
    ) -> Self:
        """Give the path new curves, in place of its points, from their control points
        listed kind by kind.

        Curve `i` runs from `anchors1[i]` to `anchors2[i]`, bending toward `handles1[i]`
        and then `handles2[i]`: the four arrays have one row per curve.

        Args:
            anchors1: Where each curve starts, in scene coordinates.
            handles1: Each curve's first handle.
            handles2: Each curve's second handle.
            anchors2: Where each curve ends.
        """
        n = _NPPCC * len(anchors1)
        points = np.empty((n, self.dim))
        for i, array in enumerate((anchors1, handles1, handles2, anchors2)):
            points[i::_NPPCC] = array
        self.points = points
        return self

    @deprecated("clear_points is reset_points: use it", category=None)
    def clear_points(self) -> Self:
        """Remove the path's own points: the same as
        [reset_points][manimgx.Mobject.reset_points].
        """
        return self.reset_points()

    def append_points(self, new_points: Point3DLike_Array) -> Self:
        """Add control points after the path's own: taken four by four, the path's
        points are its curves.

        Args:
            new_points: The points, in scene coordinates: an (n, 3) array.
        """
        # the path grows in place (its shape is a prefix of an append-only log), so a
        # traced path grows by what it gains, not by a copy of all it has
        rows = np.asarray(new_points, dtype=float).reshape(-1, self.dim)
        g = self._geometry
        if len(g.terms) == 1 and np.array_equal(g.terms[0][0][:, :3], np.eye(3)):
            m, shape = g.terms[0]
            self._geometry = Blend(
                ((m, shape.extended(rows - m[:, 3])),), g.n + len(rows)
            )
            return self
        self.points = np.concatenate([self.points, rows])
        return self

    def start_new_path(self, point: Point3DLike) -> Self:
        """Start a new subpath at a point: the next curve added begins there, not where
        the path ends.

        A curve left unfinished (a subpath started and given no curve yet) is completed
        with copies of its first point, as a curve of no length. Started where the path
        ends, the subpath just goes on.

        Args:
            point: Where the new subpath starts, in scene coordinates.
        """
        n = self._geometry.n
        if n % _NPPCC != 0:
            last = self._geometry.point(n // _NPPCC * _NPPCC)
            self.append_points([last] * (_NPPCC - n % _NPPCC) + [point])
        else:
            self.append_points([point])
        return self

    def add_cubic_bezier_curve(
        self,
        anchor1: Point3DLike,
        handle1: Point3DLike,
        handle2: Point3DLike,
        anchor2: Point3DLike,
    ) -> Self:
        """Add a curve from `anchor1` to `anchor2`, bending toward two handles: a new
        subpath, unless `anchor1` is where the path ends.

        Its four points are appended as they are, so the path's curves must all be
        whole: after [start_new_path][manimgx.VMobject.start_new_path], use
        [add_cubic_bezier_curve_to][manimgx.VMobject.add_cubic_bezier_curve_to].

        Args:
            anchor1: Where the curve starts, in scene coordinates.
            handle1: The handle it leaves `anchor1` heading toward.
            handle2: The handle it arrives at `anchor2` heading away from.
            anchor2: Where it ends.
        """
        return self.append_points([anchor1, handle1, handle2, anchor2])

    def add_cubic_bezier_curve_to(
        self, handle1: Point3DLike, handle2: Point3DLike, anchor: Point3DLike
    ) -> Self:
        """Add a curve from where the path ends to `anchor`, bending toward two handles.

        The curve leaves the path's last point heading toward `handle1`, and arrives at
        `anchor` heading away from `handle2`. The path must have a point to start from.

        Args:
            handle1: The first handle, in scene coordinates.
            handle2: The second handle.
            anchor: Where the curve ends.

        Examples:
            ```python
            import manimgx as m


            class VMobjectAddCubicBezierCurveToExample(m.Scene):
                def construct(self) -> None:
                    start, h1, h2, end = [-4, -2, 0], [-2, 3, 0], [2, 3, 0], [4, -2, 0]
                    path = m.VMobject(color=m.YELLOW, stroke_width=8)
                    path.start_new_path(start).add_cubic_bezier_curve_to(h1, h2, end)
                    handles = m.VGroup(m.Line(start, h1), m.Line(h2, end))
                    dots = [m.Dot(p, radius=0.12) for p in (start, h1, h2, end)]
                    self.add(handles.set_color(m.GREY), *dots)
                    self.play(m.Create(path, run_time=2))
            ```
        """
        self._require_points()
        new = [handle1, handle2, anchor]
        return self.append_points(
            new if self.has_new_path_started() else [self.get_last_point(), *new]
        )

    def add_cubic_bezier_curves(self, curves: Point3DLike_Array) -> Self:
        """Add curves after the path's own, given by their control points, four per
        curve: anchor, handle, handle, anchor.

        Args:
            curves: The curves' control points, in scene coordinates: an (n, 4, 3)
                array, or the points one after another.
        """
        return self.append_points(np.asarray(curves).reshape(-1, 3))

    def add_quadratic_bezier_curve_to(
        self, handle: Point3DLike, anchor: Point3DLike
    ) -> Self:
        """Add a quadratic Bézier curve from where the path ends to `anchor`, bending
        toward one handle.

        It is added as the cubic curve of the same shape. The path must have a point to
        start from.

        Args:
            handle: The handle, in scene coordinates: the curve leaves the path's last
                point heading toward it, and arrives at `anchor` heading away from it.
            anchor: Where the curve ends.

        Examples:
            ```python
            import manimgx as m


            class VMobjectAddQuadraticBezierCurveToExample(m.Scene):
                def construct(self) -> None:
                    start, handle, end = [-4, -2, 0], [0, 3, 0], [4, -2, 0]
                    path = m.VMobject(color=m.TEAL, stroke_width=8)
                    path.start_new_path(start)
                    path.add_quadratic_bezier_curve_to(handle, end)
                    handles = m.VGroup(m.Line(start, handle), m.Line(handle, end))
                    dots = [m.Dot(p, radius=0.12) for p in (start, handle, end)]
                    self.add(handles.set_color(m.GREY), *dots)
                    self.play(m.Create(path, run_time=2))
            ```
        """
        h, a, last = np.asarray(handle), np.asarray(anchor), self.get_last_point()
        return self.add_cubic_bezier_curve_to(
            2 / 3 * h + 1 / 3 * last, 2 / 3 * h + 1 / 3 * a, a
        )

    def add_line_to(self, point: Point3DLike) -> Self:
        """Add a straight line from where the path ends to a point.

        The path must have a point to start from.

        Args:
            point: Where the line ends, in scene coordinates.

        Examples:
            ```python
            import manimgx as m


            class VMobjectAddLineToExample(m.Scene):
                def construct(self) -> None:
                    stairs = m.VMobject(color=m.BLUE, stroke_width=8)
                    stairs.start_new_path([-5, -3, 0])
                    for _ in range(5):
                        stairs.add_line_to(stairs.get_end() + 1.2 * m.UP)
                        stairs.add_line_to(stairs.get_end() + 2 * m.RIGHT)
                    self.play(m.Create(stairs, run_time=3))
            ```
        """
        last = self.get_last_point()
        p = np.asarray(point, dtype=float)
        return self.add_cubic_bezier_curve_to(
            *(interpolate(last, p, t) for t in _T_VALUES[1:])
        )

    def add_smooth_curve_to(self, *points: Point3DLike) -> Self:
        """Add a curve that continues the path smoothly: it leaves where the path ends
        in the direction the path arrives there.

        Its first handle is the path's last handle mirrored through the path's end.
        Given only the anchor, the curve arrives there as the mirror image of how it
        leaves (mirrored across the perpendicular bisector of the line between its
        ends); given a second handle first, it arrives heading away from that. With no
        curve to continue, after [start_new_path][manimgx.VMobject.start_new_path], it
        is a straight line to the anchor.

        Args:
            *points: The anchor where the curve ends, or the second handle and then the
                anchor, in scene coordinates.

        Examples:
            ```python
            import manimgx as m


            class VMobjectAddSmoothCurveToExample(m.Scene):
                def construct(self) -> None:
                    wave = m.VMobject(color=m.YELLOW, stroke_width=8)
                    wave.start_new_path([-6, 0, 0])
                    wave.add_cubic_bezier_curve_to([-6, 2, 0], [-4, 2, 0], [-4, 0, 0])
                    for x in (-2, 0, 2, 4, 6):
                        wave.add_smooth_curve_to([x, 0, 0])
                    self.play(m.Create(wave, run_time=3))
            ```
        """
        if len(points) == 1:
            handle2, new_anchor = None, np.asarray(points[0])
        elif len(points) == 2:
            handle2, new_anchor = np.asarray(points[0]), np.asarray(points[1])
        else:
            raise ValueError("Only call add_smooth_curve_to with 1 or 2 points")
        if self.has_new_path_started():
            return self.add_line_to(new_anchor)
        last_h2, last_a2 = self.points[-2:]
        tangent = last_a2 - last_h2
        handle1 = last_a2 + tangent
        if handle2 is None:  # the tangent mirrored across the ends' bisector
            chord = normalize(new_anchor - last_a2)
            handle2 = new_anchor + tangent - 2 * (tangent @ chord) * chord
        return self.append_points([last_a2, handle1, handle2, new_anchor])

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def has_new_path_started(self) -> bool:
        """Whether the path ends in a subpath just started: a point that begins no curve
        yet, where the next curve added starts.

        Returns:
            True after [start_new_path][manimgx.VMobject.start_new_path], until a curve
            is added.
        """
        return self._geometry.n % _NPPCC == 1

    @deprecated("use get_end", category=None)
    def get_last_point(self) -> Point3D:
        """The path's last point: where it ends, and where the next curve added begins.

        Returns:
            The point, in scene coordinates.
        """
        return self._geometry.point(-1)

    def is_closed(self) -> bool:
        """Whether the path ends where it starts: its first and last points coincide,
        within a millionth of a unit."""
        return self.consider_points_equals(
            self._geometry.point(0), self._geometry.point(-1)
        )

    def close_path(self) -> Self:
        """Close the path: add a straight line from where it ends back to where its last
        subpath starts, unless it ends where it starts.

        The fill closes every subpath anyway; closing one makes its stroke go all the
        way around.

        Examples:
            ```python
            import manimgx as m


            class VMobjectClosePathExample(m.Scene):
                def construct(self) -> None:
                    corners = [[-2, -1.5, 0], [0, 1.5, 0], [2, -1.5, 0]]
                    style = {"fill_opacity": 0.5, "stroke_width": 8}
                    open_path = m.VMobject(color=m.GREEN, **style)
                    closed_path = m.VMobject(color=m.YELLOW, **style)
                    open_path.set_points_as_corners(corners)
                    closed_path.set_points_as_corners(corners).close_path()
                    self.add(m.VGroup(open_path, closed_path).arrange(buff=2))
            ```
        """
        if not self.is_closed():
            self.add_line_to(self.get_subpaths()[-1][0])
        return self

    def add_subpath(self, points: Point3DLike_Array) -> Self:
        """Add curves after the path's own, by their control points, four per curve: a
        new subpath, unless they start where the path ends.

        Args:
            points: The curves' control points, in scene coordinates.
        """
        return self.append_points(points)

    def append_vectorized_mobject(self, vmobject: "VMobject") -> Self:
        """Add another path's curves after this path's own: its points, not its
        submobjects.

        A subpath just started and given no curve yet (see
        [start_new_path][manimgx.VMobject.start_new_path]) is dropped for them.

        Args:
            vmobject: The path whose points to add.
        """
        if self.has_new_path_started():  # its start begins the path that was begun
            self.points = self.points[:-1]
        return self.append_points(vmobject.points)

    def add_points_as_corners(self, points: Point3DLike_Array) -> Self:
        """Add straight lines from where the path ends through each point in turn.

        The path must have a point to start from.

        Args:
            points: The corners, in scene coordinates, in order: the path then ends at
                the last.
        """
        self._require_points()
        pts = np.asarray(points, dtype=float).reshape(-1, self.dim)
        if len(pts) == 0:
            return self
        starts = np.vstack([self.points[-1:], pts[:-1]])
        if self.has_new_path_started():
            self.points = self.points[:-1]
        new = np.empty((_NPPCC * len(starts), self.dim))
        for i, t in enumerate(_T_VALUES):
            new[i::_NPPCC] = interpolate(starts, pts, t)
        return self.append_points(new)

    def set_points_as_corners(self, points: Point3DLike_Array) -> Self:
        """Give the path new points, in place of its own: straight lines through the
        given points in turn.

        The path is open: to close it, end with its first point again.

        Args:
            points: The corners, in scene coordinates, in order.

        Examples:
            ```python
            import manimgx as m


            class VMobjectSetPointsAsCornersExample(m.Scene):
                def construct(self) -> None:
                    zigzag = m.VMobject(color=m.YELLOW, stroke_width=8)
                    zigzag.set_points_as_corners(
                        [[-3, -1.5, 0], [-1.5, 1.5, 0], [0, -1.5, 0], [1.5, 1.5, 0]]
                    )
                    triangle = m.VMobject(color=m.BLUE, fill_opacity=0.5)
                    triangle.set_points_as_corners(
                        [[-2, -1.5, 0], [0, 2, 0], [2, -1.5, 0], [-2, -1.5, 0]]
                    )
                    self.add(m.VGroup(zigzag, triangle).arrange(buff=2))
            ```
        """
        pts = np.asarray(points, dtype=float)
        if len(pts) == 2:  # a segment: the one segment, placed
            self._geometry = segment(pts[0], pts[1])
            return self
        return self.set_anchors_and_handles(
            *(interpolate(pts[:-1], pts[1:], t) for t in _T_VALUES)
        )

    def set_points_smoothly(self, points: Point3DLike_Array) -> Self:
        """Give the path new points, in place of its own: a smooth curve through the
        given points in turn.

        The curve passes through each point, bending smoothly there, with no change of
        curvature (a cubic spline); if the last point is the first, it closes smoothly.

        Args:
            points: The points it passes through, in scene coordinates, in order.

        Examples:
            ```python
            import manimgx as m


            class VMobjectSetPointsSmoothlyExample(m.Scene):
                def construct(self) -> None:
                    points = [[-5, -1, 0], [-3, 2, 0], [-1, -2, 0], [1, 2, 0]]
                    points += [[3, -1, 0], [5, 1, 0]]
                    corners = m.VMobject(color=m.GREY).set_points_as_corners(points)
                    curve = m.VMobject(color=m.YELLOW, stroke_width=8)
                    curve.set_points_smoothly(points)
                    self.add(corners, *(m.Dot(p, radius=0.12) for p in points))
                    self.play(m.Create(curve, run_time=2))
            ```
        """
        self.set_points_as_corners(points)
        return self.make_smooth()

    @deprecated("use make_smooth or make_jagged", category=None)
    def change_anchor_mode(self, mode: Literal["jagged", "smooth"]) -> Self:
        """Set anew the handles of every subpath in the family, for a smooth curve
        through its anchors or straight lines between them; the anchors stay.

        Args:
            mode: "smooth" for a smooth curve (see
                [make_smooth][manimgx.VMobject.make_smooth]); "jagged" for straight
                lines ([make_jagged][manimgx.VMobject.make_jagged]).
        """
        for sub in self.family_members_with_points():
            assert isinstance(sub, VMobject)
            subpaths = sub.get_subpaths()
            sub.clear_points()
            for subpath in subpaths:
                anchors = np.append(subpath[::_NPPCC], subpath[-1:], 0)
                if mode == "smooth":
                    h1, h2 = get_smooth_cubic_bezier_handle_points(anchors)
                else:
                    h1, h2 = (
                        interpolate(anchors[:-1], anchors[1:], 1 / 3),
                        interpolate(anchors[:-1], anchors[1:], 2 / 3),
                    )
                new = np.array(subpath)
                new[1::_NPPCC], new[2::_NPPCC] = h1, h2
                sub.append_points(new)
        return self

    def make_smooth(self) -> Self:
        """Make every subpath in the family a smooth curve through its anchors, with no
        change of curvature at any (a cubic spline); a closed subpath closes smoothly.

        The anchors stay and the handles move: a polygon becomes a rounded loop through
        its corners.

        Examples:
            ```python
            import manimgx as m


            class VMobjectMakeSmoothExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(side_length=4, color=m.BLUE, stroke_width=8)
                    self.add(square.copy().set_stroke(m.GREY, 3))
                    self.play(square.animate.make_smooth(), run_time=2)
            ```
        """
        return self.change_anchor_mode("smooth")

    def make_jagged(self) -> Self:
        """Make every subpath in the family straight lines between its anchors: a curve
        through points becomes the polygon through them.
        """
        return self.change_anchor_mode("jagged")

    def _map_points(
        self, function: Callable[[Point3D], Point3D], about: np.ndarray
    ) -> None:
        """This leaf's image under `function` (about `about`): each curve its image, to within
        `_IMAGE_TOLERANCE`. A cubic's image is the cubic through the images of its ends along
        the images of its tangents (its handles shrunk by
        `pre_function_handle_to_anchor_scale_factor`, mapped, and grown back); where that is
        not within the tolerance of the true image a third and two thirds of the way along
        it, every cubic of the leaf is cut into 2, 4, … equal pieces first: the same number
        for all, so a tween from the leaf as it was (cut to match by `align_points`) moves
        each point straight to its image."""

        def image(points: np.ndarray) -> np.ndarray:
            return np.apply_along_axis(function, 1, points - about) + about

        n = len(self.points) // _NPPCC * _NPPCC
        if n == 0:
            super()._map_points(function, about)
            return
        factor = self.pre_function_handle_to_anchor_scale_factor
        curves = self.points[:n].reshape(-1, _NPPCC, 3)
        for depth in range(_IMAGE_MAX_DEPTH + 1):
            pieces = (
                curves if depth == 0 else bezier_remap(curves, len(curves) << depth)
            )
            k = len(pieces)
            a1, h1, h2, a2 = (pieces[:, i] for i in range(_NPPCC))
            # where the path runs on, a piece's end is the next one's start: mapped once
            loose = np.ones(k, dtype=bool)
            loose[:-1] = np.any(a2[:-1] != a1[1:], axis=1)
            mapped = image(
                np.concatenate(
                    (
                        a1,
                        a1 + factor * (h1 - a1),
                        a2 + factor * (h2 - a2),
                        a2[loose],
                        _checked(pieces).reshape(-1, 3),
                    )
                )
            )
            b1 = mapped[:k]
            b2 = np.empty_like(b1)
            b2[:-1] = b1[1:]
            b2[loose] = mapped[3 * k : -2 * k]
            result = np.stack(
                (
                    b1,
                    b1 + (1.0 / factor) * (mapped[k : 2 * k] - b1),
                    b2 + (1.0 / factor) * (mapped[2 * k : 3 * k] - b2),
                    b2,
                ),
                axis=1,
            )
            with np.errstate(invalid="ignore"):  # a map that blows up: nan, refined on
                true = mapped[-2 * k :].reshape(k, 2, 3)
                stray = np.linalg.norm(true - _checked(result), axis=2).max()
            if depth == _IMAGE_MAX_DEPTH or stray <= _IMAGE_TOLERANCE:
                break
        tail = self.points[n:]  # a path just started: its point
        self.points = np.concatenate(
            (result.reshape(-1, 3), image(tail) if len(tail) else tail)
        )
        if self.make_smooth_after_applying_functions:
            self.make_smooth()

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def scale_handle_to_anchor_distances(self, factor: float) -> Self:
        """Move the handles of every path in the family toward their anchors, or away
        from them, scaling their distances by a factor.

        The curves flatten toward straight lines (below 1) or bulge (above 1); the
        anchors stay.

        Args:
            factor: The factor: 0 makes each curve a straight line between its anchors,
                1 leaves it as it is.
        """
        for sub in self.family_members_with_points():
            if len(sub.points) < _NPPCC or not isinstance(sub, VMobject):
                continue
            a1, h1, h2, a2 = sub.get_anchors_and_handles()
            sub.set_anchors_and_handles(
                a1, a1 + factor * (h1 - a1), a2 + factor * (h2 - a2), a2
            )
        return self

    # ── curves and subpaths ───────────────────────────────────────────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def consider_points_equals(self, p0: Point3DLike, p1: Point3DLike) -> bool:
        """Whether two points count as one: equal within
        [tolerance_for_point_equality][manimgx.VMobject.tolerance_for_point_equality].

        Args:
            p0: A point.
            p1: Another point.
        """
        return bool(np.allclose(p0, p1, atol=self.tolerance_for_point_equality))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_cubic_bezier_tuples_from_points(self, points: Point3D_Array) -> np.ndarray:
        """Split control points into curves, four points each; an unfinished last curve
        is left out.

        Args:
            points: The control points: an (n, 3) array.

        Returns:
            The curves, as an array of shape (curves, 4, 3).
        """
        n = len(points) - len(points) % _NPPCC
        return np.asarray(points[:n]).reshape(
            -1, _NPPCC, points.shape[1] if len(points) else 3
        )

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_cubic_bezier_tuples(self) -> np.ndarray:
        """The path's curves, by their control points.

        Returns:
            An array of shape (curves, 4, 3), each curve's anchor, two handles and
            anchor.
        """
        return self.get_cubic_bezier_tuples_from_points(self.points)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_subpaths_from_points(self, points: Point3D_Array) -> list[Point3D_Array]:
        """Split control points into subpaths: a subpath starts wherever a curve does
        not begin where the one before it ends.

        Args:
            points: The control points, four per curve: an (n, 3) array.

        Returns:
            The subpaths, each an array of its control points.
        """
        return [
            points[a:b]
            for a, b, _ in subpath_ranges(points, self.tolerance_for_point_equality)
        ]

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def consider_points_equals_2d(self, p0: Point3DLike, p1: Point3DLike) -> bool:
        """Whether two points count as one seen along the z axis: their x and y
        coordinates equal within
        [tolerance_for_point_equality][manimgx.VMobject.tolerance_for_point_equality].

        Args:
            p0: A point.
            p1: Another point.
        """
        return bool(
            np.allclose(
                np.asarray(p0)[:2],
                np.asarray(p1)[:2],
                atol=self.tolerance_for_point_equality,
            )
        )

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def gen_cubic_bezier_tuples_from_points(
        self, points: Point3D_Array
    ) -> tuple[Point3D_Array, ...]:
        """Split control points into curves, four points each; an unfinished last curve
        is left out.

        Args:
            points: The control points: an (n, 3) array.

        Returns:
            The curves, each a (4, 3) array.
        """
        n = len(points) - len(points) % _NPPCC
        return tuple(points[i : i + _NPPCC] for i in range(0, n, _NPPCC))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def gen_subpaths_from_points_2d(
        self, points: Point3D_Array
    ) -> Iterator[Point3D_Array]:
        """Split control points into subpaths, comparing points by their x and y only: a
        subpath starts wherever a curve does not begin where the one before it ends.

        Args:
            points: The control points, four per curve: an (n, 3) array.

        Returns:
            The subpaths, one after another, each an array of its control points.
        """
        return (
            points[a:b]
            for a, b, _ in subpath_ranges(
                points, self.tolerance_for_point_equality, dims=2
            )
        )

    def get_subpaths(self) -> list[Point3D_Array]:
        """The path's subpaths: a subpath starts wherever a curve does not begin where
        the one before it ends.

        Returns:
            The subpaths, each an array of its control points, four per curve.
        """
        return self.get_subpaths_from_points(self.points)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_nth_curve_points(self, n: int) -> Point3D_Array:
        """The control points of one of the path's curves.

        Args:
            n: Which curve, counting from 0.

        Returns:
            Its anchor, two handles and anchor, as a (4, 3) array.
        """
        return self.points[_NPPCC * n : _NPPCC * (n + 1)]

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_nth_curve_function(self, n: int) -> Callable[[float], Point3D]:
        """One of the path's curves, as a function from 0, its start, to 1, its end.

        Args:
            n: Which curve, counting from 0.

        Returns:
            A function of the curve's parameter, from 0 to 1, giving its point there.
        """
        return bezier(self.get_nth_curve_points(n))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_nth_curve_length_pieces(
        self, n: int, sample_points: int | None = None
    ) -> np.ndarray:
        """The lengths of the straight pieces between points along one of the path's
        curves, taken at evenly spaced values of its parameter.

        Args:
            n: Which curve, counting from 0.
            sample_points: How many points to take, its ends included; None for 10,
                the path's own measure (the one its reveals and proportions go by).

        Returns:
            The pieces' lengths, in scene units, one fewer than the points.
        """
        if sample_points in (None, 10):  # the path's own, measured once
            return self._geometry.piece_lengths()[n].copy()
        curve = self.get_nth_curve_function(n)
        pts = np.array([curve(a) for a in np.linspace(0, 1, sample_points)])
        return np.linalg.norm(np.diff(pts, axis=0), axis=1)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_nth_curve_length(self, n: int, sample_points: int | None = None) -> float:
        """The length of one of the path's curves, measured along straight pieces
        between points on it.

        Args:
            n: Which curve, counting from 0.
            sample_points: How many points to measure through, its ends included (evenly
                spaced in its parameter); None for 10.

        Returns:
            The length, in scene units.
        """
        return float(np.sum(self.get_nth_curve_length_pieces(n, sample_points)))

    def get_num_curves(self) -> int:
        """How many curves the path has: its points, four per curve.

        Returns:
            The number of curves.
        """
        return self._geometry.n // _NPPCC

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_curve_functions_with_lengths(
        self, sample_points: int | None = None
    ) -> Iterator[tuple[Callable[[float], Point3D], float]]:
        """Each of the path's curves, as a function, with its length.

        Args:
            sample_points: How many points each curve's length is measured through (see
                [get_nth_curve_length][manimgx.VMobject.get_nth_curve_length]); None for
                10.

        Yields:
            Each curve's function of its parameter, from 0 to 1, and its length in scene
                units.
        """
        for n in range(self.get_num_curves()):
            yield (
                self.get_nth_curve_function(n),
                self.get_nth_curve_length(n, sample_points),
            )

    def point_from_proportion(self, alpha: float) -> Point3D:
        """The point a proportion of the way along the path, by length: 0 is its start,
        1 its end.

        The length is the path's own measure, the one a reveal draws by (nine straight
        pieces per curve), so it is where a [Create][manimgx.Create] at that proportion
        has drawn to, and a [MoveAlongPath][manimgx.MoveAlongPath] moves at a steady
        speed. Raises an exception if `alpha` is outside [0, 1] or the path has no
        points.

        Args:
            alpha: The proportion, from 0 to 1.

        Returns:
            The point, in scene coordinates.

        Examples:
            ```python
            import manimgx as m


            class VMobjectPointFromProportionExample(m.Scene):
                def construct(self) -> None:
                    points = [[-5, -2, 0], [-2, 2, 0], [1, -1, 0], [5, 2, 0]]
                    curve = m.VMobject(color=m.BLUE, stroke_width=6)
                    curve.set_points_smoothly(points)
                    self.add(curve)
                    for alpha in (0, 0.25, 0.5, 0.75, 1):
                        point = curve.point_from_proportion(alpha)
                        dot = m.Dot(point, radius=0.15, color=m.YELLOW)
                        label = m.Text(str(alpha), font_size=32).next_to(dot, m.DOWN)
                        self.add(dot, label)
            ```
        """
        if alpha < 0 or alpha > 1:
            raise ValueError(f"Alpha {alpha} not between 0 and 1.")
        self._require_points()
        curves = self.get_num_curves()
        if curves == 0:  # a point, or a subpath just started
            return self.points[-1]
        at = self._geometry.parameter_at(alpha)
        n = min(int(at), curves - 1)
        return self.get_nth_curve_function(n)(at - n)

    def get_arc_length(self, sample_points_per_curve: int | None = None) -> float:
        """The path's length: the sum of its curves' lengths, each measured along
        straight pieces between points on it.

        Args:
            sample_points_per_curve: How many points each curve is measured through, its
                ends included; None for 10, the path's own measure.

        Returns:
            The length, in scene units.
        """
        if sample_points_per_curve in (None, 10):
            return float(self._geometry.curve_lengths().sum())
        return sum(
            length
            for _, length in self.get_curve_functions_with_lengths(
                sample_points_per_curve
            )
        )

    @deprecated("use add_cubic_bezier_curve, and get_anchors", category=None)
    def get_anchors_and_handles(self) -> list[Point3D_Array]:
        """The path's control points, kind by kind: its curves' first anchors, first
        handles, second handles and second anchors.

        Returns:
            Four arrays, one row per curve, in the order
            [set_anchors_and_handles][manimgx.VMobject.set_anchors_and_handles] takes
            them.
        """
        return [self.points[i::_NPPCC] for i in range(_NPPCC)]

    @deprecated("use add_cubic_bezier_curve, and get_anchors", category=None)
    def get_start_anchors(self) -> Point3D_Array:
        """Where each of the path's curves starts.

        Returns:
            An array of one point per curve, in scene coordinates.
        """
        return self.points[::_NPPCC]

    @deprecated("use add_cubic_bezier_curve, and get_anchors", category=None)
    def get_end_anchors(self) -> Point3D_Array:
        """Where each of the path's curves ends.

        Returns:
            An array of one point per curve, in scene coordinates.
        """
        return self.points[_NPPCC - 1 :: _NPPCC]

    def get_anchors(self) -> Point3D_Array:
        """The path's anchors, curve by curve: each curve's start, then its end, so an
        anchor two curves share is listed twice.

        Returns:
            An array of points, in scene coordinates; for a path of one point, that
            point.
        """
        if self.points.shape[0] == 1:
            return self.points
        s, e = self.get_start_anchors(), self.get_end_anchors()
        out = np.empty((len(s) + len(e), self.dim))
        out[0::2], out[1::2] = s, e
        return out

    # ── the Path kind's alignment and partial rules ────────────────────────
    def align_points(self, mobject: Mobject) -> Self:
        self.paint, mobject.paint = Paint.aligned(self.paint, mobject.paint)
        if (
            not isinstance(mobject, VMobject)
            or self.get_num_points() == mobject.get_num_points()
        ):
            return self
        vmobject = mobject
        for mob in (self, vmobject):
            if mob.has_no_points():
                mob.start_new_path(mob.get_center())
            if mob.has_new_path_started():
                mob.add_line_to(mob.get_last_point())
        subpaths1, subpaths2 = self.get_subpaths(), vmobject.get_subpaths()
        new1, new2 = [], []

        def nth(paths: list[Point3D_Array], n: int) -> Point3D_Array:
            """Subpath n without its trailing null curves (a curve all at the point before it)
            — but its first — or its last point, held, when it has no subpath n."""
            if n >= len(paths):
                return np.tile(paths[-1][-1] if paths else np.zeros(3), (_NPPCC, 1))
            path = paths[n]
            k = len(path) // _NPPCC
            if k > 1:
                curves = path[: k * _NPPCC].reshape(k, _NPPCC, -1)[1:]
                before = path[_NPPCC - 1 : (k - 1) * _NPPCC : _NPPCC][:, None]
                null = np.all(  # np.allclose, curve by curve
                    np.abs(curves - before)
                    <= self.tolerance_for_point_equality + 1e-5 * np.abs(before),
                    axis=(1, 2),
                )
                kept = len(null) - int(np.argmin(null[::-1])) if not null.all() else 0
                path = path[: (kept + 1) * _NPPCC]
            return path

        for n in range(max(len(subpaths1), len(subpaths2))):
            sp1, sp2 = nth(subpaths1, n), nth(subpaths2, n)
            new1.append(
                self.insert_n_curves_to_point_list(
                    max(0, (len(sp2) - len(sp1)) // _NPPCC), sp1
                )
            )
            new2.append(
                self.insert_n_curves_to_point_list(
                    max(0, (len(sp1) - len(sp2)) // _NPPCC), sp2
                )
            )
        self.set_points(np.concatenate(new1))
        vmobject.set_points(np.concatenate(new2))
        return self

    def align_points_with_larger(self, larger: Mobject) -> Self:
        return self.align_points(larger)

    def insert_n_curves(self, n: int) -> Self:
        """Divide the path's curves into more curves, its shape unchanged.

        Each curve is split into equal stretches of its parameter, the new curves
        spread among the curves as evenly as can be (curve i of m gets the new curves j
        of n with j·m // n = i): the way a transform gives two paths as many curves as
        each other.

        Args:
            n: How many curves to add.
        """
        new_path_point = self.get_last_point() if self.has_new_path_started() else None
        self.set_points(self.insert_n_curves_to_point_list(n, self.points))
        if new_path_point is not None:
            self.append_points([new_path_point])
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def insert_n_curves_to_point_list(
        self, n: int, points: Point3D_Array
    ) -> Point3D_Array:
        """Divide the curves of a list of control points into more curves, their shape
        unchanged (see [insert_n_curves][manimgx.VMobject.insert_n_curves]).

        Args:
            n: How many curves to add.
            points: The control points, four per curve; a single point gives `n` curves
                of no length at it.

        Returns:
            The new control points.
        """
        if len(points) == 1:
            return np.repeat(points, _NPPCC * n, 0)
        tuples = self.get_cubic_bezier_tuples_from_points(points)
        return bezier_remap(tuples, len(tuples) + n).reshape(-1, 3)

    def reveal_pace(self) -> tuple[np.ndarray, np.ndarray]:
        return self._geometry.pace()

    def get_point_mobject(self, center: Point3DLike | None = None) -> "VectorizedPoint":
        point = VectorizedPoint(self.get_center() if center is None else center)
        point.match_style(self)
        return point

    def pointwise_become_partial(self, mobject: Mobject, a: float, b: float) -> Self:
        vmobject = mobject
        if a <= 0 and b >= 1:
            return self.set_points(vmobject.points)
        num_curves = len(vmobject.points) // _NPPCC
        if num_curves == 0:
            return self
        lo, lo_res = integer_interpolate(0, num_curves, a)
        hi, hi_res = integer_interpolate(0, num_curves, b)
        src = vmobject.points.copy() if self is vmobject else vmobject.points
        n = _NPPCC
        if lo == hi:
            self.points = partial_bezier_points(
                src[n * lo : n * (lo + 1)], lo_res, hi_res
            )
        else:
            pts = np.empty((n * (hi - lo + 1), self.dim))
            pts[:n] = partial_bezier_points(src[n * lo : n * (lo + 1)], lo_res, 1)
            pts[n:-n] = src[n * (lo + 1) : n * hi]
            pts[-n:] = partial_bezier_points(src[n * hi : n * (hi + 1)], 0, hi_res)
            self.points = pts
        return self

    def get_subcurve(self, a: float, b: float) -> Self:
        """A copy of the path cut down to its part from proportion `a` of the way along
        it to proportion `b`.

        The proportions go by the path's curves, each an equal share whatever its
        length, and along each curve by its parameter
        ([point_from_proportion][manimgx.VMobject.point_from_proportion] goes by
        length). The copy's submobjects are copied whole.

        Args:
            a: Where the part starts, from 0 to 1.
            b: Where it ends, from `a` to 1.

        Returns:
            A new path.

        Examples:
            ```python
            import manimgx as m


            class VMobjectGetSubcurveExample(m.Scene):
                def construct(self) -> None:
                    circle = m.Circle(radius=2.5, color=m.GREY)
                    half = circle.get_subcurve(0.25, 0.75).set_stroke(m.YELLOW, 12)
                    self.add(circle)
                    self.play(m.Create(half))
            ```
        """
        return self.copy().pointwise_become_partial(self, a, b)

    def get_direction(self) -> str:
        """Which way the path turns: "CW" (clockwise) or "CCW" (counterclockwise), by
        the sign of the area its curves' start anchors enclose.

        Returns:
            "CW" or "CCW".
        """
        return shoelace_direction(self.get_start_anchors())

    def reverse_direction(self) -> Self:
        """Reverse the order of the path's own points, so it runs the other way: from
        its end to its start.

        Its submobjects stay as they are. A drawing animation then draws it the other
        way, and a subpath inside another cuts
        a hole in the fill only if the two run opposite ways.

        Examples:
            ```python
            import manimgx as m


            class VMobjectReverseDirectionExample(m.Scene):
                def construct(self) -> None:
                    outer, inner = m.Square(side_length=4), m.Square(side_length=2)
                    same = m.VMobject(color=m.BLUE, fill_opacity=0.8)
                    same.append_vectorized_mobject(outer)
                    same.append_vectorized_mobject(inner)
                    opposite = m.VMobject(color=m.YELLOW, fill_opacity=0.8)
                    opposite.append_vectorized_mobject(outer)
                    opposite.append_vectorized_mobject(inner.reverse_direction())
                    self.add(m.VGroup(same, opposite).arrange(buff=2))
            ```
        """
        self.points = self.points[::-1].copy()
        return self

    def force_direction(self, target_direction: Literal["CW", "CCW"]) -> Self:
        """Make the path run clockwise or counterclockwise: reverse it if it runs the
        other way (see [get_direction][manimgx.VMobject.get_direction]).

        Args:
            target_direction: "CW" for clockwise, "CCW" for counterclockwise.
        """
        if self.get_direction() != target_direction:
            self.reverse_direction()
        return self

    @overload
    def get_style(self, simple: Literal[True]) -> SimpleStyle: ...
    @overload
    def get_style(self, simple: Literal[False] = False) -> StyleSnapshot: ...
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_style(self, simple: bool = False) -> SimpleStyle | StyleSnapshot:
        """The path's own style, as keywords: `set_style(**style)` gives it back.

        Args:
            simple: Whether to give only the first color and opacity of the fill and
                the stroke, and the stroke's width, in place of every color (each stop
                of a gradient) of the fill, stroke and background stroke, their widths
                and the sheen.

        Returns:
            A dictionary of [set_style][manimgx.Mobject.set_style]'s keywords.
        """
        if simple:
            return SimpleStyle(
                fill_color=self.get_fill_color(),
                fill_opacity=self.get_fill_opacity(),
                stroke_color=self.get_stroke_color(),
                stroke_opacity=self.get_stroke_opacity(),
                stroke_width=self.get_stroke_width(),
            )
        p = self.paint
        return StyleSnapshot(
            fill_color=[ManimColor(c[:3]) for c in p.fill],
            fill_opacity=[float(c[3]) for c in p.fill],
            stroke_color=[ManimColor(c[:3]) for c in p.stroke],
            stroke_opacity=[float(c[3]) for c in p.stroke],
            stroke_width=self.get_stroke_width(),
            background_stroke_color=[ManimColor(c[:3]) for c in p.background],
            background_stroke_opacity=[float(c[3]) for c in p.background],
            background_stroke_width=self.get_stroke_width(background=True),
            sheen_factor=self.paint.sheen_factor,
            sheen_direction=self.get_sheen_direction(),
        )

    @staticmethod
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_mobject_type_class() -> type[Mobject]:
        """The class of the paths' kind: `VMobject`, whatever a path's own class.

        Returns:
            [VMobject][manimgx.VMobject].
        """
        return VMobject

    def proportion_from_point(
        self, point: Point3DLike, tolerance: float = 1e-6
    ) -> float:
        """How far along the path a point on it lies, by length: the inverse of
        [point_from_proportion][manimgx.VMobject.point_from_proportion].

        The first curve the point lies on counts. Raises an exception if the point is
        not on the path.

        Args:
            point: The point, in scene coordinates.
            tolerance: How near the path the point must be: within 100 times this, in
                scene units, along each axis.

        Returns:
            The proportion, from 0 (the path's start) to 1 (its end).
        """
        p = np.asarray(point, dtype=float)
        for n in range(self.get_num_curves()):
            curve = self.get_nth_curve_points(n)
            dim = int(
                np.argmax(np.ptp(curve, axis=0))
            )  # solve along the curve's widest coordinate, then check all
            c = [
                curve[0],
                3 * (curve[1] - curve[0]),
                3 * (curve[2] - 2 * curve[1] + curve[0]),
                curve[3] - 3 * curve[2] + 3 * curve[1] - curve[0],
            ]
            coeffs = np.array([ci[dim] for ci in c])
            coeffs[0] -= p[dim]
            roots = [
                r.real
                for r in (
                    np.polynomial.Polynomial(coeffs).roots()
                    if coeffs[1:].any()
                    else [0.0]  # constant along its widest coordinate: a point
                )
                # candidates, each checked below: a double root (a stationary end) comes
                # back as a complex pair with parts near √ε
                if abs(r.imag) < 1e-4 and -1e-4 <= r.real <= 1 + 1e-4
            ]
            hits = [
                t
                for t in roots
                if np.allclose(
                    bezier(curve)(min(max(t, 0), 1)), p, atol=tolerance * 100
                )
            ]
            if hits:  # by the path's own measure: the inverse of point_from_proportion
                return self._geometry.fraction_at(n + min(max(max(hits), 0.0), 1.0))
        raise ValueError(f"Point {point} does not lie on this curve.")


VGroup = Group  # a group is a group: kinds belong to leaves
"""Another name for [Group][manimgx.Group], which holds mobjects of any kind."""


class VectorizedPoint(VMobject):
    """A path of one point: unseen, a place to put things by, or to grow them from.

    It is black, with no stroke and no fill. Its width and height are numbers of its
    own, not measured from its point.

    Args:
        location: Where the point is, in scene coordinates.
        artificial_width: The width it reports, in scene units.
        artificial_height: The height it reports, in scene units.

    Examples:
        ```python
        import manimgx as m


        class VectorizedPointExample(m.Scene):
            def construct(self) -> None:
                point = m.VectorizedPoint(4 * m.LEFT)
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                self.play(m.ReplacementTransform(point, square.shift(2 * m.RIGHT)))
        ```
    """

    defaults: ClassVar[Style] = {"color": BLACK, "fill_opacity": 0.0, "stroke_width": 0}

    def __init__(
        self,
        location: Point3DLike = ORIGIN,
        artificial_width: float = 0.01,
        artificial_height: float = 0.01,
        **kwargs: Unpack[Style],
    ) -> None:
        self.artificial_width = artificial_width
        self.artificial_height = artificial_height
        super().__init__(**kwargs)
        self.set_points(np.array([location], dtype=float))

    @property
    def width(self) -> float:
        """The point's width, in scene units: its `artificial_width`, not measured.
        Setting it changes that number and nothing else."""
        return self.artificial_width

    @width.setter
    def width(self, value: float) -> None:
        self.artificial_width = value

    @property
    def height(self) -> float:
        """The point's height, in scene units: its `artificial_height`, not measured.
        Setting it changes that number and nothing else."""
        return self.artificial_height

    @height.setter
    def height(self, value: float) -> None:
        self.artificial_height = value

    @deprecated("use get_center", category=None)
    def get_location(self) -> Point3D:
        """Where the point is.

        Returns:
            A copy of the point, in scene coordinates.
        """
        return np.array(self.points[0])

    @deprecated("use move_to", category=None)
    def set_location(self, new_loc: Point3DLike) -> Self:
        """Move the point.

        Args:
            new_loc: Where it goes, in scene coordinates.
        """
        return self.set_points(np.array([new_loc], dtype=float))


class VDict[T: Mobject = Mobject](Mobject):
    """A group whose members have keys, as a dictionary has: `vdict[key]` is a member.

    Members of any kind are added, replaced (`vdict[key] = mobject`) and removed by key;
    like any group, it draws, moves and styles them together, in the order they were
    added. With `show_keys`, each member is labeled with its key.

    Args:
        mapping_or_iterable: The first members: a dictionary of keys and mobjects, or
            (key, mobject) pairs.
        show_keys: Whether each member, added now or later, is labeled with its key: a
            [Tex][manimgx.Tex] of `str(key)` at its left, added to the member itself,
            so the label moves, animates and leaves with it, and counts in its size.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] of the group itself: as it
            has no points, they do not restyle its members (the style methods do).

    Examples:
        ```python
        import manimgx as m


        class VDictExample(m.Scene):
            def construct(self) -> None:
                shapes = m.VDict(
                    {
                        "circle": m.Circle(radius=0.9, color=m.RED),
                        "square": m.Square(side_length=1.8, color=m.GREEN),
                    },
                    show_keys=True,
                )
                shapes["triangle"] = m.Triangle(color=m.BLUE)
                self.add(shapes.arrange(buff=1))
                self.play(shapes["square"].animate.set_color(m.YELLOW))
        ```
    """

    @overload  # `VDict({...})`: members of any kinds
    def __init__[Key: Hashable](
        self: "VDict[Mobject]",
        mapping_or_iterable: (
            Mapping[Key, Mobject] | Iterable[tuple[Key, Mobject]]
        ) = {},
        show_keys: bool = False,
        **kwargs: Unpack[Style],
    ) -> None: ...
    @overload  # `VDict[Circle]({...})`: declared
    def __init__[Key: Hashable](
        self,
        mapping_or_iterable: Mapping[Key, T] | Iterable[tuple[Key, T]] = {},
        show_keys: bool = False,
        **kwargs: Unpack[Style],
    ) -> None: ...
    def __init__[Key: Hashable](
        self,
        mapping_or_iterable: (
            Mapping[Key, Mobject] | Iterable[tuple[Key, Mobject]]
        ) = {},
        show_keys: bool = False,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(**kwargs)
        self.show_keys = show_keys
        self.submob_dict: dict[Hashable, T] = {}
        """The members, by key."""
        self.add(
            mapping_or_iterable  # ty: ignore[invalid-argument-type]  # a VDict[T] is given T
        )

    def add[Key: Hashable](  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: by key
        self, mapping_or_iterable: Mapping[Key, T] | Iterable[tuple[Key, T]]
    ) -> Self:
        """Add members by key, after the group's.

        Each is labeled with its key if the group shows its keys. A key the group has already
        is given the new mobject, but the old one stays in the group: to replace a
        member, set it (`vdict[key] = mobject`).

        Args:
            mapping_or_iterable: A dictionary of keys and mobjects, or (key, mobject)
                pairs.
        """
        for key, value in dict(mapping_or_iterable).items():
            self.add_key_value_pair(key, value)
        return self

    def remove(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: by key
        self, key: Hashable
    ) -> Self:
        """Remove the member with a key from the group.

        Raises an exception if the group has no such key.

        Args:
            key: The member's key.
        """
        super().remove(self.submob_dict.pop(key))
        return self

    def __getitem__(self, key: Hashable) -> T:  # ty: ignore[invalid-method-override]  # CE's: by key
        return self.submob_dict[key]

    def __setitem__(self, key: Hashable, value: T) -> None:
        if key in self.submob_dict:
            self.remove(key)
        self.add([(key, value)])

    @deprecated("use add({key: value})", category=None)
    def add_key_value_pair(self, key: Hashable, value: T) -> Self:
        """Add a member with a key, after the group's.

        The constructor, [add][manimgx.VDict.add] and `vdict[key] = mobject` all add
        members this way. If the group shows its keys (`show_keys`), the member is
        labeled first: a [Tex][manimgx.Tex] of `str(key)`, at its left, is added to the
        member itself, so the label moves, animates and leaves with it.

        Args:
            key: Its key.
            value: The mobject.
        """
        if self.show_keys:
            from manimgx.mobjects.text import Tex

            value.add(Tex(str(key)).next_to(value, LEFT))
        self.submob_dict[key] = value
        Mobject.add(self, value)
        return self

    @deprecated("use the group's submobjects", category=None)
    def get_all_submobjects(self) -> list[T]:
        """The members, in the order of their keys.

        Returns:
            A list of the mobjects.
        """
        return list(self.submob_dict.values())


class PMobject(Mobject):
    """A point cloud: a mobject drawn as points, each a dot of its own color.

    Points are added with [add_points][manimgx.PMobject.add_points], each with a color;
    the style methods color them all. Each point is a disk as wide as a stroke of its
    `stroke_width`, a hundredth of a scene unit for each unit of width: at the default
    width, 4, about 4 pixels of a 720p frame.

    Args:
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]: `color` colors the points
            added without a color (white unless given), and `stroke_width` sizes them;
            the other paint keywords are not used.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class PMobjectExample(m.Scene):
            def construct(self) -> None:
                t = np.linspace(0, 1, 300)
                spiral = np.column_stack(
                    [3.5 * t * np.cos(20 * t), 3.5 * t * np.sin(20 * t), 0 * t]
                )
                colors = m.color_gradient([m.BLUE, m.GREEN, m.YELLOW], len(t))
                rgbas = np.array([color.to_rgba() for color in colors])
                cloud = m.PMobject(stroke_width=15).add_points(spiral, rgbas=rgbas)
                self.add(cloud)
        ```
    """

    def init_colors(self, propagate_colors: bool = True) -> Self:
        # a point's color is its row in `rgbas`, set as points are added; style gives
        # its size
        self.paint = self.paint.but(
            stroke_width=self.style.get("stroke_width", DEFAULT_STROKE_WIDTH)
        )
        return self

    def _color(self) -> ManimColor:
        return parse_colors(self.style.get("color", WHITE))[0]

    def reset_points(self) -> Self:
        self.points = np.zeros((0, 3))
        self.paint = self.paint.but(fill=np.zeros((0, 4)))
        return self

    def add_points(
        self,
        points: Point3DLike_Array,
        rgbas: np.ndarray | None = None,
        color: ParsableManimColor | None = None,
        alpha: float = 1.0,
    ) -> Self:
        """Add points to the cloud, after its own, with their colors.

        Args:
            points: The points, in scene coordinates: an (n, 3) array.
            rgbas: Their colors, one row of red, green, blue and opacity (from 0 to 1)
                per point; None to give them all `color`.
            color: Their color, when `rgbas` is None; None for the cloud's (its `color`
                style keyword, white unless given).
            alpha: Their opacity, from 0 to 1, when `rgbas` is None.
        """
        points = np.asarray(points, dtype=float).reshape(-1, 3)
        if rgbas is None:
            c = ManimColor(color) if color else self._color()
            rgbas = np.repeat([c.to_rgba_with_alpha(alpha)], len(points), axis=0)
        elif len(rgbas) != len(points):
            raise ValueError("points and rgbas must have same length")
        self.points = np.append(self.points, points, axis=0)
        self.paint = self.paint.but(fill=np.append(self.paint.fill, rgbas, axis=0))
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_all_rgbas(self) -> RGBA_Array:
        """The colors of every point of the cloud's family, member after member.

        Returns:
            An (n, 4) array of red, green, blue and opacity, from 0 to 1.
        """
        return np.concatenate(
            [m.paint.fill for m in self.family_members_with_points()]
            or [np.zeros((0, 4))]
        )

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def match_colors(self, mobject: Mobject) -> Self:
        """Give the cloud another cloud's colors, point for point.

        The two are first aligned as a transform aligns them: the one with fewer points
        is given more, repeating its points, so `mobject` may change too.

        Args:
            mobject: The cloud whose colors to take.
        """
        Mobject.align_data(self, mobject)
        self.paint = self.paint.but(fill=mobject.paint.fill)
        return self

    def thin_out(self, factor: int = 5) -> Self:
        """Keep one point in every `factor` of each cloud in the family, from its first.

        Args:
            factor: One point is kept in this many; must be positive.
        """
        if factor < 1:
            raise ValueError("factor must be positive")
        for mob in self.family_members_with_points():
            mob.points, mob.paint = (
                mob.points[::factor],
                mob.paint.but(fill=mob.paint.fill[::factor].copy()),
            )
        return self

    # ── the Points kind's alignment and partial rules ──────────────────────
    def align_points_with_larger(self, larger: Mobject) -> Self:
        n = larger.get_num_points()
        self.points = stretch_array(self.points, n)
        self.paint = self.paint.but(fill=stretch_array(self.paint.fill, n))
        return self

    def get_point_mobject(self, center: Point3DLike | None = None) -> "Point":
        return Point(self.get_center() if center is None else center)

    def pointwise_become_partial(self, mobject: Mobject, a: float, b: float) -> Self:
        # every point the stretch reaches into, as a reveal over it shows them
        n = mobject.get_num_points()
        lo = min(max(math.floor(a * n), 0), n)
        hi = min(max(math.ceil(b * n), lo), n)
        fill = mobject.paint.fill
        self.points = mobject.points[lo:hi]
        self.paint = self.paint.but(fill=fill[lo:hi] if len(fill) == n else fill)
        return self


@deprecated("Manim CE's base of point clouds along lines: use PMobject", category=None)
class Mobject1D(PMobject):
    """A point cloud of lines: points evenly spaced along each, `density` to a unit.

    Lines are added with [add_line][manimgx.Mobject1D.add_line].

    Args:
        density: How many points a line gets per scene unit of its length.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]: `color` colors the points
            added without a color (white unless given), and `stroke_width` sizes them.

    Examples:
        ```python
        import manimgx as m


        class Mobject1DExample(m.Scene):
            def construct(self) -> None:
                cloud = m.Mobject1D(density=6, stroke_width=12)
                cloud.add_line([-4, -2, 0], [4, -2, 0], color=m.BLUE)
                cloud.add_line([4, -2, 0], [0, 2.5, 0], color=m.YELLOW)
                cloud.add_line([0, 2.5, 0], [-4, -2, 0], color=m.RED)
                self.add(cloud)
        ```
    """

    def __init__(
        self, density: int = DEFAULT_POINT_DENSITY_1D, **kwargs: Unpack[Style]
    ) -> None:
        self.density = density
        self.epsilon = 1.0 / density
        super().__init__(**kwargs)

    def add_line(
        self,
        start: Point3DLike,
        end: Point3DLike,
        color: ParsableManimColor | None = None,
    ) -> Self:
        """Add a line of points from `start` toward `end`, 1/`density` scene units
        apart.

        The line stops short of `end`, where another may start; a line of no length is
        one point.

        Args:
            start: Where the line starts, in scene coordinates.
            end: Where it ends.
            color: The points' color; None for the cloud's.
        """
        s, e = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
        length = np.linalg.norm(e - s)
        points = (
            np.array([s])
            if length == 0
            else interpolate(s, e, np.arange(0, 1, self.epsilon / length)[:, None])
        )
        return self.add_points(points, color=color)


if TYPE_CHECKING:

    @deprecated("PGroup is Group: use Group, or VGroup", category=None)
    class PGroup[T: Mobject = Mobject](Group[T]):
        """Manim CE's group of point clouds: [Group][manimgx.Group], which holds
        mobjects of any kind."""

else:
    PGroup = Group  # a group is a group: kinds belong to leaves


@deprecated("Manim CE's one-point cloud: use VectorizedPoint, or Dot", category=None)
class Point(PMobject):
    """A point cloud of one point, black unless colored: unseen on the default black
    background.

    Args:
        location: Where the point is, in scene coordinates.
        color: Its color, which may be given by position (`Point(ORIGIN, RED)`); None
            for black.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]: `stroke_width` sizes the
            point.

    Examples:
        ```python
        import manimgx as m


        class PointExample(m.Scene):
            def construct(self) -> None:
                colors = [m.RED, m.YELLOW, m.GREEN, m.BLUE, m.PURPLE]
                for i, color in enumerate(colors):
                    self.add(m.Point([2.5 * i - 5, 0, 0], color, stroke_width=60))
        ```
    """

    defaults: ClassVar[Style] = {"color": BLACK}

    def __init__(
        self,
        location: Point3DLike = ORIGIN,
        color: Colors | None = None,
        **kwargs: Unpack[StyleBase],
    ) -> None:
        self.location = np.array(location, dtype=float)  # its own, as it was given
        super().__init__(
            **(Style(**kwargs) if color is None else Style(**kwargs, color=color))
        )

    def generate_points(self) -> Self:
        return self.reset_points().add_points(np.array([self.location]))


if TYPE_CHECKING:
    from manimgx.scene import Camera


_MESH_STRAIGHT = straight_path()  # a default (paths are immutable)


def _value(array: np.ndarray, held: np.ndarray | None = None) -> np.ndarray:
    """An owned read-only snapshot; an equal value keeps the array already held."""
    if held is not None and unchanged(array, held):
        return held
    array = array.copy()
    array.flags.writeable = False
    return array


class MeshMobject(Mobject):
    """A mesh: triangles between vertices, filled with one color, a color per vertex, or
    a picture; white and opaque unless styled.

    Any two meshes can morph into each other, whatever their triangles: the one with
    fewer gains some, collapsed to points. Drawn in ([Create][manimgx.Create]), a mesh
    appears triangle by triangle, in their order. A three-dimensional scene's light
    shades it only with `shade_in_3d=True`.

    Args:
        vertices: The vertices, in scene coordinates: an (n, 3) array; None for an empty
            mesh.
        triangles: The triangles: an (m, 3) array of indices into `vertices`.
        vertex_colors: A color for each vertex, blended across each triangle: an (n, 4)
            array of red, green, blue and opacity, from 0 to 1; None for the style's
            color.
        uvs: Where each vertex is in the picture: an (n, 2) array of coordinates from 0
            to 1, (0, 0) the picture's top left.
        texture: The picture: an (h, w, 4) array of RGBA values from 0 to 255, or a
            [Camera][manimgx.Camera], whose view is drawn anew every frame.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class MeshMobjectExample(m.Scene):
            def construct(self) -> None:
                vertices = np.array([[-3, -2.5, 0], [3, -2.5, 0], [0, 3, 0]])
                colors = np.array([[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]])
                triangle = m.MeshMobject(
                    vertices, np.array([[0, 1, 2]]), vertex_colors=colors
                )
                self.play(m.FadeIn(triangle))
        ```
    """

    defaults: ClassVar[Style] = {
        "fill_opacity": 1.0,
        "stroke_opacity": 0.0,
        "stroke_width": 0.0,
    }

    def __init__(
        self,
        vertices: Point3D_Array | None = None,
        triangles: np.ndarray | None = None,
        *,
        vertex_colors: np.ndarray | None = None,
        uvs: np.ndarray | None = None,
        texture: "np.ndarray | Camera | None" = None,
        **kwargs: Unpack[Style],
    ) -> None:
        # values, as they are given: regenerated, the mesh is what it was made of
        self._init_mesh = (
            None if vertices is None else np.array(vertices),
            None if triangles is None else np.array(triangles),
            None if uvs is None else np.array(uvs),
        )
        self._vertex_colors = None if vertex_colors is None else np.array(vertex_colors)
        self._texture = _value(texture) if isinstance(texture, np.ndarray) else texture
        super().__init__(**kwargs)

    @property
    def triangles(self) -> np.ndarray:
        """The mesh's readonly (m, 3) triangle indices; for a lattice these are the
        coarse triangles of the faces it draws, two each.

        Equal assignment is a no-op. Ordinary meshes snapshot replacement indices;
        a sampled lattice requires constructing an explicit MeshMobject instead.
        """
        topology = self._topology
        return topology.triangles() if isinstance(topology, Lattice) else topology

    @triangles.setter
    def triangles(self, value: npt.ArrayLike) -> None:
        array = np.asarray(value, dtype=np.int64)
        array = array if array.shape[1:] == (3,) else array.reshape(-1, 3)
        held = self.__dict__.get("_topology")
        if isinstance(held, Lattice):
            if np.array_equal(array, self.triangles):
                return
            raise ValueError(
                "A lattice's derived triangles cannot be replaced; construct "
                "MeshMobject(vertices, triangles, vertex_colors=...) explicitly"
            )
        self._topology = _value(array, held)

    @property
    def uvs(self) -> np.ndarray | None:
        """Where each vertex is in the mesh's picture: an (n, 2) array of coordinates
        from 0 to 1, read-only; None for a mesh without them. Assignments snapshot
        the supplied coordinates; equal values keep the current array."""
        return self._uvs

    @uvs.setter
    def uvs(self, value: npt.ArrayLike | None) -> None:
        self._uvs = (
            None
            if value is None
            else _value(np.asarray(value, dtype=float), self.__dict__.get("_uvs"))
        )

    @property
    def grid(self) -> tuple[int, int] | None:
        """The numbers of lattice cells along u and v, or None for explicit triangles.

        A (u, v) lattice has (u + 1) * (v + 1) samples. Its fill rows belong to cells
        and UVs to samples; ordinary mesh fill rows belong to vertices. match_points
        adopts this domain while retaining its recipient's style. A part of a surface
        has its whole lattice, and draws some of its faces.
        """
        topology = self._topology
        return (topology.u, topology.v) if isinstance(topology, Lattice) else None

    def generate_points(self) -> Self:
        vertices, triangles, uvs = self._init_mesh
        if vertices is not None:
            self.points = np.asarray(vertices, dtype=float)
            self._topology = _value(
                np.asarray(triangles, dtype=np.int64).reshape(-1, 3), self.triangles
            )
            self.uvs = uvs
        return self

    def reset_points(self) -> Self:
        super().reset_points()
        self._topology = _value(np.zeros((0, 3), dtype=np.int64))
        self.uvs = None
        return self

    def init_colors(self, propagate_colors: bool = True) -> Self:
        super().init_colors(propagate_colors)
        if self._vertex_colors is not None:
            self.paint = self.paint.but(fill=np.array(self._vertex_colors, dtype=float))
        self.paint = self.paint.but(texture=self._texture)
        return self

    # ── the Mesh kind's alignment and partial rules ────────────────────────
    def _as_soup(self) -> None:
        """Convert to explicit triangles, giving each corner its own point and paint row."""
        index = self.triangles.ravel()
        if len(self.points) == len(index) and np.array_equal(
            index, np.arange(len(index))
        ):
            return
        topology = self._topology
        if isinstance(topology, Lattice):
            if len(self.paint.fill) > 1:  # its faces' rows, one per corner of each
                cells = stretch_array(self.paint.fill, topology.u * topology.v)
                drawn = cells[topology.first : topology.end]
                self.paint = self.paint.but(fill=np.repeat(drawn, 6, axis=0))
        elif len(self.paint.fill) == len(self.points) > 1:
            self.paint = self.paint.but(fill=self.paint.fill[index])
        self.points = self.points[index]
        if self.uvs is not None:
            self.uvs = self.uvs[index]
        self._topology = _value(np.arange(len(index)).reshape(-1, 3))

    def align_points(self, mobject: Mobject) -> Self:
        # Equal topology shares the existing domain. Different topology becomes explicit
        # triangle soup; the smaller mesh gains copies collapsed to their centers.
        if not isinstance(mobject, MeshMobject):
            self.paint, mobject.paint = Paint.aligned(self.paint, mobject.paint)
            return self
        if len(self.points) != len(mobject.points) or not np.array_equal(
            self._topology, mobject._topology
        ):
            for mesh in (self, mobject):
                mesh._as_soup()
            small, large = sorted((self, mobject), key=lambda m: len(m.points))
            n = len(large.points) // 3
            if len(small.points) == 0:
                small.points = np.repeat(small.get_center()[None], n * 3, axis=0)
            else:
                pieces = small.points.reshape(-1, 3, 3)
                index = np.arange(n) * len(pieces) // n
                first = np.r_[True, index[1:] != index[:-1]]
                padded = pieces[index].copy()
                padded[~first] = padded[~first].mean(axis=1, keepdims=True)
                if len(small.paint.fill) == len(small.points) > 1:
                    colors = small.paint.fill.reshape(-1, 3, 4)[index].reshape(-1, 4)
                    small.paint = small.paint.but(fill=colors)
                if small.uvs is not None:
                    small.uvs = small.uvs.reshape(-1, 3, 2)[index].reshape(-1, 2)
                small.points = padded.reshape(-1, 3)
            small._topology = large._topology
        for a, b in ((self, mobject), (mobject, self)):
            if len(a.paint.fill) == len(a.points) > 1 and len(b.paint.fill) == 1:
                b.paint = b.paint.but(
                    fill=np.repeat(b.paint.fill, len(b.points), axis=0)
                )
        self.paint, mobject.paint = Paint.aligned(self.paint, mobject.paint)
        return self

    def _take_shape(self, mobject: Mobject) -> None:
        if isinstance(mobject, MeshMobject):
            self._topology, self._uvs = mobject._topology, mobject.uvs

    def get_point_mobject(self, center: Point3DLike | None = None) -> "MeshMobject":
        c = self.get_center() if center is None else np.asarray(center, dtype=float)
        point = MeshMobject(np.repeat(c[None], 3, axis=0), np.array([[0, 1, 2]]))
        point.paint = self.paint
        return point

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def pointwise_become_partial(self, mobject: Mobject, a: float, b: float) -> Self:
        """Take a source's geometry and paint, then keep the steps a reveal over the
        stretch shows, whole: a surface's faces, or a mesh's triangles.

        A surface's part is a surface: its whole lattice, drawing those faces, as smooth
        and with the edges they have in it. A mesh's part is its triangles alone, each
        corner with its paint and UV. Repeated calls restart from source.
        """
        if isinstance(mobject, MeshMobject):
            self._geometry = mobject._geometry
            self._take_shape(mobject)
            self.paint = mobject.paint
            topology = self._topology
            lattice = isinstance(topology, Lattice)
            n = topology.end - topology.first if lattice else len(topology)
            lo = min(max(math.floor(a * n), 0), n)
            hi = min(max(math.ceil(b * n), lo), n)
            if (lo, hi) == (0, n):
                return self
            if isinstance(topology, Lattice):
                first = topology.first
                self._topology = topology._replace(first=first + lo, end=first + hi)
                return self
            self._as_soup()  # three corners a triangle, in order: keep the part's own
            self.points = self.points[3 * lo : 3 * hi]
            if len(self.paint.fill) == 3 * n > 1:
                self.paint = self.paint.but(fill=self.paint.fill[3 * lo : 3 * hi])
            if self.uvs is not None:
                self.uvs = self.uvs[3 * lo : 3 * hi]
            self._topology = _value(np.arange(3 * (hi - lo)).reshape(-1, 3))
        return self

    def _box(self) -> np.ndarray | None:
        # a part of a surface keeps its whole lattice: its box is its drawn faces'
        topology = self._topology
        if not isinstance(topology, Lattice) or topology.end - topology.first == (
            topology.u * topology.v
        ):
            return super()._box()
        drawn = self.points[np.unique(topology.triangles())]
        return np.array([drawn.min(axis=0), drawn.max(axis=0)]) if len(drawn) else None

    def interpolate(
        self,
        mobject1: Mobject,
        mobject2: Mobject,
        alpha: float,
        path_func: PathFunc = _MESH_STRAIGHT,
    ) -> Self:
        super().interpolate(mobject1, mobject2, alpha, path_func)
        if isinstance(mobject1, MeshMobject) and isinstance(mobject2, MeshMobject):
            self._topology = mobject2._topology if alpha >= 1 else mobject1._topology
        return self


if TYPE_CHECKING:
    from pathops import Path as SkiaPath


def _append_path(target: "VMobject", path: "SkiaPath") -> "None":
    """Append a planar path through the existing cubic builder, preserving its arithmetic."""
    start = np.zeros(3)
    verb = _pathops().PathVerb
    for kind, points in path:
        parts = np.array([(*point, 0.0) for point in points], dtype=float)
        if kind == verb.MOVE:
            for part in parts:
                start = part
                target.start_new_path(part)
        elif kind == verb.CUBIC:
            first, second, end = parts
            target.add_cubic_bezier_curve_to(first, second, end)
        elif kind == verb.LINE:
            target.add_line_to(parts[0])
        elif kind == verb.CLOSE:
            target.add_line_to(start)
        elif kind == verb.QUAD:
            control, end = parts
            target.add_quadratic_bezier_curve_to(control, end)
        else:
            raise Exception(f"Unsupported: {kind}")

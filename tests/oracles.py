"""Slow, plain reference implementations the tests compare ManimGX with: each computes the same
quantity by another, obviously correct algorithm (de Casteljau's construction, numpy's root
finder, quadrature, triangle fans), so a test that agrees with one checks something.

And what an object holds, walked plainly: `reachable(root)` is everything an object reaches
(through attributes, containers, bound methods, closures, partials and an array's base), so
`reaches(root, targets)` says whether it keeps any of them, with no garbage collection to wait
on; `assert_replica(original, replica)` walks two object graphs side by side, to show that one
is an isomorphic copy of the other sharing no mutable part; `drawn_box(mob)` is the tight box
of what a mobject's family draws."""

import contextlib
import enum
import functools
import gc
import numbers
import pathlib
import sys
import types
import weakref
from collections.abc import Iterable
from itertools import pairwise
from typing import cast

import numpy as np
from numpy.polynomial import legendre


def bezier_points(curves: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Each cubic curve at each parameter, by de Casteljau's construction: (curves, len(t),
    dim)."""
    array = np.asarray(curves, dtype=float)
    p = array.reshape(-1, 1, 4, array.shape[-1])
    t = np.asarray(t, dtype=float)[None, :, None, None]
    while p.shape[2] > 1:  # each round interpolates between neighbouring points
        p = (1 - t) * p[:, :, :-1] + t * p[:, :, 1:]
    return p[:, :, 0]


def sample(curves: np.ndarray, per_curve: int = 200) -> np.ndarray:
    """Points along cubic curves, `per_curve` evenly spaced in each one's parameter."""
    points = bezier_points(curves, np.linspace(0, 1, per_curve))
    return points.reshape(-1, points.shape[-1])


def curve_box(points: np.ndarray) -> np.ndarray:
    """(2, dim): the tight box of cubic curves, by numpy's roots of each coordinate's
    derivative."""
    array = np.asarray(points, dtype=float)
    curves = array.reshape(-1, 4, array.shape[-1])
    found = [curves[:, 0], curves[:, 3]]
    for c in curves:
        for d in range(c.shape[1]):
            p0, p1, p2, p3 = c[:, d]
            derivative = [
                3 * (p3 - 3 * p2 + 3 * p1 - p0),
                6 * (p2 - 2 * p1 + p0),
                3 * (p1 - p0),
            ]
            if not any(derivative[:2]):
                continue
            for r in np.roots(derivative):
                if abs(r.imag) < 1e-12 and 0 <= r.real <= 1:
                    found.append(bezier_points(c, np.array([r.real]))[0])
    everything = np.concatenate(found)
    return np.array([everything.min(axis=0), everything.max(axis=0)])


_NODES, _WEIGHTS = legendre.leggauss(24)


def arc_lengths(points: np.ndarray, pieces: int = 16) -> np.ndarray:
    """Each cubic curve's length: Gauss–Legendre quadrature of its speed, on `pieces` equal
    stretches of each stretch between the speed's minima (where a cusp makes the speed
    kink, a quadrature across it would lose digits)."""
    array = np.asarray(points, dtype=float)
    curves = array.reshape(-1, 4, array.shape[-1])
    lengths = []
    for curve in curves:
        d = 3 * np.diff(curve, axis=0)  # B'(t) = a t² + b t + c
        a, b, c = d[0] - 2 * d[1] + d[2], 2 * (d[1] - d[0]), d[0]
        # d/dt |B'|² / 2 = (a t² + b t + c)·(2 a t + b): a cubic, zero at the speed's minima
        cubic = [2 * a @ a, 3 * a @ b, b @ b + 2 * a @ c, b @ c]
        cuts = sorted(
            r.real
            for r in (np.roots(cubic) if any(cubic) else [])
            if abs(r.imag) < 1e-12 and 0 < r.real < 1
        )
        edges = np.unique(np.concatenate([[0.0, 1.0], cuts]))
        total = 0.0
        for lo, hi in pairwise(edges):
            grid = np.linspace(lo, hi, pieces + 1)
            half = np.diff(grid) / 2
            t = ((grid[:-1] + half)[:, None] + np.outer(half, _NODES)).ravel()
            w = np.outer(half, _WEIGHTS).ravel()
            speed = np.linalg.norm(np.outer(t * t, a) + np.outer(t, b) + c, axis=1)
            total += float(speed @ w)
        lengths.append(total)
    return np.array(lengths)


def look(mob: object) -> list[tuple[object, ...]]:
    """What a mobject shows, member by member: its kind, points, paint, z-index and how many
    submobjects it has; two mobjects that look the same draw the same frames."""
    from manimgx.mobject import Mobject

    assert isinstance(mob, Mobject)
    seen = []
    for member in mob.get_family():
        p = member.paint
        seen.append(
            (
                type(member).__name__,
                member.points.tobytes(),
                *(
                    np.asarray(getattr(p, name)).tobytes()
                    for name in ("fill", "stroke", "background")
                ),
                p.stroke_width,
                p.background_width,
                p.sheen_factor,
                np.asarray(p.sheen_direction).tobytes(),
                member.z_index,
                len(member.submobjects),
            )
        )
    return seen


def polygon_area(xy: np.ndarray) -> float:
    """A polygon's signed area, positive counterclockwise, by triangles fanned from its
    first vertex."""
    array = np.asarray(xy, dtype=float)
    d = array[:, :2] - array[0, :2]
    return float(np.sum(d[1:-1, 0] * d[2:, 1] - d[2:, 0] * d[1:-1, 1]) / 2)


def area_weighted_normals(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Each vertex's normal: the sum of (b − a) × (c − a) over the triangles it is a corner of,
    added corner by corner (every triangle's first corner, then every second, then every
    third)."""
    out = np.zeros(points.shape)
    a, b, c = (points[triangles[:, k]] for k in range(3))
    faces = np.cross(b - a, c - a)
    for k in range(3):
        np.add.at(out, triangles[:, k], faces)
    return out


def drawn_box(mob: object) -> np.ndarray | None:
    """(2, dim): the tight box of what a mobject's family draws — a path's curves (by
    `curve_box`), any other kind's points — or None if it draws nothing."""
    from manimgx.mobject import Mobject

    assert isinstance(mob, Mobject)
    boxes = []
    for leaf in mob.family_members_with_points():
        points = leaf.points
        whole = len(points) - len(points) % 4 if leaf._curves else 0  # a path's curves
        if whole:
            boxes.append(curve_box(points[:whole]))
        if len(points) > whole:  # points of their own: a lone anchor, a cloud, a mesh
            rest = points[whole:]
            boxes.append(np.array([rest.min(axis=0), rest.max(axis=0)]))
    if not boxes:
        return None
    stacked = np.array(boxes)
    return np.array([stacked[:, 0].min(axis=0), stacked[:, 1].max(axis=0)])


# ── what an object holds ─────────────────────────────────────────────────────────────
_SKIP = (type, types.ModuleType, types.CodeType, types.BuiltinFunctionType, weakref.ref)
_ATOMS = (int, float, complex, bool, str, bytes, type(None), range, slice)


def _referents(obj: object) -> Iterable[object]:
    """What an object refers to: a function's closure and defaults (not its globals), a
    bound method's object and function, an array's base, an object's attributes."""
    if isinstance(obj, _SKIP):
        return ()
    if isinstance(obj, types.FunctionType):
        out: list[object] = []
        for cell in obj.__closure__ or ():
            with contextlib.suppress(ValueError):  # (an empty cell)
                out.append(cell.cell_contents)
        out.extend(obj.__defaults__ or ())
        out.extend((obj.__kwdefaults__ or {}).values())
        return out
    if isinstance(obj, types.MethodType):
        return (obj.__self__, obj.__func__)
    if isinstance(obj, np.ndarray):
        return () if obj.base is None else (obj.base,)
    if hasattr(obj, "__dict__") and not isinstance(obj, dict):
        return (*vars(obj).values(), *gc.get_referents(obj))
    return gc.get_referents(obj)


def reachable(root: object) -> dict[int, object]:
    """Everything `root` reaches, by id (itself included); classes, modules and functions'
    globals are not followed."""
    seen: dict[int, object] = {}
    stack = [root]
    while stack:
        obj = stack.pop()
        if id(obj) in seen or isinstance(obj, _ATOMS):
            continue
        seen[id(obj)] = obj
        stack.extend(_referents(obj))
    return seen


def mutable_parts(root: object) -> dict[int, object]:
    """What `root` holds that can change in place — mobjects, lists, dicts, sets, writable
    arrays, objects — reached without passing through a value (a paint, a geometry, a
    function, one of ManimGX's module-level objects), by id."""
    seen: dict[int, object] = {}
    stack = [root]
    while stack:
        obj = stack.pop()
        if id(obj) in seen or isinstance(obj, _ATOMS):
            continue
        if obj is not root and (_is_value(obj) or module_global(obj)):
            continue
        seen[id(obj)] = obj
        stack.extend(_referents(obj))
    return seen


def reaches(root: object, targets: Iterable[object]) -> list[object]:
    """The targets `root` reaches: empty if it keeps none of them."""
    ids = {id(t) for t in targets}
    return [obj for key, obj in reachable(root).items() if key in ids]


def _module_globals() -> set[int]:
    """ManimGX's module-level objects (ORIGIN, a default LinearBase…): a mobject may take one as
    a default and hold it, and a copy may hold it or a copy of it."""
    out: set[int] = set()
    for name, module in list(sys.modules.items()):
        if name.startswith("manimgx") and module is not None:
            for value in vars(module).values():
                if not isinstance(value, (types.ModuleType, type, types.FunctionType)):
                    out.add(id(value))
    return out


_GLOBALS: set[int] = set()


def module_global(obj: object) -> bool:
    """Is `obj` one of ManimGX's module-level objects (a constant, a default)?"""
    if not _GLOBALS:
        _GLOBALS.update(_module_globals())
    return id(obj) in _GLOBALS and not isinstance(obj, _ATOMS)


def _values() -> tuple[type, ...]:
    from manimgx.drawing.geometry import Blend
    from manimgx.drawing.paint import ManimColor, Paint

    return (
        Paint,
        Blend,
        ManimColor,
        types.FunctionType,
        functools.partial,
        np.ufunc,
        np.generic,
        frozenset,
        enum.Enum,
        pathlib.PurePath,
        numbers.Number,
    )


def _is_value(obj: object) -> bool:
    """Shared freely by a mobject and its replica: a value never changed in place."""
    if isinstance(obj, (*_ATOMS, *_SKIP, *_values())):
        return True
    if type(obj).__module__ in (
        "typing",
        "types",
    ):  # (`__orig_class__`: a generic alias)
        return True
    if module_global(obj):
        return True
    if isinstance(obj, np.ndarray):
        return not obj.flags.writeable
    if isinstance(obj, tuple):
        return all(_is_value(v) for v in obj)
    return False


_PAINTED = ("fill", "stroke", "background", "stroke_width", "background_width")


def _same_value(x: object, y: object) -> bool:
    from manimgx.drawing.geometry import Blend
    from manimgx.drawing.paint import Paint

    if x is y:
        return True
    if isinstance(x, np.ndarray) and isinstance(y, np.ndarray):
        return x.shape == y.shape and np.array_equal(x, y, equal_nan=True)
    if isinstance(x, types.FunctionType) and isinstance(y, types.FunctionType):
        return x.__code__ is y.__code__
    if isinstance(x, Blend) and isinstance(y, Blend):
        return np.array_equal(x.points(), y.points())
    if isinstance(x, Paint) and isinstance(y, Paint):
        return all(np.array_equal(getattr(x, n), getattr(y, n)) for n in _PAINTED)
    if isinstance(x, tuple) and isinstance(y, tuple):
        return len(x) == len(y) and all(map(_same_value, x, y))
    if module_global(x):
        return type(x) is type(y) and (
            not hasattr(x, "__dict__")
            or (
                vars(x).keys() == vars(y).keys()
                and all(_same_value(vars(x)[k], vars(y)[k]) for k in vars(x))
            )
        )
    try:
        return bool(x == y)
    except Exception:  # (an array's truth, a value with no equality)
        return False


def _same_key(a: object, b: object) -> bool:
    """Dictionary keys are identities (a graph's vertex, a VDict's key): never copied."""
    if isinstance(a, tuple) and isinstance(b, tuple):
        return len(a) == len(b) and all(map(_same_key, a, b))
    return a is b or (_is_value(a) and _same_value(a, b))


def _pairs(x: object, y: object, path: str) -> list[tuple[object, object, str]]:
    """The parts of x and y to walk next, checking that the two hold parts alike."""

    assert type(x) is type(y), f"{path}: {type(x).__name__} became {type(y).__name__}"
    if isinstance(x, (list, tuple)):
        ys = cast("list[object] | tuple[object, ...]", y)
        assert len(x) == len(ys), f"{path}: {len(x)} items became {len(ys)}"
        return [(a, b, f"{path}[{i}]") for i, (a, b) in enumerate(zip(x, ys))]
    if isinstance(x, dict):
        yd = cast("dict[object, object]", y)
        assert len(x) == len(yd), f"{path}: {len(x)} keys became {len(yd)}"
        out = []
        for (ka, va), (kb, vb) in zip(x.items(), yd.items()):
            # a key is an identity (a vertex, a VDict's key) the replica borrows, or a part
            # copied with the rest (an updater keying its clock stamp, a key made with it)
            if isinstance(ka, types.MethodType) or not _same_key(ka, kb):
                out.append((ka, kb, f"{path}.key"))
            out.append((va, vb, f"{path}[{ka!r}]"))
        return out
    if isinstance(x, set):
        assert x == y, f"{path}: the sets differ"
        return []
    if isinstance(x, types.MethodType):
        ym = cast("types.MethodType", y)
        assert x.__func__ is ym.__func__, f"{path}: another method"
        return [(x.__self__, ym.__self__, f"{path}.__self__")]
    if hasattr(x, "__dict__"):
        shared = cast("frozenset[str]", getattr(type(x), "shared", frozenset()))
        dx, dy = vars(x), vars(y)
        assert dx.keys() == dy.keys(), f"{path}: the attributes {dx.keys() ^ dy.keys()}"
        out = []
        for name in dx:
            if name in shared:  # declared shared: a value, never changed in place
                assert dx[name] is dy[name] or _same_value(dx[name], dy[name]), (
                    f"{path}.{name}: a shared attribute differs"
                )
                assert name == "style" or dx[name] is None or _is_value(dx[name]), (
                    f"{path}.{name}: a mutable {type(dx[name]).__name__} is declared shared"
                )
            else:
                out.append((dx[name], dy[name], f"{path}.{name}"))
        return out
    return []


def assert_replica(original: object, replica: object) -> None:
    """The replica is an isomorphic copy of the original that shares no mutable part.

    Walking the two object graphs side by side, each part of the replica answers to one part
    of the original: of the same type, with the same plain values; two references to one
    mobject or object in the original are two references to one in the replica (containers
    are rebuilt per reference, as `mobject.copied` rebuilds them); and nothing mutable — a
    mobject, list, dict, set, writable array or object — is in both. Values are shared freely:
    numbers, strings, read-only arrays, paints, geometries, colors, functions, and ManimGX's
    module-level objects."""
    pairs: dict[int, object] = {}
    mine: dict[int, object] = {}
    rebuilt: list[object] = []
    stack: list[tuple[object, object, str]] = [(original, replica, "root")]
    while stack:
        x, y, path = stack.pop()
        if id(x) in pairs:
            assert pairs[id(x)] is y, f"{path}: an alias became two parts"
            continue
        if module_global(
            x
        ):  # a module's default (ORIGIN, a LinearBase): kept or copied
            assert y is x or _same_value(x, y), f"{path}: {x!r} became {y!r}"
            continue
        if isinstance(x, np.ndarray) and x.flags.writeable:  # (each reference copied)
            assert isinstance(y, np.ndarray), f"{path}: an array became {y!r}"
            assert np.array_equal(x, y, equal_nan=True), f"{path}: the values differ"
            assert not np.shares_memory(x, y), f"{path}: a writable array is shared"
            continue
        if _is_value(x):
            assert _is_value(y), f"{path}: {x!r} became {y!r}"
            assert _same_value(x, y), f"{path}: {x!r} became {y!r}"
            continue
        assert x is not y, f"{path}: a mutable {type(x).__name__} is shared"
        mine[id(x)] = x
        if isinstance(x, (list, tuple, dict, set)):
            rebuilt.append(y)
        else:
            pairs[id(x)] = y
        stack.extend(_pairs(x, y, path))
    images = [pairs[k] for k in mine if k in pairs]
    assert len({id(y) for y in images}) == len(images), "two parts became one"
    assert not {id(y) for y in [*images, *rebuilt]} & set(mine), (
        "the replica holds parts of the original"
    )

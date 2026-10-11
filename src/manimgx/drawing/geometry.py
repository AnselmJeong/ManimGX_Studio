# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Geometry as values: vectors, cubic curves, polygon queries, shapes and affine blends.

A shape owns immutable points. A blend places shapes as Σ Mₖ·Sₖ; a path describes
how its coefficients change. The numerical operations here construct, query and
subdivide that geometry without scene objects or rendering state.
"""

from __future__ import annotations

import functools
import heapq
import itertools
import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from types import ModuleType
from typing import TYPE_CHECKING, Final, Literal, NamedTuple
from warnings import deprecated

import numpy as np
import numpy.typing as npt

from manimgx._engine import digest
from manimgx.caches import Memo, forgets, unchanged
from manimgx.typing import (
    MatrixMN,
    PathFunc,
    Point3D,
    Point3D_Array,
    Point3DLike,
    Point3DLike_Array,
    Vec,
    Vector3D,
    Vector3DLike,
)

if TYPE_CHECKING:
    from pathops import Path as SkiaPath

    from manimgx.typing import (
        Point2D,
        Point2D_Array,
        Point2DLike,
        Point2DLike_Array,
        PointND,
        PointND_Array,
    )


__all__ = [
    "STRAIGHT_PATH_THRESHOLD",
    "Coefficients",
    "Floats",
    "Path",
    "QuickHull",
    "R3_to_complex",
    "Step",
    "angle_axis_from_quaternion",
    "angle_between_vectors",
    "angle_of_vector",
    "bezier",
    "bezier_remap",
    "carried",
    "cartesian_to_spherical",
    "center_of_mass",
    "clockwise_path",
    "compass_directions",
    "complex_func_to_R3_func",
    "complex_to_R3",
    "counterclockwise_path",
    "cross2d",
    "earclip_triangulation",
    "find_intersection",
    "get_smooth_cubic_bezier_handle_points",
    "get_unit_normal",
    "get_winding_number",
    "integer_interpolate",
    "interpolate",
    "inverse_interpolate",
    "is_closed",
    "line_intersection",
    "midpoint",
    "norm_squared",
    "normalize",
    "normalize_along_axis",
    "partial_bezier_points",
    "path_along_arc",
    "path_along_circles",
    "perpendicular_bisector",
    "polylabel",
    "quaternion_conjugate",
    "quaternion_from_angle_axis",
    "quaternion_mult",
    "regular_vertices",
    "rotate_vector",
    "rotation_about_z",
    "rotation_matrix",
    "rotation_matrix_from_quaternion",
    "rotation_matrix_transpose",
    "rotation_matrix_transpose_from_quaternion",
    "shoelace",
    "shoelace_direction",
    "sigmoid",
    "spherical_to_cartesian",
    "spiral_path",
    "straight_path",
    "subdivide_bezier",
    "thick_diagonal",
    "z_to_vector",
]

_OUT = np.array([0.0, 0.0, 1.0])
_RIGHT = np.array([1.0, 0.0, 0.0])
_UP = np.array([0.0, 1.0, 0.0])
_DOWN = np.array([0.0, -1.0, 0.0])


def normalize(vect: Vector3DLike) -> Vector3D:
    """The unit vector in a vector's direction.

    Args:
        vect: The vector.

    Returns:
        The vector divided by its length; the zero vector stays zero.
    """
    v = np.asarray(vect, dtype=float)
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else np.zeros(len(v))


def rotation_matrix(angle: float, axis: Vector3DLike = _OUT) -> MatrixMN:
    """The matrix of a rotation about an axis through the origin.

    Raises ValueError for a zero axis: a turn about no axis is no turn at all.

    Args:
        angle: The angle, in radians, counterclockwise as seen from the tip of `axis`.
        axis: The axis's direction (its length does not matter).

    Returns:
        The 3×3 rotation matrix.
    """
    # Rodrigues' formula; identical to scipy's
    # `Rotation.from_rotvec(angle * axis).as_matrix()`
    x, y, z = normalize(axis)
    if x == y == z == 0:
        raise ValueError(f"a rotation's axis must not be zero, not {axis}")
    c, s = np.cos(angle), np.sin(angle)
    C = 1 - c
    return np.array(
        [
            [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
        ]
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def rotation_about_z(angle: float) -> MatrixMN:
    """The matrix of a rotation about the z axis.

    Args:
        angle: The angle, in radians, counterclockwise.

    Returns:
        The 3×3 rotation matrix.
    """
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rotate_vector(
    vector: Vector3DLike, angle: float, axis: Vector3DLike = _OUT
) -> Vector3D:
    """A vector rotated about an axis through the origin.

    Args:
        vector: The vector; a two-dimensional one gets a z of 0.
        angle: The angle, in radians, counterclockwise as seen from the tip of `axis`.
        axis: The axis's direction.

    Returns:
        The rotated vector.
    """
    v = np.asarray(vector, dtype=float)
    if len(v) == 2:
        v = np.append(v, 0)
    return rotation_matrix(angle, axis) @ v


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def z_to_vector(vector: Vector3DLike) -> MatrixMN:
    """A rotation that takes the z axis to a vector's direction.

    Args:
        vector: The direction.

    Returns:
        The 3×3 rotation matrix, whose columns are where the x, y and z axes go.
    """
    axis_z = normalize(vector)
    axis_y = normalize(np.cross(axis_z, _RIGHT))
    axis_x = np.cross(axis_y, axis_z)
    if np.linalg.norm(axis_y) == 0:
        axis_x = normalize(np.cross(_UP, axis_z))
        axis_y = -np.cross(axis_x, axis_z)
    return np.array([axis_x, axis_y, axis_z]).T


def angle_of_vector(vector: Vector3DLike) -> float:
    """The angle of a vector in the xy plane, counterclockwise from the x axis (its z is
    ignored).

    Returns:
        The angle, in radians, from −π to π.
    """
    v = np.asarray(vector)
    return float(np.angle(complex(v[0], v[1])))


def angle_between_vectors(v1: Vector3DLike, v2: Vector3DLike) -> float:
    """The angle between two vectors.

    Args:
        v1: A vector.
        v2: Another vector.

    Returns:
        The angle, in radians, from 0 to π.
    """
    a, b = normalize(v1), normalize(v2)
    return float(2 * np.arctan2(np.linalg.norm(a - b), np.linalg.norm(a + b)))


def turn_between(v1: Vector3DLike, v2: Vector3DLike) -> tuple[float, Vector3D]:
    """The smallest turn taking one direction to another, as (angle, axis).

    The axis is perpendicular to both; for directions along one line (a half turn, or
    none), it is the part of OUT across them, so a half turn in the plane of the screen
    stays in it, or RIGHT for directions along OUT.

    Args:
        v1: The direction turned.
        v2: The direction it is turned to.

    Returns:
        The angle, from 0 to π, and the unit axis.
    """
    a, b = np.asarray(v1, dtype=float), np.asarray(v2, dtype=float)
    cross = np.cross(a, b)
    norm = np.linalg.norm(cross)
    if norm > 0:
        return angle_between_vectors(a, b), cross / norm
    across = _OUT - (_OUT @ a) / max(float(a @ a), 1e-300) * a
    size = np.linalg.norm(across)
    return angle_between_vectors(a, b), (
        across / size if size > 1e-9 else _RIGHT.copy()
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def get_unit_normal(v1: Vector3DLike, v2: Vector3DLike, tol: float = 1e-6) -> Vector3D:
    """A unit vector perpendicular to two vectors: their cross product, normalized.

    For vectors along one line (or a zero vector), it is the part of the z axis
    perpendicular to them, normalized; [DOWN][manimgx.DOWN] if they lie along the z axis
    or are both zero.

    Args:
        v1: A vector.
        v2: Another vector.
        tol: How small, relative to the vectors, a cross product counts as zero.

    Returns:
        The unit vector.
    """
    a, b = np.asarray(v1, dtype=float), np.asarray(v2, dtype=float)
    d1, d2 = max(np.abs(a)), max(np.abs(b))
    if d1 == 0.0:
        if d2 == 0.0:
            return _DOWN.copy()
        u = b / d2
    elif d2 == 0.0:
        u = a / d1
    else:
        cp = np.cross(a / d1, b / d2)
        n = np.linalg.norm(cp)
        if n > tol:
            return cp / n
        u = a / d1
    if abs(u[0]) < tol and abs(u[1]) < tol:
        return _DOWN.copy()
    cp = np.array([-u[0] * u[2], -u[1] * u[2], u[0] * u[0] + u[1] * u[1]])
    return cp / np.linalg.norm(cp)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def compass_directions(n: int = 4, start_vect: Vector3DLike = _RIGHT) -> Point3D_Array:
    """Vectors evenly spread around the z axis, counterclockwise from a first one.

    Args:
        n: How many vectors.
        start_vect: The first vector.

    Returns:
        The vectors, as an (n, 3) array.
    """
    angles = np.arange(n) * (2 * np.pi / n)
    vector = np.asarray(start_vect, dtype=float)
    x, y, z = np.append(vector, 0) if len(vector) == 2 else vector
    c, s = np.cos(angles), np.sin(angles)
    # Matrix reductions start from +0.0; retain those zero signs in shape keys.
    return (
        np.column_stack([x * c - y * s, x * s + y * c, np.full(len(angles), z)]) + 0.0
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def regular_vertices(
    n: int, *, radius: float = 1, start_angle: float | None = None
) -> tuple[Point3D_Array, float]:
    """The vertices of a regular polygon centered at the origin, counterclockwise.

    Args:
        n: How many vertices.
        radius: How far they are from the center, in scene units.
        start_angle: The first vertex's angle, in radians, counterclockwise from the x
            axis; None for 0 when `n` is even and π/2 (a vertex on top) when it is odd.

    Returns:
        The vertices, as an (n, 3) array, and the first vertex's angle.
    """
    if start_angle is None:
        start_angle = 0 if n % 2 == 0 else np.pi / 2
    vertices = compass_directions(n, rotate_vector(_RIGHT * radius, start_angle))
    return vertices, start_angle


def line_intersection(line1: Point3DLike_Array, line2: Point3DLike_Array) -> Point3D:
    """Where two lines in the xy plane cross, each line through two points (their z is
    ignored).

    Raises an exception if the lines are parallel.

    Args:
        line1: Two points on the first line.
        line2: Two points on the second line.

    Returns:
        The point, with a z of 0.
    """
    padded = [
        np.pad(np.array(line)[:, :2], ((0, 0), (0, 1)), constant_values=1)
        for line in (line1, line2)
    ]
    l1, l2 = (np.cross(*p) for p in padded)
    x, y, z = np.cross(l1, l2)
    if z == 0:
        raise ValueError(
            "The lines are parallel, there is no unique intersection point."
        )
    return np.array([x / z, y / z, 0])


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def find_intersection(
    p0s: Point3DLike_Array,
    v0s: Point3DLike_Array,
    p1s: Point3DLike_Array,
    v1s: Point3DLike_Array,
    threshold: float = 1e-5,
) -> list[Point3D]:
    """For each pair of lines, the point of the first nearest the second: where they
    cross, if they do.

    The first line of each pair is `p0 + t·v0`, the second `p1 + s·v1`.

    Args:
        p0s: A point on each first line.
        v0s: Each first line's direction.
        p1s: A point on each second line.
        v1s: Each second line's direction.
        threshold: The least the division is by, so that parallel lines give `p0`
            rather than divide by zero.

    Returns:
        One point per pair.
    """
    result = []
    arrays = (np.asarray(a, dtype=float) for a in (p0s, v0s, p1s, v1s))
    for p0, v0, p1, v1 in zip(*arrays, strict=True):
        normal = np.cross(v1, np.cross(v0, v1))
        denom = max(np.dot(v0, normal), threshold)
        result.append(p0 + np.dot(p1 - p0, normal) / denom * v0)
    return result


def midpoint(p1: Point3D, p2: Point3D) -> Point3D:
    """The point halfway between two points.

    Args:
        p1: A point.
        p2: Another point.

    Returns:
        The point between them.
    """
    return (np.asarray(p1) + np.asarray(p2)) / 2


def cartesian_to_spherical(vec: Vector3DLike) -> Vec:
    """A vector's spherical coordinates.

    Args:
        vec: The vector.

    Returns:
        Its length r, its azimuth θ (the angle of its xy part from the x axis, from −π
        to π) and its polar angle φ (from the z axis, from 0 to π); zeros for the zero
        vector.
    """
    v = np.asarray(vec, dtype=float)
    r = np.linalg.norm(v)
    if r == 0:
        return np.zeros(3)
    # the polar angle by its tangent: arccos(z / r) loses digits near the poles
    return np.array([r, np.arctan2(v[1], v[0]), np.arctan2(np.hypot(v[0], v[1]), v[2])])


def spherical_to_cartesian(spherical: np.ndarray) -> Vector3D:
    """The vector of spherical coordinates (see
    [cartesian_to_spherical][manimgx.cartesian_to_spherical]).

    Args:
        spherical: The length r, the azimuth θ and the polar angle φ, in radians.

    Returns:
        The vector (r cos θ sin φ, r sin θ sin φ, r cos φ).
    """
    r, theta, phi = spherical
    return np.array(
        [
            r * np.cos(theta) * np.sin(phi),
            r * np.sin(theta) * np.sin(phi),
            r * np.cos(phi),
        ]
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def shoelace(xy: np.ndarray) -> float:
    """The signed area of the polygon through points in turn, back to the first: the
    integral of y dx around it.

    It is positive if the polygon runs clockwise, negative if counterclockwise. A
    polygon given closed, its first point repeated last, has the same area.

    Args:
        xy: The polygon's vertices, x and y first in each row.

    Returns:
        The signed area, in square scene units.
    """
    x, y = xy[:, 0], xy[:, 1]
    return float((np.roll(x, -1) - x) @ (np.roll(y, -1) + y) / 2)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def shoelace_direction(xy: np.ndarray) -> str:
    """Which way a polygon runs around: "CW" (clockwise) if its
    [shoelace][manimgx.shoelace] area is positive, "CCW" (counterclockwise) otherwise.

    Args:
        xy: The polygon's vertices, x and y first in each row.

    Returns:
        "CW" or "CCW".
    """
    return "CW" if shoelace(xy) > 0 else "CCW"


def perpendicular_bisector(
    line: Point3DLike_Array, norm_vector: Vector3DLike = _OUT
) -> Point3D_Array:
    """Two points on the perpendicular bisector of a segment, in the plane perpendicular
    to a vector.

    Args:
        line: The segment's two ends.
        norm_vector: The normal of the plane the bisector lies in.

    Returns:
        The segment's midpoint plus and minus its direction crossed with
        `norm_vector`; for a unit normal, each a segment's length from the midpoint.
    """
    p1, p2 = np.asarray(line[0]), np.asarray(line[1])
    direction = np.cross(p1 - p2, np.asarray(norm_vector))
    m = midpoint(p1, p2)
    return np.array([m + direction, m - direction])


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def cross2d(a: np.ndarray, b: np.ndarray) -> npt.NDArray[np.float64] | float:
    """The z of the cross product of vectors in the xy plane: `a.x·b.y − a.y·b.x`.

    Args:
        a: A vector, or an (n, 2) array of them.
        b: Another, or as many.

    Returns:
        The number, or one per row.
    """
    if len(a.shape) == 2:
        return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    return a[0] * b[1] - b[0] * a[1]


@deprecated("use numpy: np.mean(points, axis=0)", category=None)
def center_of_mass(points: Point3D_Array) -> Point3D:
    """The average of points.

    Returns:
        Their mean.
    """
    return np.average(np.asarray(points), 0)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def angle_axis_from_quaternion(quaternion: np.ndarray) -> tuple[float, Vector3D]:
    """The angle and axis of a unit quaternion (w, x, y, z): the angle 2·arccos(w),
    taken from 2π when it is larger than π, and the axis (x, y, z), normalized.

    Args:
        quaternion: The unit quaternion.

    Returns:
        The angle, in radians, from 0 to π, and the axis.
    """
    axis = normalize(quaternion[1:])
    angle = 2 * np.arccos(quaternion[0])
    if angle > np.pi:
        angle = 2 * np.pi - angle
    return angle, axis


@deprecated("use numpy: 1 / (1 + np.exp(-x))", category=None)
def sigmoid(x: float) -> float:
    """The logistic function, 1 / (1 + e^(−x)): from 0 to 1, 1/2 at 0.

    Args:
        x: The number.
    """
    return 1.0 / (1 + np.exp(-x))


def complex_to_R3(complex_num: complex) -> Vec:
    """The point of a complex number: its real part as x, its imaginary part as y.

    Args:
        complex_num: The number.

    Returns:
        The point, with a z of 0.
    """
    return np.array((complex_num.real, complex_num.imag, 0))


def R3_to_complex(point: Point3D) -> complex:
    """The complex number of a point: x + iy (its z is ignored)."""
    return complex(*point[:2])


def complex_func_to_R3_func(
    complex_func: Callable[[complex], complex],
) -> Callable[[Point3D], Point3D]:
    """A function of complex numbers as a function of points: a point (x, y, z) goes
    where the function sends x + iy, with a z of 0.

    Args:
        complex_func: The function of complex numbers.

    Returns:
        The function of points.
    """
    return lambda p: complex_to_R3(complex_func(R3_to_complex(p)))


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def norm_squared(v: Vector3DLike) -> float:
    """A vector's length, squared.

    Args:
        v: The vector.

    Returns:
        The sum of the squares of its coordinates.
    """
    v = np.asarray(v)
    return float(np.dot(v, v))


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def rotation_matrix_transpose(angle: float, axis: Vector3DLike) -> MatrixMN:
    """The transpose of [rotation_matrix][manimgx.rotation_matrix]: the rotation by
    `-angle`.

    Args:
        angle: The angle, in radians.
        axis: The axis's direction.

    Returns:
        The 3×3 matrix.
    """
    return rotation_matrix(angle, axis).T


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def rotation_matrix_from_quaternion(quat: np.ndarray) -> MatrixMN:
    """The matrix of the rotation by a unit quaternion.

    Args:
        quat: The unit quaternion (w, x, y, z).

    Returns:
        The 3×3 rotation matrix.
    """
    w, x, y, z = quat
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def get_winding_number(points: Point3DLike_Array) -> float:
    """How many times the closed polygon through points winds counterclockwise around
    the origin, in the xy plane.

    Args:
        points: The polygon's vertices, in order; it closes from the last back to the
            first.

    Returns:
        The number of turns, negative for clockwise, and whole unless a side passes
        through the origin.
    """
    total = 0.0
    pts = np.asarray(points, dtype=float)
    for p1, p2 in zip(pts, np.roll(pts, -1, axis=0), strict=True):
        d_angle = angle_of_vector(p2) - angle_of_vector(p1)
        d_angle = ((d_angle + np.pi) % (2 * np.pi)) - np.pi
        total += d_angle
    return total / (2 * np.pi)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def quaternion_mult(*quats: Sequence[float] | npt.NDArray[np.float64]) -> list[float]:
    """The product of quaternions (w, x, y, z), in order: the first times the second,
    and so on.

    Args:
        *quats: The quaternions.

    Returns:
        The product as a list of four floats; (1, 0, 0, 0) for none.
    """
    result = [float(x) for x in quats[0]] if quats else [1.0, 0.0, 0.0, 0.0]
    for quat in quats[1:]:
        (w1, x1, y1, z1), (w2, x2, y2, z2) = result, (float(x) for x in quat)
        result = [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 + y1 * w2 + z1 * x2 - x1 * z2,
            w1 * z2 + z1 * w2 + x1 * y2 - y1 * x2,
        ]
    return result


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def quaternion_from_angle_axis(
    angle: float, axis: np.ndarray, axis_normalized: bool = False
) -> list[float]:
    """The unit quaternion (w, x, y, z) of a rotation about an axis.

    Raises ValueError for a zero axis: a turn about no axis is no turn at all.

    Args:
        angle: The angle, in radians.
        axis: The axis's direction.
        axis_normalized: Whether `axis` has length 1 already.

    Returns:
        The quaternion, cos(angle/2) followed by the axis times sin(angle/2).
    """
    unit = axis if axis_normalized else normalize(axis)
    if not np.any(unit):
        raise ValueError(f"a rotation's axis must not be zero, not {axis}")
    return [np.cos(angle / 2), *np.sin(angle / 2) * unit]


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def quaternion_conjugate(
    quaternion: Sequence[float] | npt.NDArray[np.float64],
) -> Vec:
    """A quaternion's conjugate: (w, −x, −y, −z), the inverse rotation of a unit one.

    Args:
        quaternion: The quaternion (w, x, y, z).
    """
    result = np.array(quaternion, dtype=float)
    result[1:] *= -1
    return result


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def rotation_matrix_transpose_from_quaternion(quat: np.ndarray) -> list[Vec]:
    """The transpose of the matrix of the rotation by a unit quaternion: its rows are
    where the x, y and z axes go.

    Args:
        quat: The unit quaternion (w, x, y, z).

    Returns:
        The three rows.
    """
    inverse = quaternion_conjugate(quat)
    return [
        np.array(quaternion_mult(quat, [0, *basis], inverse)[1:])
        for basis in np.identity(3)
    ]


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def thick_diagonal(dim: int, thickness: int = 2) -> npt.NDArray[np.uint8]:
    """A square matrix of ones in a band along its diagonal, and zeros elsewhere.

    Args:
        dim: How many rows and columns.
        thickness: The band's width: ones where the row and column differ by less.

    Returns:
        The matrix, of 8-bit integers.
    """
    rows = np.arange(dim).repeat(dim).reshape((dim, dim))
    return (np.abs(rows - rows.T) < thickness).astype("uint8")


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def normalize_along_axis(array: np.ndarray, axis: int) -> npt.NDArray[np.float64]:
    """Divide the vectors along an array's last axis by their lengths, in place (zero
    vectors are left as they are).

    Args:
        array: The array, of floats.
        axis: Its last axis (along another, the lengths are not matched to their
            vectors).

    Returns:
        The same array.
    """
    norms = np.sqrt((array * array).sum(axis))
    norms[norms == 0] = 1
    array /= np.repeat(norms, array.shape[axis]).reshape(array.shape)
    return array


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def earclip_triangulation(
    verts: Point3DLike_Array, ring_ends: Sequence[int]
) -> list[int]:
    """Triangles covering a polygon with holes, by ear clipping.

    Each hole is joined to the outline at their closest vertices, and ears are then
    clipped from the one ring, in order.

    Args:
        verts: The rings' vertices, one ring after another: the outline, then the holes
            (x and y count).
        ring_ends: Where each ring ends in `verts`: the index after its last vertex.

    Returns:
        The triangles, as indices into `verts`, three per triangle.
    """
    points = np.asarray(verts, dtype=float)[:, :2]
    rings = [
        list(range(a, b)) for a, b in zip([0, *ring_ends[:-1]], ring_ends, strict=True)
    ]

    def area(ring: list[int]) -> float:  # signed: positive counterclockwise
        x, y = points[ring].T
        return float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) / 2)

    def cross(o: int, a: int, b: int) -> float:
        (ax, ay), (bx, by) = points[a] - points[o], points[b] - points[o]
        return float(ax * by - ay * bx)

    outline = rings[0]
    for hole in rings[1:]:
        if np.sign(area(hole)) == np.sign(area(outline)):
            hole = hole[
                ::-1
            ]  # a hole winds against its outline, or the bridged ring crosses itself
        gaps = np.linalg.norm(points[outline][:, None] - points[hole][None], axis=2)
        i, j = np.unravel_index(int(np.argmin(gaps)), gaps.shape)
        outline = outline[: i + 1] + hole[j:] + hole[: j + 1] + outline[i:]
    turn = np.sign(area(outline)) or 1.0
    ring, triangles = list(outline), []
    while len(ring) > 3:
        for k in range(len(ring)):
            a, b, c = ring[k - 1], ring[k], ring[(k + 1) % len(ring)]
            if cross(a, b, c) * turn > 0 and not any(
                cross(a, b, q) * turn >= 0
                and cross(b, c, q) * turn >= 0
                and cross(c, a, q) * turn >= 0
                for q in ring
                if not any(np.allclose(points[q], points[v]) for v in (a, b, c))
            ):
                break
        else:
            k = 1  # no proper ear (degenerate input): clip anyway rather than loop forever
            a, b, c = ring[0], ring[1], ring[2]
        triangles += [a, b, c]
        del ring[k]
    return triangles + ring


class Polygon:
    """A polygon with holes, as [polylabel][manimgx.polylabel] reads it: its edges, its
    area and its centroid.

    Args:
        rings: Its rings, each closed (its first vertex repeated at its end): the
            outline, then any holes.
    """

    def __init__(self, rings: Sequence[Point2DLike_Array]) -> None:
        np_rings: list[Point2D_Array] = [np.asarray(ring) for ring in rings]
        csum = np.cumsum([ring.shape[0] for ring in np_rings])
        self.array: Point2D_Array = np.concatenate(np_rings, axis=0)
        self.start: Point2D_Array = np.delete(self.array, csum - 1, axis=0)
        self.stop: Point2D_Array = np.delete(self.array, csum % csum[-1], axis=0)
        self.diff: Point2D_Array = np.delete(
            np.diff(self.array, axis=0), csum[:-1] - 1, axis=0
        )
        self.norm: Point2D_Array = self.diff / np.einsum(
            "ij,ij->i", self.diff, self.diff
        ).reshape(-1, 1)
        x, y = (self.start[:, 0], self.start[:, 1])
        xr, yr = (self.stop[:, 0], self.stop[:, 1])
        self.area: float = 0.5 * (np.dot(x, yr) - np.dot(xr, y))
        if self.area:
            factor = x * yr - xr * y
            cx = np.sum((x + xr) * factor) / (6.0 * self.area)
            cy = np.sum((y + yr) * factor) / (6.0 * self.area)
            self.centroid = np.array([cx, cy])

    def compute_distance(self, point: Point2DLike) -> float:
        """How far a point is from the polygon's edges: positive inside, negative
        outside.

        Args:
            point: The point, x and y.

        Returns:
            The distance, in scene units.
        """
        scalars = np.einsum("ij,ij->i", self.norm, point - self.start)
        clips = np.clip(scalars, 0, 1).reshape(-1, 1)
        d: float = np.min(
            np.linalg.norm(self.start + self.diff * clips - point, axis=1)
        )
        return d if self.inside(point) else -d

    def inside(self, point: Point2DLike) -> bool:
        """Whether a point is inside the polygon or on its edges: a ray from it toward
        +x crosses the edges an odd number of times.

        Args:
            point: The point, x and y.
        """
        x, y = point
        x0, y0 = self.start[:, 0], self.start[:, 1]
        x1, y1 = self.stop[:, 0], self.stop[:, 1]
        on = (
            (np.minimum(x0, x1) <= x)
            & (x <= np.maximum(x0, x1))
            & (np.minimum(y0, y1) <= y)
            & (y <= np.maximum(y0, y1))
            & (np.abs((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)) <= 1e-8)
        )
        if on.any():
            return True
        with np.errstate(divide="ignore", invalid="ignore"):
            crossed = ((y0 > y) != (y1 > y)) & (
                x < (x1 - x0) / (y1 - y0) * (y - y0) + x0
            )
        return bool(np.count_nonzero(crossed) % 2)


class Cell:
    """A square cell of the search [polylabel][manimgx.polylabel] makes: its center `c`,
    its half-size `h`, its center's distance `d` from the polygon's edges, and `p`, the
    most any point of the cell can be from them.
    Cells are ordered for the search by decreasing `p`.

    Args:
        c: Its center, x and y.
        h: Half its side, in scene units.
    """

    def __init__(self, c: Point2DLike, h: float, polygon: Polygon) -> None:
        self.c: Point2D = np.asarray(c)
        self.h = h
        self.d = polygon.compute_distance(self.c)
        self.p = self.d + self.h * np.sqrt(2)

    def __lt__(self, other: Cell) -> bool:
        return self.p > other.p


def polylabel(rings: Sequence[Point3DLike_Array], precision: float = 0.01) -> Cell:
    """The pole of inaccessibility of a polygon: the point inside it farthest from its
    edges, where a label fits best.

    Args:
        rings: The polygon's rings, each closed (its first vertex repeated at its end):
            the outline, then any holes. Their x and y count.
        precision: How far, at most, the point found may be from the best, in its
            distance from the edges, in scene units.

    Returns:
        The cell found, whose `c` is the point (x and y) and `d` its distance from the
        nearest edge.
    """
    np_rings: list[Point2D_Array] = [np.asarray(ring)[:, :2] for ring in rings]
    polygon = Polygon(np_rings)
    mins = np.min(polygon.array, axis=0)
    maxs = np.max(polygon.array, axis=0)
    dims = maxs - mins
    s = np.min(dims)
    h = s / 2.0
    queue: list[Cell] = []
    xv, yv = np.meshgrid(np.arange(mins[0], maxs[0], s), np.arange(mins[1], maxs[1], s))
    for corner in np.vstack([xv.ravel(), yv.ravel()]).T:
        heapq.heappush(queue, Cell(corner + h, h, polygon))
    best = Cell(polygon.centroid, 0, polygon)
    bbox = Cell(mins + dims / 2, 0, polygon)
    if bbox.d > best.d:
        best = bbox
    # No inscribed circle is wider than the bounding box.
    if best.d >= h:
        return best
    directions = np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]])
    while queue:
        cell = heapq.heappop(queue)
        if cell.d > best.d:
            best = cell
        if cell.p - best.d > precision:
            h = cell.h / 2.0
            offsets = cell.c + directions * h
            for offset in offsets:
                heapq.heappush(queue, Cell(offset, h, polygon))
    return best


class SubFacet:
    """A face of a facet (an end of an edge, an edge of a triangle), equal to another of
    the same points. Its topology identity captures those coordinates at construction.
    """

    def __init__(self, coordinates: PointND_Array) -> None:
        self.coordinates = coordinates
        # Numeric tuples keep topology hashes independent of Python's byte-hash seed.
        self.points = frozenset(tuple(c.tolist()) for c in coordinates)

    def __hash__(self) -> int:
        return hash(self.points)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SubFacet):
            raise ValueError
        return self.points == other.points


class Facet:
    """A facet of a hull (an edge in two dimensions, a triangle in three): its points,
    its center, its outward normal and its subfacets.

    Args:
        coordinates: Its points, one per row.
        internal: A point inside the hull, which its normal points away from.
    """

    def __init__(self, coordinates: PointND_Array, internal: PointND) -> None:
        self.coordinates = coordinates
        self.center: PointND = np.mean(coordinates, axis=0)
        self.normal = self.compute_normal(internal)
        self.subfacets = frozenset(
            SubFacet(np.delete(self.coordinates, i, axis=0))
            for i in range(self.coordinates.shape[0])
        )

    def compute_normal(self, internal: PointND) -> PointND:
        """The facet's unit normal, pointing away from a point inside the hull.

        Args:
            internal: The point inside.
        """
        centered = self.coordinates - self.center
        _, _, vh = np.linalg.svd(centered)
        normal: PointND = vh[-1, :]
        normal /= np.linalg.norm(normal)

        # If the normal points towards the internal point, flip it!
        if np.dot(normal, self.center - internal) < 0:
            normal *= -1

        return normal

    def __hash__(self) -> int:
        return hash(self.subfacets)


class Horizon:
    """What a point outside a hull sees of it: the facets it sees, and the subfacets
    between those and the facets it doesn't."""

    def __init__(self) -> None:
        self.facets: set[Facet] = set()
        self.boundary: list[SubFacet] = []


@deprecated(
    "Manim CE's machinery for ConvexHull: use ConvexHull, or ConvexHull3D",
    category=None,
)
class QuickHull:
    """The convex hull of points, in two dimensions or more, by the Quickhull algorithm.

    [build][manimgx.QuickHull.build] computes it: the hull's facets (its edges in two
    dimensions, its triangles in three) are then those of `facets` not in `removed`.

    Args:
        tolerance: How far beyond a facet a point must be to count as outside it.
    """

    def __init__(self, tolerance: float = 1e-5) -> None:
        self.facets: list[Facet] = []
        self.removed: set[Facet] = set()
        self.outside: dict[Facet, tuple[PointND_Array | None, PointND | None]] = {}
        self.neighbors: dict[SubFacet, set[Facet]] = {}
        self.unclaimed: PointND_Array | None = None
        self.internal: PointND | None = None
        self.tolerance = tolerance

    def initialize(self, points: PointND_Array) -> None:
        """Start the hull as a simplex of extreme points, and share the points outside
        it among its facets; [build][manimgx.QuickHull.build] calls it first.

        Args:
            points: The points, one per row.
        """
        # The initial simplex from extreme points, each the farthest from the span of those before
        # (CE sampled it with an unseeded generator: the same input gave a different hull layout
        # on every run)
        chosen = [int(np.argmin(points[:, 0]))]
        while len(chosen) < points.shape[1] + 1:
            offsets = points - points[chosen[0]]
            if len(chosen) > 1:
                basis, _ = np.linalg.qr((points[chosen[1:]] - points[chosen[0]]).T)
                offsets = offsets - offsets @ basis @ basis.T
            chosen.append(int(np.argmax(np.linalg.norm(offsets, axis=1))))
        simplex = points[chosen]
        self.unclaimed = points
        new_internal: PointND = np.mean(simplex, axis=0)
        self.internal = new_internal

        # Build Simplex
        for c in range(simplex.shape[0]):
            facet = Facet(np.delete(simplex, c, axis=0), internal=new_internal)
            self.classify(facet)
            self.facets.append(facet)

        # Attach Neighbors
        for f in self.facets:
            for sf in f.subfacets:
                self.neighbors.setdefault(sf, set()).add(f)

    def classify(self, facet: Facet) -> None:
        """Give a new facet the points no facet has yet that lie beyond it, and among
        them the farthest, the next point to add; [build][manimgx.QuickHull.build] calls
        it for each facet it makes.
        """
        assert self.unclaimed is not None, (
            "Call .initialize() before using .classify()."
        )

        if not self.unclaimed.size:
            self.outside[facet] = (None, None)
            return

        # Compute Projections
        projections = (self.unclaimed - facet.center) @ facet.normal
        arg = np.argmax(projections)
        mask = projections > self.tolerance

        # Identify Eye and Outside Set
        eye = self.unclaimed[arg] if projections[arg] > self.tolerance else None
        outside = self.unclaimed[mask]
        self.outside[facet] = (outside, eye)
        self.unclaimed = self.unclaimed[~mask]

    def compute_horizon(self, eye: PointND, start_facet: Facet) -> Horizon:
        """What a point outside the hull sees of it, from a facet it sees: the hull
        grows to the point from the edge of what it sees.

        Args:
            eye: The point.
            start_facet: A facet it sees.

        Returns:
            The facets it sees and the subfacets bounding them.
        """
        horizon = Horizon()
        self._recursive_horizon(eye, start_facet, horizon)
        return horizon

    def _recursive_horizon(self, eye: PointND, facet: Facet, horizon: Horizon) -> bool:
        visible = np.dot(facet.normal, eye - facet.center) > 0
        if not visible:
            return False

        # If the eye is visible from the facet:
        # Label the facet as visible and cross each edge
        horizon.facets.add(facet)
        for subfacet in facet.subfacets:
            neighbor = (self.neighbors[subfacet] - {facet}).pop()
            # If the neighbor is not visible, then the edge shared must be on the boundary
            if neighbor not in horizon.facets and not self._recursive_horizon(
                eye, neighbor, horizon
            ):
                horizon.boundary.append(subfacet)
        return True

    def build(self, points: PointND_Array) -> None:
        """Compute the convex hull of points.

        Raises an exception for points in one dimension, or fewer than one more than
        their dimensions.

        Args:
            points: The points, one per row, each of two coordinates or more.
        """
        num, dim = points.shape
        if (dim == 0) or (num < dim + 1):
            raise ValueError("Not enough points supplied to build Convex Hull!")
        if dim == 1:
            raise ValueError("The Convex Hull of 1D data is its min-max!")

        self.initialize(points)

        # This helps the type checker.
        assert self.unclaimed is not None
        assert self.internal is not None

        while True:
            updated = False
            for facet in self.facets:
                if facet in self.removed:
                    continue
                _outside, eye = self.outside[facet]
                if eye is not None:
                    updated = True
                    horizon = self.compute_horizon(eye, facet)
                    for f in horizon.facets:
                        points_to_append = self.outside[f][0]
                        # TODO: is this always true?
                        assert points_to_append is not None
                        self.unclaimed = np.vstack((self.unclaimed, points_to_append))
                        self.removed.add(f)
                        for sf in f.subfacets:
                            self.neighbors[sf].discard(f)
                            if self.neighbors[sf] == set():
                                del self.neighbors[sf]
                    for sf in horizon.boundary:
                        nf = Facet(
                            np.vstack((sf.coordinates, eye)), internal=self.internal
                        )
                        self.classify(nf)
                        self.facets.append(nf)
                        for nsf in nf.subfacets:
                            self.neighbors.setdefault(nsf, set()).add(nf)
            if not updated:
                break


def interpolate[T](start: T, end: T, alpha: float | np.ndarray) -> T:
    """The value a fraction of the way from one value to another: (1 − alpha)·start +
    alpha·end.

    Args:
        start: The value at 0: a number or an array.
        end: The value at 1, of the same kind.
        alpha: How far from `start` to `end`: 0 gives `start`, 1 `end`, and beyond them
            it goes on along the line; an array gives one value per entry.

    Returns:
        The value between.
    """
    return (1 - alpha) * start + alpha * end  # pyright: ignore[reportOperatorIssue]  # ty: ignore[unsupported-operator]  # T: numbers, arrays


def integer_interpolate(start: float, end: float, alpha: float) -> tuple[int, float]:
    """Which whole step from `start` toward `end` a fraction falls in, and how far into
    it: for `start` 0 and `end` n, which of n curves, and where along it.

    Args:
        start: The first step's start, a whole number.
        end: The last step's end, a whole number past `start`.
        alpha: How far from `start` to `end`, from 0 to 1.

    Returns:
        The step, from `start` to `end` − 1, and the fraction of it, from 0 to 1: step +
        fraction is `start` + (`end` − `start`)·`alpha`; at 1, the last step, wholly.
    """
    if alpha >= 1:
        return int(end - 1), 1.0
    if alpha <= 0:
        return int(start), 0.0
    reached = (end - start) * alpha
    # whole steps down (floor, not toward 0), and never past the last, however it rounds
    whole = min(math.floor(reached), int(end - start) - 1)
    return int(start) + whole, reached - whole


def inverse_interpolate(start: float, end: float, value: float) -> float:
    """How far a value is from one value to another: the inverse of
    [interpolate][manimgx.interpolate].

    Args:
        start: The value at 0.
        end: The value at 1.

    Returns:
        The fraction, (value − start) / (end − start).
    """
    return float(np.true_divide(value - start, end - start))


_NPPCC = 4


def sample(function: Callable[..., object], *args: np.ndarray) -> np.ndarray:
    """Evaluate a function at every point of a grid of arguments.

    `args` are arrays of one shape, one per argument of `function`. The function is
    called once on the whole arrays, as most numeric functions allow, and checked
    against single calls at the first, middle and last points; a function written for
    one value at a time (`math.cos`, `if t < 0`) raises or differs there, and is then
    called once per point.

    Args:
        function: The function, from the arguments to a value.
        *args: The arguments' values: arrays of one shape.

    Returns:
        The values: an array of the arguments' shape, followed by a value's.
    """
    shape, n = args[0].shape, args[0].size
    flat = [a.ravel() for a in args]
    try:
        out = np.asarray(function(*args), dtype=float)
        k = len(shape)
        if out.shape[:k] != shape and out.shape[-k:] == shape:  # values first
            out = np.moveaxis(out, range(out.ndim - k, out.ndim), range(k))
        values = out.reshape(n, -1)
        for i in {0, n // 2, n - 1}:
            one = np.asarray(function(*(float(f[i]) for f in flat)), dtype=float)
            if not np.allclose(values[i], one.ravel(), rtol=1e-9, atol=1e-12):
                raise ValueError(i)
        return out
    except Exception:  # not vectorizable: one point at a time
        out = np.array(
            [function(*(float(f[i]) for f in flat)) for i in range(n)], float
        )
        return out.reshape(*shape, *out.shape[1:])


def subpath_ranges(
    points: Point3D_Array, atol: float, dims: int = 3
) -> list[tuple[int, int, bool]]:
    """(start, end, closed) per subpath: one starts where a curve does not begin at the previous
    curve's end (CE's rule); it is closed when its ends coincide."""
    n = len(points) - len(points) % _NPPCC
    if n < _NPPCC:
        return []
    ends, starts = (
        points[_NPPCC - 1 : n - 1 : _NPPCC, :dims],
        points[_NPPCC:n:_NPPCC, :dims],
    )
    breaks = ~np.all(np.abs(ends - starts) <= atol + 1e-5 * np.abs(starts), axis=1)
    splits = [0, *((np.flatnonzero(breaks) + 1) * _NPPCC).tolist(), n]
    return [
        (a, b, bool(np.allclose(points[a, :dims], points[b - 1, :dims], atol=atol)))
        for a, b in itertools.pairwise(splits)
        if b - a >= _NPPCC
    ]


def _pathops() -> ModuleType:
    """skia-pathops, which finds the regions (imported when first needed: it has no build for
    Pyodide, so in the browser these shapes can't be made)."""
    try:
        import pathops
    except ImportError as error:
        raise ImportError(
            "Union, Difference, Intersection and Exclusion need skia-pathops, which has"
            " no build for the browser (Pyodide) yet"
        ) from error
    return pathops


def _to_path(points: Point3D_Array, tolerance: float) -> SkiaPath:
    """An outline's planar path, with the same complete subpaths and closure tolerance."""
    path = _pathops().Path()
    if not np.all(np.isfinite(points)):
        return path
    for start, end, closed in subpath_ranges(points, tolerance, dims=2):
        path.moveTo(*points[start, :2])
        for _p0, p1, p2, p3 in points[start:end].reshape(-1, 4, 3):
            path.cubicTo(*p1[:2], *p2[:2], *p3[:2])
        if closed:
            path.close()
    return path


def bezier(points: Point3D_Array) -> Callable[[float], Point3D]:
    """A cubic Bézier curve as a function: from its first control point at 0 to its last
    at 1.

    Args:
        points: Its four control points: anchor, handle, handle, anchor.

    Returns:
        A function of the curve's parameter, from 0 to 1, giving its point there.
    """
    P = np.asarray(points)

    def cubic(t: float) -> Point3D:
        mt = 1 - t
        return mt**3 * P[0] + 3 * t * mt**2 * P[1] + 3 * t**2 * mt * P[2] + t**3 * P[3]

    return cubic


def partial_bezier_points(points: Point3D_Array, a: float, b: float) -> Point3D_Array:
    """The control points of part of a cubic Bézier curve, from its parameter `a` to
    `b`.

    Args:
        points: The curve's four control points.
        a: Where the part starts, from 0 to 1.
        b: Where it ends, from `a` to 1.

    Returns:
        The part's four control points.
    """
    if a == 1:
        arr = np.array(points)
        arr[:] = arr[-1]
        return arr
    if b == 0:
        arr = np.array(points)
        arr[:] = arr[0]
        return arr
    ma, mb = 1 - a, 1 - b
    a2, b2, ma2, mb2 = a * a, b * b, ma * ma, mb * mb
    a3, b3, ma3, mb3 = a2 * a, b2 * b, ma2 * ma, mb2 * mb
    m = np.array(
        [
            [ma3, 3 * ma2 * a, 3 * ma * a2, a3],
            [ma2 * mb, 2 * ma * a * mb + ma2 * b, a2 * mb + 2 * ma * a * b, a2 * b],
            [ma * mb2, a * mb2 + 2 * ma * mb * b, 2 * a * mb * b + ma * b2, a * b2],
            [mb3, 3 * mb2 * b, 3 * mb * b2, b3],
        ]
    )
    return m @ np.asarray(points)


_SUBDIVISION: Memo[int, np.ndarray] = Memo(1 << 10)


def _subdivision_matrix(n: int | np.integer) -> np.ndarray:
    m = _SUBDIVISION.get(n)
    if m is not None:
        return m
    n = int(n)
    m = np.empty((4 * n, 4))
    for i in range(n):
        i2, i3 = i * i, i * i * i
        ip1 = i + 1
        ip12, ip13 = ip1 * ip1, ip1 * ip1 * ip1
        nmi = n - i
        nmi2, nmi3 = nmi * nmi, nmi * nmi * nmi
        nmim1 = nmi - 1
        nmim12, nmim13 = nmim1 * nmim1, nmim1 * nmim1 * nmim1
        m[4 * i : 4 * (i + 1)] = [
            [nmi3, 3 * nmi2 * i, 3 * nmi * i2, i3],
            [
                nmi2 * nmim1,
                2 * nmi * nmim1 * i + nmi2 * ip1,
                nmim1 * i2 + 2 * nmi * i * ip1,
                i2 * ip1,
            ],
            [
                nmi * nmim12,
                nmim12 * i + 2 * nmi * nmim1 * ip1,
                2 * nmim1 * i * ip1 + nmi * ip12,
                i * ip12,
            ],
            [nmim13, 3 * nmim12 * ip1, 3 * nmim1 * ip12, ip13],
        ]
    m /= n**3
    return _SUBDIVISION.keep(n, m)


def subdivide_bezier(points: Point3D_Array, n_divisions: int) -> Point3D_Array:
    """Split a cubic Bézier curve into curves over equal stretches of its parameter.

    Args:
        points: The curve's four control points.
        n_divisions: How many curves.

    Returns:
        Their control points, four per curve, one curve after another.
    """
    points = np.asarray(points)
    if n_divisions == 1:
        return points
    return _subdivision_matrix(n_divisions) @ points


def bezier_remap(tuples: np.ndarray, new_count: int) -> np.ndarray:
    """Split cubic Bézier curves into more, their shape unchanged.

    Each curve is split over equal stretches of its parameter, the new curves spread
    among the curves as evenly as can be: curve i of m gets the new curves j of
    `new_count` with j·m // `new_count` = i (4 curves into 6: 2, 1, 2, 1).

    Args:
        tuples: The curves' control points: an array of shape (curves, 4, dimensions).
        new_count: How many curves to make, at least as many as there are.

    Returns:
        The new curves' control points, an array of shape (new_count, 4, dimensions).
    """
    tuples = np.asarray(tuples)
    count, nppc, dim = tuples.shape
    if new_count == count:
        return np.array(tuples, dtype=float, order="C")
    if count and new_count % count == 0:
        pieces = _subdivision_matrix(new_count // count) @ tuples
        return np.asarray(pieces, dtype=float).reshape(new_count, nppc, dim)
    starts = (np.arange(count + 1) * new_count + count - 1) // count
    out = np.empty((new_count, nppc, dim))
    for curve, start, end in zip(tuples, starts[:-1], starts[1:], strict=True):
        factor = end - start
        out[start:end] = subdivide_bezier(curve, factor).reshape(factor, nppc, dim)
    return out


def is_closed(points: Point3D_Array) -> bool:
    """Whether points end where they start: the last equal to the first, within 1e-8
    plus 1e-5 of the first's coordinates.
    """
    # np.isclose's tolerances, independent of the sign
    start, end = points[0], points[-1]
    return bool(np.all(np.abs(end - start) <= 1e-08 + 1e-05 * np.abs(start)))


def get_smooth_cubic_bezier_handle_points(
    anchors: Point3D_Array,
) -> tuple[Point3D_Array, Point3D_Array]:
    """The handles of a smooth curve through anchors: a cubic spline, bending with no
    change of curvature at any anchor, and closed smoothly if the last anchor is the
    first.

    Args:
        anchors: The anchors, in order.

    Returns:
        Each curve's first handles and second handles, as two arrays with one row per
        curve (one fewer than the anchors).
    """
    A = np.asarray(anchors, dtype=float)
    n = A.shape[0]
    if n == 1:
        return np.zeros((0, A.shape[1])), np.zeros((0, A.shape[1]))
    if n == 2:
        return (
            interpolate(A[0], A[1], 1 / 3)[None],
            interpolate(A[0], A[1], 2 / 3)[None],
        )
    closed = is_closed(A)
    if n > _SMOOTHING_UP_TO:
        return _smooth_closed(A) if closed else _smooth_open(A)
    to_h1, to_h2 = _smoothing(n, closed)
    return to_h1 @ A, to_h2 @ A


# anchors; beyond, the solve itself (linear time) beats a dense map
_SMOOTHING_UP_TO = 256


@forgets
@functools.lru_cache(maxsize=64)
def _smoothing(n: int, closed: bool) -> tuple[np.ndarray, np.ndarray]:
    """(K1, K2): smooth handles are K1·A and K2·A, maps that depend only on the number of anchors
    (the solve, run once on the identity)."""
    k1, k2 = (_smooth_closed if closed else _smooth_open)(np.eye(n))
    k1.flags.writeable = k2.flags.writeable = False
    return k1, k2


def _smooth_closed(A: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    N, dim = A.shape[0] - 1, A.shape[1]
    cp, up = np.empty(N - 1), np.empty(N - 1)
    cp[0], up[0] = 1 / 3, 1 / 3
    for i in range(1, N - 1):
        cp[i] = 1 / (4 - cp[i - 1])
        up[i] = -cp[i] * up[i - 1]
    cp_last = 1 / (3 - cp[N - 2])
    up_last = cp_last * (1 - up[N - 2])
    q = np.empty((N, dim))
    q[N - 1] = up_last
    for i in range(N - 2, -1, -1):
        q[i] = up[i] - cp[i] * q[i + 1]
    Dp = np.empty((N, dim))
    AUX = 4 * A[:N] + 2 * A[1:]
    Dp[0] = AUX[0] / 3
    for i in range(1, N - 1):
        Dp[i] = cp[i] * (AUX[i] - Dp[i - 1])
    Dp[N - 1] = cp_last * (AUX[N - 1] - Dp[N - 2])
    Y = Dp
    for i in range(N - 2, -1, -1):
        Y[i] = Dp[i] - cp[i] * Y[i + 1]
    H1 = Y - 1 / (1 + q[0] + q[N - 1]) * q * (Y[0] + Y[N - 1])
    H2 = np.empty((N, dim))
    H2[: N - 1] = 2 * A[1:N] - H1[1:N]
    H2[N - 1] = 2 * A[N] - H1[0]
    return H1, H2


def _smooth_open(A: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    N, dim = A.shape[0] - 1, A.shape[1]
    cp = np.empty(N - 1)
    cp[0] = 0.5
    for i in range(1, N - 1):
        cp[i] = 1 / (4 - cp[i - 1])
    Dp = np.empty((N, dim))
    Dp[0] = 0.5 * A[0] + A[1]
    AUX = 4 * A[1 : N - 1] + 2 * A[2:N]
    for i in range(1, N - 1):
        Dp[i] = cp[i] * (AUX[i - 1] - Dp[i - 1])
    Dp[N - 1] = 1 / (7 - 2 * cp[N - 2]) * (8 * A[N - 1] + A[N] - 2 * Dp[N - 2])
    H1 = Dp
    for i in range(N - 2, -1, -1):
        H1[i] = Dp[i] - cp[i] * H1[i + 1]
    H2 = np.empty((N, dim))
    H2[: N - 1] = 2 * A[1:N] - H1[1:N]
    H2[N - 1] = 0.5 * (A[N] + H1[N - 1])
    return H1, H2


type Floats = npt.NDArray[np.float64]
"""A NumPy array of floats."""
type Coefficients = tuple[Floats, Floats, Floats]  # Lₛ, Lₑ, k
"""A path's rule at one moment: the 3×3 matrices Lₛ and Lₑ and the vector k that take
each point to Lₛ·start + Lₑ·end + k."""
type Step = tuple[float, Floats, Floats] | Floats | Callable[[float], Floats]
"""A step of a motion: a turn (an angle, an axis and a pivot, a point of the object as
it began), a move by a vector, or a move along a curve (a function of α giving where the
object has been carried at α)."""

STRAIGHT_PATH_THRESHOLD: Final = 0.01
"""The smallest angle, in radians, [path_along_arc][manimgx.path_along_arc] and
[spiral_path][manimgx.spiral_path] turn through: with less, they are the
[straight path][manimgx.straight_path]."""
_PATH_AXIS: Final = np.array([0.0, 0.0, 1.0])
_EYE: Final = np.eye(3)
_ZERO: Final = np.zeros(3)


def _cross(axis: Floats) -> Floats:
    """K with K·v = axis × v."""
    x, y, z = axis
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


@dataclass(frozen=True, slots=True, eq=False)
class Path:
    """How the points of a shape travel in a transform, from where they start to where
    they end, as a value.

    A path takes each point to Lₛ·start + Lₑ·end + k, where Lₛ, Lₑ and k depend on the
    animation's progress α alone: so a shape moves without its points being touched.
    Call it as `path(start, end, alpha)`, on arrays of points; the functions below make
    the paths ManimGX provides.

    Args:
        kind: What the path is. "motion": the shape is carried by the motion G of its
            `steps` while it changes along straight lines in the moving frame,
            G(α)·((1 − α)·start + α·G(1)⁻¹·end); with no steps, the straight path.
            "arc": each point travels along a circular arc from its start to its end,
            turning through `angle` (and at a steady rate along `axis`, if its ends
            differ along it). "spiral": each point spirals out from its start to
            its end, start + α·R((α − 1)·`angle`)·(end − start).
        angle: The angle an "arc" or "spiral" path turns through, in radians,
            counterclockwise about `axis`.
        axis: The axis the path turns about.
        steps: The steps of a "motion" path, taken in order: each a move (a vector), a
            move along a curve, or a turn about a pivot.
    """

    kind: Literal["motion", "arc", "spiral"] = "motion"
    angle: float = 0.0
    axis: Floats = field(default_factory=lambda: _PATH_AXIS.copy())
    steps: tuple[Step, ...] = ()
    _end: list[Floats] = field(default_factory=list, init=False, repr=False)  # G(1)

    @deprecated("ManimGX's machinery: a transform calls it", category=None)
    def coefficients(self, alpha: float) -> Coefficients:
        """The path's rule at a moment: each point goes to Lₛ·start + Lₑ·end + k.

        Args:
            alpha: The animation's progress, from 0 to 1.

        Returns:
            The 3×3 matrices Lₛ and Lₑ, and the vector k.
        """
        if self.kind == "motion":
            if not self.steps:
                return (1 - alpha) * _EYE, alpha * _EYE, _ZERO
            if not self._end:
                self._end.append(self.motion(1.0))
            g, end = self.motion(alpha), self._end[0]
            le = alpha * g[:3, :3] @ end[:3, :3].T
            return (
                (1 - alpha) * g[:3, :3],
                le,
                g[:3, 3] - le @ end[:3, 3],
            )
        if self.kind == "spiral":
            rot = rotation_matrix((alpha - 1) * self.angle, self.axis)
            return _EYE - alpha * rot, alpha * rot, _ZERO
        # across the axis, an arc about the center; along it, a steady move (the turn and
        # (I − R) leave a point's height along the axis alone, so it is moved apart)
        rot = rotation_matrix(alpha * self.angle, self.axis)
        along = alpha * np.outer(self.axis, self.axis)
        if self.angle == np.pi:
            cs = ce = 0.5 * _EYE
        else:
            k = _cross(self.axis) / (2 * np.tan(self.angle / 2))
            cs, ce = 0.5 * _EYE - k, 0.5 * _EYE + k
        return (_EYE - rot) @ cs + rot - along, (_EYE - rot) @ ce + along, _ZERO

    @deprecated("ManimGX's machinery: a transform calls it", category=None)
    def motion(self, alpha: float) -> Floats:
        """The motion the path's steps have carried the shape by at a moment.

        Args:
            alpha: The animation's progress, from 0 to 1.

        Returns:
            The 4×4 affine matrix G(α).
        """
        return carried((step, alpha) for step in self.steps)

    def __call__(
        self, start: Point3D_Array, end: Point3D_Array, alpha: float
    ) -> Point3D_Array:
        ls, le, k = self.coefficients(alpha)
        return start @ ls.T + end @ le.T + k


@deprecated("ManimGX's machinery: a transform calls it", category=None)
def carried(steps: Iterable[tuple[Step, float]]) -> Floats:
    """The motion of steps taken in order, each as far as its own fraction.

    A move goes that fraction of its vector, and a move along a curve to where the curve
    has carried the object at that fraction; a turn turns through that fraction of its
    angle, about its pivot where the steps before it have carried the pivot.

    Args:
        steps: The steps (see [Step][manimgx.Step]), each with its fraction, from 0 to
            1.

    Returns:
        The 4×4 affine matrix of the motion.
    """
    g = np.eye(4)
    for step, alpha in steps:
        if isinstance(step, np.ndarray):
            g[:3, 3] += alpha * step
        elif isinstance(step, tuple):
            angle, axis, pivot = step
            turn = rotation_matrix(alpha * angle, axis)
            p = g[:3, :3] @ pivot + g[:3, 3]
            g[:3] = turn @ g[:3]
            g[:3, 3] += p - turn @ p
        else:
            g[:3, 3] += step(alpha) - step(0.0)
    return g


def _unit(axis: Vector3DLike) -> Floats:
    unit = normalize(axis)
    if not unit.any():
        raise ValueError(f"a path's axis must not be zero, not {axis}")
    return unit


def straight_path() -> Path:
    """The straight path: each point goes along the line from its start to its end, as
    a transform moves points by default.
    """
    return Path()


def path_along_arc(arc_angle: float, axis: Vector3DLike = _PATH_AXIS) -> Path:
    """A path along arcs: each point travels along a circular arc from its start to its
    end, turning through an angle, as a transform's `path_arc` makes it move.

    Args:
        arc_angle: The angle each arc turns through, in radians, counterclockwise about
            `axis`; smaller in size than
            [STRAIGHT_PATH_THRESHOLD][manimgx.STRAIGHT_PATH_THRESHOLD], the straight
            path.
        axis: The axis the arcs turn about.
    """
    if abs(arc_angle) < STRAIGHT_PATH_THRESHOLD:
        return straight_path()
    return Path("arc", arc_angle, _unit(axis))


def path_along_circles(
    arc_angle: float,
    centers: Point3DLike | Point3DLike_Array,
    axis: Vector3DLike = _PATH_AXIS,
) -> PathFunc:
    """A path about centers: each point turns about its center through an angle while
    it moves from its start to its end, as a transform's `path_arc_centers` makes it
    move.

    With one center, the shape turns about it as a whole, as a [Path][manimgx.Path];
    with a center per point, each point turns about its own, as a plain function of
    `(start, end, alpha)`.

    Args:
        arc_angle: The angle, in radians, counterclockwise about `axis`.
        centers: One center, or one per point, in scene coordinates.
        axis: The axis the points turn about.
    """
    unit_axis = _unit(axis)
    points: Floats = np.asarray(centers, dtype=np.float64)
    if points.ndim == 1:
        return Path(steps=((arc_angle, unit_axis, points),))

    def path(start: Point3D_Array, end: Point3D_Array, alpha: float) -> Point3D_Array:
        detransformed = (
            points + (end - points) @ rotation_matrix(-arc_angle, unit_axis).T
        )
        rot = rotation_matrix(alpha * arc_angle, unit_axis)
        return points + ((1 - alpha) * start + alpha * detransformed - points) @ rot.T

    return path


def clockwise_path() -> Path:
    """A path along half circles, clockwise: each point turns through π on its way from
    its start to its end.
    """
    return path_along_arc(-np.pi)


def counterclockwise_path() -> Path:
    """A path along half circles, counterclockwise: each point turns through π on its
    way from its start to its end.
    """
    return path_along_arc(np.pi)


def spiral_path(angle: float, axis: Vector3DLike = _PATH_AXIS) -> Path:
    """A spiral path: each point spirals out from its start to its end, its offset from
    its start growing as it turns counterclockwise through `angle` (for a positive
    angle) into line with its end.

    Args:
        angle: How far each point turns, in radians, about `axis`; smaller in size than
            [STRAIGHT_PATH_THRESHOLD][manimgx.STRAIGHT_PATH_THRESHOLD], the straight
            path.
        axis: The axis the points turn about.
    """
    if abs(angle) < STRAIGHT_PATH_THRESHOLD:
        return straight_path()
    return Path("spiral", angle, _unit(axis))


type Matrix = Floats  # 3×4: [linear 3×3 | translation]
type Term = tuple[Matrix, "Shape"]

IDENTITY: Final = np.hstack([np.eye(3), np.zeros((3, 1))])
IDENTITY.flags.writeable = False  # a shape's placement, shared
CANONICAL: Final = 1024  # the most points of a shape reduced to a canonical form
_T: Final = np.linspace(0.0, 1.0, 10)[:, None]
_BERNSTEIN: Final = np.hstack(
    [(1 - _T) ** 3, 3 * (1 - _T) ** 2 * _T, 3 * (1 - _T) * _T**2, _T**3]
)


class Shape:
    """Immutable control points (n × 3). Content-addressed, so equal shapes share GPU memory."""

    __slots__ = ("_affine", "_boxes", "_key", "array", "log")

    def __init__(self, array: Floats, log: Log | None = None) -> None:
        array.flags.writeable = False
        self.array: Floats = array
        # the append-only points this shape is a prefix of (a growing path)
        self.log = log
        self._key: int | None = None
        self._affine: tuple[int, Floats, Matrix] | None = None
        self._boxes: dict[bool, Floats] | None = None

    def box(self, curves: bool) -> Floats:
        """(2, 3): the box of what the points make — for a path (`curves`), its curves' tight box
        (`curve_box`). Kept, as the shape never changes, and read-only: a value."""
        boxes = self._boxes
        if boxes is None:
            boxes = self._boxes = {}
        box = boxes.get(curves)
        if box is None:
            box = boxes[curves] = _frozen(extent(self.array, curves))
        return box

    def extended(self, rows: Floats) -> Shape:
        """This shape with rows appended — in place, when it is its log's longest prefix (a
        growing path costs what it grows); else into a log of its own."""
        log = self.log
        if log is None or log.length != len(self.array):
            log = Log(self.array)
        return log.extended(rows)

    @property
    def key(self) -> int:
        """Content address; shapes equal to 1e-9 are the same shape."""
        if self._key is None:
            self._key = digest(
                str(self.array.shape).encode(), np.round(self.array, 9).tobytes()
            )
        return self._key

    @property
    def affine(self) -> tuple[int, Floats, Matrix]:
        """(key, canonical points C, A) with the shape = A·C: C names its affine class (every segment,
        circle or triangle is one), uploaded once, so a shape that only moves, turns, scales or shears is
        never uploaded again. A has zero columns where the shape is flat. A shape of more than
        CANONICAL points is not reduced to a canonical form, which would cost about what uploading
        it does: it is an affine image of the last such shape of its size, if it is one (a surface
        raised, turned or moved by setting its points), or else its own class (C, its points; A,
        the identity), which its key finds again if it recurs as itself."""
        if self._affine is None:
            if len(self.array) > CANONICAL:
                self._affine = _big_class(self)
                return self._affine
            # equal content, seen before: its class and place
            self._affine = _CLASSES.recall(self.key, lambda: _affine_class(self.array))
        return self._affine

    def __deepcopy__(self, memo: dict[int, object]) -> Shape:
        return self


_CLASSES: Memo[int, tuple[int, Floats, Matrix]] = Memo(1 << 14)  # content → class
# (n, 3) → the class of the last shape of n > CANONICAL points given a class of its own
_LAST: Memo[tuple[int, ...], tuple[int, Floats, Matrix]] = Memo(1 << 6)
_LOGS = itertools.count(1)


def _big_class(shape: Shape) -> tuple[int, Floats, Matrix]:
    """A shape of more than CANONICAL points: the last such shape's class if it is an affine image of
    that shape's points, placed by the map; else a class of its own."""
    last = _LAST.get(shape.array.shape)
    if last is not None:
        a = _affine_image(last[1], shape.array)
        if a is not None:
            return last[0], last[1], a
    return _LAST.keep(shape.array.shape, (shape.key, shape.array, IDENTITY))


def _affine_image(base: Floats, points: Floats) -> Matrix | None:
    """The affine map A (3×4) with points = A·base, if there is one to 1e-9 of their size: the
    identity for the same points (not a fit, which would be off by rounding); else fitted at 16
    points spread along them (where a shape that is not one fails), then checked at every
    point."""
    if unchanged(points, base):
        return IDENTITY
    probe = np.linspace(0, len(base) - 1, 16).astype(int)
    rows = np.hstack([base[probe], np.ones((len(probe), 1))])
    fit = np.linalg.lstsq(rows, points[probe], rcond=None)[0]  # points ≈ [base 1]·fit
    tolerance = 1e-9 * (1.0 + np.abs(points[probe]).max())
    if np.abs(rows @ fit - points[probe]).max() > tolerance:
        return None
    if np.abs(base @ fit[:3] + fit[3] - points).max() > tolerance:
        return None
    return np.ascontiguousarray(fit.T)


class Log:
    """Control points that only grow: every prefix is a shape sharing the array, and appending to the
    longest writes in place, so a traced path grows by a curve, not by a copy."""

    __slots__ = ("array", "id", "length")

    def __init__(self, rows: Floats) -> None:
        self.array = np.empty((max(64, 2 * len(rows)), 3))
        self.array[: len(rows)] = rows
        self.length = len(rows)
        self.id = next(_LOGS)

    def extended(self, rows: Floats) -> Shape:
        end = self.length + len(rows)
        if end > len(self.array):
            grown = np.empty((2 * end, 3))
            grown[: self.length] = self.array[: self.length]
            self.array = grown
        self.array[self.length : end] = rows
        self.length = end
        return Shape(self.array[:end], self)


def _affine_class(points: Floats) -> tuple[int, Floats, Matrix]:
    """Center and whiten the points (unit covariance in the subspace they span), then fix the
    remaining rotation by the points themselves: the first farthest point on +x, the first farthest
    from that line in the +y half-plane, then +z (ties within 1e-6 keep their order). Canonical
    points are O(1), well within float32."""
    n = len(points)
    if n == 0:
        return digest(str(points.shape).encode()), points, IDENTITY.copy()
    center = points.mean(axis=0)
    d = points - center
    values, vectors = np.linalg.eigh(d.T @ d / n)
    # a direction thinner than 1e-6 of the shape's size is flat
    spanned = values > values[-1] * 1e-12 if values[-1] > 0 else values > 1.0
    rank = int(spanned.sum())
    canonical = np.zeros_like(points)
    linear = np.zeros((3, 3))
    if rank:
        roots = np.sqrt(values[spanned])
        x = d @ (vectors[:, spanned] / roots)  # whitened: n × rank
        frame = np.zeros((rank, rank))
        rest = x
        for axis in range(rank):
            norms = np.einsum("ij,ij->i", rest, rest)
            pick = int(np.argmax(norms >= norms.max() * (1 - 1e-6)))
            frame[axis] = rest[pick] / np.sqrt(norms[pick])
            rest = rest - np.outer(rest @ frame[axis], frame[axis])
        canonical[:, :rank] = x @ frame.T
        linear[:, :rank] = (vectors[:, spanned] * roots) @ frame.T
    canonical.flags.writeable = False
    key = digest(  # + 0.0: no negative zeros
        str(points.shape).encode(), (np.round(canonical, 7) + 0.0).tobytes()
    )
    return key, canonical, np.hstack([linear, center[:, None]])


_DEFINED: Memo[tuple[object, ...], Shape] = Memo(1 << 12)


def defined(definition: tuple[object, ...], make: Callable[[], Floats]) -> Shape:
    """The shape a definition names (`("arc", start, angle, n)`), made once and shared — with its
    affine class and upload — by every mobject that draws it."""
    return _DEFINED.recall(definition, lambda: Shape(np.array(make(), dtype=float)))


SEGMENT: Final = Shape(
    np.array([[0.0, 0, 0], [1 / 3, 0, 0], [2 / 3, 0, 0], [1.0, 0, 0]])
)


def _frozen(array: Floats) -> Floats:
    """`array`, read-only: what is cached is handed out as a value."""
    array.setflags(write=False)  # (cheaper than `flags.writeable`: no flags object)
    return array


def curve_box(points: Floats) -> Floats:
    """(2, D): the tight box of cubic Bézier curves (control points in fours). The anchors lie on
    the curves, and each curve lies in its control points' hull, so the anchors' box is tight
    unless a handle leaves it; only such curves are solved for their turning points: per
    coordinate, the roots of the derivative, a quadratic (solved without cancellation, so a
    vanishing leading term is harmless). Any parameter in [0, 1] is a point of the curve, so a
    clipped or spurious root is harmless too."""
    ends = np.concatenate([points[0::4], points[3::4]])
    lo, hi = ends.min(axis=0), ends.max(axis=0)
    p = points.reshape(-1, 4, points.shape[-1])
    p = p[((p < lo) | (p > hi)).any(axis=(1, 2))]
    if len(p) == 0:
        return np.array([lo, hi])
    p0, p1, p2, p3 = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
    c = p1 - p0  # B'(t)/3 = a t² + 2 h t + c, per coordinate
    h = p2 - p1 - c
    a = p3 - p0 - 3 * (p2 - p1)
    q = -(h + np.copysign(np.sqrt(np.maximum(h * h - a * c, 0)), h))  # roots q/a, c/q
    t = np.clip([q / np.where(a == 0, 1, a), c / np.where(q == 0, 1, q)], 0, 1)
    turns = p0 + t * (3 * c + t * (3 * h + t * a))  # B(t), by Horner
    return np.array(
        [np.minimum(lo, turns.min(axis=(0, 1))), np.maximum(hi, turns.max(axis=(0, 1)))]
    )


def extent(points: Floats, curves: bool) -> Floats:
    """(2, D): the box of what the points make: a path's (`curves`: complete cubic curves) is its
    curves' tight box, anything else's its points'."""
    if curves and len(points) and len(points) % 4 == 0:
        return curve_box(points)
    return np.array([points.min(axis=0), points.max(axis=0)])


def placed_box(m: Matrix, shape: Shape, curves: bool) -> Floats:
    """(2, 3): the box of `shape` placed by `m`. A map along the axes keeps each coordinate's
    extremes: there it is the shape's own box, mapped; else the placed points' box."""
    linear = m[:, :3]
    d = linear.diagonal()
    if np.count_nonzero(linear) == np.count_nonzero(d):  # along the axes
        ends = shape.box(curves) * d + m[:, 3]
        return np.array([ends.min(axis=0), ends.max(axis=0)])
    return extent(shape.array @ linear.T + m[:, 3], curves)


def segment(start: Floats, end: Floats) -> Blend:
    """A straight segment (one cubic curve, handles at its thirds, as CE makes it): the one
    segment shape, placed by [end − start | start]."""
    m = np.zeros((3, 4))
    m[:, 0], m[:, 3] = np.subtract(end, start), start
    return Blend(((m, SEGMENT),), 4)


def _compose(linear: Floats, matrix: Matrix) -> Matrix:
    """linear ∘ matrix, where `linear` is 3×3 (no translation of its own): one product, as the
    translation column transforms like any other."""
    return linear @ matrix


class Blend:
    """points = Σ M·S over `terms`. Immutable: every edit returns a new blend."""

    __slots__ = ("_boxes", "_pace", "_pieces", "_points", "n", "terms")

    def __init__(self, terms: tuple[Term, ...], n: int) -> None:
        self.terms = terms
        self.n = n  # number of points, known without materializing
        self._points: Floats | None = None
        self._pieces: Floats | None = None
        self._pace: tuple[Floats, Floats] | None = None
        self._boxes: dict[bool, Floats] | None = None

    def box(self, curves: bool) -> Floats:
        """(2, 3): the box of what the points make — for a path (`curves`), its curves' tight box:
        not its anchors' (a curve bulges between them), not its handles' (they overshoot).
        Cached, as a blend never changes, and read-only: a value."""
        boxes = self._boxes
        if boxes is None:
            boxes = self._boxes = {}
        box = boxes.get(curves)
        if box is None:
            box = boxes[curves] = _frozen(
                placed_box(*self.terms[0], curves)  # one shape placed
                if len(self.terms) == 1
                else extent(self.points(), curves)
            )
        return box

    @staticmethod
    def of(points: npt.ArrayLike, dim: int = 3) -> Blend:
        """A blend of one fresh shape. Translation is factored out, so translated copies share it."""
        array = np.array(points, dtype=float).reshape(-1, dim)
        if len(array) == 0:
            return EMPTY
        origin = array[0].copy()
        matrix = IDENTITY.copy()
        matrix[:, 3] = origin
        return Blend(((matrix, Shape(array - origin)),), len(array))

    def points(self) -> Floats:
        if self._points is None:
            out = np.zeros((self.n, 3))
            for m, shape in self.terms:
                out += shape.array @ m[:, :3].T + m[:, 3]
            out.flags.writeable = False
            self._points = out
        return self._points

    @property
    def cached(self) -> Floats | None:
        """The points, if they have been read; else None (what is compared with them for free)."""
        return self._points

    def point(self, k: int) -> Floats:
        """Point k (from the end if negative) without materializing the blend: a path being
        built reads where it ends once a curve, not all its points."""
        if self._points is not None or not self.terms:
            return self.points()[k]
        out = np.zeros(3)
        for m, shape in self.terms:
            out += shape.array[k] @ m[:, :3].T + m[:, 3]
        return out

    def translated(self, vector: Floats) -> Blend:
        """The blend moved by `vector`: one term's offset, no product (a move is the commonest
        edit of all) — and its boxes moved with it, when known."""
        if not self.terms:
            return self
        (first, shape), *rest = self.terms
        moved = first.copy()
        moved[:, 3] += vector
        blend = Blend(((moved, shape), *rest), self.n)
        if self._boxes:
            blend._boxes = {k: _frozen(box + vector) for k, box in self._boxes.items()}
        return blend

    def scaled(self, factor: float, about: Floats) -> Blend:
        """The blend scaled by `factor` about `about` — x ↦ f·x + (1 − f)·about: every term's
        map times f, the rest added once; its boxes, when known, scaled with it."""
        if not self.terms:
            return self
        terms = [(m * factor, shape) for m, shape in self.terms]
        terms[0][0][:, 3] += about * (1.0 - factor)
        blend = Blend(tuple(terms), self.n)
        if self._boxes:
            blend._boxes = {}
            for k, box in self._boxes.items():
                ends = (box - about) * factor + about
                blend._boxes[k] = _frozen(ends if factor >= 0 else ends[::-1].copy())
        return blend

    def transformed(self, m: Matrix) -> Blend:
        """The blend after the affine map `m` (its boxes follow a map along the axes)."""
        if not self.terms:
            return self
        terms = [(_compose(m[:, :3], a), shape) for a, shape in self.terms]
        terms[0][0][:, 3] += m[:, 3]
        blend = Blend(tuple(terms), self.n)
        if self._boxes:
            d = m.diagonal()
            if np.count_nonzero(m[:, :3]) == np.count_nonzero(d):  # along the axes
                blend._boxes = {}
                for k, box in self._boxes.items():
                    ends = box * d + m[:, 3]
                    blend._boxes[k] = _frozen(
                        np.array([ends.min(axis=0), ends.max(axis=0)])
                    )
        return blend

    @staticmethod
    def mix(a: Blend, b: Blend, coefficients: Coefficients) -> Blend:
        """`Lₛ·a + Lₑ·b + k` point by point; terms of the same shape merge, so a morph between copies
        of one shape stays one matrix."""
        ls, le, offset = coefficients
        if len(a.terms) == 1 and len(b.terms) == 1 and a.terms[0][1] is b.terms[0][1]:
            mixed = _compose(ls, a.terms[0][0]) + _compose(le, b.terms[0][0])
            mixed[:, 3] += offset
            return Blend(((mixed, a.terms[0][1]),), a.n)
        merged: dict[int, Term] = {}
        for linear, blend in ((ls, a), (le, b)):
            for m, shape in blend.terms:
                term = _compose(linear, m)
                if shape.key in merged:
                    term = merged[shape.key][0] + term
                merged[shape.key] = (term, shape)
        if not merged:
            return Blend((), a.n)
        terms = list(merged.values())
        terms[0][0][:, 3] += offset
        return Blend(tuple(terms), a.n)

    def piece_lengths(self) -> Floats:
        """(curves, 9): lengths of each curve's polyline through 10 points — the path's own
        measure of length, which its reveals, proportions and lengths all go by."""
        pieces = self._pieces
        if pieces is None:
            pts = self.points()
            curves = pts[: len(pts) // 4 * 4].reshape(-1, 4, 3)
            samples = np.einsum("tk,ckd->ctd", _BERNSTEIN, curves)
            pieces = np.linalg.norm(np.diff(samples, axis=1), axis=2)
            pieces.flags.writeable = False
            self._pieces = pieces
        return pieces

    def curve_lengths(self) -> Floats:
        """Length of each cubic curve."""
        return self.piece_lengths().sum(axis=1)

    def pace(self) -> tuple[Floats, Floats]:
        """(s, u): the fraction s of the length reached at curve parameter u. A reveal reads it once:
        constant pen speed, and the drawn part stays put under later transforms."""
        pieces = self.piece_lengths()
        curves = len(pieces)
        u = np.concatenate(
            [
                [0.0],
                (np.arange(curves)[:, None] + np.arange(1, 10)[None, :] / 9).ravel(),
            ]
        )
        s = np.concatenate([[0.0], np.cumsum(pieces.ravel())])
        return (s / s[-1] if s[-1] > 0 else u / max(curves, 1)), u

    def parameter_at(self, fraction: float) -> float:
        """The curve parameter u ∈ [0, curves] a fraction of the length along the path:
        the inverse of `fraction_at`, through the pace."""
        if self._pace is None:
            self._pace = self.pace()
        s, u = self._pace
        return float(np.interp(fraction, s, u))

    def fraction_at(self, parameter: float) -> float:
        """The fraction of the path's length reached at curve parameter u ∈ [0, curves]."""
        if self._pace is None:
            self._pace = self.pace()
        s, u = self._pace
        return float(np.interp(parameter, u, s))

    def __deepcopy__(self, memo: dict[int, object]) -> Blend:
        return self


EMPTY: Final = Blend((), 0)


def linear_about(linear: Floats, about: Floats) -> Matrix:
    """The affine map x ↦ L(x − about) + about."""
    m = np.empty((3, 4))
    m[:, :3] = linear
    m[:, 3] = about - linear @ about
    return m


@forgets
@functools.cache
def grid_triangles(u: int, v: int) -> np.ndarray:
    """Two triangles per lattice cell, in the same u-major cell order."""
    index = np.arange((u + 1) * (v + 1)).reshape(u + 1, v + 1)
    a, b, c, d = index[:-1, :-1], index[1:, :-1], index[1:, 1:], index[:-1, 1:]
    triangles = np.stack([a, b, c, a, c, d], axis=-1).reshape(-1, 3)
    triangles.flags.writeable = False
    return triangles


class Lattice(NamedTuple):
    """A sampled surface's topology: its samples a (u + 1) by (v + 1) grid, its faces the
    u by v cells between them in u-major order, of which it draws `first` to `end`: all,
    or a part's (the faces a reveal over the part's stretch shows)."""

    u: int
    v: int
    first: int
    end: int

    @classmethod
    def of(cls, u: int, v: int) -> Lattice:
        """All the faces of a u by v lattice."""
        return cls(u, v, 0, u * v)

    def triangles(self) -> np.ndarray:
        """The faces it draws, two triangles each: indices into its samples, read-only,
        and one array for equal lattices."""
        return _lattice_triangles(*self)


@forgets
@functools.cache
def _lattice_triangles(u: int, v: int, first: int, end: int) -> np.ndarray:
    """A lattice's drawn faces' triangles: the whole grid's array when it draws them all."""
    every = grid_triangles(u, v)
    return every if (first, end) == (0, u * v) else every[2 * first : 2 * end]

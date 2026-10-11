"""Bézier algorithms cut, split and smooth curves without changing them.

- A curve is exactly its ends at 0 and 1, and de Casteljau's construction everywhere between.
- A part of a curve is the curve, reparametrized; split into n (any integer, whatever is
  remembered), a curve's pieces are its equal stretches of parameter, end to end, from its start
  to its end exactly; remapped from m curves into n ≥ m, new curve j is an equal stretch of
  curve j·m // n, in an array of its own.
- A smooth curve through anchors is a natural cubic spline: continuous in its first and second
  derivatives at every anchor, straight at its ends (or closed smoothly), on either side of
  the size where a precomputed map gives way to the solve; it moves with its anchors under any
  affine map.
- `integer_interpolate` finds the step and the fraction of it: step + fraction = n·alpha.


The geometry helpers are the geometry they name.

- A rotation matrix is a rotation: orthogonal, of determinant 1, fixing its axis; turns about
  one axis add; its transpose turns back; it agrees with its quaternion.
- A turn needs an axis: given a zero axis, everything that turns about one (a rotation matrix,
  its transpose, a turned vector, a quaternion, a mobject's rotation, an arc's, a spiral's or a
  circle's path) raises, rather than scaling by cos(angle).
- A compass orbit stays at its height and radius, evenly spaced in the plane.
- A polygon's signed area and its orientation are its own: they do not depend on where it is,
  or on which vertex it starts at.
- Conversions are inverse: spherical and Cartesian coordinates, angles and axes of quaternions.
- A unit normal is a unit vector perpendicular to both vectors; an intersection lies on both
  lines; a triangulation covers its polygon, holes excluded.
- A hull encloses its points, and every boundary of its facets is shared by two of them,
  whatever the points' type, repeats and signed zeros; its points changing afterwards changes
  nothing of it. A boundary is named by its points as they were, in any order, of any type,
  whatever their zeros' signs.
- A polygon's pole of inaccessibility is a point inside it, within `precision` as far from its
  edges as the farthest point inside is, wherever and however large the polygon is.

Geometry is a lazy blend of immutable shapes: points = Σ M·S.

- A blend's points are the points its edits made: every edit (a move, a scale, an affine map,
  a mix of two blends) equals the same edit done on plain points, however they chain.
- A box a blend carries through its edits is the box of its points: a path's is its curves'
  tight box, by the roots of their derivatives, not its anchors' or handles'.
- A shape is its affine class placed: A·C gives back its points, and C is small.
- A shape is named by its content: equal points (to 1e-9) are one key, never 0, the key no
  upload may have. A big shape's class is the last one of its size when it is an affine image
  of it (and other points of that size are not), and the same points are that image exactly,
  by the identity.
- A growing path's shapes are prefixes of one log: growing never changes a shape made before,
  whichever prefix is grown.

A path takes each point from where it starts to where it ends.

- Every path, of every kind, is exactly at the start at 0 and exactly at the end at 1, in
  three dimensions too: an arc about an axis moves along the axis as well.
- The straight path runs along the chord; an arc path turns each point about the center of its
  arc, at a steady angle; a spiral path is the formula its docstring gives.
- A motion is its steps: a turn keeps its pivot, as the steps before it carried the pivot,
  where it is; moves add; a path about one center turns a shape rigidly about it."""

from collections.abc import Callable

import numpy as np
import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule
from tests import oracles
from tests.strategies import angles, arrays, curves, points, vectors

import manimgx as m
from manimgx.caches import clear
from manimgx.drawing import geometry as g

unit = st.floats(0, 1)
cubic = arrays((4, 3), 20)
CONTROLS = np.array([[0.0, 0, 0], [2, 4, -1], [6, -3, 5], [10, -5, 2]])


def close(a: np.ndarray, b: np.ndarray, scale: np.ndarray) -> None:
    np.testing.assert_allclose(a, b, atol=1e-9 * (1 + np.abs(scale).max()))


class TestCurve:
    @given(points=cubic, t=unit)
    def test_it_is_de_casteljaus_construction(
        self, points: np.ndarray, t: float
    ) -> None:
        close(
            g.bezier(points)(t),
            oracles.bezier_points(points, np.array([t]))[0, 0],
            points,
        )
        np.testing.assert_array_equal(g.bezier(points)(0), points[0])
        np.testing.assert_array_equal(g.bezier(points)(1), points[3])

    @given(points=cubic, a=unit, b=unit, s=unit)
    def test_a_part_is_the_curve_reparametrized(
        self, points: np.ndarray, a: float, b: float, s: float
    ) -> None:
        a, b = min(a, b), max(a, b)
        part = g.partial_bezier_points(points, a, b)
        close(g.bezier(part)(s), g.bezier(points)(a + s * (b - a)), points)

    @given(
        points=cubic,
        n=st.integers(1, 2000),
        numpy=st.booleans(),
        forget=st.booleans(),
        s=unit,
    )
    # n³ overflows numpy's int32; what is made for it is remembered for an int too
    @example(points=CONTROLS, n=2000, numpy=True, forget=True, s=0.37)
    def test_split_pieces_are_equal_stretches_end_to_end(
        self, points: np.ndarray, n: int, numpy: bool, forget: bool, s: float
    ) -> None:
        if forget:
            clear()
        # numpy's integers, as numpy code passes them
        count = np.int32(n) if numpy else n
        with np.errstate(over="raise", invalid="raise"):
            split = g.subdivide_bezier(points, count)  # ty: ignore[invalid-argument-type]
        pieces = split.reshape(n, 4, 3)
        close(
            oracles.bezier_points(pieces, np.array([s]))[:, 0],
            oracles.bezier_points(points, (np.arange(n) + s) / n)[0],
            points,
        )
        close(pieces[1:, 0], pieces[:-1, 3], points)
        np.testing.assert_array_equal(pieces[0, 0], points[0])
        np.testing.assert_array_equal(pieces[-1, 3], points[3])

    @given(
        many=st.integers(1, 5).flatmap(lambda n: arrays((n, 4, 3), 20)),
        more=st.integers(0, 20),
        fortran=st.booleans(),
    )
    @example(many=np.zeros((0, 4, 3)), more=0, fortran=False)
    def test_remapped_curves_are_their_curves_equal_stretches(
        self, many: np.ndarray, more: int, fortran: bool
    ) -> None:
        if fortran:
            many = np.asfortranarray(many)
        many.setflags(write=False)
        new = len(many) + more
        out = g.bezier_remap(many, new)
        assert out.shape == (new, 4, 3)
        assert out.flags.c_contiguous
        assert out.flags.writeable
        assert not np.shares_memory(out, many)
        owners = [j * len(many) // new for j in range(new)]
        samples = np.array([0.0, 0.37, 1.0])
        for j, owner in enumerate(owners):
            stretch = (owners[:j].count(owner) + samples) / owners.count(owner)
            close(
                oracles.bezier_points(out[j], samples),
                oracles.bezier_points(many[owner], stretch),
                many,
            )


def spline(anchors: np.ndarray) -> np.ndarray:
    h1, h2 = g.get_smooth_cubic_bezier_handle_points(anchors)
    return np.stack([anchors[:-1], h1, h2, anchors[1:]], axis=1)


def derivatives(c: np.ndarray) -> tuple[np.ndarray, ...]:
    """(B'(0), B'(1), B''(0), B''(1)) of each curve."""
    return (
        3 * (c[:, 1] - c[:, 0]),
        3 * (c[:, 3] - c[:, 2]),
        6 * (c[:, 2] - 2 * c[:, 1] + c[:, 0]),
        6 * (c[:, 3] - 2 * c[:, 2] + c[:, 1]),
    )


anchors = st.integers(3, 300).flatmap(lambda n: arrays((n, 3), 10))
MAPPED = (
    g._SMOOTHING_UP_TO
)  # the most anchors smoothed by a precomputed map, not the solve


def scattered(n: int) -> np.ndarray:
    return np.random.default_rng(n).normal(size=(n, 3))


class TestSmooth:
    @given(points=anchors)
    @example(points=scattered(MAPPED))
    @example(points=scattered(MAPPED + 1))
    def test_an_open_curve_is_a_natural_spline(self, points: np.ndarray) -> None:
        points[-1] += 1  # open
        assume(not g.is_closed(points))
        c = spline(points)
        d0, d1, s0, s1 = derivatives(c)
        close(d1[:-1], d0[1:], points)
        close(s1[:-1], s0[1:], points)
        close(s0[0], np.zeros_like(s0[0]), points)
        close(s1[-1], np.zeros_like(s1[-1]), points)

    @given(points=anchors)
    @example(points=scattered(MAPPED - 1))  # and the first again: MAPPED anchors
    @example(points=scattered(MAPPED))
    def test_a_closed_curve_closes_smoothly(self, points: np.ndarray) -> None:
        c = spline(np.vstack([points, points[:1]]))
        d0, d1, s0, s1 = derivatives(c)
        close(np.roll(d1, 1, axis=0), d0, points)
        close(np.roll(s1, 1, axis=0), s0, points)

    @given(
        points=st.integers(3, 30).flatmap(lambda n: arrays((n, 3), 10)),
        linear=arrays((3, 3), 2),
        offset=arrays(3, 10),
    )
    def test_it_moves_with_its_anchors(
        self, points: np.ndarray, linear: np.ndarray, offset: np.ndarray
    ) -> None:
        points[-1] += 1
        assume(not g.is_closed(points) and not g.is_closed(points @ linear.T + offset))
        close(
            spline(points @ linear.T + offset),
            spline(points) @ linear.T + offset,
            points,
        )


alphas = unit | st.sampled_from(
    [np.nextafter(0, 1), np.nextafter(1, 0)]
)  # rounding bites there


@given(start=st.integers(-50, 50), n=st.integers(1, 1000), alpha=alphas)
def test_integer_interpolate_finds_the_step_and_its_fraction(
    start: int, n: int, alpha: float
) -> None:
    # (it truncated toward 0 below a start of 0, and could step past the last step)
    step, fraction = g.integer_interpolate(start, start + n, alpha)
    assert start <= step < start + n
    assert 0 <= fraction <= 1
    assert step + fraction == pytest.approx(
        start + n * alpha, abs=1e-9 * (n + abs(start))
    )


@given(start=st.floats(-100, 100), end=st.floats(-100, 100), alpha=unit)
def test_inverse_interpolate_inverts_interpolate(
    start: float, end: float, alpha: float
) -> None:
    assume(abs(end - start) > 1e-6)
    assert g.inverse_interpolate(
        start, end, g.interpolate(start, end, alpha)
    ) == pytest.approx(alpha, abs=1e-9 * (1 + abs(start) + abs(end)) / abs(end - start))


class TestRotationMatrix:
    @given(angle=angles(), axis=vectors())
    def test_it_is_a_rotation_about_its_axis(
        self, angle: float, axis: np.ndarray
    ) -> None:
        r = g.rotation_matrix(angle, axis)
        np.testing.assert_allclose(r @ r.T, np.eye(3), atol=1e-12)
        assert np.linalg.det(r) == pytest.approx(1, abs=1e-12)
        np.testing.assert_allclose(r @ axis, axis, atol=1e-12 * np.linalg.norm(axis))

    @given(a=angles(), b=angles(), axis=vectors())
    def test_turns_about_one_axis_add(
        self, a: float, b: float, axis: np.ndarray
    ) -> None:
        np.testing.assert_allclose(
            g.rotation_matrix(a, axis) @ g.rotation_matrix(b, axis),
            g.rotation_matrix(a + b, axis),
            atol=1e-12,
        )
        np.testing.assert_allclose(
            g.rotation_matrix_transpose(a, axis),
            g.rotation_matrix(-a, axis),
            atol=1e-12,
        )

    @given(angle=st.floats(0.01, np.pi - 0.01), axis=vectors(), v=vectors())
    def test_it_turns_counterclockwise_seen_from_its_axis(
        self, angle: float, axis: np.ndarray, v: np.ndarray
    ) -> None:
        across = v - (v @ axis) / (axis @ axis) * axis  # v's part a turn moves
        assume(np.linalg.norm(across) > 1e-2 * np.linalg.norm(v))
        turned = g.rotation_matrix(angle, axis) @ across
        assert np.cross(across, turned) @ axis > 0

    @given(angle=angles(), axis=vectors())
    def test_it_is_its_quaternion(self, angle: float, axis: np.ndarray) -> None:
        q = np.array(g.quaternion_from_angle_axis(angle, axis))
        np.testing.assert_allclose(
            g.rotation_matrix_from_quaternion(q),
            g.rotation_matrix(angle, axis),
            atol=1e-12,
        )
        rows = g.rotation_matrix_transpose_from_quaternion(q)
        np.testing.assert_allclose(rows, g.rotation_matrix(angle, axis).T, atol=1e-12)

    @given(v=arrays(2, 10), angle=angles())
    def test_a_plane_vector_turns_in_its_plane(
        self, v: np.ndarray, angle: float
    ) -> None:
        c, s = np.cos(angle), np.sin(angle)
        np.testing.assert_allclose(
            g.rotate_vector(v, angle),
            [c * v[0] - s * v[1], s * v[0] + c * v[1], 0],
            atol=1e-12 * (1 + np.abs(v).max()),
        )


class TestZToVector:
    @given(v=vectors())
    def test_it_turns_the_z_axis_to_the_vector(self, v: np.ndarray) -> None:
        r = g.z_to_vector(v)
        np.testing.assert_allclose(r @ r.T, np.eye(3), atol=1e-12)
        assert np.linalg.det(r) == pytest.approx(1, abs=1e-12)
        np.testing.assert_allclose(r @ m.OUT, v / np.linalg.norm(v), atol=1e-12)


polygons = st.integers(3, 12).flatmap(lambda n: arrays((n, 2), 10))


class TestShoelace:
    @given(xy=polygons, shift=arrays(2, 50), start=st.integers(0, 11))
    def test_the_area_is_the_polygons_wherever_it_is(
        self, xy: np.ndarray, shift: np.ndarray, start: int
    ) -> None:
        # shoelace's sign: positive clockwise
        expected = -oracles.polygon_area(xy)
        moved = np.roll(xy + shift, start % len(xy), axis=0)
        assert g.shoelace(moved) == pytest.approx(
            expected, abs=1e-9 * (1 + np.abs(moved).max()) ** 2
        )

    @given(xy=polygons, shift=arrays(2, 50))
    def test_the_orientation_is_the_polygons_wherever_it_is(
        self, xy: np.ndarray, shift: np.ndarray
    ) -> None:
        area = oracles.polygon_area(xy)
        assume(abs(area) > 1e-6)
        expected = "CCW" if area > 0 else "CW"
        assert g.shoelace_direction(xy) == expected
        assert g.shoelace_direction(xy + shift) == expected

    def test_a_closed_ring_counts_its_repeated_vertex_once(self) -> None:
        square = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
        assert g.shoelace(square) == g.shoelace(np.vstack([square, square[:1]])) == -1


class TestWindingNumber:
    @given(radius=st.floats(0.1, 10), center=arrays(2, 20), n=st.integers(3, 40))
    def test_a_circle_winds_once_about_what_it_holds(
        self, radius: float, center: np.ndarray, n: int
    ) -> None:
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        ring = np.stack(
            [center[0] + radius * np.cos(t), center[1] + radius * np.sin(t), 0 * t], 1
        )
        inside = np.linalg.norm(center) < radius * np.cos(np.pi / n) - 1e-9
        outside = np.linalg.norm(center) > radius + 1e-9
        assume(inside or outside)
        assert g.get_winding_number(ring) == pytest.approx(1 if inside else 0, abs=1e-9)
        assert g.get_winding_number(ring[::-1]) == pytest.approx(
            -1 if inside else 0, abs=1e-9
        )


class TestConversions:
    @given(v=vectors(min_norm=1e-6, bound=100))
    def test_spherical_coordinates_are_inverse(self, v: np.ndarray) -> None:
        r, theta, phi = g.cartesian_to_spherical(v)
        assert r >= 0
        assert -np.pi <= theta <= np.pi
        assert 0 <= phi <= np.pi
        np.testing.assert_allclose(
            g.spherical_to_cartesian(np.array([r, theta, phi])), v, atol=1e-12 * r
        )

    @given(angle=st.floats(0, np.pi), axis=vectors())
    def test_a_quaternions_angle_and_axis_are_inverse(
        self, angle: float, axis: np.ndarray
    ) -> None:
        got_angle, got_axis = g.angle_axis_from_quaternion(
            np.array(g.quaternion_from_angle_axis(angle, axis))
        )
        assert got_angle == pytest.approx(angle, abs=1e-6)
        if angle > 1e-6:
            np.testing.assert_allclose(got_axis, axis / np.linalg.norm(axis), atol=1e-9)

    @given(quats=st.lists(arrays(4, 2), min_size=3, max_size=3))
    def test_quaternion_products_associate(self, quats: list[np.ndarray]) -> None:
        a, b, c = quats
        np.testing.assert_allclose(
            g.quaternion_mult(g.quaternion_mult(a, b), c),
            g.quaternion_mult(a, g.quaternion_mult(b, c)),
            atol=1e-9,
        )


class TestUnitNormal:
    @given(a=points(10), b=points(10))
    def test_it_is_a_unit_vector_perpendicular_to_both(
        self, a: np.ndarray, b: np.ndarray
    ) -> None:
        n = g.get_unit_normal(a, b)
        assert np.linalg.norm(n) == pytest.approx(1, abs=1e-12)
        for v in (a, b):
            if np.linalg.norm(v) > 1e-9:
                assert abs(n @ v) / np.linalg.norm(v) < 1e-6


class TestAngles:
    @given(a=vectors(), b=vectors(), angle=angles(), axis=vectors())
    def test_the_angle_between_two_vectors_turns_with_them(
        self, a: np.ndarray, b: np.ndarray, angle: float, axis: np.ndarray
    ) -> None:
        between = g.angle_between_vectors(a, b)
        assert 0 <= between <= np.pi
        cos = a @ b / np.linalg.norm(a) / np.linalg.norm(b)
        assert np.cos(between) == pytest.approx(cos, abs=1e-9)
        r = g.rotation_matrix(angle, axis)
        assert g.angle_between_vectors(r @ a, r @ b) == pytest.approx(between, abs=1e-6)


class TestIntersections:
    @given(lines=arrays((2, 2, 3), 10))
    def test_where_two_lines_cross_is_on_both(self, lines: np.ndarray) -> None:
        (a, b), (c, d) = lines[:, :, :2]
        u, v = b - a, d - c
        assume(min(np.linalg.norm(u), np.linalg.norm(v)) > 1e-2)
        assume(
            abs(u[0] * v[1] - u[1] * v[0])
            > 1e-2 * np.linalg.norm(u) * np.linalg.norm(v)
        )
        p = g.line_intersection(lines[0], lines[1])[:2]
        for start, direction in ((a, u), (c, v)):
            offset = p - start
            cross = direction[0] * offset[1] - direction[1] * offset[0]
            assert abs(cross) <= 1e-6 * np.linalg.norm(direction) * (
                1 + np.linalg.norm(offset)
            )

    @given(
        a=st.tuples(st.integers(-9, 9), st.integers(-9, 9)),
        u=st.tuples(st.integers(-9, 9), st.integers(-9, 9)).filter(any),
        t=st.integers(-5, 5),
    )
    def test_parallel_lines_have_no_intersection(
        self, a: tuple[int, int], u: tuple[int, int], t: int
    ) -> None:
        # whole numbers: exactly parallel in floats too
        line1 = np.array([[*a, 0], [a[0] + u[0], a[1] + u[1], 0]], dtype=float)
        line2 = line1 + np.array([u[1], -u[0], 0]) * t  # moved across itself, or not
        with pytest.raises(ValueError, match="parallel"):
            g.line_intersection(line1, line2)


class TestEarclipTriangulation:
    @given(
        n=st.integers(3, 30),
        radii=st.lists(st.floats(0.5, 2), min_size=30, max_size=30),
        hole=st.just(0.0) | st.floats(0.05, 0.5),
    )
    def test_its_triangles_cover_a_star_shaped_polygon_but_its_hole(
        self, n: int, radii: list[float], hole: float
    ) -> None:
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        ring = np.stack([radii[:n] * np.cos(t), radii[:n] * np.sin(t), 0 * t], 1)
        # the polygon scaled about a point it holds, its center: a hole inside it
        verts, ends = (
            (np.vstack([ring, hole * ring]), [n, 2 * n]) if hole else (ring, [n])
        )
        triangles = np.array(g.earclip_triangulation(verts, ends)).reshape(-1, 3)
        assert len(triangles) == len(verts) - 2 + 2 * (len(ends) - 1)
        total = sum(abs(oracles.polygon_area(verts[tri, :2])) for tri in triangles)
        expected = abs(oracles.polygon_area(ring[:, :2])) * (1 - hole**2)
        assert total == pytest.approx(expected, rel=1e-9)


@given(n=st.integers(1, 40), radius=st.floats(0.1, 10), start=st.floats(-7, 7))
def test_regular_vertices_are_evenly_spread_on_their_circle(
    n: int, radius: float, start: float
) -> None:
    vertices, first = g.regular_vertices(n, radius=radius, start_angle=start)
    assert first == start
    np.testing.assert_allclose(
        vertices[0],
        radius * np.array([np.cos(start), np.sin(start), 0]),
        atol=1e-12 * radius,
    )
    turn = g.rotation_matrix(2 * np.pi / n)
    np.testing.assert_allclose(
        vertices[1:], vertices[:-1] @ turn.T, atol=1e-12 * radius
    )


@pytest.mark.parametrize("dimension", [2, 3])
@given(n=st.integers(1, 96), start=arrays(3, 20))
def test_compass_orbits_keep_height_radius_and_even_spacing(
    dimension: int, n: int, start: np.ndarray
) -> None:
    orbit = g.compass_directions(n, start[:dimension])
    assert orbit.shape == (n, 3)
    np.testing.assert_array_equal(orbit[:, 2], start[2] if dimension == 3 else 0)
    planar = orbit[:, 0] + 1j * orbit[:, 1]
    np.testing.assert_allclose(np.abs(planar), np.hypot(*start[:2]), atol=1e-12)
    np.testing.assert_allclose(
        np.roll(planar, -1), planar * np.exp(2j * np.pi / n), atol=1e-12
    )
    np.testing.assert_array_equal(orbit[0, :2], start[:2])


@given(
    dimension=st.integers(2, 5),
    seed=st.integers(0, 2**32 - 1),
    dtype=st.sampled_from(["float32", "float64", "int64"]),
    zeros=st.lists(st.tuples(st.integers(0, 15), st.integers(0, 4)), max_size=6),
    repeats=st.lists(st.integers(0, 15), max_size=4),
)
def test_a_hull_encloses_its_points_with_shared_closed_boundaries(
    dimension: int,
    seed: int,
    dtype: str,
    zeros: list[tuple[int, int]],
    repeats: list[int],
) -> None:
    coordinates = 100 * np.random.default_rng(seed).normal(size=(16, dimension))
    for row, column in zeros:
        coordinates[row, column % dimension] = 0.0
    coordinates = coordinates.astype(dtype)
    again = coordinates[repeats]
    again[again == 0] *= -1  # a repeat with its zeros' signs turned
    points = np.concatenate((coordinates, again))
    kept = points.copy()
    hull = g.QuickHull(tolerance=1e-3)
    hull.build(points)
    # a hull's points are a value: changing them afterwards changes nothing
    points += 10

    active = set(hull.facets) - hull.removed
    assert active
    for facet in active:
        assert len(facet.subfacets) == dimension
        np.testing.assert_allclose(np.linalg.norm(facet.normal), 1, atol=1e-7)
        assert np.max((kept - facet.center) @ facet.normal) < 1e-3
        for boundary in facet.subfacets:
            adjacent = hull.neighbors[boundary]
            assert facet in adjacent
            assert len(adjacent) == 2
            assert adjacent <= active
            assert all(boundary in neighbor.subfacets for neighbor in adjacent)
            # a boundary is named by its points as they were: in any order, of any type,
            # whatever their zeros' signs
            rows = boundary.coordinates[::-1].astype(np.float64)
            rows[rows == 0] *= -1
            name = g.SubFacet(rows)
            rows += 1
            assert hull.neighbors[name] == adjacent


def from_edges(rings: list[np.ndarray], point: np.ndarray) -> float:
    """How far a point is from the nearest edge of the rings: positive inside them (an odd
    number of edges crossed on the way to +x), negative outside."""
    edges = np.concatenate([np.stack([r[:-1, :2], r[1:, :2]], 1) for r in rings])
    a, b = edges[:, 0], edges[:, 1]
    along = np.clip(
        np.einsum("ij,ij->i", point - a, b - a) / np.einsum("ij,ij->i", b - a, b - a),
        0,
        1,
    )
    nearest = float(
        np.min(np.linalg.norm(a + along[:, None] * (b - a) - point, axis=1))
    )
    spans = (a[:, 1] > point[1]) != (b[:, 1] > point[1])
    with np.errstate(divide="ignore", invalid="ignore"):
        cross = a[:, 0] + (point[1] - a[:, 1]) * (b[:, 0] - a[:, 0]) / (
            b[:, 1] - a[:, 1]
        )
    inside = np.count_nonzero(spans & (point[0] < cross)) % 2
    return nearest if inside else -nearest


@st.composite
def poles(draw: st.DrawFn) -> tuple[list[np.ndarray], float]:
    """A polygon's closed rings and how far its pole of inaccessibility is from its edges: a
    rectangle's (half its height), a triangle's (its incircle's radius), a regular polygon's
    (its apothem), or a square's with a square hole in its middle (its pole on a diagonal,
    as far from the outline as from the hole's corner); placed by any similarity."""
    kind = draw(st.sampled_from(["rectangle", "triangle", "regular", "holed"]))
    if kind == "rectangle":
        width = draw(st.floats(1, 8))
        rings = [np.array([[0, 0], [width, 0], [width, 1], [0, 1]])]
        radius = 0.5
    elif kind == "triangle":
        apex = np.array([draw(st.floats(-1, 2)), draw(st.floats(0.3, 2))])
        corners = np.array([[0, 0], [1, 0], apex])
        sides = np.linalg.norm(corners - np.roll(corners, 1, axis=0), axis=1)
        rings, radius = (
            [corners],
            apex[1] / sides.sum(),
        )  # twice the area, by the perimeter
    elif kind == "regular":
        n = draw(st.integers(3, 12))
        t = 2 * np.pi * np.arange(n) / n
        rings, radius = [np.stack([np.cos(t), np.sin(t)], 1)], np.cos(np.pi / n)
    else:
        hole = draw(st.floats(0.1, 1.5))
        square = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]])
        rings = [2 * square, hole * square[::-1]]
        radius = np.sqrt(2) * (2 - hole) / (1 + np.sqrt(2))
    scale, turn = draw(st.floats(0.1, 10)), g.rotate_vector
    angle, shift = draw(angles()), draw(arrays(2, 100))
    placed = []
    for ring in rings:
        closed = np.vstack([ring, ring[:1]]).astype(float)
        flat = np.column_stack([closed, np.zeros(len(closed))])
        placed.append(np.array([turn(p, angle) for p in flat]) * scale + [*shift, 0])
    return placed, float(radius * scale)


@given(polygon=poles(), precision=st.floats(0.005, 0.2))
def test_the_pole_is_inside_within_precision_of_the_farthest_point(
    polygon: tuple[list[np.ndarray], float], precision: float
) -> None:
    rings, radius = polygon
    precision *= radius
    cell = g.polylabel(rings, precision)
    assert cell.d == pytest.approx(from_edges(rings, cell.c), rel=1e-9, abs=1e-12)
    assert radius - precision <= cell.d <= radius * (1 + 1e-9)


def scale_of(points: np.ndarray) -> float:
    return 1.0 + float(np.abs(points).max(initial=0.0))


class TestCurveBox:
    @given(points=curves())
    def test_it_is_the_curves_tight_box(self, points: np.ndarray) -> None:
        np.testing.assert_allclose(
            g.curve_box(points), oracles.curve_box(points), atol=1e-9 * scale_of(points)
        )

    @given(points=curves())
    def test_it_holds_every_point_of_the_curves(self, points: np.ndarray) -> None:
        low, high = g.curve_box(points)
        drawn = oracles.sample(points)
        tolerance = 1e-9 * scale_of(points)
        assert np.all(drawn >= low - tolerance)
        assert np.all(drawn <= high + tolerance)

    @given(points=arrays((7, 3)))
    def test_anything_but_a_path_is_boxed_by_its_points(
        self, points: np.ndarray
    ) -> None:
        np.testing.assert_array_equal(
            g.extent(points, curves=True), [points.min(0), points.max(0)]
        )
        np.testing.assert_array_equal(
            g.extent(points[:4], curves=False), [points[:4].min(0), points[:4].max(0)]
        )


class TestShape:
    @given(points=curves())
    def test_its_affine_class_placed_is_itself(self, points: np.ndarray) -> None:
        _, canonical, placement = g.Shape(points.copy()).affine
        # a direction thinner than 1e-6 of the shape's size counts as flat (float32 holds
        # 7 digits), so the shape comes back to within that
        size = float(np.ptp(points, axis=0).max())
        np.testing.assert_allclose(
            canonical @ placement[:, :3].T + placement[:, 3],
            points,
            atol=2e-6 * size + 1e-12,
        )
        # whitened: O(1), whatever the shape's size, so float32 holds it
        assert np.abs(canonical).max() <= np.sqrt(len(points)) + 1e-9

    @given(points=curves())
    def test_equal_content_is_one_key_never_0(self, points: np.ndarray) -> None:
        key = g.Shape(points.copy()).key
        assert key == g.Shape(points.copy()).key
        assert key != 0

    @given(
        seed=st.integers(0, 2**32 - 1),
        more=st.integers(1, 8),
        angle=angles(),
        axis=vectors(),
        scale=st.floats(0.5, 2),
        shift=arrays(3, 10),
    )
    def test_a_big_shape_is_the_last_ones_class_when_it_is_its_image(
        self,
        seed: int,
        more: int,
        angle: float,
        axis: np.ndarray,
        scale: float,
        shift: np.ndarray,
    ) -> None:
        rng = np.random.default_rng(seed)
        points = rng.normal(size=(g.CANONICAL + more, 3))
        key, base, _ = g.Shape(points.copy()).affine
        again, again_base, placement = g.Shape(points.copy()).affine
        assert again == key
        assert again_base is base
        assert np.array_equal(placement, g.IDENTITY)  # exactly: no fit, no jitter
        turn = np.column_stack([scale * g.rotation_matrix(angle, axis), shift])
        moved = points @ turn[:, :3].T + turn[:, 3]
        moved_key, moved_base, placed = g.Shape(moved).affine
        assert moved_key == key
        assert moved_base is base
        np.testing.assert_allclose(placed, turn, atol=1e-6)
        assert g.Shape(points + rng.normal(size=points.shape)).affine[0] != key

    def test_a_shape_never_changes(self) -> None:
        shape = g.Shape(np.zeros((4, 3)))
        with pytest.raises(ValueError, match="read-only"):
            shape.array[0, 0] = 1


class GrowingPaths(RuleBasedStateMachine):
    """Shapes extended from any prefix of a log keep their own points."""

    @initialize(rows=arrays((4, 3), 10))
    def begin(self, rows: np.ndarray) -> None:
        self.made = [(g.Shape(rows.copy()), rows.copy())]

    @rule(
        which=st.integers(0, 1000),
        rows=st.integers(1, 40).flatmap(lambda n: arrays((n, 3), 10)),
    )
    def extend(self, which: int, rows: np.ndarray) -> None:
        shape, expected = self.made[which % len(self.made)]
        self.made.append((shape.extended(rows), np.concatenate([expected, rows])))

    @invariant()
    def every_shape_keeps_its_points(self) -> None:
        for shape, expected in self.made:
            np.testing.assert_array_equal(shape.array, expected)


TestGrowingPaths = GrowingPaths.TestCase
TestGrowingPaths.settings = settings(stateful_step_count=30)


class BlendEdits(RuleBasedStateMachine):
    """A blend under any chain of edits is the plain points under the same edits, and the
    boxes it carries are its points' boxes."""

    @initialize(points=curves())
    def begin(self, points: np.ndarray) -> None:
        self.blend = g.Blend.of(points)
        self.points = points.copy()

    @rule()
    def measure(self) -> None:  # boxes cached now are carried through the edits after
        self.blend.box(True)
        self.blend.box(False)

    @rule(vector=arrays(3, 10))
    def translate(self, vector: np.ndarray) -> None:
        self.blend = self.blend.translated(vector)
        self.points = self.points + vector

    @rule(factor=st.floats(-3, 3), about=arrays(3, 10))
    def scale(self, factor: float, about: np.ndarray) -> None:
        self.blend = self.blend.scaled(factor, about)
        self.points = (self.points - about) * factor + about

    @rule(matrix=arrays((3, 4), 3))
    def transform(self, matrix: np.ndarray) -> None:
        self.blend = self.blend.transformed(matrix)
        self.points = self.points @ matrix[:, :3].T + matrix[:, 3]

    @rule(factors=arrays(3, 3), offset=arrays(3, 10))
    def transform_along_the_axes(self, factors: np.ndarray, offset: np.ndarray) -> None:
        matrix = np.hstack([np.diag(factors), offset[:, None]])
        self.blend = self.blend.transformed(matrix)
        self.points = self.points * factors + offset

    @rule(
        other=curves(min_curves=6, max_curves=6),
        alpha=st.floats(0, 1),
        angle=st.floats(0.02, 3),
        axis=vectors(),
    )
    def mix(
        self, other: np.ndarray, alpha: float, angle: float, axis: np.ndarray
    ) -> None:
        other = (
            other[: len(self.points)]
            if len(other) >= len(self.points)
            else np.resize(other, self.points.shape)
        )
        path = g.path_along_arc(angle, axis) if angle > 1.5 else g.straight_path()
        self.blend = g.Blend.mix(
            self.blend, g.Blend.of(other), path.coefficients(alpha)
        )
        self.points = path(self.points, other, alpha)

    @invariant()
    def its_points_are_the_edited_points(self) -> None:
        np.testing.assert_allclose(
            self.blend.points(), self.points, atol=1e-9 * scale_of(self.points)
        )

    @invariant()
    def its_boxes_are_its_points_boxes(self) -> None:
        tolerance = 1e-9 * scale_of(self.points)
        np.testing.assert_allclose(
            self.blend.box(True), oracles.curve_box(self.points), atol=tolerance
        )
        np.testing.assert_allclose(
            self.blend.box(False),
            [self.points.min(0), self.points.max(0)],
            atol=tolerance,
        )


TestBlendEdits = BlendEdits.TestCase
TestBlendEdits.settings = settings(stateful_step_count=12)


@pytest.mark.parametrize(
    ("path_kind", "alpha"),
    [("straight", 0.0), ("straight", 0.3), ("straight", 1.0), ("circle", 0.4)],
)
def test_a_mix_of_independent_placements_of_one_shape_stays_one_shape(
    path_kind: str, alpha: float
) -> None:
    base = g.Blend.of(CONTROLS)
    a = base.translated(np.array([2.0, -1.0, 3.0]))
    b = base.transformed(np.array([[0.0, -1, 0, 4], [1, 0, 0, 5], [0, 0, 1, 6]]))
    before = tuple(matrix.copy() for blend in (a, b) for matrix, _ in blend.terms)
    path = (
        g.straight_path()
        if path_kind == "straight"
        else g.path_along_circles(np.pi / 3, np.array([1.0, 2.0, 3.0]))
    )
    assert isinstance(path, g.Path)
    coefficients = path.coefficients(alpha)
    if path_kind == "circle":
        assert coefficients[2].any()

    other_shape = g.Shape(base.terms[0][1].array.copy())
    generic_b = g.Blend(((b.terms[0][0].copy(), other_shape),), b.n)
    expected = g.Blend.mix(a, generic_b, coefficients)
    assert other_shape is not base.terms[0][1]
    assert other_shape.key == base.terms[0][1].key
    assert expected.terms[0][1] is other_shape

    mixed = g.Blend.mix(a, b, coefficients)
    assert len(mixed.terms) == 1
    assert mixed.terms[0][1] is base.terms[0][1]
    assert mixed.terms[0][0].tobytes() == expected.terms[0][0].tobytes()
    assert mixed.points().tobytes() == expected.points().tobytes()
    for matrix, expected in zip(
        (matrix for blend in (a, b) for matrix, _ in blend.terms), before, strict=True
    ):
        np.testing.assert_array_equal(matrix, expected)
        assert not np.shares_memory(mixed.terms[0][0], matrix)


def test_multi_term_and_empty_mixes_keep_their_generic_semantics() -> None:
    a = g.Blend.of(CONTROLS)
    b = g.Blend.of(CONTROLS + 1)
    coefficients = g.straight_path().coefficients(0.4)
    multi = g.Blend((*a.terms, *b.terms), len(CONTROLS))
    np.testing.assert_allclose(
        g.Blend.mix(multi, a, coefficients).points(),
        0.6 * multi.points() + 0.4 * a.points(),
    )
    assert g.Blend.mix(g.EMPTY, g.EMPTY, coefficients).terms == ()


@given(start=arrays(3), end=arrays(3))
def test_a_segment_is_one_straight_curve_between_its_ends(
    start: np.ndarray, end: np.ndarray
) -> None:
    points = g.segment(start, end).points()
    np.testing.assert_allclose(
        points,
        [start + k / 3 * (end - start) for k in range(4)],
        atol=1e-12 * scale_of(points),
    )


@given(angle=angles(), about=arrays(3, 10))
def test_linear_about_keeps_its_point(angle: float, about: np.ndarray) -> None:
    turn = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1],
        ]
    )
    m = g.linear_about(turn, about)
    np.testing.assert_allclose(
        m[:, :3] @ about + m[:, 3], about, atol=1e-12 * scale_of(about)
    )


clouds = st.integers(1, 6).flatmap(
    lambda n: st.tuples(arrays((n, 3), 10), arrays((n, 3), 10))
)
arc_angles = st.floats(g.STRAIGHT_PATH_THRESHOLD, 2 * np.pi - 1e-3).map(
    lambda a: a
) | st.floats(-2 * np.pi + 1e-3, -g.STRAIGHT_PATH_THRESHOLD)


@st.composite
def every_path(draw: st.DrawFn) -> g.PathFunc:
    kind = draw(st.sampled_from(["straight", "arc", "spiral", "circles", "motion"]))
    if kind == "straight":
        return g.straight_path()
    if kind == "arc":
        return g.path_along_arc(draw(arc_angles), draw(vectors()))
    if kind == "spiral":
        return g.spiral_path(draw(arc_angles), draw(vectors()))
    if kind == "circles":
        return g.path_along_circles(
            draw(angles()), draw(arrays(3, 10)), draw(vectors())
        )
    steps = draw(
        st.lists(
            st.one_of(
                arrays(3, 10),
                st.tuples(angles(), vectors(), arrays(3, 10)),
            ),
            max_size=4,
        )
    )
    return g.Path(steps=tuple(steps))


@given(path=every_path(), ends=clouds)
def test_every_path_starts_at_the_start_and_ends_at_the_end(
    path: g.PathFunc, ends: tuple[np.ndarray, np.ndarray]
) -> None:
    start, end = ends
    np.testing.assert_allclose(path(start, end, 0.0), start, atol=1e-9)
    np.testing.assert_allclose(path(start, end, 1.0), end, atol=1e-9)


@given(ends=clouds, alpha=st.floats(0, 1))
def test_the_straight_path_runs_along_the_chord(
    ends: tuple[np.ndarray, np.ndarray], alpha: float
) -> None:
    start, end = ends
    np.testing.assert_allclose(
        g.straight_path()(start, end, alpha),
        start + alpha * (end - start),
        atol=1e-12,
    )


@given(angle=arc_angles, axis=vectors(), ends=clouds, alpha=st.floats(0, 1))
def test_an_arc_path_turns_each_point_about_its_arcs_center(
    angle: float, axis: np.ndarray, ends: tuple[np.ndarray, np.ndarray], alpha: float
) -> None:
    """Across the axis, each point turns at a steady rate about a center it keeps its
    distance from; along the axis, it moves at a steady rate."""
    start, end = ends
    unit = axis / np.linalg.norm(axis)
    at = g.path_along_arc(angle, axis)(start, end, alpha)
    along = lambda p: p @ unit  # noqa: E731
    across = lambda p: p - np.outer(p @ unit, unit)  # noqa: E731
    np.testing.assert_allclose(
        along(at), along(start) + alpha * (along(end) - along(start)), atol=1e-9
    )
    s, e, a = across(start), across(end), across(at)
    chord = e - s
    center = (s + e) / 2 + np.cross(unit, chord) / (2 * np.tan(angle / 2))
    np.testing.assert_allclose(
        a - center,
        (s - center) @ g.rotation_matrix(alpha * angle, unit).T,
        atol=1e-7 * (1 + np.abs(center).max()),
    )


@given(angle=arc_angles, axis=vectors(), ends=clouds, alpha=st.floats(0, 1))
def test_a_spiral_path_is_its_formula(
    angle: float, axis: np.ndarray, ends: tuple[np.ndarray, np.ndarray], alpha: float
) -> None:
    start, end = ends
    turn = g.rotation_matrix((alpha - 1) * angle, axis)
    np.testing.assert_allclose(
        g.spiral_path(angle, axis)(start, end, alpha),
        start + alpha * (end - start) @ turn.T,
        atol=1e-9,
    )


@given(
    angle=angles(),
    center=arrays(3, 10),
    axis=vectors(),
    shape=arrays((5, 3), 10),
    alpha=st.floats(0, 1),
)
def test_a_path_about_one_center_turns_a_shape_rigidly(
    angle: float, center: np.ndarray, axis: np.ndarray, shape: np.ndarray, alpha: float
) -> None:
    turned = (shape - center) @ g.rotation_matrix(angle, axis).T + center
    at = g.path_along_circles(angle, center, axis)(shape, turned, alpha)
    np.testing.assert_allclose(
        at,
        (shape - center) @ g.rotation_matrix(alpha * angle, axis).T + center,
        atol=1e-9,
    )


class TestCarried:
    @given(
        steps=st.lists(
            st.one_of(arrays(3, 10), st.tuples(angles(), vectors(), arrays(3, 10))),
            max_size=5,
        ),
        shape=arrays((5, 3), 10),
        alpha=st.floats(-0.25, 1.25),
    )
    def test_mixed_steps_carry_a_shape_rigidly_in_three_dimensions(
        self, steps: list[g.Step], shape: np.ndarray, alpha: float
    ) -> None:
        def curve(t: float) -> np.ndarray:
            return np.array([2 + t, 3 - t * t, -1 + t * t * t])

        steps = [*steps]
        steps.insert(len(steps) // 2, curve)

        def at(t: float) -> np.ndarray:
            # Carry the points and every future pivot themselves, without composing
            # matrices. Each turn fixes the pivot where earlier steps brought it.
            pivots = np.array([s[2] for s in steps if isinstance(s, tuple)])
            points = np.concatenate((shape, pivots.reshape(-1, 3)))
            pivot_index = len(shape)
            for step in steps:
                if isinstance(step, np.ndarray):
                    points += t * step
                elif isinstance(step, tuple):
                    angle, axis, _ = step
                    pivot = points[pivot_index].copy()
                    points = (points - pivot) @ g.rotation_matrix(
                        t * angle, axis
                    ).T + pivot
                    pivot_index += 1
                else:
                    points += step(t) - step(0)
            return points[: len(shape)]

        expected = at(alpha)
        motion = g.carried((step, alpha) for step in steps)
        np.testing.assert_allclose(
            shape @ motion[:3, :3].T + motion[:3, 3], expected, atol=1e-9
        )
        path = g.Path(steps=tuple(steps))
        actual = path(shape, at(1), alpha)
        np.testing.assert_allclose(actual, expected, atol=1e-9)
        np.testing.assert_allclose(
            np.linalg.norm(actual[:, None] - actual, axis=2),
            np.linalg.norm(shape[:, None] - shape, axis=2),
            atol=1e-9,
        )


ZERO_AXIS: dict[str, Callable[[float, np.ndarray], object]] = {
    "rotation_matrix": g.rotation_matrix,
    "rotation_matrix_transpose": g.rotation_matrix_transpose,
    "rotate_vector": lambda angle, axis: g.rotate_vector(m.RIGHT, angle, axis),
    "quaternion_from_angle_axis": g.quaternion_from_angle_axis,
    "Mobject.rotate": lambda angle, axis: m.Square().rotate(angle, axis=axis),
    "path_along_arc": g.path_along_arc,
    "spiral_path": g.spiral_path,
    "path_along_circles": lambda angle, axis: g.path_along_circles(
        angle, m.ORIGIN, axis
    ),
}


@pytest.mark.parametrize("name", ZERO_AXIS)
@pytest.mark.parametrize("angle", [1.0, -2.5])
def test_a_turn_needs_an_axis(name: str, angle: float) -> None:
    with pytest.raises(ValueError, match="axis"):
        ZERO_AXIS[name](angle, np.zeros(3))

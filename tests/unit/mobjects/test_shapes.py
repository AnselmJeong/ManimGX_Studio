"""Shapes are where their parameters put them.

- An arc runs on its circle from its start angle through its angle: its ends exactly there,
  its points within a thousandth of the radius of the circle; a circle is the arc of a whole
  turn about its center; an arc's center is its circle's, in whatever plane it has been turned
  into. An annulus's boundaries are two circles wound opposite ways; a sector joins its inner
  arc to its outer one, reversed. An arc between two points starts at one and ends at the
  other.
- A tip points along the path at the end it is on, its point on that end: in the plane of the
  screen however the path bends, in space where it ends straight, and where the path's last
  handle has no length too.
- A line's ends, length, vector and angle are its own; `put_start_and_end_on` puts a line's or
  an arrow's ends anywhere, a segment turned back on itself too. An arrow's tip point is where
  it ends, its shaft stops at the tip's base, and scaled, its tip keeps its size.
- A dashed line's ends are the line's, tipped or not, and its handles those of the dashes it
  draws, cut out of its path: its first dash's first and its last dash's last, straight or
  bent; drawn solid, the line's own.
- A screen rectangle keeps its height and its center as its aspect ratio changes; a
  full-screen one is the screen rectangle as tall as the frame.
- A regular polygram walks its vertices in groups, by its density.
- Rounding a polygram's corners cuts each with an arc of the radius tangent to its two sides
  (for a negative radius, that arc mirrored across its chord, into the corner), joined by what
  is left of the sides: each outline closed and apart from the others, in its paint; a radius
  of 0 changes nothing.
"""

import math

import numpy as np
import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st
from tests import oracles
from tests.strategies import arrays, curves

import manimgx as m
from manimgx.mobjects.shapes import TipableVMobject

radii = st.floats(0.1, 10)


turns = st.floats(0.05, 2 * np.pi).flatmap(lambda a: st.sampled_from([a, -a]))


@given(radius=radii, start=st.floats(-7, 7), angle=turns, center=arrays(3, 5))
def test_an_arc_runs_on_its_circle(
    radius: float, start: float, angle: float, center: np.ndarray
) -> None:
    arc = m.Arc(radius=radius, start_angle=start, angle=angle, arc_center=center)
    at = lambda a: center + radius * np.array([np.cos(a), np.sin(a), 0])  # noqa: E731
    np.testing.assert_allclose(arc.points[0], at(start), atol=1e-9 * radius)
    np.testing.assert_allclose(arc.points[-1], at(start + angle), atol=1e-9 * radius)
    drawn = oracles.sample(arc.points, 50)
    np.testing.assert_allclose(
        np.linalg.norm(drawn - center, axis=1), radius, rtol=1e-3
    )
    np.testing.assert_allclose(arc.get_arc_center(), center, atol=1e-9 * (1 + radius))


@given(
    radius=radii,
    angle=turns,
    turn=st.floats(-3, 3),
    axis=arrays(3, 1),
    about=arrays(3, 5),
)
def test_an_arcs_center_turns_with_it(
    radius: float, angle: float, turn: float, axis: np.ndarray, about: np.ndarray
) -> None:
    assume(np.linalg.norm(axis) > 1e-2 and abs(angle) < 2 * np.pi - 1e-2)
    arc = m.Arc(radius=radius, angle=angle).rotate(turn, axis, about_point=about)
    expected = m.rotation_matrix(turn, axis) @ (np.zeros(3) - about) + about
    np.testing.assert_allclose(
        arc.get_arc_center(), expected, atol=1e-7 * (1 + radius + np.abs(about).max())
    )


@given(radius=radii, center=arrays(3, 5))
def test_a_circle_is_a_whole_turn_about_its_center(
    radius: float, center: np.ndarray
) -> None:
    circle = m.Circle(radius=radius).move_to(center)
    np.testing.assert_allclose(circle.get_center(), center, atol=1e-9 * (1 + radius))
    assert circle.width == pytest.approx(2 * radius, rel=1e-9)
    assert circle.is_closed()


@given(radius=radii, width=st.floats(0.2, 3), center=arrays(3, 5))
def test_an_annulus_has_oppositely_wound_circular_boundaries(
    radius: float, width: float, center: np.ndarray
) -> None:
    ring = m.Annulus(
        inner_radius=radius, outer_radius=radius + width, arc_center=center
    )
    outer, inner = ring.get_subpaths()
    for points, size, winding in [(outer, radius + width, 1), (inner, radius, -1)]:
        anchors = points[::4] - center
        np.testing.assert_allclose(np.linalg.norm(anchors, axis=1), size, atol=1e-12)
        area = np.cross(anchors, np.roll(anchors, -1, axis=0)).sum(axis=0)[2]
        assert winding * area > 0
        np.testing.assert_allclose(points[0], points[-1], atol=1e-12)


@pytest.mark.parametrize("solid", [False, True])
@given(radius=radii, start=st.floats(-7, 7), angle=turns, center=arrays(3, 5))
def test_a_sector_joins_its_inner_and_reversed_outer_arcs(
    solid: bool, radius: float, start: float, angle: float, center: np.ndarray
) -> None:
    sector = (
        m.Sector(radius=radius, start_angle=start, angle=angle, arc_center=center)
        if solid
        else m.AnnularSector(
            inner_radius=radius / 2,
            outer_radius=radius,
            start_angle=start,
            angle=angle,
            arc_center=center,
        )
    )
    unit = m.Arc(start_angle=start, angle=angle).points
    n = len(unit)
    np.testing.assert_allclose(
        sector.points[:n], unit * (0 if solid else radius / 2) + center, atol=1e-12
    )
    np.testing.assert_allclose(
        sector.points[n + 4 : -4], unit[::-1] * radius + center, atol=1e-12
    )
    curves = sector.get_cubic_bezier_tuples()
    np.testing.assert_allclose(curves[:, 3], np.roll(curves[:, 0], -1, axis=0))


@given(start=arrays(3, 5), end=arrays(3, 5), angle=turns)
def test_an_arc_between_points_joins_them(
    start: np.ndarray, end: np.ndarray, angle: float
) -> None:
    start[2] = end[2] = 0
    assume(np.linalg.norm(end - start) > 1e-2 and abs(angle) < 2 * np.pi - 1e-2)
    arc = m.ArcBetweenPoints(start, end, angle=angle)
    np.testing.assert_allclose(arc.get_start(), start, atol=1e-9)
    np.testing.assert_allclose(arc.get_end(), end, atol=1e-9)


def arriving(points: np.ndarray) -> np.ndarray:
    """The direction a path comes into its end: from the curve's Taylor expansion there,
    B(1 − s) ≈ B(1) − s B′ + s²/2 B″ − s³/6 B‴, its first derivative at the end that does
    not vanish (none shorter than the tip's tolerance), as the path travels."""
    p0, p1, p2, p3 = points[-4:]
    tolerance = 1e-9 * (1 + np.abs(p3).max())
    for sign, d in (
        (1, p3 - p2),
        (-1, p3 - 2 * p2 + p1),
        (1, p3 - 3 * p2 + 3 * p1 - p0),
    ):
        if np.linalg.norm(d) > tolerance:  # (each a multiple of B′, B″, B‴ at the end)
            return sign * d / np.linalg.norm(d)
    raise AssertionError("a curve of one point has no direction")


@given(points=curves(max_curves=3), collapse=st.booleans(), straight=st.booleans())
def test_a_tip_points_along_the_path_at_its_end(
    points: np.ndarray, collapse: bool, straight: bool
) -> None:
    if straight:  # (its last curve straight, anywhere in space)
        start, end = points[-4], points[-1]
        points[-3], points[-2] = (
            start + (end - start) / 3,
            start + 2 * (end - start) / 3,
        )
    else:  # (bending, in the plane of the screen)
        points[:, 2] = 0
    if collapse:
        points[-2] = points[-1]  # a last handle of no length
    path = TipableVMobject()
    path.points = points
    assume(
        np.linalg.norm(
            oracles.bezier_points(points[-4:], np.array([0.0, 1.0]))[0][1] - points[-4]
        )
        > 1e-3
    )
    direction = arriving(points)
    assume(np.linalg.norm(points[-1] - points[-4]) > 1e-3)
    end = points[-1].copy()
    path.add_tip()
    tip = path.tip
    along = tip.tip_point - tip.base
    np.testing.assert_allclose(tip.tip_point, end, atol=1e-9 * (1 + np.abs(end).max()))
    np.testing.assert_allclose(
        along / np.linalg.norm(along), direction, atol=1e-9 if straight else 2e-3
    )


@given(ends=arrays((2, 3), 10))
def test_a_line_is_its_ends(ends: np.ndarray) -> None:
    start, end = ends
    assume(np.linalg.norm(end - start) > 1e-3)
    line = m.Line(start, end)
    np.testing.assert_allclose(line.get_start(), start, atol=1e-9)
    np.testing.assert_allclose(line.get_end(), end, atol=1e-9)
    assert line.get_length() == pytest.approx(np.linalg.norm(end - start), rel=1e-9)
    np.testing.assert_allclose(line.get_vector(), end - start, atol=1e-9)
    assert line.get_angle() == pytest.approx(
        np.arctan2(*(end - start)[1::-1]), abs=1e-9
    )


@given(ends=arrays((2, 3), 10), new=arrays((2, 3), 10))
@example(  # (turned back on itself along z: it used to keep its direction)
    ends=np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]]),
    new=np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 0.0]]),
)
@example(
    ends=np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]]),
    new=np.array([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]]),
)
def test_put_start_and_end_on_puts_the_ends_there(
    ends: np.ndarray, new: np.ndarray
) -> None:
    for make in (m.Line, lambda a, b: m.Arrow(a, b, buff=0)):
        assume(
            np.linalg.norm(ends[1] - ends[0]) > 1e-2
            and np.linalg.norm(new[1] - new[0]) > 1e-2
        )
        line = make(*ends)
        line.put_start_and_end_on(*new)
        np.testing.assert_allclose(line.get_start(), new[0], atol=1e-7)
        np.testing.assert_allclose(line.get_end(), new[1], atol=1e-7)


@given(ends=arrays((2, 3), 10))
def test_an_arrows_tip_is_where_it_ends(ends: np.ndarray) -> None:
    start, end = ends
    start[2] = end[2] = 0
    assume(np.linalg.norm(end - start) > 0.5)
    arrow = m.Arrow(start, end, buff=0)
    np.testing.assert_allclose(arrow.tip.tip_point, end, atol=1e-9)
    shaft_end = arrow.points[-1]
    np.testing.assert_allclose(shaft_end, arrow.tip.base, atol=1e-6)
    length = arrow.tip.length
    arrow.scale(2)
    assert arrow.tip.length == pytest.approx(length, rel=1e-9)


@given(
    ends=arrays((2, 3), 10),
    path_arc=st.floats(-3, 3).map(lambda a: a if abs(a) >= 0.1 else 0.0),
    dash_length=st.floats(0.01, 4),
    dashed_ratio=st.floats(0.05, 0.95),
    tipped=st.booleans(),
    solid=st.booleans(),
)
@example(  # (60 dashes, each 0.05 long)
    ends=np.array([[-3.0, 0.0, 0.0], [3.0, 0.0, 0.0]]),
    path_arc=0.0,
    dash_length=0.05,
    dashed_ratio=0.5,
    tipped=True,
    solid=False,
)
def test_a_dashed_lines_handles_are_its_end_dashes(
    ends: np.ndarray,
    path_arc: float,
    dash_length: float,
    dashed_ratio: float,
    tipped: bool,
    solid: bool,
) -> None:
    start, end = ends
    start[2] = end[2] = 0
    assume(np.linalg.norm(end - start) > 0.5)
    line = m.DashedLine(
        start,
        end,
        path_arc=path_arc,
        dash_length=dash_length,
        dashed_ratio=dashed_ratio,
    )
    if tipped:
        line.add_tip()
    if solid:
        line.match_style(m.Line())
    # the pieces it draws, cut out of its path: its parameter u where
    # frac((u − phase) / period) < duty, or all of it if it is drawn solid
    period, duty, phase = line.paint.dash or (1.0, 1.0, 0.0)
    starts = phase + period * np.arange(-1, 1 / period + 1)
    windows = np.stack([starts, starts + duty * period], axis=1)
    pieces = np.clip(windows[(windows[:, 0] < 1) & (windows[:, 1] > 0)], 0, 1)
    (a, b), (c, d) = pieces[0], pieces[-1]
    first, last = line.get_subcurve(a, b), line.get_subcurve(c, d)
    np.testing.assert_allclose(line.get_first_handle(), first.points[1], atol=1e-9)
    np.testing.assert_allclose(line.get_last_handle(), last.points[-2], atol=1e-9)
    np.testing.assert_allclose(
        line.get_start(), start, atol=1e-9
    )  # (its ends: the line's)
    np.testing.assert_allclose(line.get_end(), end, atol=1e-9)


@pytest.mark.config(frame_height=7.3)
@pytest.mark.parametrize(("ratio", "height"), [(16 / 9, 4), (4 / 3, 3), (0.7, 2.6)])
def test_a_screen_rectangle_keeps_its_height_as_its_aspect_changes(
    ratio: float, height: float
) -> None:
    screen = m.ScreenRectangle(aspect_ratio=ratio, height=height, color=m.BLUE)
    assert screen.width == pytest.approx(ratio * height)
    assert screen.height == pytest.approx(height)
    screen.shift((1, 2, 0))
    screen.aspect_ratio = 1.5
    np.testing.assert_allclose(screen.get_center(), (1, 2, 0))
    assert screen.width == pytest.approx(1.5 * height)
    assert screen.height == pytest.approx(height)
    full = m.FullScreenRectangle(aspect_ratio=ratio, height=height, color=m.BLUE)
    expected = m.ScreenRectangle(aspect_ratio=ratio, height=height, color=m.BLUE)
    expected.height = m.config.frame_height
    np.testing.assert_array_equal(full.points, expected.points)
    np.testing.assert_array_equal(full.paint.fill, expected.paint.fill)
    assert full.height == pytest.approx(7.3)
    assert full.aspect_ratio == pytest.approx(ratio)


@pytest.mark.parametrize(
    ("n", "density"),
    [(5, 2), (6, 2), (12, 8), (7, -2), (9, 0), (61, 2**60), (61, -(2**60))],
)
@pytest.mark.parametrize("start", [None, 0.31])
def test_polygram_groups_walk_their_vertices_in_density_order(
    n: int, density: int, start: float | None
) -> None:
    shape = m.RegularPolygram(n, density=density, radius=2.3, start_angle=start)
    group_count = math.gcd(n, density)
    group_size = n // group_count
    groups = shape.get_vertex_groups()
    assert len(groups) == group_count
    first = start if start is not None else 0 if group_size % 2 == 0 else np.pi / 2
    assert shape.start_angle == first
    for i, vertices in enumerate(groups):
        index = [(k * (density // group_count)) % group_size for k in range(group_size)]
        angles = first + i * m.TAU / n + m.TAU * np.array(index) / group_size
        expected = 2.3 * np.column_stack(
            (np.cos(angles), np.sin(angles), np.zeros(group_size))
        )
        np.testing.assert_allclose(vertices, expected, atol=1e-12)


@given(
    n=st.integers(3, 8),
    size=st.floats(0.5, 3),
    turn=st.floats(0, 2 * np.pi),
    fraction=st.floats(0.05, 0.9),
    sign=st.sampled_from([1, -1]),
    components=st.integers(2, 6),
    framed=st.booleans(),
)
@example(  # (a square with a square hole: two outlines)
    n=4, size=2**0.5, turn=np.pi / 4, fraction=0.25, sign=1, components=5, framed=True
)
def test_rounding_cuts_each_corner_with_an_arc_tangent_to_its_sides(
    n: int,
    size: float,
    turn: float,
    fraction: float,
    sign: int,
    components: int,
    framed: bool,
) -> None:
    groups = [m.RegularPolygon(n, radius=size, start_angle=turn).get_vertices()]
    if framed:  # (a hole, wound the other way)
        hole = m.RegularPolygon(n, radius=size / 3, start_angle=turn)
        groups.append(hole.get_vertices()[::-1])
    shape = m.Polygram(*groups, color=m.BLUE, fill_opacity=0.4)
    paint, before = shape.paint, shape.points.copy()
    assert shape.round_corners(0) is shape
    np.testing.assert_array_equal(shape.points, before)
    exterior = 2 * np.pi / n  # (each corner turns the outline by it)
    side = min(np.linalg.norm(group[1] - group[0]) for group in groups)
    # (small enough that each arc touches its sides at most halfway along them)
    radius = sign * fraction * side / 2 / np.tan(exterior / 2)
    cut = abs(radius) * np.tan(exterior / 2)
    assert (
        shape.round_corners(radius, components_per_rounded_corner=components) is shape
    )
    assert shape.paint is paint
    paths = shape.get_subpaths()
    assert len(paths) == len(groups)
    for path, corners in zip(paths, groups, strict=True):
        curves = path.reshape(-1, 4, 3)
        assert len(curves) == len(corners) * components
        np.testing.assert_allclose(curves[1:, 0], curves[:-1, 3], atol=1e-9)
        np.testing.assert_allclose(curves[-1, 3], curves[0, 0], atol=1e-9)
        for i, corner in enumerate(corners):
            nearby = corners[i - 1], corners[(i + 1) % len(corners)]
            incoming = (corner - nearby[0]) / np.linalg.norm(corner - nearby[0])
            outgoing = (nearby[1] - corner) / np.linalg.norm(nearby[1] - corner)
            arc = curves[i * components : (i + 1) * components - 1]
            np.testing.assert_allclose(arc[0, 0], corner - cut * incoming, atol=1e-9)
            np.testing.assert_allclose(arc[-1, 3], corner + cut * outgoing, atol=1e-9)
            inward = np.cross(m.OUT, incoming) * np.sign(
                np.cross(incoming, outgoing)[2]
            )
            center = arc[0, 0] + abs(radius) * inward  # (tangent to the sides there)
            if radius < 0:  # (the same arc, mirrored across its chord)
                center = arc[0, 0] + arc[-1, 3] - center
            anchors = np.vstack([arc[:, 0], arc[-1:, 3]])
            np.testing.assert_allclose(
                np.linalg.norm(anchors - center, axis=1), abs(radius), atol=1e-9
            )
            remainder = curves[(i + 1) * components - 1]  # (what is left of the side)
            np.testing.assert_allclose(
                remainder[3], nearby[1] - cut * outgoing, atol=1e-9
            )

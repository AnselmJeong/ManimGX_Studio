"""Spatial shapes are where their parameters put them.

- A spatial arrow's shaft meets its tip, whose apex is the requested end, in any direction.
- A cone's or cylinder's direction replaces the one before, carries its edits, parts and sheen
  about the origin, and comes back to where it was; a spatial line rebuilt between new ends
  starts from a fresh frame.
- A torus is its tube revolved about the axis, starting from the inner side and turning down.
- A polyhedron's faces follow its vertices, the same faces in the same paint.
"""

import numpy as np
import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st
from tests.strategies import arrays

import manimgx as m


@given(ends=arrays((2, 3), 5), height=st.floats(0.05, 0.7))
@example(ends=np.array([[0.0, 0.0, 0.0], [0.0, 2.0**-24, 3.0]]), height=0.5)
@example(ends=np.array([[2.0**-23, 2.0**-23, 0.0], [0.0, 2.0**-23, 4.0]]), height=0.5)
def test_an_arrow_joins_its_shaft_to_its_tip_in_any_direction(
    ends: np.ndarray,
    height: float,
) -> None:
    start, end = ends
    length = np.linalg.norm(end - start)
    assume(length > 2 * height)
    direction = (end - start) / length
    # a direction a hair off the axis turns by its tiny cross product with it: to about the
    # square root of the float precision, of the coordinates
    tolerance = np.sqrt(np.finfo(float).eps) * (1 + np.abs(ends).max())
    arrow = m.Arrow3D(
        start,
        end,
        height=height,
        resolution=6,
        color=m.RED,
        fill_opacity=0.4,
        checkerboard_colors=[m.BLUE, m.YELLOW],
    )
    np.testing.assert_allclose(arrow.base_top.get_center(), start, atol=tolerance)
    np.testing.assert_allclose(
        arrow.base_bottom.get_center(),
        end - height * direction,
        atol=tolerance,
    )
    np.testing.assert_allclose(arrow.cone.points[0], end, atol=tolerance)
    np.testing.assert_allclose(arrow.end_point.get_center(), end, atol=tolerance)
    for surface in [arrow, arrow.cone]:
        assert np.allclose(surface.paint.fill[:, :3], m.RED.to_rgb())
        assert np.allclose(surface.paint.fill[:, 3], 0.4)


@pytest.mark.parametrize("kind", [m.Cone, m.Cylinder])
@given(directions=arrays((3, 3), 5))
def test_successive_directions_replace_each_other_and_round_trip(
    kind: type[m.Cone] | type[m.Cylinder], directions: np.ndarray
) -> None:
    surface = (
        kind(show_base=True, resolution=4)
        if kind is m.Cone
        else m.Cylinder(resolution=4)
    )
    original = [part.points.copy() for part in surface.get_family()]
    sheen = [part.paint.sheen_direction.copy() for part in surface.get_family()]
    for direction in [*directions, m.ORIGIN, m.OUT]:
        assert surface.set_direction(direction) is surface
        axis = (
            surface.points[0] - surface.base_circle.get_center()
            if isinstance(surface, m.Cone)
            else surface.base_bottom.get_center() - surface.base_top.get_center()
        )
        wanted = direction if np.linalg.norm(direction) else m.OUT
        np.testing.assert_allclose(
            axis / np.linalg.norm(axis), wanted / np.linalg.norm(wanted), atol=1e-7
        )
    for part, points, expected_sheen in zip(
        surface.get_family(), original, sheen, strict=True
    ):
        np.testing.assert_allclose(part.points, points, atol=1e-12)
        np.testing.assert_allclose(
            part.paint.sheen_direction, expected_sheen, atol=1e-12
        )


@pytest.mark.parametrize("kind", [m.Cone, m.Cylinder])
def test_directions_carry_edits_children_and_sheen_about_the_origin(
    kind: type[m.Cone] | type[m.Cylinder],
) -> None:
    surface = kind(resolution=4)
    surface.add(m.Line(m.ORIGIN, m.RIGHT))
    surface.shift((1, 2, 3)).stretch(0.7, 0).set_sheen(0.5, m.UP).rotate(m.PI / 4)
    points = [part.points.copy() for part in surface.get_family()]
    sheen = [part.paint.sheen_direction.copy() for part in surface.get_family()]
    for direction, indices, signs in [
        (m.UP, [1, 2, 0], [-1, 1, -1]),
        (m.RIGHT, [2, 1, 0], [1, 1, -1]),
    ]:
        surface.set_direction(direction)
        for part, original, light in zip(
            surface.get_family(), points, sheen, strict=True
        ):
            np.testing.assert_allclose(
                part.points, original[:, indices] * signs, atol=1e-12
            )
            np.testing.assert_allclose(
                part.paint.sheen_direction, light[indices] * signs, atol=1e-12
            )


def test_rebuilding_a_spatial_line_resets_its_direction_frame() -> None:
    line = m.Line3D((-1, 2, 3), (4, -2, -1), resolution=4)
    line.set_direction(m.UP)
    start, end = np.array([2, -3, 1]), np.array([-3, 2, -1])
    line.set_start_and_end_attrs(start, end)
    np.testing.assert_allclose(line.base_top.get_center(), start, atol=1e-12)
    np.testing.assert_allclose(line.base_bottom.get_center(), end, atol=1e-12)


@given(radius=st.floats(0.3, 5), tube_fraction=st.floats(0.05, 0.9))
def test_a_torus_revolves_its_tube_from_the_inner_side_downward(
    radius: float, tube_fraction: float
) -> None:
    tube = radius * tube_fraction
    torus = m.Torus(major_radius=radius, minor_radius=tube, resolution=(5, 7))
    x, y, z = torus.points.T
    np.testing.assert_allclose(
        (np.hypot(x, y) - radius) ** 2 + z**2, tube**2, atol=1e-12
    )
    for u, v, point in [
        (0, 0, (radius - tube, 0, 0)),
        (0, m.PI / 2, (radius, 0, -tube)),
        (0, m.PI, (radius + tube, 0, 0)),
        (m.PI / 2, 0, (0, radius - tube, 0)),
    ]:
        np.testing.assert_allclose(torus.func(u, v), point, atol=1e-12)


@given(vertices=arrays((5, 3), 5))
def test_faces_follow_vertices_without_replacing_their_identity_or_style(
    vertices: np.ndarray,
) -> None:
    faces = [[0, 1, 2, 3], [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]
    poly = m.Polyhedron(
        [[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0], [0, 0, 1]],
        faces,
        graph_config={"vertex_type": m.VectorizedPoint},
    )
    original_faces = list(poly.faces)
    for i, face in enumerate(poly.faces):
        face.set_color(m.RED if i % 2 else m.BLUE).set_opacity((i + 1) / 5)
    paints = [face.paint for face in poly.faces]
    for i, vertex in enumerate(vertices):
        poly.graph[i].move_to(vertex)
    assert poly.update_faces(poly) is poly
    for face, original, paint, indices in zip(
        poly.faces, original_faces, paints, faces, strict=True
    ):
        assert face is original
        assert face.paint is paint
        np.testing.assert_allclose(
            face.get_start_anchors(), vertices[indices], atol=1e-9
        )
        np.testing.assert_allclose(
            face.get_end_anchors()[-1], vertices[indices[0]], atol=1e-9
        )

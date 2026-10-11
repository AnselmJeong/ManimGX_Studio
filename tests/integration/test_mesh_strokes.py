"""A mesh's nearest outlined face is visible, independently of face and object order."""

import itertools

import numpy as np
import pytest

import manimgx as m
from manimgx import _engine
from manimgx.rendering import feed

SIZE = (160, 90)


def outlined_faces(
    depths: tuple[float, ...], *, filled: bool, occluder_first: bool, samples: int
) -> np.ndarray:
    """Coincident projected squares; a red square lies between their depths."""
    player = _engine.Player(*SIZE, samples)
    camera = m.Camera(three_d=True, focal_distance=20)
    view, _, _ = feed.view(camera, *SIZE)

    def mesh(
        key: int, planes: tuple[float, ...], extent: float, *, filled: bool
    ) -> None:
        loop = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]])
        # Perspective maps every face to the same square. The nearest one wholly hides
        # the others; reversing the mesh's face order cannot change its picture.
        vertices = np.concatenate(
            [
                np.column_stack([loop * extent * (1 - z / 20), np.full(len(loop), z)])
                for z in planes
            ]
        ).astype("<f8")
        triangles = np.concatenate(
            [np.array([0, 1, 2, 0, 2, 3]) + 5 * i for i in range(len(planes))]
        ).astype("<u4")
        player.add_mesh(
            key,
            vertices.tobytes(),
            np.zeros((len(vertices), 2), "<f8").tobytes(),
            np.tile([0.0, 0.0, 1.0], (len(vertices), 1)).astype("<f8").tobytes(),
            triangles.tobytes() if filled else b"",
            5,
            5,
        )

    mesh(1, depths, 2, filled=filled)
    mesh(2, (5.0,), 3, filled=True)
    records = np.zeros(2, feed.RECORD)
    records["key1"] = [1, 2]
    records["m1"][:, :, :3] = np.eye(3)
    records["fill"][0] = [0.125, 0.25, 0.75, float(filled)]
    records["stroke"][0] = [0.875, 0.875, 0.875, 1]
    records["params"][0] = [0, len(depths), 0.2, 0]
    records["fill"][1] = [0.75, 0.125, 0.125, 1]
    records["params"][1] = [0, 1, 0, 0]
    if occluder_first:
        records = records[::-1].copy()
    return np.frombuffer(player.render(view, records.tobytes()), np.uint8).reshape(
        SIZE[1], SIZE[0], 4
    )


@pytest.mark.parametrize("filled", [False, True], ids=["stroke-only", "filled"])
@pytest.mark.parametrize("occluder_first", [False, True])
@pytest.mark.parametrize("samples", [1, 4])
def test_mesh_strokes_keep_the_nearest_face_in_every_order(
    filled: bool, occluder_first: bool, samples: int
) -> None:
    def picture(depths: tuple[float, ...]) -> np.ndarray:
        return outlined_faces(
            depths, filled=filled, occluder_first=occluder_first, samples=samples
        )

    expected = picture((10.0,))
    np.testing.assert_array_equal(
        expected[SIZE[1] // 2, SIZE[0] // 2, :3],
        [32, 64, 191] if filled else [191, 32, 32],
    )
    for depths in itertools.permutations((0.0, 2.0, 10.0)):
        np.testing.assert_array_equal(picture(depths), expected)


def test_a_normal_magnitude_cannot_change_an_outlined_planes_visibility() -> None:
    """The same tilted plane, with equivalent normals across forty binary orders."""
    view, _, _ = feed.view(m.Camera(three_d=True), *SIZE)
    points = np.array(
        [[-2, -2, -2], [2, -2, 2], [2, 2, 2], [-2, 2, -2], [-2, -2, -2]], "<f8"
    )
    records = np.zeros(1, feed.RECORD)
    records["key1"] = 1
    records["m1"][0, :, :3] = np.eye(3)
    records["fill"] = [0.125, 0.25, 0.75, 1]
    records["stroke"] = [0.875, 0.875, 0.875, 1]
    records["params"] = [0, 1, 0.5, 0]

    def picture(scale: float) -> np.ndarray:
        player = _engine.Player(*SIZE, 4)
        player.add_mesh(
            1,
            points.tobytes(),
            np.zeros((len(points), 2), "<f8").tobytes(),
            (np.tile([-1.0, 0.0, 1.0], (len(points), 1)) * scale)
            .astype("<f8")
            .tobytes(),
            np.array([0, 1, 2, 0, 2, 3], "<u4").tobytes(),
            5,
            5,
        )
        return np.frombuffer(player.render(view, records.tobytes()), np.uint8)

    expected = picture(1.0)
    for exponent in [-20, -10, 10, 20]:
        np.testing.assert_array_equal(picture(2.0**exponent), expected)

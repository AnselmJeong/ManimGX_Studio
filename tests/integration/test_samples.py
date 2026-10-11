"""Antialiasing changes edge coverage, never depth ordering or transparency."""

from itertools import permutations

import numpy as np
import pytest

import manimgx as m
from manimgx import _engine
from manimgx.rendering import feed

SIZE = (160, 90)
RED = np.array([0.75, 0.125, 0.125])
BLUE = np.array([0.125, 0.125, 0.75])


@pytest.mark.parametrize("samples", [1, 4])
@pytest.mark.parametrize("alpha", [0.0, 0.25, 0.5, 1.0])
@pytest.mark.parametrize("order", [(0, 1), (1, 0)])
def test_a_foreground_mesh_obscures_only_its_opacity(
    samples: int, alpha: float, order: tuple[int, int]
) -> None:
    player = _engine.Player(*SIZE, samples)
    view, _, _ = feed.view(m.Camera(three_d=True, focal_distance=20), *SIZE)
    for key, z in ((1, 10), (2, 5)):
        # Both quads project to the same square; the center is far from every edge.
        xy = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]]) * 2 * (1 - z / 20)
        points = np.column_stack([xy, np.full(4, z)]).astype("<f8")
        player.add_mesh(
            key,
            points.tobytes(),
            np.zeros((4, 2), "<f8").tobytes(),
            np.tile([0, 0, 1], (4, 1)).astype("<f8").tobytes(),
            np.array([0, 1, 2, 0, 2, 3], "<u4").tobytes(),
        )
    records = np.zeros(2, feed.RECORD)
    records["key1"] = [1, 2]
    records["m1"][:, :, :3] = np.eye(3)
    records["fill"] = [[*BLUE, alpha], [*RED, 1]]
    records["params"][:, 1] = 2
    pixels = np.frombuffer(
        player.render(view, records[list(order)].tobytes()), np.uint8
    ).reshape(SIZE[1], SIZE[0], 4)
    expected = 255 * (alpha * BLUE + (1 - alpha) * RED)
    assert np.abs(pixels[SIZE[1] // 2, SIZE[0] // 2, :3] - expected).max() <= 1


@pytest.mark.parametrize("samples", [1, 4])
@pytest.mark.parametrize("meshes", [False, True])
@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_points_between_layers_keep_the_same_composite_at_each_sample_count(
    samples: int, meshes: bool, order: tuple[int, ...]
) -> None:
    player = _engine.Player(*SIZE, samples)
    feeder = feed.Feeder(*SIZE, player)
    camera = m.Camera(three_d=True)
    opacity = 0.4
    colors = (m.RED, m.GREEN, m.BLUE)
    layers: list[m.Mobject] = []
    for i, color in enumerate(colors):
        if i == 1:
            mob = m.PMobject(stroke_width=180).add_points(
                [m.ORIGIN], color=color, alpha=opacity
            )
        elif meshes:
            mob = m.MeshMobject(
                np.array([[-10, -10, 0], [10, -10, 0], [10, 10, 0], [-10, 10, 0]]),
                np.array([[0, 1, 2], [0, 2, 3]]),
                color=color,
                fill_opacity=opacity,
            )
        else:
            mob = m.Square(
                side_length=20, color=color, fill_opacity=opacity, stroke_width=0
            )
        layers.append(mob.shift(i * m.OUT))
    pixels = np.frombuffer(
        player.render(*feeder.frame(camera, [layers[i] for i in order])), np.uint8
    ).reshape(SIZE[1], SIZE[0], 4)
    expected = np.zeros(3)
    for color in colors:
        expected = opacity * m.ManimColor(color).to_rgb() + (1 - opacity) * expected
    assert np.abs(pixels[SIZE[1] // 2, SIZE[0] // 2, :3] - 255 * expected).max() <= 2


def test_material_layers_keep_the_same_interior_color_at_each_sample_count() -> None:
    layers: list[m.Mobject] = [m.AmbientLight(intensity=0.5)]
    for z, color, alpha in [(0, m.RED, 1), (1, m.BLUE, 0.4)]:
        layers.append(
            m.MeshMobject(
                np.array([[-10, -10, z], [10, -10, z], [10, 10, z], [-10, 10, z]]),
                np.array([[0, 1, 2], [0, 2, 3]]),
                color=color,
                fill_opacity=alpha,
            ).set_material(m.Material(roughness=1))
        )
    images: list[np.ndarray] = []
    for samples in [1, 4]:
        player = _engine.Player(*SIZE, samples)
        feeder = feed.Feeder(*SIZE, player)
        pixels = np.frombuffer(
            player.render(*feeder.frame(m.Camera(three_d=True), layers)), np.uint8
        ).reshape(SIZE[1], SIZE[0], 4)
        images.append(pixels[SIZE[1] // 2, SIZE[0] // 2, :3].astype(int))
    assert images[0].max() > 20
    assert np.abs(images[0] - images[1]).max() <= 1

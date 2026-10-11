"""A reveal moves through every shape by the same steps, each shown whole with all it draws.

- u counts a shape's steps: a path's curves, a cloud's points, a mesh's triangles, a surface's
  faces. A reveal (`Create`, `Uncreate`, `ShowPassingFlash`) shows every step its window
  reaches into.
- A surface's face shows with its edges, and its edges only with it: none before the reveal
  reaches the face, whatever colors it (its fill, or a colorscale by value).
- A point shows once the reveal reaches into it.
- A part (`pointwise_become_partial`) draws what a reveal over its stretch shows: a surface's
  part is a surface, its faces as smooth and with the edges they have in the whole.
"""

from collections.abc import Callable

import numpy as np
import pytest

import manimgx as m
from manimgx.config import config
from manimgx.rendering.film import Frame

W, H = 640, 360


def _frames(
    build: Callable[[m.Scene], None], monkeypatch: pytest.MonkeyPatch
) -> list[np.ndarray]:
    """Every frame of a scene whose construct is `build`: red, green and blue, from 0 to 1."""
    monkeypatch.setattr(config, "pixel_width", W)
    monkeypatch.setattr(config, "pixel_height", H)
    monkeypatch.setattr(config, "frame_rate", 10)
    shown: list[np.ndarray] = []

    def sink(frame: Frame) -> None:
        pixels = np.frombuffer(frame.pixels(), np.uint8).reshape(H, W, 4)[..., :3]
        shown.extend([pixels.astype(float) / 255] * frame.repeat)

    class Scene(m.Scene):
        def construct(self) -> None:
            build(self)

    Scene().render(frames=sink)
    return shown


def _column(x: float) -> int:
    """The pixel column holding scene x."""
    return int(np.floor(W / 2 + x * W / config.frame_width))


def _sheet(by_value: bool) -> m.Surface:
    """A flat sheet over [-2, 2] by [-1, 1], 8 faces along x (u: the reveal's order) by 4:
    blue, with white edges, so a frame's red is its edges alone."""
    sheet = m.Surface(
        lambda u, v: np.array([u, v, 0.0]),
        u_range=(-2, 2),
        v_range=(-1, 1),
        resolution=(8, 4),
        checkerboard_colors=False,
        fill_color=m.PURE_BLUE,
    )
    if by_value:  # its colors a colorscale's: a picture, at v = 0.5 on every vertex
        sheet.set_fill_by_value(
            m.ThreeDAxes(), colorscale=[(m.PURE_BLUE, -1), (m.PURE_BLUE, 1)]
        )
    return sheet.set_stroke(m.WHITE, width=4, opacity=1)


@pytest.mark.parametrize("by_value", [False, True], ids=["filled", "by-value"])
def test_a_surface_shows_each_face_with_its_edges_as_the_reveal_reaches_it(
    by_value: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    def build(scene: m.Scene) -> None:
        scene.play(m.Create(_sheet(by_value)), run_time=1, rate_func=m.linear)

    frames = _frames(build, monkeypatch)
    edges, faces = [f[..., 0] for f in frames], [f[..., 2] for f in frames]
    assert edges[0].max() == 0
    assert faces[0].max() == 0
    # at 10 fps, 3/10 of the 32 faces reach into the 10th (to x = -0.5), 5/10 to the 16th (0)
    for k, front in ((3, -0.5), (5, 0.0)):
        past, before = _column(front) + 4, _column(front) - 4
        assert edges[k][:, past:].max() == 0, "an edge shows past the faces drawn"
        assert faces[k][:, past:].max() == 0
        assert edges[k][:, :before].max() > 0.5, "the faces drawn show no edges"
    assert edges[-1][:, _column(1.5)].max() > 0.5


@pytest.mark.parametrize(("a", "b"), [(0.0, 0.5), (0.3, 0.8)])
def test_a_surface_part_draws_what_a_reveal_over_its_stretch_shows(
    a: float, b: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    def part(scene: m.Scene) -> None:
        sheet = _sheet(by_value=False)
        scene.add(sheet.copy().pointwise_become_partial(sheet, a, b))

    def revealed(scene: m.Scene) -> None:
        sheet = _sheet(by_value=False)
        sheet.paint = sheet.paint.but(trim=np.array([a, b]))
        scene.add(sheet)

    shown = _frames(part, monkeypatch)[-1]
    assert shown[..., 0].max() > 0.5  # its edges
    np.testing.assert_array_equal(shown, _frames(revealed, monkeypatch)[-1])


def test_a_point_shows_once_the_reveal_reaches_into_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    xs = (-3.0, -1.0, 1.0, 3.0)

    def build(scene: m.Scene) -> None:
        cloud = m.PMobject(stroke_width=20)
        cloud.add_points([[x, 0, 0] for x in xs], color=m.WHITE)
        scene.play(m.Create(cloud), run_time=1, rate_func=m.linear)

    frames = _frames(build, monkeypatch)
    shown = [[bool(f[H // 2, _column(x), 0] > 0.5) for x in xs] for f in frames]
    assert shown[0] == [False] * 4
    assert shown[1] == [True, False, False, False]  # 1/10 of 4 points reaches into one
    assert shown[3] == [True, True, False, False]  # 3/10 of 4: into the second
    assert shown[-1] == [True] * 4

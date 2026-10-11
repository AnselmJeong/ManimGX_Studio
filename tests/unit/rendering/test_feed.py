"""The feed hands the player each shape as its object defines it, named by its content, and
keeps the player's store in step with its own books; the player derives what drawing needs.

- An upload is named by its content: `digest` reads its parts as one stream, wherever they are
  split, tells apart content that differs by a bit, and is never 0, the key no upload may have.
- A smooth mesh's normals are the player's own: each vertex's is the sum of its faces'
  (b − a) × (c − a) (`oracles.area_weighted_normals`), to the bit: a lit mesh is drawn exactly
  as it is with those normals given.
- The player takes a mesh whose texture coordinates, normals and triangles fit its points,
  and refuses one whose do not.
- A record's reveal window is over u, which counts its shape's steps: a path's curves, a
  cloud's points, a mesh's triangles, a surface's faces.
- A surface's part uploads the faces it draws, cut from its whole lattice as it draws them.
- A batch of a reveal's frames has each frame's window, as the frame alone would.
- A path and a cloud of points drawn in one frame draw as each does alone.
- Over any run of frames of any mobjects (paths, graded paths, colored clouds and meshes,
  surfaces, images; moved, copied, recolored, stretched, morphed, turned partway into
  another shape, cut to a part), idle time, sweeps, and uploads or evictions that fail:
  what the feed counts resident is what the player holds; nothing is uploaded while it is
  resident, nothing evicted that is not (a path that draws nothing, an upload that failed),
  and a key names one content of one kind for good (a shape's affine class: its floats to a
  class's precision, since the class made again from other points may differ in its last
  bits); a frame draws only what is resident, a path from paths, a cloud from points, a
  mesh from meshes, its rows the brush its mobject shows (a row for each vertex of a mesh
  as sent), its textures the image's pixels; an upload given directly names its content as
  it is then (a texture is borrowed: by identity); and nothing the caller let go of
  outlives the sweep that finds its key stale.
"""

import contextlib
import gc
import weakref
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule
from tests import oracles
from tests.scenes import frames, scene_3d

import manimgx as m
from manimgx._engine import Player, Recorder, digest
from manimgx.rendering import feed


def _legacy_patches(
    cells: np.ndarray, x: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate patches as the feed did before points-only evaluation."""
    value, slope = feed._hermite(x)
    along_t = np.einsum("bq,abuvd->auvqd", value, cells)
    points = np.einsum("ap,auvqd->uvpqd", value, along_t)
    ds = np.einsum("ap,auvqd->uvpqd", slope, along_t)
    dt = np.einsum("ap,bq,abuvd->uvpqd", value, slope, cells, optimize=True)
    return points, ds, dt


def _surface_grid(kind: str) -> np.ndarray:
    if kind == "realistic":
        u = v = np.linspace(-3.0, 3.0, 49)
    elif kind == "strided":
        u, v = np.linspace(-2.0, 2.0, 9), np.linspace(-1.0, 1.0, 11)
    else:
        u = np.linspace(0.0, 2 * np.pi, 9) if kind != "plain" else np.linspace(-1, 1, 4)
        v = np.linspace(0.0, np.pi, 7) if kind == "pole" else np.linspace(-1, 1, 6)
    s, t = np.meshgrid(u, v, indexing="ij")
    if kind == "periodic":
        xyz = np.stack([np.cos(s), np.sin(s), t + 0.2 * np.cos(2 * s)], axis=-1)
    elif kind == "pole":
        xyz = np.stack(
            [np.sin(t) * np.cos(s), np.sin(t) * np.sin(s), np.cos(t)], axis=-1
        )
    else:
        xyz = np.stack([s, t, 0.8 * np.sin(2 * np.hypot(s, t))], axis=-1)
    grid = np.concatenate([xyz, np.stack([s, t], axis=-1)], axis=-1)
    return grid[::2, ::2] if kind == "strided" else grid


def _legacy_refine_surface(
    grid: np.ndarray, steps: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Refine a surface with the former contractions and two-axis gather."""
    x = np.linspace(0.0, 1.0, steps + 1)
    cells = feed._cells(grid)
    points, ds, dt = _legacy_patches(cells, x)
    normal = np.cross(ds[..., :3], dt[..., :3])
    thin = (
        np.linalg.norm(normal, axis=-1)
        <= 1e-10 * (1.0 + np.abs(grid[..., :3]).max()) ** 2
    )
    if thin.any():
        i, j = np.nonzero(thin.any(axis=(2, 3)))
        _, ds, dt = _legacy_patches(
            cells[:, :, i, j][:, :, None], 1e-3 + (1.0 - 2e-3) * x
        )
        nudged = np.cross(ds[..., :3], dt[..., :3])[0]
        normal[i, j] = np.where(thin[i, j][..., None], nudged, normal[i, j])
    order, triangles = feed._face_layout(steps)
    block, faces = len(order), (len(grid) - 1) * (grid.shape[1] - 1)
    points = points[:, :, order[:, 0], order[:, 1]].reshape(faces * block, -1)
    normal = normal[:, :, order[:, 0], order[:, 1]].reshape(faces * block, 3)
    offsets = np.arange(faces)[:, None, None] * block
    return points, normal, (triangles[None] + offsets).reshape(-1, 3), block


@pytest.mark.parametrize(
    ("kind", "steps"),
    [("plain", 1), ("strided", 2), ("periodic", 4), ("pole", 8), ("realistic", 16)],
)
def test_surface_patch_simplifications_are_bit_exact(kind: str, steps: int) -> None:
    grid = _surface_grid(kind)
    if kind == "strided":
        assert not grid.flags.c_contiguous
    cells = feed._cells(grid)
    x = np.linspace(0.0, 1.0, steps + 1)
    expected = _legacy_patches(cells, x)
    points_only = feed._patches(cells, x, derivatives=False)
    assert len(points_only) == 1
    assert points_only[0].tobytes() == expected[0].tobytes()
    del points_only
    actual = feed._patches(cells, x)
    assert actual[0].tobytes() == expected[0].tobytes()
    assert actual[1].tobytes() == expected[1].tobytes()
    assert actual[2].tobytes() == expected[2].tobytes()


@pytest.mark.parametrize(
    ("kind", "steps"),
    [("plain", 1), ("strided", 2), ("periodic", 4), ("pole", 8), ("realistic", 16)],
)
def test_surface_refinement_gather_keeps_every_result(kind: str, steps: int) -> None:
    grid = _surface_grid(kind)
    expected = _legacy_refine_surface(grid, steps)
    actual = feed.refine_surface(grid, steps)
    assert all(
        a.tobytes() == b.tobytes()
        for a, b in zip(actual[:3], expected[:3], strict=True)
    )
    assert actual[3] == expected[3]


def test_surface_step_selection_keeps_its_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grid = _surface_grid("pole")
    original = feed._patches

    linear = np.array([[1.2, 0.1, 0.0], [0.0, 0.8, 0.2], [0.3, 0.0, 1.1]])
    mid = _legacy_patches(feed._cells(grid[..., :3]), np.array([0.5]))[0][:, :, 0, 0]
    flat = (
        grid[:-1, :-1, :3] + grid[1:, :-1, :3] + grid[:-1, 1:, :3] + grid[1:, 1:, :3]
    ) / 4
    deviation = float(np.linalg.norm((mid - flat) @ linear.T, axis=-1).max())
    selected = int(
        np.clip(
            np.ceil(np.sqrt(deviation / feed.SURFACE_TOLERANCE)),
            1,
            feed.SURFACE_STEPS,
        )
    )
    requests: list[bool] = []

    def tracked(
        cells: np.ndarray, x: np.ndarray, *, derivatives: bool = True
    ) -> tuple[np.ndarray, ...]:
        requests.append(derivatives)
        return original(cells, x, derivatives=derivatives)

    monkeypatch.setattr(feed, "_patches", tracked)
    assert feed.surface_steps(grid, linear) == selected
    assert requests == [False]


class TestDigest:
    @given(data=st.binary(max_size=2048), cut=st.integers(0, 2048))
    def test_it_reads_its_parts_as_one_stream(self, data: bytes, cut: int) -> None:
        cut = min(cut, len(data))
        assert digest(data[:cut], data[cut:]) == digest(data) == digest(b"", data, b"")

    @given(
        data=st.binary(min_size=1, max_size=512),
        at=st.integers(0),
        bit=st.integers(0, 7),
    )
    def test_it_tells_apart_content_that_differs_by_a_bit(
        self, data: bytes, at: int, bit: int
    ) -> None:
        changed = bytearray(data)
        changed[at % len(data)] ^= 1 << bit
        assert digest(bytes(changed)) != digest(data)

    @given(data=st.binary(max_size=512))
    def test_it_is_never_0(self, data: bytes) -> None:
        assert digest(data) != 0


def bumpy_sphere(seed: int) -> tuple[np.ndarray, np.ndarray]:
    """A sphere's grid of points, pushed in and out at random, and its triangles."""
    rng = np.random.default_rng(seed)
    u, v = np.meshgrid(np.linspace(0, 2 * np.pi, 24), np.linspace(0.2, 2.9, 12))
    r = 2 + 0.3 * rng.random(u.shape)
    points = np.stack(
        [r * np.sin(v) * np.cos(u), r * np.sin(v) * np.sin(u), r * np.cos(v)], -1
    ).reshape(-1, 3)
    i, j = np.meshgrid(np.arange(11), np.arange(23), indexing="ij")
    a, b, c, d = i * 24 + j, (i + 1) * 24 + j, (i + 1) * 24 + j + 1, i * 24 + j + 1
    triangles = np.concatenate(
        [np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)]
    )
    return points, triangles


class GivenNormals:
    """The player, with a smooth mesh's normals given: the oracle's."""

    def __init__(self, *args: int) -> None:
        self.player = Player(*args)

    def __getattr__(self, name: str) -> object:
        return getattr(self.player, name)

    def add_mesh(
        self,
        key: int,
        points: bytes,
        uvs: bytes,
        normals: bytes,
        triangles: bytes,
        outline: int = 0,
        block: int = 0,
    ) -> None:
        if not normals:
            p = np.frombuffer(points, "<f8").reshape(-1, 3)
            t = np.frombuffer(triangles, "<u4").reshape(-1, 3).astype(np.int64)
            normals = oracles.area_weighted_normals(p, t).tobytes()
        self.player.add_mesh(key, points, uvs, normals, triangles, outline, block)


def picture(seed: int) -> np.ndarray:
    """The first frame of a lit bumpy sphere, seen from above and aside."""
    points, triangles = bumpy_sphere(seed)

    def construct(scene: m.ThreeDScene) -> None:
        scene.set_camera_orientation(phi=60 * m.DEGREES, theta=-50 * m.DEGREES)
        scene.add(m.MeshMobject(points, triangles, shade_in_3d=True))
        scene.wait(0.1)

    return frames(scene_3d(construct))[0]


@pytest.mark.config(pixel_width=320, pixel_height=180)
@pytest.mark.parametrize("seed", [0, 1])
def test_a_lit_mesh_is_drawn_with_the_normals_its_faces_sum_to(
    seed: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    derived = picture(seed)
    monkeypatch.setattr(feed, "Player", GivenNormals)
    given_normals = picture(seed)
    assert np.array_equal(derived, given_normals)
    assert derived[..., :3].any()  # something was drawn


MESHES: dict[str, tuple[dict[str, np.ndarray], bool]] = {  # a mesh's changes; taken?
    "as it is": ({}, True),
    "with normals": ({"normals": np.ones((4, 3))}, True),
    "uvs for 3 points of 4": ({"uvs": np.zeros((3, 2))}, False),
    "normals for 3 points of 4": ({"normals": np.ones((3, 3))}, False),
    "a point it lacks": ({"triangles": np.array([[0, 1, 4]])}, False),
    "part of a triangle": ({"triangles": np.array([0, 1, 2, 3])}, False),
}


@pytest.mark.parametrize("name", MESHES)
@pytest.mark.parametrize("sink", [Player, Recorder])
def test_a_mesh_is_taken_if_it_fits_its_points(
    name: str, sink: type[Player] | type[Recorder]
) -> None:
    changes, taken = MESHES[name]
    mesh = {
        "points": np.zeros((4, 3)),
        "uvs": np.zeros((4, 2)),
        "normals": np.zeros((0, 3)),
        "triangles": np.array([[0, 1, 2], [1, 2, 3]]),
    } | changes

    def add() -> None:
        sink(16, 16, 1).add_mesh(
            1,
            np.asarray(mesh["points"], "<f8").tobytes(),
            np.asarray(mesh["uvs"], "<f8").tobytes(),
            np.asarray(mesh["normals"], "<f8").tobytes(),
            np.asarray(mesh["triangles"], "<u4").tobytes(),
        )

    if taken:
        add()
    else:
        with pytest.raises(ValueError, match="mesh"):
            add()


@pytest.mark.parametrize("sink", [Player, Recorder])
def test_mesh_uploads_reserve_key_zero(sink: type[Player] | type[Recorder]) -> None:
    with pytest.raises(ValueError, match="key 0 is reserved"):
        sink(16, 16, 1).add_mesh(0, b"", b"", b"", b"")


@pytest.mark.parametrize("start_paced", [False, True])
@pytest.mark.parametrize("end_paced", [False, True])
def test_batched_reveals_follow_the_same_pace_as_individual_frames(
    start_paced: bool, end_paced: bool
) -> None:
    start = m.VMobject().set_points_as_corners([m.ORIGIN, m.RIGHT, 4 * m.RIGHT])
    end = start.copy()
    start.paint = start.paint.but(
        trim=np.array([0.1, 0.4]),
        pace=start.reveal_pace() if start_paced else None,
    )
    end.paint = end.paint.but(
        trim=np.array([0.2, 0.7]),
        pace=(
            (np.array([0.0, 0.75, 1.0]), np.array([0.0, 1.0, 2.0]))
            if end_paced
            else None
        ),
    )
    camera = m.Camera()
    feeder = feed.Feeder(32, 32, Recorder(32, 32, 10))
    objects: list[m.Mobject] = [start, end]
    cameras: list[feed.CameraView] = []
    fixed: set[m.Mobject] = set()
    args = (camera, False, objects, 32, 32, cameras, fixed)
    live = feed.unpack(feeder.record(start, *args))
    progress = np.array([0.8, 0.0, 0.2, 1.0, 0.5, 0.2, -0.1, 1.2])

    batch = feeder.mix(start, end, m.straight_path(), progress, args, live)

    assert batch is not None
    expected = np.array(
        [
            start.paint.mixed(start.paint, end.paint, float(t)).window(2)
            for t in progress
        ],
        dtype=np.float32,
    )
    np.testing.assert_array_equal(batch["params"][:, :2], expected)


def record_of(mob: m.Mobject, sink: "Sink | Recorder") -> np.void:
    """The record a feed of its own makes of a mobject alone, in a 2D view."""
    feeder = feed.Feeder(32, 32, sink)  # ty: ignore[invalid-argument-type]
    objects: list[m.Mobject] = [mob]
    made = feed.unpack(
        feeder.record(mob, m.Camera(), False, objects, 32, 32, [], set())
    )
    assert made is not None
    return made


@pytest.mark.parametrize("trim", [(0.0, 1.0), (0.25, 0.5), (-0.1, 0.0)])
def test_a_records_window_is_over_its_shapes_steps(trim: tuple[float, float]) -> None:
    corners = np.array([[0.0, 0, 0], [1.0, 0, 0], [0.0, 1, 0], [1.0, 1, 0]])
    surface = m.Surface(lambda u, v: np.array([u, v, 0.0]), resolution=(2, 3))
    shapes: list[tuple[m.Mobject, int]] = [
        (m.VMobject().set_points_as_corners([m.ORIGIN, m.RIGHT, m.UP]), 2),
        (m.PMobject().add_points(np.zeros((8, 3))), 8),
        (m.MeshMobject(corners, np.array([[0, 1, 2], [1, 3, 2], [0, 1, 3]])), 3),
        (surface, 6),
    ]
    for mob, steps in shapes:
        mob.paint = mob.paint.but(trim=np.array(trim))
        window = record_of(mob, Recorder(32, 32, 10))["params"][:2]
        np.testing.assert_allclose(window, np.array(trim) * steps, rtol=1e-6)


def test_a_surfaces_part_uploads_its_faces_as_its_whole_lattice_draws_them() -> None:
    whole = m.Surface(
        lambda u, v: np.array([u, v, u * v]), resolution=(4, 3)
    )  # 12 faces
    part = whole.copy().pointwise_become_partial(whole, 0.25, 0.5)  # faces 3 to 6
    sinks = Sink(), Sink()
    windows = [
        record_of(mob, sink)["params"][:2] for mob, sink in zip((whole, part), sinks)
    ]
    uploads = [
        next(sink.parts[key] for key, kind in sink.kinds.items() if kind == "mesh")
        for sink in sinks
    ]
    (points, _), _, (normals, _), (triangles, _), (sizes, _) = uploads[0]
    outline, block = (int(x) for x in sizes.split())
    (p, _), _, (n, _), (t, _), (part_sizes, _) = uploads[1]
    assert part_sizes == sizes

    def floats(data: bytes) -> np.ndarray:
        return np.frombuffer(data, "<f8").reshape(-1, 3)

    drawn = slice(3 * block, 6 * block)
    np.testing.assert_array_equal(floats(p), floats(points)[drawn])
    np.testing.assert_array_equal(floats(n), floats(normals)[drawn])
    every = np.frombuffer(triangles, "<u4")
    per = len(every) // 12  # a face's triangles' indices
    np.testing.assert_array_equal(
        np.frombuffer(t, "<u4"), every[3 * per : 6 * per] - 3 * block
    )
    assert outline > 2
    assert tuple(windows[0]) == (0.0, 12.0)
    assert tuple(windows[1]) == (0.0, 3.0)  # u counts the faces it draws


@pytest.mark.parametrize("points_first", [False, True])
@pytest.mark.parametrize("n", [3, 4])
def test_public_path_and_point_cloud_draw_independently_in_one_frame(
    points_first: bool,
    n: int,
) -> None:
    points = np.array(
        [[-0.5, -0.5, 0.0], [-0.5, 0.5, 0.0], [0.5, 0.5, 0.0], [0.5, -0.5, 0.0]]
    )[:n]
    path = m.VMobject(color=m.BLUE, stroke_width=8).set_points(points).shift(2 * m.LEFT)
    cloud = (
        m.PMobject(stroke_width=20).add_points(points, color=m.RED).shift(2 * m.RIGHT)
    )
    camera = m.Camera()

    def picture(objects: list[m.Mobject]) -> np.ndarray:
        player = Player(160, 90)
        feeder = feed.Feeder(160, 90, player)
        return np.frombuffer(
            player.render(*feeder.frame(camera, objects)), np.uint8
        ).reshape(90, 160, 4)

    alone_path, alone_cloud = picture([path]), picture([cloud])
    together = picture([cloud, path] if points_first else [path, cloud])
    assert alone_cloud[:, 80:, :3].any()
    if n == 4:
        assert alone_path[:, :80, :3].any()
    np.testing.assert_array_equal(together[:, :80], alone_path[:, :80])
    np.testing.assert_array_equal(together[:, 80:], alone_cloud[:, 80:])


# ── residency ──────────────────────────────────────────────────────────────────────────
class Injected(RuntimeError):
    """A failure the test asked the player for."""


type Part = tuple[bytes, str | None]  # an upload's part, and the type of its floats


def same(a: list[Part], b: list[Part]) -> bool:
    """Whether two uploads are one content: their parts the same bytes, their floats to a
    shape class's precision (1e-9 of their size; a float32 part, to its own)."""
    if [t for _, t in a] != [t for _, t in b]:
        return False
    for (x, kind), (y, _) in zip(a, b, strict=True):
        if kind is None or len(x) != len(y):
            if x != y:
                return False
            continue
        u, v = np.frombuffer(x, kind), np.frombuffer(y, kind)
        scale = 1 + float(np.abs(u).max(initial=0))
        if not np.allclose(
            u, v, rtol=0, atol=(1e-9 if kind == "<f8" else 1e-6) * scale
        ):
            return False
    return True


class Sink:
    """The engine's take recorder, with the test's own books: what is resident under each
    key, what each key was first uploaded with, and a failure on demand."""

    def __init__(self) -> None:
        self.engine = Recorder(32, 32, 10)
        self.resident: dict[int, bytes] = {}
        self.named: dict[int, bytes] = {}
        self.parts: dict[int, list[Part]] = {}
        self.kinds: dict[int, str] = {}  # what each key was uploaded as
        self.vertices: dict[int, int] = {}  # a mesh's vertex count, as sent
        self.failing: set[str] = set()

    def _add(self, kind: str, key: int, parts: list[Part], *args: object) -> None:
        if kind in self.failing:
            self.failing.discard(kind)
            raise Injected(kind)
        assert key not in self.resident, f"{kind} {key:x} uploaded while resident"
        assert same(self.parts.setdefault(key, parts), parts), f"{key:x}: two contents"
        assert self.kinds.setdefault(key, kind) == kind, f"{key:x}: two kinds"
        content = b"".join(part for part, _ in parts)
        self.named.setdefault(key, content)
        getattr(self.engine, "add_" + kind)(key, *args)
        self.resident[key] = content

    def add_path(
        self, key: int, points: bytes, subpaths: bytes, ca: list[float]
    ) -> None:
        self._add(
            "path", key, [(points, "<f8"), (subpaths, None)], points, subpaths, ca
        )

    def add_points(self, key: int, vertices: bytes) -> None:
        self._add("points", key, [(vertices, "<f4")], vertices)

    def add_mesh(self, key: int, points: bytes, uvs: bytes, normals: bytes,
                 triangles: bytes, outline: int = 0, block: int = 0) -> None:  # fmt: skip
        parts: list[Part] = [(points, "<f8"), (uvs, "<f8"), (normals, "<f8"),
                             (triangles, None), (b"%d %d" % (outline, block), None)]  # fmt: skip
        self._add("mesh", key, parts, points, uvs, normals, triangles, outline, block)
        self.vertices[key] = len(points) // 24

    def add_rows(self, key: int, rows: bytes) -> None:
        self._add("rows", key, [(rows, None)], rows)

    def add_texture(self, key: int, width: int, height: int, rgba: bytes) -> None:
        self._add("texture", key, [(rgba, None)], width, height, rgba)

    def add_environment(self, key: int, width: int, height: int, rgbe: bytes) -> None:
        self.engine.add_environment(key, width, height, rgbe)

    def grow_path(self, key: int, points: bytes, closed: bool = False) -> None:
        raise AssertionError("no growing paths here")

    def evict(self, keys: list[int]) -> None:
        if "evict" in self.failing:
            self.failing.discard("evict")
            raise Injected("evict")
        for key in keys:
            assert key in self.resident, f"{key:x} evicted, never resident"
            del self.resident[key]
        self.engine.evict(keys)

    def stored(self) -> tuple[int, int]:
        return self.engine.stored()


def test_a_tween_materializes_only_the_frames_consumed_and_reloads_evicted_values() -> (
    None
):
    """A non-affine cloud morph, revisiting old values after their uploads were evicted."""
    points = np.array(
        [[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0], [0.25, 0.5, 0]], float
    )
    start = m.PMobject().add_points(points)
    end = start.copy().set_points(points + np.array([[0, 0, 0]] * 4 + [[0.5, 0, 0]]))
    leaf = start.copy()
    progress = np.tile(np.linspace(0.1, 0.9, 25), 3)
    camera, path, sink = m.Camera(), m.straight_path(), Sink()
    feeder = feed.Feeder(32, 32, sink)  # ty: ignore[invalid-argument-type]
    frames = iter(
        feeder.tween(
            camera,
            [leaf],
            [(leaf, [start, end], path, np.zeros(len(progress), int), progress)],
        )
    )
    assert not sink.resident
    for number, t in enumerate(progress):
        _, records = next(frames)
        if number == 0:
            assert sum(kind == "points" for kind in sink.kinds.values()) <= 2
        expected_sink = Sink()
        expected = feed.Feeder(32, 32, expected_sink)  # ty: ignore[invalid-argument-type]
        alone = start.copy()
        alone.interpolate(start, end, float(t), path)
        assert records == expected.frame(camera, [alone])[1]
        feeder.sweep(pressed=True)
        keys = {
            int(row[name])
            for row in np.frombuffer(records, feed.RECORD)
            for name in (*feed.KEYS, "texture")
            if row[name]
        }
        assert set(sink.resident) == keys
    with pytest.raises(StopIteration):
        next(frames)


def test_streaming_still_mixes_whole_keyframe_intervals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An interval revisited by a nonmonotone clock is vectorized when it becomes current."""
    start = m.Square()
    keys: list[m.Mobject] = [
        start,
        start.copy().shift(m.RIGHT),
        start.copy().shift(m.UP),
    ]
    leaf, sink, camera = start.copy(), Sink(), m.Camera()
    feeder = feed.Feeder(32, 32, sink)  # ty: ignore[invalid-argument-type]
    intervals = np.repeat([0, 1, 0], 30)
    progress = np.tile(np.linspace(0, 1, 30), 3)
    batches: list[int] = []
    mix = feeder.mix

    def measured(*args: object) -> np.ndarray | None:
        batches.append(len(args[3]))  # ty: ignore[invalid-argument-type]
        return mix(*args)  # ty: ignore[invalid-argument-type]

    monkeypatch.setattr(feeder, "mix", measured)
    frames = feeder.tween(
        camera, [leaf], [(leaf, keys, m.straight_path(), intervals, progress)]
    )
    for f, (_, records) in enumerate(frames):
        assert batches == [30] * (1 + f // 30)
        feeder.sweep(pressed=True)
        assert all(
            int(row[name]) in feeder.sizes
            for row in np.frombuffer(records, feed.RECORD)
            for name in feed.KEYS
            if row[name]
        )


@pytest.mark.parametrize("fixed", [False, True])
def test_a_delayed_tween_can_return_before_its_start_after_eviction(
    fixed: bool,
) -> None:
    from manimgx.scene import _tracks

    points = np.array(
        [[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0], [0.25, 0.5, 0]], float
    )
    start = m.PMobject().add_points(points)
    keys = [
        start.copy().set_points(points + np.array([[0, 0, 0]] * 4 + [[x, x, 0]]))
        for x in [0, 0.5, 1]
    ]
    # The state before the play need not be its first explicit keyframe.
    leaf = start.copy().shift(0.125 * m.UP)
    tween = m.Transform(leaf, keys=keys, rate_func=m.linear)
    clock = m.Succession(m.Wait(1), tween, rate_func=m.there_and_back)
    clock.begin_all()
    leaves = _tracks(clock, [(tween, m.straight_path())], np.linspace(0, 1, 4), set())
    assert leaves[0][3].tolist() == [-1, 1, 1, -1]
    camera, sink = m.Camera(), Sink()
    if fixed:
        camera.fixed_in_frame_mobjects.add(leaf)
    feeder = feed.Feeder(32, 32, sink)  # ty: ignore[invalid-argument-type]
    original = feeder.frame(camera, [leaf])[1]
    for number, (_, records) in enumerate(feeder.tween(camera, [leaf], leaves)):
        if number in (0, 3):
            assert records == original
        used = {
            int(row[name])
            for row in np.frombuffer(records, feed.RECORD)
            for name in (*feed.KEYS, "texture")
            if row[name]
        }
        assert used <= set(sink.resident)
        feeder.sweep(pressed=True)
        assert set(sink.resident) == used


def test_pressure_preserves_pending_current_and_camera_resources() -> None:
    sink = Sink()
    feeder = feed.Feeder(32, 32, sink)  # ty: ignore[invalid-argument-type]
    keys = [
        feeder.path(m.RegularPolygon(n)._geometry.terms[0][1])[0] for n in range(3, 7)
    ]

    def records(key: int) -> bytes:
        row = np.zeros(1, feed.RECORD)
        row["key1"] = key
        return row.tobytes()

    feeder.frames = 10
    feeder.latest = [records(keys[0])]
    feeder.sweep([records(keys[1]), records(keys[2])], pressed=True)
    assert set(sink.resident) == set(keys[:3])
    assert set(feeder.sizes) == set(keys[:3])


PIXELS = [np.full((2, 2, 4), v, np.uint8) for v in (0, 90, 200)]
ROWS = [np.linspace(0, 1, 4 * n).reshape(n, 4) for n in (2, 3, 6)]
FORMS = [
    m.Square().points,  # the square's path as a cloud: one form, two kinds of resource
    np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], float),
    np.array([[0, 0, 0], [2, 0, 0], [0, 1, 0], [0, 0, 1]], float),
    np.array([[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]], float),
]
# rows given directly: a picture's pixels as floats among them (one bytes, two kinds)
GIVEN_ROWS = [*ROWS, PIXELS[1].reshape(-1, 4).astype(float)]


def mobject(kind: int, variant: int) -> m.Mobject:
    """A leaf of each kind the feed uploads: a path, a graded path (rows), a cloud with a
    color per point (rows), a mesh with a color per vertex, a surface with a color per
    cell, an image (a texture)."""
    rows = ROWS[variant % len(ROWS)]
    if kind == 0:
        return m.RegularPolygon(3 + variant)
    if kind == 1:
        return m.Square().set_fill([m.RED, m.BLUE, m.GREEN][: 2 + variant % 2], 1)
    if kind == 2:
        form = FORMS[variant % len(FORMS)]
        cloud = m.PMobject().add_points(form)
        cloud.paint = cloud.paint.but(fill=np.resize(rows, (len(form), 4)))
        return cloud
    if kind == 3:
        mesh = m.MeshMobject(FORMS[1], np.array([[0, 1, 2]]))
        mesh.paint = mesh.paint.but(fill=np.resize(rows, (3, 4)))
        return mesh
    if kind == 4:
        surface = m.Surface(
            lambda u, v: np.array([u, v, 0.2 * variant * u * v]),
            resolution=(2, 3),
            checkerboard_colors=False,
        )
        surface.paint = surface.paint.but(fill=np.resize(rows, (6, 4)))
        return surface
    return m.ImageMobject(PIXELS[variant % len(PIXELS)])


def bent(mob: m.Mobject, by: float) -> m.Mobject:
    return mob.copy().apply_function(lambda p: p + by * p[0] * m.UP)


def morph(mob: m.Mobject, alpha: float, twice: bool) -> None:
    """The mobject partway between two bent copies of itself (`twice`: between two such
    mixes): a geometry of two terms, or of four."""
    a, b = bent(mob, 0.3), bent(mob, -0.2)
    if twice:
        x, y = a.copy(), b.copy()
        x.interpolate(a, b, 0.3)
        y.interpolate(b, bent(mob, 0.5), 0.6)
        a, b = x, y
    mob.interpolate(a, b, alpha)


def into_a_ring(mob: m.Mobject) -> None:
    """A path partway into a ring: two shapes whose subpaths differ (a pair to upload)."""
    if isinstance(mob, m.VMobject):
        ring, start = m.Annulus(), mob.copy()
        start.align_data(ring)
        mob.align_data(ring)
        mob.interpolate(start, ring, 0.5)


EDITS: dict[str, Callable[[m.Mobject, int], object]] = {
    "move": lambda mob, v: mob.shift(0.25 * m.RIGHT),
    "recolor": lambda mob, v: (
        None
        if isinstance(mob, m.ImageMobject)
        else mob.set_color(m.ManimColor.from_rgb((v / 5, 0.5, 0.2)))
    ),
    "stretch": lambda mob, v: mob.stretch(1 + v / 4, 0),
    "morph": lambda mob, v: morph(mob, v / 6, twice=v % 2 == 1),
    "into a ring": lambda mob, v: into_a_ring(mob),
    "part": lambda mob, v: mob.pointwise_become_partial(mob.copy(), 0.0, 0.4 + v / 10),
}


@dataclass
class Handed:
    """An upload made directly: of rows or a texture, its input, and the key it was given."""

    kind: str
    data: np.ndarray
    key: int


class Residency(RuleBasedStateMachine):
    @initialize()
    def begin(self) -> None:
        self.sink = Sink()
        self.feeder = feed.Feeder(32, 32, self.sink)  # ty: ignore[invalid-argument-type]
        self.camera = m.Camera()
        self.pool: list[m.Mobject] = [mobject(k, 0) for k in range(6)]
        self.held: list[Handed] = []  # the direct uploads whose inputs the test holds
        self.dropped: list[tuple[weakref.ref[np.ndarray], int]] = []

    @rule(which=st.lists(st.integers(0, 63), min_size=1, max_size=6))
    def frame(self, which: list[int]) -> None:
        shown = list(dict.fromkeys(self.pool[i % len(self.pool)] for i in which))
        try:
            _, data, _ = self.feeder.frame(self.camera, shown)
        except Injected:
            return
        drawn = [mob for mob in shown if mob.has_points()]
        records = np.frombuffer(data, feed.RECORD)
        assert len(records) == len(drawn)
        for mob, record in zip(drawn, records, strict=True):
            keys = [int(record[name]) for name in (*feed.KEYS, "texture")]
            missing = [k for k in keys if k and k not in self.sink.resident]
            assert not missing, f"a {type(mob).__name__} draws what is not resident"
            kind = (
                "path"
                if isinstance(mob, m.VMobject)
                else "points"
                if isinstance(mob, m.PMobject)
                else "mesh"
            )
            shapes = {
                self.sink.kinds[int(record[k])] for k in ("key1", "key2") if record[k]
            }
            assert shapes <= {kind}, f"a {type(mob).__name__} draws {shapes} resources"
            self.assert_shows(mob, record)

    def assert_shows(self, mob: m.Mobject, record: np.void) -> None:
        """A record's rows are the brush its mobject shows (each end of a tween's), a row
        for each vertex of a mesh as sent; an image's texture is its pixels."""
        resident = self.sink.resident
        ends = mob.paint.ends("fill")
        for rows, shape, brush in (("fill_rows", "key1", ends[0]),
                                   ("fill_rows2", "key2", ends[1])):  # fmt: skip
            if not (key := int(record[rows])):
                continue
            if isinstance(mob, m.MeshMobject):  # (one shape: it is both ends')
                sent = int(record[shape]) or int(record["key1"])
                assert len(resident[key]) // 16 == self.sink.vertices[sent]
            else:
                assert resident[key] == np.ascontiguousarray(brush, "<f4").tobytes()
        if record["texture"] and isinstance(mob, m.ImageMobject):
            pixels = np.ascontiguousarray(mob.pixel_array, np.uint8).tobytes()
            assert resident[int(record["texture"])] == pixels

    @rule(
        i=st.integers(0, 63),
        how=st.sampled_from([*EDITS, "another", "copy"]),
        variant=st.integers(0, 5),
    )
    def edit(self, i: int, how: str, variant: int) -> None:
        k = i % len(self.pool)
        if how == "another":
            self.pool[k] = mobject(i % 6, variant)
        elif how == "copy":
            self.pool.append(self.pool[k].copy())  # copies share what they draw
        else:
            EDITS[how](self.pool[k], variant)

    @rule(frames=st.sampled_from([1, feed.MARK, feed.KEEP, feed.SWEEP]))
    def idle(self, frames: int) -> None:
        self.feeder.frames += frames

    @rule(fails=st.booleans())
    def sweep(self, fails: bool) -> None:
        """Time enough for a sweep, whose eviction may fail."""
        self.feeder.frames += feed.SWEEP
        if fails:
            self.sink.failing.add("evict")
        with contextlib.suppress(Injected):
            self.feeder.sweep()
        self.sink.failing.discard("evict")

    @rule(kind=st.sampled_from(["path", "points", "mesh", "rows", "texture", "evict"]))
    def fail_next(self, kind: str) -> None:
        self.sink.failing.add(kind)

    @rule(which=st.integers(0, 3), readonly=st.booleans(),
          kind=st.sampled_from(["rows", "texture"]))  # fmt: skip
    def upload(self, which: int, readonly: bool, kind: str) -> None:
        given = GIVEN_ROWS if kind == "rows" else PIXELS
        data = given[which % len(given)].copy()
        data.flags.writeable = not readonly
        try:
            key = getattr(self.feeder, kind)(data)
        except Injected:
            return
        content = np.ascontiguousarray(data, "<f4") if kind == "rows" else data
        assert self.sink.named[key] == content.tobytes()
        self.held.append(Handed(kind, data, key))

    @rule(i=st.integers(0, 63), change=st.booleans())
    def again(self, i: int, change: bool) -> None:
        """An input handed over again, perhaps changed in place first (if it can be)."""
        if not self.held:
            return
        item = self.held[i % len(self.held)]
        if change and item.data.flags.writeable:
            item.data.reshape(-1)[0] += 1
        try:
            item.key = getattr(self.feeder, item.kind)(item.data)
        except Injected:
            return
        if item.kind == "rows":  # rows by content; a texture is borrowed: by identity
            content = np.ascontiguousarray(item.data, "<f4").tobytes()
            assert self.sink.named[item.key] == content

    @rule(i=st.integers(0, 63))
    def let_go(self, i: int) -> None:
        if self.held:
            item = self.held.pop(i % len(self.held))
            self.dropped.append((weakref.ref(item.data), item.key))
            del item

    @invariant()
    def its_books_are_the_players(self) -> None:
        counted = {
            k for k, n in self.feeder.sizes.items() if n != -1
        }  # -1: draws nothing
        assert counted <= set(self.sink.resident), "counted resident, but not"
        assert set(self.sink.resident) <= counted, (
            "resident, but forgotten: never evicted"
        )

    def teardown(self) -> None:
        """With nothing shown for long enough, a sweep forgets every key, and every input let
        go of is collected: a key in flight (a failed upload's) holds its input until then."""
        self.held, self.pool = [], []
        self.sink.failing.clear()
        self.feeder.frame(
            self.camera, []
        )  # a frame of nothing: the last shown holds nothing
        self.feeder.frames += feed.KEEP + 2 * feed.SWEEP
        self.feeder.sweep()
        gc.collect()
        alive = [key for ref, key in self.dropped if ref() is not None]
        assert not alive, f"{len(alive)} inputs let go of outlive their keys' sweep"


TestResidency = Residency.TestCase
TestResidency.settings = settings(max_examples=60, stateful_step_count=40)

"""A 3D view composites what can be seen through in depth order, whatever order it is drawn
in: a pixel shows every surface, shape and point on its ray, the nearer over the farther — in a
picture and in a video alike, however many a ray meets. Where things meet edge to edge, each
covers its own part of a pixel."""

from pathlib import Path

import numpy as np
import pytest
from tests import scenes
from tests.integration.corpus.frames import decode

import manimgx as m

SIZE = (320, 180)
OPACITY = 0.4
COLORS = (m.RED, m.GREEN, m.BLUE, m.YELLOW, m.TEAL, m.PURPLE)


pytestmark = pytest.mark.config(pixel_width=SIZE[0], pixel_height=SIZE[1])


def stack(
    order: list[int],
    points: frozenset[int] = frozenset(),
    colors: tuple[m.ManimColor, ...] = COLORS,
    meshes: frozenset[int] = frozenset(),
    *,
    mesh_resolution: int = 1,
    mesh_shift: float = 0.0,
) -> m.Scene:
    """Layers one behind another, layer k nearer than layer k - 1, in `colors[k]`, each
    see-through; added in `order`. Each is a plane filling the view (a shape, or, if in
    `meshes`, a surface), or, if in `points`, a point's disk over its center."""

    def layer(k: int, color: m.ManimColor) -> m.Mobject:
        if k in points:
            shape = m.PMobject(stroke_width=270).add_points(
                [m.ORIGIN], color=color, alpha=OPACITY
            )
        elif k in meshes:
            shape = m.Surface(
                lambda u, v: np.array([u, v, 0.0]),
                u_range=[-20, 20],
                v_range=[-20, 20],
                resolution=mesh_resolution,
                checkerboard_colors=False,
                stroke_width=0,
                shade_in_3d=False,  # (its color as given, as a shape's)
            ).set_fill(color, OPACITY)
            shape.shift(mesh_shift * (m.RIGHT - m.UP))
        else:
            shape = m.Square(side_length=40.0).set_fill(color, OPACITY)
            shape.set_stroke(width=0)
        return shape.shift(0.5 * k * m.OUT)

    def construct(scene: m.ThreeDScene) -> None:
        scene.set_camera_orientation(phi=0.0, theta=-90 * m.DEGREES)
        layers = [layer(k, color) for k, color in enumerate(colors)]
        scene.add(*(layers[k] for k in order))
        scene.wait(0.1)

    return scenes.scene_3d(construct)


def picture(scene: m.Scene) -> np.ndarray:
    """The first frame the scene shows (RGB rows)."""
    return scenes.frames(scene)[0][..., :3]


def composite(colors: tuple[m.ManimColor, ...] = COLORS) -> np.ndarray:
    """The layers over black, nearest first: each seen through all nearer ones."""
    rgb = np.zeros(3)
    seen = 1.0  # how much of what is behind the nearer layers shows
    for color in reversed(colors):
        rgb += seen * OPACITY * m.ManimColor(color).to_rgb()
        seen *= 1.0 - OPACITY
    return rgb * 255


@pytest.mark.parametrize("colors", [COLORS, COLORS * 2], ids=["six", "twelve"])
def test_see_through_layers_composite_in_depth_order_in_any_order(
    colors: tuple[m.ManimColor, ...],
) -> None:
    # twelve: more than a pixel sorts at once (`FEW`), so it takes them a batch at a time
    n = len(colors)
    forward = picture(stack(list(range(n)), colors=colors))
    backward = picture(stack(list(reversed(range(n))), colors=colors))
    assert np.array_equal(forward, backward)
    center = forward[SIZE[1] // 2, SIZE[0] // 2].astype(float)
    assert np.abs(center - composite(colors)).max() <= 2.0


ALL, ODD = frozenset(range(len(COLORS))), frozenset(range(1, len(COLORS), 2))


@pytest.mark.parametrize(
    ("points", "colors", "meshes"),
    [
        (ALL, COLORS, frozenset()),
        (ODD, COLORS, frozenset()),
        (ALL, (m.TEAL,) * len(COLORS), frozenset()),
        (ODD, COLORS, frozenset({2, 4})),
    ],
    ids=[
        "points",
        "points-between-planes",
        "points-of-one-color",
        "points-between-surfaces",
    ],
)
def test_see_through_points_composite_in_depth_order_in_any_order(
    points: frozenset[int],
    colors: tuple[m.ManimColor, ...],
    meshes: frozenset[int],
) -> None:
    # points alone blend far to near (of one color, in any order); between planes, shapes or
    # surfaces, each blends among the points between the same two planes
    n = len(colors)
    forward = picture(stack(list(range(n)), points, colors, meshes))
    backward = picture(stack(list(reversed(range(n))), points, colors, meshes))
    assert np.array_equal(forward, backward)
    center = forward[SIZE[1] // 2, SIZE[0] // 2].astype(float)
    assert np.abs(center - composite(colors)).max() <= 2.0


@pytest.mark.parametrize("resolution", [1, 2, 4])
@pytest.mark.parametrize("offset", [0.0, 0.02, 0.04])
def test_surface_tessellation_preserves_points_depth_order(
    resolution: int, offset: float
) -> None:
    # More triangles may meet a pixel, or a backend may append one node per sample.
    # Neither creates more depth boundaries: each point stays between the same planes.
    # Moving the grid by half a pixel makes its triangles share the center's samples.
    for order in (list(range(len(COLORS))), list(reversed(range(len(COLORS))))):
        shown = picture(
            stack(
                order,
                ODD,
                meshes=frozenset({2, 4}),
                mesh_resolution=resolution,
                mesh_shift=offset,
            )
        )
        center = shown[SIZE[1] // 2, SIZE[0] // 2].astype(float)
        assert np.abs(center - composite()).max() <= 2.0


def test_a_title_fixed_in_the_frame_changes_no_pixel_but_its_own() -> None:
    # a deep pile of see-through points and a line beside it: a title fixed in the frame, over
    # everything, takes no place among the scene's depths, so the pile is drawn as without it
    def scene(title: bool) -> m.Scene:
        def construct(s: m.ThreeDScene) -> None:
            s.set_camera_orientation(phi=0.0, theta=-90 * m.DEGREES)
            rng = np.random.default_rng(5)
            pile = m.PMobject(stroke_width=20).add_points(
                rng.normal(scale=0.02, size=(400, 3)) + [-1.0, -1.5, 0.0],
                color=m.YELLOW,
                alpha=0.55,
            )
            s.add(pile, m.Line([4.0, -3.5, 0.0], [4.0, -0.5, 0.0], stroke_width=4))
            if title:
                s.add_fixed_in_frame_mobjects(m.Text("A title").to_corner(m.UL))
            s.wait(0.1)

        return scenes.scene_3d(construct)

    # the title is in the top left; the pile and the line below
    bottom = slice(SIZE[1] // 2, None)
    assert np.array_equal(picture(scene(True))[bottom], picture(scene(False))[bottom])


def test_points_show_where_an_earlier_frame_had_see_through_surfaces() -> None:
    # a see-through surface over the whole view, then over its top only: the points below it
    # show in the last frame as if it had always been at the top
    def surface(v_range: list[float]) -> m.Surface:
        return m.Surface(
            lambda u, v: np.array([u, v, 1.0]),
            u_range=[-8, 8],
            v_range=v_range,
            resolution=1,
            checkerboard_colors=False,
            stroke_width=0,
        ).set_fill(m.BLUE, 0.5)

    def scene(first: list[float]) -> m.Scene:
        def construct(s: m.ThreeDScene) -> None:
            s.set_camera_orientation(phi=0.0, theta=-90 * m.DEGREES)
            grid = [[x, y, 0.0] for x in np.linspace(-6, 6, 13) for y in (-3, -2, -1)]
            s.add(
                m.PMobject(stroke_width=40).add_points(grid, color=m.YELLOW, alpha=0.6)
            )
            sheet = surface(first)
            s.add(sheet)
            s.wait(0.1)
            s.remove(sheet)
            s.add(surface([3.0, 5.0]))
            s.wait(0.1)

        return scenes.scene_3d(construct)

    bottom = slice(SIZE[1] // 2, None)
    moved = scenes.frames(scene([-5.0, 5.0]))[-1][..., :3]
    still = scenes.frames(scene([3.0, 5.0]))[-1][..., :3]
    assert np.array_equal(moved[bottom], still[bottom])


def test_a_video_frame_that_outgrows_the_lists_is_drawn_whole(tmp_path: Path) -> None:
    # every pixel meets six planes, more than the lists first hold: the frame is drawn again
    stack(list(range(len(COLORS)))).render(tmp_path / "stack.mp4")
    frame = next(decode(tmp_path / "stack.mp4", SIZE)).astype(float)
    expected = picture(stack(list(range(len(COLORS))))).astype(float)
    assert np.abs(frame - expected).mean() <= 1.0


@pytest.mark.parametrize("three_d", [False, True], ids=["2d", "3d"])
def test_a_mesh_and_a_shape_meeting_edge_to_edge_show_no_seam(three_d: bool) -> None:
    # a mesh and a shape side by side on black, their common edge through the middle of a pixel:
    # the pixel is half of each (were their coverages mixed as if independent, a quarter of the
    # black would show through it: a dark seam)
    boundary = 0.5 * 8 / SIZE[1]  # half a pixel right of the view's centre, in units

    def seam(scene: m.Scene) -> None:
        if isinstance(scene, m.ThreeDScene):
            scene.set_camera_orientation(phi=0.0, theta=-90 * m.DEGREES)
        mesh = m.Surface(
            lambda u, v: np.array([u, v, 0]),
            u_range=[-5, boundary],
            v_range=[-3, 3],
            resolution=(1, 1),
            stroke_width=0,
        )
        corners = [[boundary, -3, 0], [5, -3, 0], [5, 3, 0], [boundary, 3, 0]]
        shape = m.Polygon(*corners, stroke_width=0, fill_opacity=1)
        scene.add(mesh.set_color(m.WHITE), shape.set_fill(m.WHITE))
        scene.wait(0.1)

    told = scenes.scene_3d(seam) if three_d else scenes.scene(seam)
    shown = picture(told).astype(float)
    row, middle = SIZE[1] // 2, SIZE[0] // 2
    left, here, right = (shown[row, middle + k] for k in (-3, 0, 3))
    assert np.abs(here - 0.5 * (left + right)).max() <= 2.0

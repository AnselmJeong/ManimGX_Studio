"""A 3D view shows what lies in front of its camera: a shape that reaches behind the camera
shows the part in front of it, exactly where a surface in its place would, at any angle; what
lies wholly behind the camera shows nothing. Where shapes meet, the one drawn later shows if
they lie in one plane, the nearer if they do not, however near or far the camera; surfaces
too. Manim's light shades the side of a shape or surface the eye sees, however far off the
view's axis it lies."""

import numpy as np
import pytest
from tests import scenes

import manimgx as m
from manimgx.config import config

SIZE = (320, 180)
pytestmark = pytest.mark.config(pixel_width=SIZE[0], pixel_height=SIZE[1])


def view(
    *mobs: m.Mobject, phi: float, theta: float, distance: float | None = None
) -> np.ndarray:
    """What a 3D view of the mobjects shows (RGB rows), the camera at `phi` and `theta`
    (degrees), `distance` from its focus."""

    def construct(scene: m.ThreeDScene) -> None:
        scene.set_camera_orientation(
            phi=phi * m.DEGREES, theta=theta * m.DEGREES, focal_distance=distance
        )
        scene.add(*mobs)
        scene.wait(0.05)

    shown = scenes.frames(scenes.scene_3d(construct))
    return shown[0][..., :3].astype(int)


def coverage(mob: m.Mobject, phi: float, theta: float) -> np.ndarray:
    """How much of each pixel a white mobject covers over black, the camera at (phi, theta)."""
    return view(mob, phi=phi, theta=theta).sum(axis=2) / 765.0


def shape(side: float) -> m.Mobject:
    return m.Square(side_length=side, fill_opacity=1, stroke_width=0).set_fill(m.WHITE)


def surface(side: float) -> m.Mobject:
    half = side / 2
    mesh = m.Surface(
        lambda u, v: np.array([u, v, 0]),
        u_range=[-half, half],
        v_range=[-half, half],
        resolution=(32, 32),
        stroke_width=0,
        fill_opacity=1,
    ).set_color(m.WHITE)
    mesh.shade_in_3d = False
    return mesh


@pytest.mark.parametrize(("phi", "theta"), [(78, -60), (85, -90), (89, -45)])
def test_a_floor_reaching_behind_the_camera_shows_what_a_surface_does(
    phi: float, theta: float
) -> None:
    # a floor 40 units wide around the origin, the camera 20 units away and low over it
    path, mesh = coverage(shape(40), phi, theta), coverage(surface(40), phi, theta)
    assert path.sum() > 0.25 * path.size
    assert (
        np.abs(path - mesh) <= 0.5
    ).all()  # they differ at their edges' anti-aliasing alone


@pytest.mark.parametrize("tilt", [30, 80, 89.5])
@pytest.mark.parametrize("height", [19.9, 19.95, 20.3])
def test_a_tilted_square_crossing_the_near_plane_shows_what_a_surface_does(
    tilt: float, height: float
) -> None:
    # looking straight down from 20 units up: the near plane is at 19.95
    def placed(mob: m.Mobject) -> m.Mobject:
        return mob.rotate(tilt * m.DEGREES, axis=m.RIGHT).shift(
            height * m.OUT + 0.3 * m.RIGHT
        )

    path = coverage(placed(shape(2)), 0, -90)
    mesh = coverage(placed(surface(2)), 0, -90)
    assert (np.abs(path - mesh) <= 0.5).all()
    # in all, by no more than the surface's sampled edges miss an exact edge's area by
    edge_pixels = ((path > 0) & (path < 1)).sum()
    assert abs(path.sum() - mesh.sum()) <= 0.15 * edge_pixels + 1.0


def test_a_shape_wholly_behind_the_camera_shows_nothing() -> None:
    behind = shape(2).shift(25 * m.OUT)  # the camera is 20 units up
    assert coverage(behind, 0, -90).max() == 0


BLUE = (m.ManimColor(m.BLUE).to_rgb() * 255).round()


def centre_colour(mobs: list[m.Mobject], distance: float) -> np.ndarray:
    """The view's centre pixel, looking down at the mobjects from `distance` away."""
    shown = view(*mobs, phi=30, theta=-60, distance=distance)
    return shown[SIZE[1] // 2, SIZE[0] // 2]


@pytest.mark.parametrize("distance", [5.0, 20.0, 60.0])
def test_shapes_in_one_plane_meet_by_draw_order_at_any_distance(
    distance: float,
) -> None:
    below = m.Square(side_length=2, fill_opacity=1, stroke_width=0).set_fill(m.RED)
    above = m.Square(side_length=1, fill_opacity=1, stroke_width=0).set_fill(m.BLUE)
    tilt = lambda mob: mob.rotate(20 * m.DEGREES, axis=m.RIGHT)
    shown = centre_colour([tilt(below), tilt(above)], distance)
    assert np.abs(shown.astype(int) - BLUE).max() <= 2  # the one drawn later


@pytest.mark.parametrize("distance", [5.0, 20.0, 60.0])
def test_shapes_a_hair_apart_meet_by_depth_at_any_distance(distance: float) -> None:
    # the nearer square, 0.001 above, drawn first: the nearer shows, wherever the camera is
    near = m.Square(side_length=1, fill_opacity=1, stroke_width=0).set_fill(m.BLUE)
    far = m.Square(side_length=2, fill_opacity=1, stroke_width=0).set_fill(m.RED)
    shown = centre_colour([near.shift(0.001 * m.OUT), far], distance)
    assert np.abs(shown.astype(int) - BLUE).max() <= 2


@pytest.mark.parametrize("distance", [5.0, 20.0, 60.0, 200.0])
def test_meshes_a_hair_apart_meet_by_depth_at_any_distance(distance: float) -> None:
    # the nearer surface, 0.001 above, drawn first: the nearer shows, wherever the camera is
    def sheet(side: float, color: m.ManimColor, z: float) -> m.Mobject:
        mesh = surface(side).set_color(color).shift(z * m.OUT)
        return mesh

    shown = centre_colour([sheet(1, m.BLUE, 0.001), sheet(2, m.RED, 0.0)], distance)
    assert np.abs(shown.astype(int) - BLUE).max() <= 2


def floor_mesh(grid: float = 0.0) -> m.Mobject:
    """A blue surface floor, 6 units wide, its grid lines `grid` wide (white)."""
    mesh = m.Surface(
        lambda u, v: np.array([u, v, 0]),
        u_range=[-3, 3],
        v_range=[-3, 3],
        resolution=(8, 8),
        stroke_width=grid,
        stroke_color=m.WHITE,
        fill_opacity=1,
    ).set_fill(m.BLUE)
    mesh.shade_in_3d = False
    return mesh


@pytest.mark.parametrize(
    ("phi", "distance"), [(40, 5.0), (75, 20.0), (85, 20.0), (80, 60.0)]
)
def test_a_shape_on_a_surface_shows_however_steep_and_far(
    phi: float, distance: float
) -> None:
    # a red square lying on a surface floor (with its grid lines) shows wherever it covers, as
    # on a shape floor; one a hair below it does not show at all
    def on(offset: float | None) -> np.ndarray:
        floor = [] if offset is None else [floor_mesh(grid=1.0)]
        square = shape(2).set_fill(m.RED).shift((offset or 0.0) * m.OUT)
        return view(*floor, square, phi=phi, theta=-90, distance=distance)

    covered = on(None)[..., 0] > 250  # its pixels, whole
    red = lambda rgb: (rgb[..., 0] > 150) & (rgb[..., 2] < 120)
    assert covered.sum() > 20
    assert red(on(0.0))[covered].all()
    assert not red(on(-0.001)).any()


@pytest.mark.parametrize("phi", [60, 85])
def test_a_surfaces_grid_shows_over_its_faces(phi: float) -> None:
    def grid(fill: float) -> np.ndarray:
        floor = floor_mesh(grid=6.0).set_fill(m.BLUE, opacity=fill)
        return view(floor, phi=phi, theta=-60)

    # where the grid alone (over black) covers most of a pixel, it shows over its faces at
    # least as bright (white over blue, not blue: the faces hide none of it)
    alone, over = grid(0.0).min(axis=2), grid(1.0).min(axis=2)
    lines = alone > 150
    assert lines.sum() > 100
    assert (over[lines] >= alone[lines] - 5).all()


@pytest.mark.parametrize("opacity", [1.0, 0.5])
def test_where_shapes_cross_their_crossing_is_as_smooth_as_their_edges(
    opacity: float,
) -> None:
    # a floor and a tilted square through it: along the line where they cross, each pixel
    # shows each in the share of it where it is nearer, as an image drawn 4 x 4 times finer
    # and averaged does (within its own sampling: a sixteenth of the colours' difference; a
    # pixel's centre's order alone misses by half of it)
    def crossing(scale: int) -> np.ndarray:
        config.pixel_width, config.pixel_height = SIZE[0] * scale, SIZE[1] * scale
        floor = shape(4).set_fill(m.BLUE, opacity=opacity)
        tilted = shape(4).set_fill(m.RED, opacity=opacity)
        tilted.rotate(0.7, axis=m.UP).rotate(0.4, axis=m.RIGHT)
        rgb = view(floor, tilted, phi=60, theta=-50)
        return rgb.reshape(SIZE[1], scale, SIZE[0], scale, 3).mean(axis=(1, 3))

    drawn, finer = crossing(1), crossing(4)
    assert np.abs(drawn - finer).max() <= 0.06 * 255


def test_a_line_just_above_a_floor_shows_its_whole_width_at_a_grazing_view() -> None:
    def line() -> m.Mobject:
        return (
            m.Line(4 * m.LEFT, 4 * m.RIGHT, stroke_width=8)
            .set_color(m.WHITE)
            .shift(0.001 * m.OUT + 2 * m.UP)
        )

    floor = m.Square(side_length=12, fill_opacity=1, stroke_width=0).set_fill(m.BLUE_E)
    over = coverage(m.VGroup(floor, line()), 82, -90)
    alone = coverage(line(), 82, -90)
    lit = alone > 0.9
    assert lit.sum() > 50
    assert (
        over[lit].min() > 0.9
    )  # every pixel the line covers alone, it covers over the floor


@pytest.mark.parametrize("kind", ["shape", "surface"])
def test_manims_light_shades_the_side_the_eye_sees_off_the_axis(kind: str) -> None:
    # off the axis, turned 20° past edge-on to it but toward the eye, lit on the eye's side
    normal = np.array([-np.cos(20 * m.DEGREES), 0.0, -np.sin(20 * m.DEGREES)])
    if kind == "shape":
        mob: m.Mobject = m.Square(
            side_length=2, fill_opacity=1, stroke_width=0, shade_in_3d=True
        ).set_fill(m.GRAY)
    else:
        mob = m.Surface(
            lambda u, v: np.array([u, v, 0]),
            u_range=[-1, 1],
            v_range=[-1, 1],
            resolution=(4, 4),
            stroke_width=0,
            fill_opacity=1,
        ).set_color(m.GRAY)
    mob.rotate(-110 * m.DEGREES, axis=m.UP).shift(
        4 * m.RIGHT
    )  # its plane faces `normal`

    def construct(scene: m.ThreeDScene) -> None:
        scene.set_camera_orientation(phi=0, theta=-90 * m.DEGREES, focal_distance=6)
        scene.camera.light_source.move_to(4 * m.RIGHT + 3 * normal)
        scene.add(mob)
        scene.wait(0.05)

    rgb = scenes.frames(scenes.scene_3d(construct))[0][..., :3].astype(int)
    shown = rgb[rgb.max(axis=2) > 10]
    assert len(shown) > 50
    base = round(m.ManimColor(m.GRAY).to_rgb()[0] * 255)
    # lit: the side the eye sees faces the light
    assert np.median(shown[:, 0]) > base + 60

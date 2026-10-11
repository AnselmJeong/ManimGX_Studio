"""What the engine draws is what the shapes say.

Strokes are drawn as SVG and PostScript define them (h: half the stroke's width).

- A cap ends a stroke where it shows: butt (AUTO) at its end, square h past it, round a
  half-disk of radius h; a partial reveal's moving end is capped like any other.
- Each dash is a stroke of its own: its ends are capped.
- A subpath that is one point is a dot with round caps, a square with square ones, nothing with
  butt ones. A point cloud's point is that dot: as wide as a stroke of its width.
- A joint fills the outside of a turn: a miter to its tip (AUTO), a bevel across the bodies'
  outer corners, round an arc of radius h. A closed subpath shown whole is joined at its seam.
- A stroke is painted once: however its pieces overlap, no pixel blends it twice.

A fill covers what its curves enclose (closed by a straight return to their start), however
far its control points bulge. An image enlarged is reconstructed from its pixels by its
`resampling_algorithm`: nearest holds each pixel, linear runs straight between pixel centres,
cubic follows Keys' kernel.
"""

from collections.abc import Callable

import numpy as np
import pytest
from tests import oracles, scenes

import manimgx as m
from manimgx.config import config
from manimgx.constants import Resampling

W, H = 640, 360
WIDTH = 40  # stroke width: h = 0.2 units
pytestmark = pytest.mark.config(pixel_width=W, pixel_height=H, frame_rate=10)


def _frames(build: Callable[[m.Scene], None]) -> list[np.ndarray]:
    """The red channel of every frame of a scene whose construct is `build`, white on black."""
    return [rgba[..., 0] / 255 for rgba in scenes.frames(scenes.scene(build))]


def _pixel(x: float, y: float) -> tuple[int, int]:
    """The pixel (row, column) holding scene point (x, y)."""
    unit = W / config.frame_width
    return int(np.floor(H / 2 - y * unit)), int(np.floor(W / 2 + x * unit))


def _extent(row: np.ndarray) -> float:
    """How long a row's drawn run is, in scene units: its coverage summed."""
    return float(row.sum()) / (W / config.frame_width)


# the rows 6 to 7 px below the axis (h = 9 px): a round cap reaches past the end by its mean
# half-chord there
BAND = np.linspace(6, 7, 1001)
ROUND_BAND = float(np.mean(np.sqrt(81 - BAND**2))) / 45


@pytest.mark.parametrize(
    ("cap", "past", "past_off_axis"),
    [
        (m.CapStyleType.AUTO, 0.0, 0.0),
        (m.CapStyleType.BUTT, 0.0, 0.0),
        (m.CapStyleType.SQUARE, 0.2, 0.2),
        (m.CapStyleType.ROUND, 0.2, ROUND_BAND),
    ],
    ids=["auto", "butt", "square", "round"],
)
def test_a_cap_ends_the_stroke_where_it_shows(
    cap: m.CapStyleType,
    past: float,
    past_off_axis: float,
) -> None:
    def build(scene: m.Scene) -> None:
        line = m.Line(m.LEFT * 2, m.RIGHT * 2, stroke_width=WIDTH).set_cap_style(cap)
        scene.play(m.Create(line), run_time=1, rate_func=m.linear)

    frames = _frames(build)
    row = H // 2
    off = row + 6  # the band 6 to 7 px below the axis
    whole, half = frames[-1], frames[5]  # at 10 fps: the whole line, and its first half
    assert _extent(whole[row]) == pytest.approx(4 + 2 * past, abs=0.03)
    assert _extent(whole[off]) == pytest.approx(4 + 2 * past_off_axis, abs=0.03)
    assert _extent(half[row]) == pytest.approx(2 + 2 * past, abs=0.03)


def test_each_dash_is_capped() -> None:
    def build(scene: m.Scene) -> None:
        dashed = m.DashedLine(m.LEFT * 2, m.RIGHT * 2, dash_length=0.5, stroke_width=10)
        scene.add(dashed.set_cap_style(m.CapStyleType.ROUND))

    row = _frames(build)[-1][_pixel(0, 0)[0]]
    runs = np.split(row, np.flatnonzero(np.diff((row > 0).astype(int)) == 1) + 1)[1:]
    # ⌈4 / 0.5 · ½⌉ = 4 dashes, each ½ · 4 / 4 = 0.5 long, and h = 0.05 longer at both ends
    assert [_extent(r) for r in runs] == pytest.approx([0.6] * 4, abs=0.03)


@pytest.mark.parametrize(
    ("cap", "centre", "diagonal", "far"),
    [
        (m.CapStyleType.ROUND, 1, 0, 0),
        (m.CapStyleType.SQUARE, 1, 1, 0),
        (m.CapStyleType.BUTT, 0, 0, 0),
    ],
    ids=["round", "square", "butt"],
)
def test_a_point_is_a_dot(
    cap: m.CapStyleType,
    centre: float,
    diagonal: float,
    far: float,
) -> None:
    def build(scene: m.Scene) -> None:
        point = m.VMobject(stroke_width=WIDTH).set_points(np.zeros((4, 3)))
        scene.add(point.set_cap_style(cap))

    frame = _frames(build)[-1]
    for (x, y), expected in (
        ((0.02, 0.02), centre),
        ((0.16, 0.16), diagonal),
        ((0.25, 0.0), far),
    ):
        assert frame[_pixel(x, y)] == pytest.approx(expected, abs=0.05)


def test_a_cloud_point_is_the_dot_of_a_one_point_subpath() -> None:
    def drawn(mob: m.Mobject) -> np.ndarray:
        def build(scene: m.Scene) -> None:
            scene.add(mob)

        return _frames(build)[-1]

    cloud = m.PMobject(stroke_width=WIDTH).add_points([m.ORIGIN], color=m.WHITE)
    dot = m.VMobject(stroke_width=WIDTH).set_points(np.zeros((4, 3)))
    point, stroke = drawn(cloud), drawn(dot.set_cap_style(m.CapStyleType.ROUND))
    assert point.sum() == pytest.approx(stroke.sum(), rel=0.02)
    assert np.abs(point - stroke).max() <= 0.1


@pytest.mark.parametrize(
    ("joint", "near", "middle", "tip"),
    [
        (m.LineJointType.AUTO, 1, 1, 1),
        (m.LineJointType.MITER, 1, 1, 1),
        (m.LineJointType.BEVEL, 1, 0, 0),
        (m.LineJointType.ROUND, 1, 1, 0),
    ],
    ids=["auto", "miter", "bevel", "round"],
)
def test_a_joint_fills_the_outside_of_the_turn(
    joint: m.LineJointType,
    near: float,
    middle: float,
    tip: float,
) -> None:
    def build(scene: m.Scene) -> None:
        corner = m.VMobject(stroke_width=WIDTH).set_points_as_corners(
            [m.LEFT * 2 + m.DOWN, m.RIGHT + m.DOWN, m.RIGHT + m.UP]
        )
        corner.joint_type = joint
        scene.add(corner)

    frame = _frames(build)[-1]
    # along the outer diagonal from the corner (1, -1), in h: the bevel's line crosses it at 0.5,
    # the round's arc at 0.71, the miter's tip at 1
    for s, expected in ((0.3, near), (0.6, middle), (0.9, tip)):
        assert frame[_pixel(1 + s * 0.2, -1 - s * 0.2)] == pytest.approx(
            expected, abs=0.05
        )


def test_a_closed_subpath_is_joined_at_its_seam() -> None:
    def build(scene: m.Scene) -> None:
        scene.add(
            m.Square(side_length=2, stroke_width=WIDTH).set_cap_style(
                m.CapStyleType.ROUND
            )
        )

    frame = _frames(build)[-1]
    for x, y in (
        (1, 1),
        (-1, 1),
        (-1, -1),
        (1, -1),
    ):  # every corner mitered, its seam's too
        assert frame[
            _pixel(x + 0.18 * np.sign(x), y + 0.18 * np.sign(y))
        ] == pytest.approx(1, abs=0.05)


@pytest.mark.parametrize("joint", list(m.LineJointType), ids=lambda j: j.name.lower())
@pytest.mark.parametrize("cap", list(m.CapStyleType), ids=lambda c: c.name.lower())
def test_a_stroke_is_painted_once(joint: m.LineJointType, cap: m.CapStyleType) -> None:
    def build(scene: m.Scene) -> None:
        zig = [np.array([0.4 * i - 2, 0.8 if i % 2 else -0.8, 0]) for i in range(11)]
        path = m.VMobject(stroke_width=WIDTH, stroke_opacity=0.5).set_points_as_corners(
            zig
        )
        path.joint_type = joint
        scene.add(path.set_cap_style(cap))
        dashed = m.DashedLine(
            m.LEFT * 2 + m.UP * 2, m.RIGHT * 2 + m.UP * 2.5, stroke_width=WIDTH
        )
        scene.add(dashed.set_stroke(opacity=0.5).set_cap_style(cap))

    frame = _frames(build)[-1]
    assert frame.max() == pytest.approx(0.5, abs=1 / 255)


class Enlarged(m.Scene):
    """A two-pixel image, black then white, stretched over the whole frame."""

    def __init__(self, algorithm: Resampling) -> None:
        super().__init__()
        self.algorithm = algorithm

    def construct(self) -> None:
        pixels = np.array([[0, 255]], dtype=np.uint8)
        image = m.ImageMobject(pixels, resampling_algorithm=self.algorithm)
        image.stretch_to_fit_width(config.frame_width)
        self.add(image.stretch_to_fit_height(config.frame_height))


@pytest.mark.config(pixel_width=320, pixel_height=180)
@pytest.mark.parametrize(
    ("algorithm", "kernel"),
    [
        (0, lambda t: np.round(t)),
        (2, lambda t: t),
        (3, lambda t: -(t**3) + 1.5 * t**2 + 0.5 * t),  # Keys, a = -1/2, edges held
    ],
    ids=["nearest", "linear", "cubic"],
)
def test_an_image_is_reconstructed_by_its_resampling_algorithm(
    algorithm: Resampling,
    kernel: Callable[[np.ndarray], np.ndarray],
) -> None:
    row = scenes.frames(Enlarged(algorithm))[-1][90, :, 0]
    columns = np.arange(90, 231, 10)  # between the pixels' centres, at 80 and 240
    t = (columns + 0.5 - 80) / 160
    assert row[columns] == pytest.approx(255 * kernel(t), abs=1.5)


def _filled(mob: m.VMobject) -> float:
    """The area a white fill shows alone on black, in square units: its pixels' coverage
    summed."""

    def alone(scene: m.Scene) -> None:
        scene.add(mob)
        scene.wait(0.1)

    shown = scenes.frames(scenes.scene(alone))[0][..., 0].astype(float) / 255
    return float(shown.sum()) / (H / config.frame_height) ** 2


def _enclosed(points: np.ndarray) -> float:
    """The area cubic curves (four points each) enclose, closed by a straight return to
    their start."""
    return abs(oracles.polygon_area(oracles.sample(points, 4001)))


@pytest.mark.parametrize("kind", ["open", "bulging"])
def test_a_fill_covers_what_its_curves_enclose(kind: str) -> None:
    # large enough that the composite visits only the tiles its curves cross and those inside them: a fill closed by
    # the straight return to its start (an open path: no curve runs there), and one whose control points bulge far
    # past its curve (inside its control polygon, outside it), each cover what their curves enclose
    if kind == "open":
        corners = [[-3, -2, 0], [0, 2, 0], [3, -2, 0]]
        points = np.concatenate(
            [
                [p, p + (q - p) / 3, p + 2 * (q - p) / 3, q]
                for p, q in zip(
                    np.array(corners[:-1], float),
                    np.array(corners[1:], float),
                    strict=True,
                )
            ]
        )
    else:
        points = np.array(
            [[-3, -1.5, 0], [-3, 3.5, 0], [3, 3.5, 0], [3, -1.5, 0]], float
        )
    mob = m.VMobject(fill_opacity=1, stroke_width=0).set_points(points)
    mob.set_fill(m.WHITE, 1)
    assert abs(_filled(mob) - _enclosed(points)) <= 0.005 * _enclosed(points)

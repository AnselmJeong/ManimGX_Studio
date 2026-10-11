"""ManimBanner.expand opens the logo into the banner as a function of its progress, from the
banner as it is when it begins.

- No part jumps: between two instants the scene computes, nothing moves further than the
  parting's top speed allows.
- It ends exactly on the banner: the expanded banner of a banner scaled by s and moved is the
  unit banner's, scaled by s and moved the same way; what `direction` holds still (the M for
  "right", the shapes for "left", the middle of the banner for "center") has not moved.
- A letter is never seen ahead of the square that uncovers it; the letters go in front of the
  shapes (as the M is) only where none of them overlaps a shape, and end in front.

Each story is told with every frame computed, at 10 and 60 fps.
"""

from fractions import Fraction
from itertools import pairwise
from typing import Literal

import pytest
from tests import scenes

import manimgx as m
from manimgx.config import config

type Direction = Literal["left", "right", "center"]
type Place = tuple[float, float, float]  # scale, then shift x, y
# a part as seen: its x-range, its fill opacity, its place in the draw order
type Part = tuple[float, float, float, int]
type Seen = dict[Fraction, dict[str, Part]]  # at every instant the scene computes

DIRECTIONS: tuple[Direction, ...] = ("right", "center", "left")
PLACES: list[Place] = [(1.0, 0.0, 0.0), (0.5, 1.0, 2.0), (0.25, -3.0, -1.0)]
RUN_TIME = 1.5


def expanded(place: Place, direction: Direction, fps: int) -> Seen:
    """What a banner, scaled and moved, shows at every instant of its expanding, at `fps`."""
    config.frame_rate = fps
    scale, dx, dy = place
    b = m.ManimBanner().scale(scale).shift([dx, dy, 0])
    parts: dict[str, m.Mobject] = {"M": b.M, "circle": b.circle, "square": b.square}
    parts["triangle"] = b.triangle
    parts |= dict(zip("anim", b.anim, strict=True))

    def construct(scene: m.Scene) -> None:
        scene.add(b)
        scene.play(b.expand(RUN_TIME, direction))

    def seen(scene: m.Scene) -> dict[str, Part]:
        order = {id(leaf): i for i, leaf in enumerate(scene.display_list())}
        return {
            name: (
                float(part.points[:, 0].min()),
                float(part.points[:, 0].max()),
                float(part.paint.fill[:, 3].max()),
                order.get(id(part), -1),
            )
            for name, part in parts.items()
        }

    return scenes.instants(construct, seen)


@pytest.mark.parametrize("fps", [10, 60])
@pytest.mark.parametrize("direction", DIRECTIONS)
@pytest.mark.parametrize("place", PLACES)
def test_the_banner_expands_without_a_jump(
    place: Place,
    direction: Direction,
    fps: int,
) -> None:
    seen = expanded(place, direction, fps)
    # the parting's top speed: (6.25 + 0.8)·s over the first two thirds of the run time,
    # eased in and out (ease_in_out_cubic is steepest, slope 3, halfway)
    top = 7.05 * place[0] * 3 / (RUN_TIME * 2 / 3)
    for a, b in pairwise(sorted(seen)):
        for name in ("M", "square"):
            moved = abs(seen[b][name][0] - seen[a][name][0])
            assert moved <= top * float(b - a) + 1e-9, f"{name} jumps at {b} s"


@pytest.mark.parametrize("direction", DIRECTIONS)
@pytest.mark.parametrize("place", PLACES[1:])
def test_the_banner_ends_as_the_unit_banner_scaled_and_moved(
    place: Place,
    direction: Direction,
) -> None:
    scale, dx, _ = place
    unit = expanded(PLACES[0], direction, 10)
    seen = expanded(place, direction, 10)
    start, end, unit_end = seen[min(seen)], seen[max(seen)], unit[max(unit)]
    for name, (x0, x1, *_) in unit_end.items():
        assert end[name][:2] == pytest.approx(
            (scale * x0 + dx, scale * x1 + dx), abs=1e-9
        )

    def middle(parts: dict[str, Part]) -> float:
        return (parts["M"][0] + parts["triangle"][1]) / 2

    if direction == "right":
        assert end["M"][:2] == pytest.approx(start["M"][:2], abs=1e-9)
    elif direction == "left":
        assert end["square"][:2] == pytest.approx(start["square"][:2], abs=1e-9)
    else:
        assert middle(end) == pytest.approx(middle(start), abs=1e-9)
    for name in "anim":
        assert end[name][2] == 1, f"{name} is shown at the end"
        assert end[name][3] > end["circle"][3], f"{name} ends in front of the shapes"


@pytest.mark.parametrize("direction", DIRECTIONS)
def test_the_letters_are_uncovered_by_the_shapes(
    direction: Direction,
) -> None:
    seen = expanded(PLACES[1], direction, 60)
    instants = sorted(seen)
    for t in instants:
        square = (seen[t]["square"][0] + seen[t]["square"][1]) / 2
        for name in "anim":
            x0, x1, opacity, _ = seen[t][name]
            assert opacity == 0 or (x0 + x1) / 2 < square, f"{name} ahead at {t} s"
    for a, b in pairwise(instants):
        for name in "anim":
            front = [seen[t][name][3] > seen[t]["circle"][3] for t in (a, b)]
            if front[0] != front[1]:  # it changes places with the shapes: none overlaps
                for t in (a, b):
                    assert all(seen[t][k][1] < seen[t]["circle"][0] for k in "anim")

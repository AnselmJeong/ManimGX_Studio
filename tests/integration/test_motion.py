"""An animation carries out what it says, from the world as it finds it — alone or together.

- `.animate` records calls and carries them out when it begins: a Succession of `.animate`
  calls on one object goes on from where the last one left it.
- A call's arguments are as it is written: `.animate.move_to(dot)` goes where the dot was, so a
  Succession of such moves cycles its dots, computed frame by frame or at once. A mobject the
  call makes part of the object, or takes out, is that very mobject.
- A turn is a motion, not an endpoint: `.animate.rotate(a)` keeps the object rigid all the way
  and turns it through the whole angle (a full turn turns).
- Tweens that begin together on one object compose: its motion is all of their steps (a turn
  about the object's moving center, moves added up), its shape and paint change as each says.
  One that begins while another moves the object takes it over from there.

Each story is told with every frame computed, and probed at every instant the scene computes.
"""

import math
from collections.abc import Callable
from fractions import Fraction

import numpy as np
import pytest
from tests import scenes

import manimgx as m

type Probe = Callable[[m.Square], tuple[float, ...]]
pytestmark = pytest.mark.config(frame_rate=10)


def pose(square: m.Square) -> tuple[float, ...]:
    """The square's center, side and first edge's direction (degrees, mod 360)."""
    points = square.points
    edge = points[3] - points[0]
    center = square.get_center()
    angle = math.degrees(math.atan2(edge[1], edge[0])) % 360
    return float(center[0]), float(center[1]), float(np.linalg.norm(edge)), angle


def area(square: m.Square) -> tuple[float, ...]:
    anchors = square.points[::4, :2]
    x, y = anchors[:, 0], anchors[:, 1]
    shoelace = float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    return (abs(shoelace) / 2, float(np.linalg.norm(square.points[0, :2] - 1)))


def told(
    tell: Callable[[m.Square], list[m.Animation]], probe: Probe
) -> dict[Fraction, tuple[float, ...]]:
    """What `probe` sees of a 2×2 square at every instant, as `tell` plays with it for a
    second."""
    square = m.Square(2)

    def construct(scene: m.Scene) -> None:
        scene.add(square)
        scene.play(*tell(square), run_time=1, rate_func=m.linear)

    return scenes.instants(construct, lambda _: probe(square))


@pytest.mark.parametrize("angle", [math.pi / 2, math.pi, 2 * math.pi, -math.pi / 3])
def test_animate_rotate_is_rigid_and_turns_through_its_angle(angle: float) -> None:
    seen = told(lambda s: [s.animate.rotate(angle)], area)
    areas = [a for a, _ in seen.values()]
    assert min(areas) == pytest.approx(4, abs=1e-9), "the square keeps its shape"
    turned = max(travel for _, travel in seen.values())
    chord = 2 * math.sqrt(2) * abs(math.sin(min(abs(angle), math.pi) / 2))
    assert turned == pytest.approx(chord, abs=1e-9), "its corner goes round"


def test_animate_binds_when_it_begins() -> None:
    seen = told(
        lambda s: [
            m.Succession(s.animate.shift(2 * m.RIGHT), s.animate.rotate(m.PI / 2))
        ],
        pose,
    )
    second = [pose for t, pose in seen.items() if t >= Fraction(1, 2)]
    assert all(x == pytest.approx(2, abs=1e-9) for x, *_ in second), "turning in place"
    assert second[-1][3] == pytest.approx(270, abs=1e-6)


def test_animate_chain_turns_about_its_moving_center() -> None:
    seen = told(lambda s: [s.animate.shift(2 * m.RIGHT + m.UP).rotate(m.PI / 2)], pose)
    for t, (x, y, side, _) in seen.items():
        assert (x, y) == pytest.approx((2 * float(t), float(t)), abs=1e-9)
        assert side == pytest.approx(2, abs=1e-9)


CORNERS = (m.UL, m.UR, m.DR, m.DL)


@pytest.mark.parametrize("fast", [False, True])
def test_animate_takes_its_arguments_as_written(fast: bool) -> None:
    """Four dots on the corners, each moved to the next one's corner in turn."""
    dots = [m.Dot(corner) for corner in CORNERS]

    def cycle(scene: m.Scene) -> None:
        scene.add(*dots)
        after = dots[1:] + dots[:1]
        moves = (dot.animate.move_to(to) for dot, to in zip(dots, after, strict=True))
        scene.play(m.Succession(*moves), run_time=1)

    scenes.record(cycle, fast=fast)
    for dot, corner in zip(dots, CORNERS[1:] + CORNERS[:1], strict=True):
        assert dot.get_center() == pytest.approx(corner, abs=1e-9)


def test_animate_adds_and_removes_the_mobjects_it_is_given() -> None:
    square, kept, added = m.Square(), m.Dot(), m.Dot(m.RIGHT)
    square.add(kept)

    def edit(scene: m.Scene) -> None:
        scene.add(square)
        scene.play(square.animate.add(added).remove(kept))

    scenes.scene(edit).render()
    assert any(s is added for s in square.submobjects)
    assert all(s is not kept for s in square.submobjects)


STORIES: dict[
    str, tuple[Callable[[m.Square], list[m.Animation]], tuple[float, ...]]
] = {
    # the corpus's three: a move (and a scale) with a turn
    "shift and scale with a turn": (
        lambda s: [s.animate.shift(m.RIGHT).scale(2), m.Rotate(s, m.PI / 2)],
        (1, 0, 4, 270),
    ),
    "a turn with a shift and scale": (
        lambda s: [m.Rotate(s, m.PI / 2), s.animate.shift(m.RIGHT).scale(2)],
        (1, 0, 4, 270),
    ),
    "two turns": (
        lambda s: [m.Rotate(s, m.PI / 2), m.Rotate(s, m.PI / 3)],
        (0, 0, 2, 330),
    ),
}


@pytest.mark.parametrize("name", STORIES)
def test_tweens_at_once_compose(name: str) -> None:
    tell, end = STORIES[name]
    seen = told(tell, pose)
    assert seen[max(seen)] == pytest.approx(end, abs=1e-6)
    for _x, y, side, _ in seen.values():  # the center never leaves its straight path
        assert y == pytest.approx(0, abs=1e-9) or name == "two turns"
        assert side >= 2 - 1e-9


def test_a_fade_and_a_move_compose() -> None:
    seen = told(
        lambda s: [m.FadeIn(s), s.animate.shift(m.RIGHT)],
        lambda square: (float(square.get_x()), float(square.paint.stroke[0, 3])),
    )
    for t, (x, opacity) in seen.items():
        assert (x, opacity) == pytest.approx((float(t), float(t)), abs=1e-9)


def test_a_tween_that_begins_later_takes_the_object_over() -> None:
    """The turn begins halfway through the shift: from then on the square turns where it is."""
    seen = told(
        lambda s: [
            m.LaggedStart(
                s.animate.shift(2 * m.RIGHT), m.Rotate(s, m.PI / 2), lag_ratio=0.5
            )
        ],
        pose,
    )
    poses = [seen[t] for t in sorted(seen)]
    turning = [p for p in poses if abs(p[3] - 180) > 1e-6]
    assert turning, "the square turns"
    for x, y, side, _ in turning:
        assert (x, y, side) == pytest.approx((turning[0][0], 0, 2), abs=1e-9)
    assert poses[-1][3] == pytest.approx(270, abs=1e-6)


def stroke(square: m.Square) -> tuple[float, ...]:
    """The square's stroke (its first row) and its width."""
    paint = square.paint
    return (*map(float, paint.stroke[0]), float(paint.stroke_width))


@pytest.mark.parametrize("composed", [False, True])
def test_write_draws_each_border_in_the_paint_it_is_seen_in(composed: bool) -> None:
    """A blue square that draws no stroke (its unseen stroke red) is traced in blue, thins
    away in blue and ends as it was: alone, or with a move that outlasts the Write."""

    def tell(s: m.Square) -> list[m.Animation]:
        write = m.Write(s.set_fill(m.BLUE, 1).set_stroke(m.RED, width=0))
        if not composed:
            return [write]
        return [m.AnimationGroup(write, m.Wait(2)), s.animate.shift(m.RIGHT)]

    seen = told(tell, stroke)
    blue, red = (tuple(m.ManimColor(c).to_rgba()) for c in (m.BLUE, m.RED))
    *end, width = seen[max(seen)]
    assert (*end, width) == pytest.approx((*red, 0))
    drawn = [color for *color, width in seen.values() if width > 0]
    assert drawn, "a border is drawn"
    for color in drawn:
        assert color == pytest.approx(blue, abs=1e-6)

"""Scene time is one clock: a frame shows the world at its own instant, at any frame rate.

A time-based updater is handed exactly the time it has been live since it was last brought
forward, attached, added to the scene or resumed, measured on its own clock (`ChangeSpeed`'s
speed clock for `ChangeSpeed.add_updater`); the world is brought to every frame, every play's
end and the closing frame. So in each story below, a dot pushed by such an updater is where its
exact trajectory puts it at every instant the scene computes, at 10, 30 and 60 fps: what a
frame shows does not depend on the frame rate. The corpus cannot see this, since it compares a
scene's closing frame only when CE happens to draw that instant.
"""

from collections.abc import Callable
from fractions import Fraction
from itertools import pairwise

import numpy as np
import pytest

import manimgx as m
from manimgx.animation import clock
from manimgx.config import config
from manimgx.mobject import flow
from manimgx.scene import Act

type Story = Callable[[Probe], None]
type Trajectory = Callable[[Fraction], Fraction]
type Profile = dict[Fraction, Fraction]

SPEED = 4  # units per second of the updater's clock
# ChangeSpeed speed profiles, {node: speed}, with their implicit ends
SLOWING: Profile = {
    Fraction(0): Fraction(1),
    Fraction(2, 5): Fraction(1),
    Fraction(1, 2): Fraction(1, 5),
    Fraction(4, 5): Fraction(1, 5),
    Fraction(1): Fraction(1),
}
TO_A_STOP: Profile = {Fraction(0): Fraction(1), Fraction(1): Fraction(0)}


def push(mob: m.Mobject, dt: float) -> None:
    mob.shift(m.RIGHT * SPEED * dt)


def pull(mob: m.Mobject, dt: float) -> None:
    mob.shift(m.LEFT * SPEED * dt)


class Probe(m.Scene):
    """A dot at x = -4 and a story told with it; at every instant the scene computes, the time,
    the time its own updater has been handed, and where the dot is."""

    def __init__(self, story: Story) -> None:
        super().__init__()
        self.story = story
        self.dot = m.Dot().shift(m.LEFT * 4)
        self.elapsed = 0.0
        self.seen: list[tuple[Fraction, float, float]] = []

    def construct(self) -> None:
        self.add_updater(self.look)
        self.story(self)

    def look(self, dt: float) -> None:
        self.elapsed += dt
        self.seen.append((clock.now, self.elapsed, float(self.dot.get_x())))


def covered(speeds: Profile, length: Fraction, s: Fraction) -> Fraction:
    """How far a ChangeSpeed's wrapped animation, `length` seconds long, has run `s` seconds
    into its play (none before it): between two nodes its speed goes linearly, in real time,
    from one node's to the next's; after the last node, it is scene time again."""
    if s <= 0:
        return Fraction(0)
    done = Fraction(0)
    for (a, v), (b, w) in pairwise(speeds.items()):
        span = length * (b - a) * 2 / (v + w)  # the real time this stretch takes
        if s <= span:
            return done + v * s + (w - v) * s * s / (2 * span)
        s -= span
        done += length * (b - a)
    return done + s


def one_wait(s: Probe) -> None:
    s.add(s.dot)
    s.dot.add_updater(push)
    s.wait(2)


def two_waits(s: Probe) -> None:
    s.add(s.dot)
    s.dot.add_updater(push)
    s.wait(1)
    s.wait(1)


def attached_between_plays(s: Probe) -> None:
    s.add(s.dot)
    s.wait(1)
    s.dot.add_updater(push)
    s.wait(1)


def added_between_plays(s: Probe) -> None:
    s.dot.add_updater(push)
    s.wait(1)
    s.add(s.dot)
    s.wait(1)


def swapped_between_plays(s: Probe) -> None:
    s.add(s.dot)
    s.dot.add_updater(push)
    s.wait(1)
    s.dot.clear_updaters()
    s.dot.add_updater(pull)
    s.wait(1)


def suspended_between_plays(s: Probe) -> None:
    s.add(s.dot)
    s.dot.add_updater(push)
    s.wait(1)
    s.dot.suspend_updating()
    s.wait(1)
    s.dot.resume_updating()
    s.wait(1)


def ending_between_frames(s: Probe) -> None:
    s.add(s.dot)
    s.dot.add_updater(push)
    s.wait(0.25)
    s.wait(1)


def sped(s: Probe) -> None:
    s.add(s.dot)
    m.ChangeSpeed.add_updater(s.dot, push)
    s.play(m.ChangeSpeed(m.Wait(2), speedinfo={0.4: 1, 0.5: 0.2, 0.8: 0.2, 1: 1}))
    s.wait(0.5)


def slowed_to_a_stop(s: Probe) -> None:
    s.add(s.dot)
    m.ChangeSpeed.add_updater(s.dot, push)
    s.wait(1)
    s.play(m.ChangeSpeed(m.Wait(1), speedinfo={1: 0}))


def stopping(t: Fraction) -> Fraction:
    """Where slowed_to_a_stop's dot is: a second at speed 1, then its play's."""
    return -4 + SPEED * (min(t, Fraction(1)) + covered(TO_A_STOP, Fraction(1), t - 1))


STORIES: dict[str, tuple[Story, Trajectory]] = {
    "one_wait": (one_wait, lambda t: -4 + SPEED * t),
    "two_waits": (two_waits, lambda t: -4 + SPEED * t),
    "attached_between_plays": (
        attached_between_plays,
        lambda t: -4 + SPEED * max(t - 1, Fraction(0)),
    ),
    "added_between_plays": (
        added_between_plays,
        lambda t: -4 + SPEED * max(t - 1, Fraction(0)),
    ),
    "swapped_between_plays": (
        swapped_between_plays,
        lambda t: -4 + SPEED * (min(t, Fraction(1)) - max(t - 1, Fraction(0))),
    ),
    "suspended_between_plays": (
        suspended_between_plays,
        lambda t: -4 + SPEED * (min(t, Fraction(1)) + max(t - 2, Fraction(0))),
    ),
    # the closing frame is the first frame time after the end, and shows the world there
    "ending_between_frames": (ending_between_frames, lambda t: -4 + SPEED * t),
    "sped": (sped, lambda t: -4 + SPEED * covered(SLOWING, Fraction(2), t)),
    "slowed_to_a_stop": (slowed_to_a_stop, stopping),
}


@pytest.mark.parametrize("fps", [10, 30, 60])
@pytest.mark.parametrize("name", STORIES)
def test_the_world_at_every_instant(
    name: str, fps: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, trajectory = STORIES[name]
    monkeypatch.setattr(config, "frame_rate", fps)
    scene = Probe(story)
    scene.render()
    instants = {t for t, _, _ in scene.seen}
    unseen = [k for k in range(scene.frame) if Fraction(k, fps) not in instants]
    assert not unseen, f"frames {unseen} were not brought to their instants"
    for t, elapsed, x in scene.seen:
        assert elapsed == pytest.approx(float(t), abs=1e-9), f"scene updater at {t} s"
        assert x == pytest.approx(float(trajectory(t)), abs=1e-9), f"the dot at {t} s"


def spring(mob: m.Mobject, dt: float) -> None:
    """x' = −x, one Euler step: an integrator (two steps of dt/2 are not one of dt)."""
    mob.shift(-mob.get_center() * dt)


class Integrating(m.Scene):
    """A dot a spring pulls to the origin, and the path it traces; where the dot is at every
    instant the scene computes."""

    def construct(self) -> None:
        self.at: dict[Fraction, float] = {}
        self.dot = m.Dot(m.RIGHT * 2).add_updater(spring)
        self.trace = m.TracedPath(self.dot.get_center)
        self.add(self.dot, self.trace)
        self.wait(1.5)

    def _instant(
        self,
        t: Fraction,
        act: Act | None = None,
        stepping: bool = True,
        framing: bool = True,
    ) -> None:
        super()._instant(t, act, stepping, framing)
        self.at[t] = float(self.dot.get_x())


@pytest.mark.parametrize("fps", [10, 24, 25, 30, 60])
def test_a_simulation_does_not_depend_on_the_frame_rate(
    fps: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An updater that integrates steps on the simulation clock — every tick, and at the
    scene's events — never on frames: at every instant, at any frame rate, the dot is where
    that many Euler steps take it (a frame between two ticks shows the last), and the path it
    traces is the same, a point per tick."""
    monkeypatch.setattr(config, "frame_rate", fps)
    scene = Integrating()
    scene.render()
    h = Fraction(1, config.simulation_rate)
    for t, x in scene.at.items():
        assert x == pytest.approx(2 * (1 - float(h)) ** int(t // h), rel=1e-12), t
    shown = max(
        scene.at
    )  # the closing frame: the end, or the first frame time after it
    ticks = [2 * (1 - float(h)) ** k for k in range(int(shown // h) + 1)]
    assert scene.trace.points[3::4, 0] == pytest.approx(ticks, rel=1e-12)


class Tracing(m.Scene):
    """A dot a tween carries round an arc, and the path it traces; at every instant, how far
    the path's end is from the dot."""

    def construct(self) -> None:
        self.gaps: list[float] = []
        self.dot = m.Dot(m.RIGHT * 2)
        self.trace = m.TracedPath(self.dot.get_center)
        self.add(self.dot, self.trace)
        self.play(m.Rotate(self.dot, m.PI, about_point=m.ORIGIN), rate_func=m.linear)

    def _instant(
        self,
        t: Fraction,
        act: Act | None = None,
        stepping: bool = True,
        framing: bool = True,
    ) -> None:
        super()._instant(t, act, stepping, framing)
        gap = self.trace.points[-1] - self.dot.get_center()
        self.gaps.append(float(abs(gap).max()))


@pytest.mark.parametrize("fps", [10, 24, 25, 30, 60])
def test_a_traced_path_is_the_same_at_any_frame_rate(
    fps: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The path a point traces holds where it was at every tick — the same points at any frame
    rate — and at a frame between two ticks runs on to where it is: never behind it."""
    monkeypatch.setattr(config, "frame_rate", fps)
    scene = Tracing()
    scene.render()
    assert max(scene.gaps) < 1e-12
    h = 1 / config.simulation_rate
    angles = np.pi * np.arange(config.simulation_rate + 1) * h
    ticks = np.stack([2 * np.cos(angles), 2 * np.sin(angles)], axis=1)
    assert scene.trace.points[3::4, :2] == pytest.approx(ticks, abs=1e-12)


class Lifting(m.Scene):
    """A dot a flow carries right, which a per-frame updater lifts a step every frame, and the
    path it traces; where the dot is at every frame."""

    def construct(self) -> None:
        self.dot = m.Dot()
        self.dot.add_updater(flow(lambda d, dt: d.shift(m.RIGHT * dt)))
        self.dot.add_updater(lambda d: d.shift(m.UP / 100))
        self.trace = m.TracedPath(self.dot.get_center)
        self.shown: list[np.ndarray] = []
        self.add(self.trace, self.dot)
        self.wait(1)

    def _emit(self, repeat: int = 1) -> None:
        self.shown.append(self.dot.get_center()[:2].copy())
        super()._emit(repeat)


@pytest.mark.parametrize("fps", [10, 24, 25, 30, 60])
def test_a_per_frame_move_is_traced_over_its_frame(
    fps: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A per-frame updater moves a point at frames only: the change it makes at a frame is the
    change over that frame, so the path spreads it over the frame, in proportion to time. Here
    both motions are uniform, so between two frames the path runs straight from where the one
    showed the dot to where the next shows it: no stairs at the ticks between them."""
    monkeypatch.setattr(config, "frame_rate", fps)
    scene = Lifting()
    scene.render()
    shown = np.array(scene.shown)
    for point in scene.trace.points[3::4, :2]:
        k = min(int(point[0] * fps + 1e-9), len(shown) - 2)
        a, b = shown[k], shown[k + 1]
        u, v = b - a, point - a
        assert abs(u[0] * v[1] - u[1] * v[0]) / np.hypot(*u) < 1e-12


class Counting(m.Scene):
    """How often a per-frame updater is called over a play — with a traced path in the scene,
    which is simulated, or without one."""

    def __init__(self, traced: bool) -> None:
        super().__init__()
        self.traced, self.calls = traced, 0

    def construct(self) -> None:
        def count(mob: m.Mobject) -> None:
            self.calls += 1

        dot = m.Dot().add_updater(count)
        self.add(dot)
        if self.traced:
            self.add(m.TracedPath(dot.get_center))
        self.play(dot.animate.shift(m.RIGHT), run_time=2)


@pytest.mark.parametrize("fps", [10, 25, 60])
def test_a_per_frame_updater_runs_once_a_frame(
    fps: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An updater that takes no time is called at every frame and event, and at no tick of the
    simulation clock between them: as often whether or not the scene simulates anything.
    """
    monkeypatch.setattr(config, "frame_rate", fps)
    counts = []
    for traced in (False, True):
        scene = Counting(traced)
        scene.render()
        counts.append(scene.calls)
    assert counts[0] == counts[1]

"""A scene shows the world at each frame's instant, whichever way it computes it, and
whatever its frame rate; it holds its mobjects as its methods say, and runs their updaters
as they stand when their turns come.

- A play the scene computes ahead of time (a pure play: tweens only) shows exactly what the
  same play computed frame by frame shows, for any story, rate functions that overshoot
  included.
- The world at an instant does not depend on the frame rate, for any story: a part begins
  and finishes at its window, an instant the scene computes whether a frame falls there or
  not, and takes the world as it is then, all else brought there first.
- A group of no animations is an error. A wait that stops at a frame ends there: what is
  simulated is brought to that instant.
- Over any run of `add`, `remove`, `add_foreground_mobjects`, `remove_foreground_mobjects`
  and `bring_to_back` over groups that share members, the scene holds what a plain model
  holds: adding takes the added families' members out of the groups that held them (each
  group split, its other members kept in place) and puts them in front, each once, under the
  foreground; removing splits every group that held a removed member the same way; the
  members are each family's in order, each once at its last place, stably sorted by z-index,
  and a frame draws those with points, the foreground's last. However deep the groups are.
- An instant walks a mobject's updaters, then the scene's, as they stood when it began, and
  what is appended to them on the way: each runs when its turn comes if it is still among its
  owner's updaters, once per time it was added, handed the time since it, or an updater equal
  to it, last ran or was added; a recorder runs after everything else, if it is still there.
"""

import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

import numpy as np
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule
from tests.scenes import (
    ANY_RATE,
    Leaf,
    Node,
    Recorder,
    Story,
    assert_same_frames,
    assert_same_instants,
    assert_same_outcome,
    outcome,
    record,
    scene,
    stories,
)

import manimgx as m
from manimgx import mobject as core

# a story renders twice: two fifths of the profile's examples
stories_settings = settings(max_examples=max(10, settings().max_examples * 2 // 5))
RESTRUCTURED = (
    Story(  # a later part restructures its mobject (a circle into three dots)
        stage=["square", "circle"],
        added=[True, True],
        plays=[
            [
                Node(
                    "lagged",
                    [Leaf("fade_in", 0), Leaf("transform", 1, shape="dots")],
                    0.5,
                )
            ]
        ],
    )
)
TURNED = Story(  # a later `.animate` turn turns rigidly, not along the chord
    stage=["dots", "square"],
    added=[True, True],
    plays=[
        [
            Node(
                "succession",
                [Leaf("shift", 0), Leaf("turn", 1, angle=np.pi, rate="linear")],
            )
        ]
    ],
)


class TestComputedAhead:
    @stories_settings
    @given(story=stories(rates=ANY_RATE))
    @example(story=RESTRUCTURED)
    @example(story=TURNED)
    def test_a_play_computed_ahead_is_the_play_computed_frame_by_frame(
        self, story: Story
    ) -> None:
        assert_same_outcome(outcome(story, fast=True), outcome(story, fast=False))


class TestFrameRates:
    @stories_settings
    @given(story=stories(rates=ANY_RATE))
    def test_the_world_at_an_instant_is_the_same_at_every_frame_rate(
        self, story: Story
    ) -> None:
        assert_same_outcome(
            outcome(story, fps=10), outcome(story, fps=30), assert_same_instants
        )


def test_a_group_of_no_animations_is_an_error() -> None:
    def story(s: Recorder) -> None:
        s.play(m.AnimationGroup())

    with pytest.raises(ValueError, match="without animations"):
        record(story)


@pytest.mark.config(frame_rate=30)
@pytest.mark.parametrize(
    ("duration", "count"),
    [
        (math.nextafter(5 / 6, 0), 26),
        (5 / 6, 26),
        (math.nextafter(5 / 6, math.inf), 27),
    ],
)
def test_frame_boundaries_distinguish_adjacent_durations(
    duration: float, count: int
) -> None:
    made = scene(lambda s: s.wait(duration))
    film = made.render()
    assert film.frame_count == count
    assert float(made.clock) == duration


@pytest.mark.parametrize("duration", [1e-8, math.ulp(0.0)])
def test_a_positive_wait_never_becomes_zero(duration: float) -> None:
    made = scene(lambda s: s.wait(duration))
    film = made.render()
    assert float(made.clock) == duration
    assert made.clock > 0
    assert film.frame_count == 2


@pytest.mark.config(frame_rate=10)
def test_an_absolute_target_subtraction_does_not_add_a_frame() -> None:
    def story(s: m.Scene) -> None:
        s.wait(14.6)
        s.wait(20.8 - s.time)
        s.wait(3)
        s.wait(26.4 - s.time)
        s.wait(1.2)
        s.wait(30.5 - s.time)

    made = scene(story)
    film = made.render()
    assert float(made.clock) == 30.5
    assert film.frame_count == 306


@pytest.mark.parametrize("fast", [False, True])
@pytest.mark.parametrize("introduced", [False, True])
def test_observed_event_boundaries_compose_without_rewinding(
    fast: bool, introduced: bool
) -> None:
    def story(s: Recorder, nested: bool) -> None:
        dot = m.Dot()
        first, tiny = m.Wait(0.1), m.Wait(1e-18)
        move = m.Transform(
            dot, dot.copy().shift(m.RIGHT), run_time=0.1, introducer=introduced
        )
        if not introduced:
            s.add(dot)
        if nested:
            s.play(m.Succession(first, tiny, move))
        else:
            s.play(first)
            s.play(tiny)
            s.play(move)

    nested = record(lambda s: story(s, True), fps=10, fast=fast)
    separate = record(lambda s: story(s, False), fps=10, fast=fast)
    assert nested.clock == separate.clock > Fraction(1, 5)
    assert float(nested.clock) == 0.2
    assert nested.frame == separate.frame == 3
    assert_same_frames(nested.frames, separate.frames)


def test_a_sub_ulp_event_never_rewinds_a_simulated_updater() -> None:
    steps: list[float] = []

    def story(s: m.Scene) -> None:
        s.add_updater(steps.append)
        s.wait(0.1)
        s.wait(1e-18)
        s.wait(0.1)

    made = scene(story)
    made.render()
    assert min(steps) >= 0
    assert made.clock > Fraction(1, 5)
    assert float(made.clock) == 0.2


@pytest.mark.config(frame_rate=30000 / 1001)
def test_the_scene_and_film_keep_the_same_fractional_frame_rate() -> None:
    made = scene(lambda s: s.wait(1001 / 30000))
    film = made.render()
    assert film.fps == made._fps() == Fraction(30000, 1001)
    assert made.clock == Fraction(1001, 30000)
    assert film.frame_count == 2


@pytest.mark.parametrize("fps", [7, 10, 24])
def test_a_wait_that_stops_ends_at_its_instant(fps: int) -> None:
    ends: list[tuple[float, float]] = []

    def story(s: Recorder) -> None:
        dot = m.Dot()
        dot.add_updater(
            lambda mob, dt: mob.shift(dt * m.RIGHT)
        )  # simulated: a unit a second
        s.add(dot)
        s.wait_until(lambda: s.time >= 0.05)
        ends.append((s.time, dot.get_x()))

    record(story, fps=fps)
    time, x = ends[0]
    assert time == pytest.approx(
        np.ceil(0.05 * fps) / fps
    )  # the first frame it holds at
    assert x == pytest.approx(time)


# ── membership ─────────────────────────────────────────────────────────────────────────
def ids(mobs: list[m.Mobject]) -> list[int]:
    return [id(x) for x in mobs]


def once(mobs: list[m.Mobject]) -> list[m.Mobject]:
    """Each once, at its last place."""
    return [x for i, x in enumerate(mobs) if all(y is not x for y in mobs[i + 1 :])]


def family(roots: list[m.Mobject]) -> list[m.Mobject]:
    """Every member of the roots' families, in order (a group before its members), each
    once, at its last place."""
    order: list[m.Mobject] = []

    def visit(mob: m.Mobject) -> None:
        order.append(mob)
        for child in mob.submobjects:
            visit(child)

    for root in roots:
        visit(root)
    return once(order)


def split(roots: list[m.Mobject], taken: set[int]) -> list[m.Mobject]:
    """The roots with the members `taken` out: each group that held one gives way to its
    other members, in place (and goes, if none is left)."""

    def prune(mob: m.Mobject) -> tuple[bool, list[m.Mobject]]:
        if id(mob) in taken:
            return True, []
        parts = [prune(child) for child in mob.submobjects]
        if any(hit for hit, _ in parts):
            return True, [x for _, kept in parts for x in kept]
        return False, [mob]

    return [x for root in roots for x in prune(root)[1]]


picks = st.lists(st.integers(0, 99), min_size=1, max_size=3)


class Membership(RuleBasedStateMachine):
    """The scene against a plain model of what its methods say it holds."""

    @initialize(
        edges=st.lists(st.lists(st.integers(0, 9), max_size=3), min_size=1, max_size=8),
        drawn=st.lists(st.booleans(), min_size=10, max_size=10),
        z=st.lists(st.sampled_from([0, 0, 1]), min_size=10, max_size=10),
    )
    def begin(self, edges: list[list[int]], drawn: list[bool], z: list[int]) -> None:
        self.nodes = [m.Mobject()]
        for indexes in edges:  # groups over the members before them: shared, nested
            parent = m.Mobject()
            parent.submobjects = [self.nodes[i % len(self.nodes)] for i in indexes]
            self.nodes.append(parent)
        for node, points, depth in zip(self.nodes, drawn, z, strict=False):
            if points:
                node.points = np.zeros((1, 3))
            node.z_index = depth
        self.scene = m.Scene()
        self.mobjects: list[m.Mobject] = []
        self.foreground: list[m.Mobject] = []

    def picked(self, which: list[int]) -> list[m.Mobject]:
        return once([self.nodes[i % len(self.nodes)] for i in which])

    def added(self, mobs: list[m.Mobject]) -> None:
        new = once([*mobs, *self.foreground])
        self.mobjects = split(self.mobjects, {id(x) for x in family(new)}) + new

    def removed(self, mobs: list[m.Mobject]) -> None:
        taken = {id(x) for x in mobs}
        self.mobjects = split(self.mobjects, taken)
        self.foreground = split(self.foreground, taken)

    @rule(which=picks)
    def add(self, which: list[int]) -> None:
        self.scene.add(*self.picked(which))
        self.added(self.picked(which))

    @rule(which=picks)
    def remove(self, which: list[int]) -> None:
        self.scene.remove(*self.picked(which))
        self.removed(self.picked(which))

    @rule(which=picks)
    def add_foreground(self, which: list[int]) -> None:
        self.scene.add_foreground_mobjects(*self.picked(which))
        self.foreground = once([*self.foreground, *self.picked(which)])
        self.added(self.picked(which))

    @rule(which=picks)
    def remove_foreground(self, which: list[int]) -> None:
        self.scene.remove_foreground_mobjects(*self.picked(which))
        taken = {id(x) for x in family(self.picked(which))}
        self.foreground = split(self.foreground, taken)

    @rule(which=picks)
    def bring_to_back(self, which: list[int]) -> None:
        self.scene.bring_to_back(*self.picked(which))
        self.removed(self.picked(which))
        self.mobjects = [*self.picked(which), *self.mobjects]

    @invariant()
    def it_holds_what_its_methods_say(self) -> None:
        assert ids(self.scene.mobjects) == ids(self.mobjects)
        assert ids(self.scene.foreground_mobjects) == ids(self.foreground)
        members = sorted(family(self.mobjects), key=lambda x: x.z_index)
        assert ids(self.scene.get_mobject_family_members()) == ids(members)
        everything = family([*self.mobjects, *self.foreground])
        drawn = sorted(
            [x for x in everything if x.has_points()], key=lambda x: x.z_index
        )
        assert ids(self.scene.display_list()) == ids(drawn)


TestMembership = Membership.TestCase
TestMembership.settings = settings(stateful_step_count=20)


def test_scene_membership_handles_groups_deeper_than_the_call_stack() -> None:
    leaf = m.Mobject()
    tree = leaf
    for _ in range(sys.getrecursionlimit() + 10):
        parent = m.Group()
        parent.submobjects = [tree]
        tree = parent
    scene = m.Scene().add(tree)
    scene.remove(m.Mobject())
    assert scene.mobjects == [tree]
    scene.remove(leaf)
    assert scene.mobjects == []


# ── the updaters of an instant ─────────────────────────────────────────────────────────
VERBS = (
    "nothing",
    "remove",
    "readd",
    "clear",
    "match",
    "append",
    "remove an equal one",
    "drop the scene's other",
)
KINDS = ("plain", "recorder", "twin", "twin recorder", "again")


@dataclass
class Entry:
    """An updater of the program: its kind ("again": an earlier one, added once more), and
    what it does the first time it runs."""

    kind: str
    verb: str = "nothing"
    target: int = 0


@dataclass
class Made:
    """An updater as made: the object, its label in the log, whether it records, what makes
    it equal to others (equal updaters share their clock), and its action's index."""

    updater: Callable[[m.Mobject, float], None]
    label: str
    records: bool
    key: object
    action: int | None


programs = st.lists(
    st.builds(
        Entry,
        kind=st.sampled_from(KINDS),
        verb=st.sampled_from(VERBS),
        target=st.integers(0, 4),
    ),
    min_size=1,
    max_size=5,
)
scene_actions = st.none() | st.tuples(st.sampled_from(VERBS), st.integers(0, 4))


class Twin:
    """An owner of an updater method: every `twin.run` is equal to every other, not the same."""

    def __init__(self, log: list[tuple[str, float]]) -> None:
        self.log = log

    def run(self, mob: m.Mobject, dt: float) -> None:
        self.log.append(("twin", dt))


class RecordingTwin(Twin):
    @core.record
    def run(self, mob: m.Mobject, dt: float) -> None:
        self.log.append(("twin recorder", dt))


def told(
    program: list[Entry], scene_action: tuple[str, int] | None
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    """(what the scene ran, what the law says runs) for one instant, a second after the
    updaters were added."""
    log: list[tuple[str, float]] = []
    acted: set[int] = set()
    host, donor, scene = m.Mobject(), m.Mobject(), m.Scene()
    twins = {"twin": Twin(log), "twin recorder": RecordingTwin(log)}
    made: list[Made] = []
    actions: list[tuple[str, int]] = [(e.verb, e.target) for e in program]
    if scene_action is not None:
        actions.append(scene_action)

    def plain(label: str, action: int | None) -> Callable[[m.Mobject, float], None]:
        def updater(mob: m.Mobject, dt: float) -> None:
            log.append((label, dt))
            if action is not None and action not in acted:
                acted.add(action)
                act(action)

        return updater

    for i, entry in enumerate(program):
        if entry.kind in twins:
            twin = twins[entry.kind]
            made.append(
                Made(twin.run, entry.kind, entry.kind == "twin recorder", twin, None)
            )
        elif entry.kind == "again" and i > 0:
            made.append(made[entry.target % i])
        else:
            updater = plain(str(i), i)
            if entry.kind == "recorder":
                core.record(updater)
            made.append(Made(updater, str(i), entry.kind == "recorder", updater, i))
    fresh = Made(plain("new", None), "new", False, "new", None)
    donated = Made(plain("donated", None), "donated", False, "donated", None)
    donor.add_updater(donated.updater)

    def other(dt: float) -> None:  # the scene's second updater
        log.append(("scene's other", dt))

    def act(action: int) -> None:
        verb, target = actions[action]
        chosen = made[target % len(made)]
        if verb == "drop the scene's other":
            scene.remove_updater(other)
        if verb in ("remove", "readd"):
            host.remove_updater(chosen.updater)
        if verb == "readd":
            host.add_updater(chosen.updater)
        if verb == "remove an equal one":
            equal = chosen.key.run if isinstance(chosen.key, Twin) else chosen.updater
            host.remove_updater(equal)
        if verb == "clear":
            host.clear_updaters()
        if verb == "match":
            host.match_updaters(donor)
        if verb == "append":
            host.add_updater(fresh.updater)

    for x in made:
        host.add_updater(x.updater)
    scene.add(host)
    if scene_action is not None:
        index = len(actions) - 1

        def on_scene(dt: float) -> None:
            log.append(("scene", dt))
            if index not in acted:
                acted.add(index)
                act(index)

        scene.add_updater(on_scene)
        scene.add_updater(other)
    # one instant, as the scene computes each: the private pass is the only way to make one
    # alone (a render makes many, each over updaters the instant before changed)
    scene._records = scene._recording()
    scene._pass(Fraction(1), None, stepping=True, framing=False)
    return log, law(made, actions, scene_action is not None, fresh, donated)


def law(
    made: list[Made],
    actions: list[tuple[str, int]],
    on_scene: bool,
    fresh: Made,
    donated: Made,
) -> list[tuple[str, float]]:
    """What runs at the instant, by the law: a plain interpreter of it."""
    t, log, acted = 1.0, [], set()
    walk = [x.updater for x in made]  # the updaters as the instant began
    live = walk  # as they are now: the same list until one is made anew
    info = {id(x.updater): x for x in (*made, fresh, donated)}
    clocks: dict[object, float] = {info[id(u)].key: 0.0 for u in walk}
    records = any(x.records for x in made)
    collected: list[Callable[[m.Mobject, float], None]] = []
    dropped = False  # the scene's other updater

    def run(updater: Callable[[m.Mobject, float], None]) -> None:
        x = info[id(updater)]
        log.append((x.label, t - clocks.get(x.key, t)))
        clocks[x.key] = t
        if x.action is not None and x.action not in acted:
            acted.add(x.action)
            act(x.action)

    def without(updater: Callable[[m.Mobject, float], None]) -> None:
        nonlocal live
        live = [u for u in live if u is not updater]
        key = info[id(updater)].key if id(updater) in info else None
        if not any(info[id(u)].key == key for u in live):
            clocks.pop(key, None)

    def act(action: int) -> None:
        nonlocal live, dropped
        verb, target = actions[action]
        chosen = made[target % len(made)]
        dropped = dropped or verb == "drop the scene's other"
        if verb in ("remove", "readd"):
            without(chosen.updater)
        if verb == "readd":
            live.append(chosen.updater)
            clocks[chosen.key] = t
        if verb == "remove an equal one":
            if isinstance(chosen.key, Twin):  # equal, not the same: nothing goes
                live = list(live)
            else:
                without(chosen.updater)
        if verb in ("clear", "match"):
            live = []
            clocks.clear()
        if verb == "match":
            live.append(donated.updater)
            clocks[donated.key] = t
        if verb == "append":
            live.append(fresh.updater)
            clocks[fresh.key] = t

    for updater in walk:  # a list that grows as it is walked while it is the live one
        if live is not walk and not any(u is updater for u in live):
            continue
        if records and info[id(updater)].records:
            collected.append(updater)
            continue
        run(updater)
    if on_scene:  # the scene's updaters, as they stand when their turns come
        log.append(("scene", 1.0))
        act(len(actions) - 1)
        if not dropped:
            log.append(("scene's other", 1.0))
    for updater in collected:
        if any(u is updater for u in live):
            run(updater)
    return log


@settings(max_examples=150)
@given(program=programs, scene_action=scene_actions)
@example(  # an updater re-added before its turn runs from now
    program=[Entry("plain", "readd", 1), Entry("plain")], scene_action=None
)
@example(  # a scene updater cancels a recorder the mobject's walk collected
    program=[Entry("recorder"), Entry("plain")], scene_action=("remove", 0)
)
@example(  # a recorder that removes itself does not run its second time
    program=[Entry("recorder", "remove", 0), Entry("again", target=0)],
    scene_action=None,
)
@example(  # equal methods share one clock; the one left after removal keeps it
    program=[Entry("twin recorder"), Entry("twin recorder")],
    scene_action=("remove an equal one", 0),
)
def test_an_updater_runs_if_it_is_there_when_its_turn_comes(
    program: list[Entry], scene_action: tuple[str, int] | None
) -> None:
    ran, expected = told(program, scene_action)
    assert ran == expected


def test_a_recorder_cleared_in_place_does_not_run() -> None:
    log: list[str] = []
    scene, host = m.Scene(), m.Mobject()

    @core.record
    def recorder(mob: m.Mobject, dt: float) -> None:
        log.append("recorder")

    scene.add(host.add_updater(recorder))
    scene.add_updater(lambda dt: host.updaters.clear())  # (its list, edited in place)
    scene._records = scene._recording()
    scene._pass(Fraction(1), None, stepping=True, framing=False)
    assert log == []

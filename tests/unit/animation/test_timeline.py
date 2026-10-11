"""An animation is a function of its progress: parts staggered in exact windows, keyframes
reached exactly, rate functions followed past their ends.

- Every animation, by registry (`ANIMATIONS`): made, it changes none of the mobjects it is
  given, nor their saved states; begun, it shows what it showed (it acts only when brought to a
  progress); brought to a progress, it shows the same whether or not it was at another before
  (a composition only going forward: its finished parts stay finished).
- A part's progress runs through its window of the animation's (the first opening at 0, the
  last closing at 1), eased by the rate function; at the ends of its window it is exactly the
  rate function's ends, so a finished animation is exactly its end state, a play of no length
  too.
- Past the ends of the unit interval (a rate function that overshoots or backs up), a tween's
  end intervals run on: a move or a turn eased by `ease_out_back` goes 10% past its end and
  back.
- While an animation plays, a mobject whose updating it suspends moves as its updaters move it
  (they run on a model of it); then it resumes the updating it suspended, and only that: a
  mobject suspended before it began stays suspended.


A group plays its parts, each in its window of the group's time; it is not itself a
mobject of the scene.

- Laws: a group of one part plays the part; a LaggedStart of no lag is an AnimationGroup is a
  play of the parts; successions nest; a group easing one linear part plays it as the part eased
  itself, rate functions that come back included.
- A group lasts until its last part ends; a play's `lag_ratio` and `run_time` lay it out as if
  given to the group. A part over the whole group is handed the group's time bit for bit.
- At every instant of a play, for any story, the scene holds what it held, then what the play
  acts on that it lacked (each by itself, in order), then each introducer's mobject from its
  window's opening; as a part's window closes, a remover's mobject leaves and a replacement's
  target takes its mobject's place.


ChangeSpeed plays an animation along a speed profile, and its clock keeps pace.

- Between two points of `speedinfo` the speed changes steadily in the scene's time: the
  animation's measured pace is the profile's speed, and it reaches each point when the
  stretches before it (`(b − a)·2/(v + w)` of its run time each) have played.
- At speed 1 throughout it is the animation itself, frame for frame, and its updaters get the
  scene's time.
- The updaters of `ChangeSpeed.add_updater` run at the same speeds, from the instant the
  ChangeSpeed begins, whatever the animation's rate function; their clock never runs backward,
  even while two ChangeSpeeds overlap (the one begun last rules).
"""

from collections.abc import Callable
from fractions import Fraction
from itertools import pairwise
from typing import Unpack

import numpy as np
import pytest
from hypothesis import example, given, reject, settings
from hypothesis import strategies as st
from tests.oracles import look as appearance
from tests.scenes import (
    SHAPES,
    Leaf,
    Look,
    Recorder,
    Story,
    assert_same_frames,
    assert_same_outcome,
    instants,
    leaves,
    look,
    outcome,
    record,
    same_look,
    stories,
)
from tests.strategies import ANIMATIONS, RATE_FUNCTIONS

import manimgx as m
from manimgx.animation import clock
from manimgx.animation import easing as rf
from manimgx.animation.timeline import (
    Animation,
    AnimationGroup,
    keyframe_at,
    prepare,
    schedule,
    warp,
    windows,
)
from manimgx.animation.transform import Transform, TransformOptions

ENDING = [f for f in RATE_FUNCTIONS if f(1.0) == 1]  # the rate functions that arrive
lags = st.sampled_from([0.0, 0.05, 0.1, 0.2, 1 / 3, 0.5, 0.9, 1.0])


class TestGetSubAlpha:
    @given(lag=lags, n=st.integers(1, 12))
    def test_a_windows_ends_are_exact(self, lag: float, n: int) -> None:
        anim = m.Animation(m.Mobject(), lag_ratio=lag, rate_func=rf.linear)
        assert anim.get_sub_alpha(0.0, 0, n) == 0.0
        assert anim.get_sub_alpha(1.0, n - 1, n) == 1.0
        for i in range(n):  # every part has finished at the end, none has begun at 0
            assert anim.get_sub_alpha(1.0, i, n) == 1.0
            assert anim.get_sub_alpha(0.0, i, n) == 0.0

    @given(lag=lags, n=st.integers(2, 12), alpha=st.floats(0, 1))
    def test_parts_go_in_order(self, lag: float, n: int, alpha: float) -> None:
        anim = m.Animation(m.Mobject(), lag_ratio=lag, rate_func=rf.linear)
        progress = [anim.get_sub_alpha(alpha, i, n) for i in range(n)]
        assert all(a >= b for a, b in pairwise(progress))
        assert all(0 <= p <= 1 for p in progress)

    @given(lag=lags, n=st.integers(1, 6), alpha=st.floats(0, 1))
    def test_each_part_runs_the_rate_function_in_its_window(
        self, lag: float, n: int, alpha: float
    ) -> None:
        anim = m.Animation(m.Mobject(), lag_ratio=lag, rate_func=rf.ease_out_back)
        span = (n - 1) * lag + 1
        for i in range(n):
            time = min(max(alpha * span - i * lag, 0.0), 1.0)
            assert anim.get_sub_alpha(alpha, i, n) == pytest.approx(
                rf.ease_out_back(time), abs=1e-12
            )


class TestKeyframeAt:
    @given(steps=st.integers(1, 5), alpha=st.floats(-1, 2))
    def test_it_is_continuous_and_runs_on_past_the_ends(
        self, steps: int, alpha: float
    ) -> None:
        i, t = keyframe_at(steps, alpha)
        assert 0 <= i < steps
        assert i + t == pytest.approx(alpha * steps, abs=1e-9)


ENDS = [
    *(
        pytest.param(rate, lag, 1.0, id=f"{getattr(rate, '__name__', '')}-{lag:.2g}")
        for rate in ENDING
        for lag in (0.0, 0.1, 0.2, 1 / 3, 0.9)
    ),
    pytest.param(rf.smooth, 0.0, 0.0, id="a play of no length"),
]


class TestEnds:
    @pytest.mark.parametrize(("rate", "lag", "run_time"), ENDS)
    def test_a_finished_transform_is_exactly_its_target(
        self, rate: rf.RateFunction, lag: float, run_time: float
    ) -> None:
        start = m.VGroup(*(m.Square(0.5).shift(i * m.RIGHT) for i in range(4)))
        target = m.VGroup(
            *(
                m.Circle(0.3, color=m.RED, fill_opacity=0.7).shift(i * m.UP)
                for i in range(4)
            )
        )

        def story(s: Recorder) -> None:
            s.stage = [start]
            s.add(start)
            s.play(
                m.Transform(
                    start, target, rate_func=rate, lag_ratio=lag, run_time=run_time
                )
            )

        record(story, fps=10)
        for got, want in zip(
            start.family_members_with_points(),
            target.family_members_with_points(),
            strict=True,
        ):
            # (to a rounding: a blend's points are sums of its terms)
            np.testing.assert_allclose(got.points, want.points, rtol=0, atol=1e-12)
            assert got.paint.mix is None  # a plain paint, not one left mid-tween
            for name in ("fill", "stroke"):
                np.testing.assert_array_equal(
                    getattr(got.paint, name), getattr(want.paint, name)
                )

    @pytest.mark.parametrize(
        "rate",
        [rf.ease_out_back, rf.ease_in_back, rf.running_start, rf.ease_out_elastic],
        ids=lambda f: f.__name__,
    )
    @pytest.mark.parametrize("kind", ["move", "turn"])
    def test_a_tween_follows_its_rate_function_past_its_ends(
        self, rate: rf.RateFunction, kind: str
    ) -> None:
        """A move's distance, and a turn's angle, are the rate function's at every instant."""
        square = m.Square()
        start = square.points[0] - square.get_center()

        # the move's distance, or the turn's angle (a quarter turn: 1)
        def done() -> float:
            if kind == "move":
                return float(square.get_x())
            corner = square.points[0] - square.get_center()
            return float(np.angle(complex(*corner[:2]) / complex(*start[:2]))) / (
                np.pi / 2
            )

        def story(s: m.Scene) -> None:
            s.add(square)
            s.play(
                square.animate(rate_func=rate, run_time=1).shift(m.RIGHT)
                if kind == "move"
                else m.Rotate(square, np.pi / 2, rate_func=rate, run_time=1)
            )

        for t, got in instants(story, lambda s: done()).items():
            assert got == pytest.approx(rate(float(min(t, 1))), abs=1e-9), t


def kept(world: list[m.Mobject]) -> list[object]:
    """What the given mobjects show, and what their saved states would restore."""
    return [appearance(mob) for mob in world] + [
        None
        if (saved := getattr(mob, "saved_state", None)) is None
        else appearance(saved)
        for mob in world
    ]


def visible(world: list[m.Mobject], anim: Animation) -> list[Look]:
    """What a frame would draw of the given mobjects and of the animation's own, leaf by leaf:
    the leaves seen (a transparent one, as alignment adds, draws nothing)."""
    roots = list(dict.fromkeys([*world, anim.mobject]))
    drawn = dict.fromkeys(x for r in roots for x in r.get_family() if x.has_points())
    return [
        look(x)
        for x in drawn
        if max(x.paint.fill[:, 3].max(), x.paint.stroke[:, 3].max()) > 1e-9
    ]


def assert_same_leaves(a: list[Look], b: list[Look]) -> None:
    assert len(a) == len(b), f"{len(a)} leaves seen, then {len(b)}"
    for i, (x, y) in enumerate(zip(a, b, strict=True)):
        assert same_look(x, y), f"leaf {i} differs"


def every(xfails: dict[str, str] | None = None) -> pytest.MarkDecorator:
    """Each registry entry, those that fail the law for a bug of their own marked so."""
    xfails = xfails or {}
    return pytest.mark.parametrize(
        "name",
        [
            pytest.param(
                name, marks=pytest.mark.xfail(strict=True, reason=xfails[name])
            )
            if name in xfails
            else name
            for name in sorted(ANIMATIONS)
        ],
    )


class TestEveryAnimation:
    @every()
    def test_made_it_changes_nothing(self, name: str) -> None:
        played = ANIMATIONS[name]
        world = played.world()
        before = kept(world)
        played.make(world)
        assert kept(world) == before

    @every()
    def test_begun_it_shows_what_it_showed(self, name: str) -> None:
        played = ANIMATIONS[name]
        world = played.world()
        anim = played.make(world)
        before = visible(world, anim)
        anim.begin()
        assert_same_leaves(before, visible(world, anim))

    @every()
    @settings(max_examples=8)
    @given(a=st.floats(0, 1), b=st.floats(0, 1))
    def test_it_is_a_function_of_its_progress(
        self, name: str, a: float, b: float
    ) -> None:
        clock.reset()  # (a ChangeSpeed warps the scene's speed clock as it begins)
        played = ANIMATIONS[name]
        there, straight = played.world(), played.world()
        anim, direct = played.make(there), played.make(straight)
        if isinstance(anim, AnimationGroup):  # its finished parts stay finished
            a, b = sorted((a, b))
        anim.begin()
        anim.interpolate(a)
        anim.interpolate(b)
        direct.begin()
        direct.interpolate(b)
        assert_same_leaves(visible(there, anim), visible(straight, direct))


SUSPENDING: dict[str, Callable[[m.Mobject], m.Animation]] = {
    "a tween": lambda dot: dot.animate.set_color(m.RED),
    "a procedure": lambda dot: m.UpdateFromAlphaFunc(
        dot,
        lambda mob, alpha: mob.set_opacity(1 - alpha / 2),
        suspend_mobject_updating=True,
    ),
}


@pytest.mark.parametrize("name", sorted(SUSPENDING))
def test_an_animation_resumes_only_the_updating_it_suspended(name: str) -> None:
    held, free = m.Dot(), m.Dot(m.UP)

    def construct(s: m.Scene) -> None:
        for dot in (held, free):
            dot.add_updater(lambda mob, dt: mob.shift(dt * m.RIGHT))
        held.suspend_updating()
        s.add(held, free)
        s.play(SUSPENDING[name](held), SUSPENDING[name](free))
        s.wait(1)

    seen = instants(construct, lambda s: (held.get_x(), free.get_x()))
    assert max(seen) == 2
    for t, (x_held, x_free) in seen.items():  # (in the play, a model of it moves it)
        assert (x_held, x_free) == (0, pytest.approx(t)), t
    assert held.updating_suspended
    assert not free.updating_suspended


Play = Callable[[list[m.Mobject]], list[m.Animation]]


def story(
    play: Play, **options: Unpack[TransformOptions]
) -> Callable[[Recorder], None]:
    """Three overlapping shapes on the stage, then one play (with the play's options)."""

    def tell(s: Recorder) -> None:
        s.stage = [
            m.Square(1.6, color=m.BLUE, fill_opacity=0.5),
            m.Circle(0.8, color=m.RED, fill_opacity=0.5).shift(0.5 * m.RIGHT),
            m.Triangle(color=m.GREEN, fill_opacity=0.5).shift(0.4 * m.UP),
        ]
        s.add(*s.stage)
        s.play(*play(s.stage), **options)

    return tell


def told(play: Play, fps: int = 10) -> Recorder:
    return record(story(play), fps)


def alike(*plays: Play) -> None:
    first = outcome(story(plays[0]))
    for play in plays[1:]:
        assert_same_outcome(outcome(story(play)), first)


def built(parts: list[Leaf]) -> Callable[[list[m.Mobject]], list[m.Animation]]:
    return lambda stage: [leaf.build(stage) for leaf in parts]


class TestLaws:
    @given(leaf=leaves(3))
    def test_a_group_of_one_is_its_part(self, leaf: Leaf) -> None:
        alike(lambda s: [leaf.build(s)], lambda s: [m.AnimationGroup(leaf.build(s))])

    @given(parts=st.lists(leaves(3), min_size=1, max_size=3))
    def test_a_lagged_start_of_no_lag_is_a_group_is_a_play(
        self, parts: list[Leaf]
    ) -> None:
        make = built(parts)
        alike(
            make,
            lambda s: [m.AnimationGroup(*make(s))],
            lambda s: [m.LaggedStart(*make(s), lag_ratio=0)],
        )

    @given(parts=st.lists(leaves(3), min_size=3, max_size=3))
    def test_successions_nest(self, parts: list[Leaf]) -> None:
        make = built(parts)
        alike(
            lambda s: [m.Succession(*make(s))],
            lambda s: [m.Succession(make(s)[0], m.Succession(*make(s)[1:]))],
            lambda s: [m.Succession(m.Succession(*make(s)[:2]), make(s)[2])],
        )

    @pytest.mark.parametrize(
        "rate",
        [
            f
            for f in RATE_FUNCTIONS
            if all(0 <= f(t) <= 1 for t in np.linspace(0, 1, 101))
        ],
        ids=lambda f: f.__name__,
    )
    @pytest.mark.parametrize("fps", [7, 10, 60])
    def test_a_group_eases_its_part_as_the_part_eases_itself(
        self, rate: rf.RateFunction, fps: int
    ) -> None:
        def eased(by_group: bool) -> Play:
            def play(s: list[m.Mobject]) -> list[m.Animation]:
                if by_group:
                    return [
                        m.AnimationGroup(
                            s[0].animate(rate_func=rf.linear).shift(m.RIGHT),
                            rate_func=rate,
                        )
                    ]
                return [s[0].animate(rate_func=rate).shift(m.RIGHT)]

            return play

        group, part = told(eased(True), fps), told(eased(False), fps)
        assert_same_frames(group.frames, part.frames)
        np.testing.assert_allclose(
            group.stage[0].get_center(), part.stage[0].get_center(), atol=1e-12
        )


class TestLayout:
    @given(
        times=st.lists(
            st.sampled_from([0.0, 0.3, 0.5, 1.0, 2.5]), min_size=1, max_size=5
        ),
        lag=st.floats(0, 2),
    )
    @example(times=[2.5, 0.0], lag=1.0000004191481406)
    def test_a_group_lasts_until_its_last_part_ends(
        self, times: list[float], lag: float
    ) -> None:
        group = m.AnimationGroup(
            *(m.Animation(m.Mobject(), run_time=t) for t in times), lag_ratio=lag
        )
        ends = [lag * sum(times[:i]) + t for i, t in enumerate(times)]
        assert group.run_time == pytest.approx(max(ends), abs=1e-6)
        assert m.Succession(*group.animations).run_time == pytest.approx(
            sum(times), abs=1e-6
        )

    @given(times=st.lists(st.floats(0, 5), min_size=2, max_size=5))
    @example(times=[2.500001047870352, 1e-8, 1 / 3])
    def test_nested_successions_keep_exact_durations(self, times: list[float]) -> None:
        parts = [m.Wait(t) for t in times]
        flat = m.Succession(*parts)
        nested = m.Succession(parts[0], m.Succession(*parts[1:]))
        expected = sum((clock.rational(t) for t in times), Fraction(0))
        assert flat._duration == nested._duration == expected
        flat_windows, nested_windows = windows(flat), windows(nested)
        assert [w.opens * flat._duration for w in flat_windows] == [
            w.opens * nested._duration for w in nested_windows
        ]

    @given(
        parts=st.lists(leaves(3), min_size=2, max_size=3),
        lag=st.sampled_from([0.25, 0.5, 1.0]),
        run_time=st.sampled_from([0.5, 2.0]),
    )
    def test_a_plays_options_lay_the_group_out(
        self, parts: list[Leaf], lag: float, run_time: float
    ) -> None:
        make = built(parts)
        by_group = story(
            lambda s: [m.AnimationGroup(*make(s), lag_ratio=lag, run_time=run_time)]
        )
        by_play = story(
            lambda s: [m.AnimationGroup(*make(s))], lag_ratio=lag, run_time=run_time
        )
        assert_same_outcome(outcome(by_play), outcome(by_group))

    @given(alpha=st.lists(st.floats(0, 1), min_size=1, max_size=20))
    def test_a_part_over_the_whole_group_gets_its_time_bit_for_bit(
        self, alpha: list[float]
    ) -> None:
        group = m.AnimationGroup(
            m.Animation(m.Mobject(), run_time=2),
            m.Animation(m.Mobject(), run_time=1),
            rate_func=rf.smooth,
        )
        a = np.array(alpha)
        (_, whole, _), _ = schedule(group, a)
        np.testing.assert_array_equal(whole, warp(rf.smooth, a))


def held(before: list[m.Mobject], play: Animation, at: Fraction) -> list[m.Mobject]:
    """What a scene holding `before` holds at a progress of a play, by the play's rule."""
    members = list(before)

    def lacks(mob: m.Mobject) -> bool:
        family = {id(x) for root in members for x in root.get_family()}
        return id(mob) not in family and any(
            x.has_points() or x.updaters for x in mob.get_family()
        )

    def replacing(part: Animation) -> m.Mobject | None:
        """The target that takes the part's mobject's place as it closes, if any."""
        if isinstance(part, Transform) and part.replace_mobject_with_target_in_scene:
            return part.target_mobject
        return None

    parts = windows(play)
    promised: set[int] = (
        set()
    )  # what joins later: an introducer's, a replacement's target
    for part, *_ in parts:
        if part.is_introducer():
            promised.add(id(part.mobject))
        elif id(part.mobject) not in promised and lacks(part.mobject):
            members.append(part.mobject)
        if (target := replacing(part)) is not None:
            promised.add(id(target))
    # an instant is where its float is, as the play's parts compare times: at one, what
    # closes before what opens
    events = sorted(
        [(float(w.opens), 1, w.part) for w in parts]
        + [(1.0 if w.closes is None else float(w.closes), 0, w.part) for w in parts],
        key=lambda event: (event[0], event[1]),
    )
    for when, opens, part in events:
        if when > float(at):
            break
        if opens:
            if part.is_introducer() and lacks(part.mobject):
                members.append(part.mobject)
            continue
        if part.is_remover():
            members = [x for x in members if x is not part.mobject]
        if (new := replacing(part)) is not None:
            members = [new if x is part.mobject else x for x in members if x is not new]
    return members


class TestMembership:
    @pytest.mark.config(frame_rate=10)
    @settings(max_examples=30)
    @given(story=stories())
    def test_a_play_changes_the_scene_only_as_its_parts_open_and_close(
        self, story: Story
    ) -> None:
        plays: list[tuple[Fraction, Fraction, list[m.Mobject], Animation]] = []
        after: list[tuple[list[m.Mobject], list[m.Mobject]]] = []

        def tell(s: m.Scene) -> None:
            stage = [
                SHAPES[shape]().shift([i - 2.0, 0.5 * (i % 2), 0])
                for i, shape in enumerate(story.stage)
            ]
            s.add(
                *(mob for mob, added in zip(stage, story.added, strict=True) if added)
            )
            for trees in story.plays:
                anims = [prepare(tree.build(stage)) for tree in trees]
                play = (
                    anims[0]
                    if len(anims) == 1
                    else AnimationGroup(
                        *anims, group=m.Group(), suspend_mobject_updating=False
                    )
                )
                start, before = s.clock, list(s.mobjects)
                s.play(play)
                plays.append((start, s.clock, before, play))
                after.append((list(s.mobjects), held(before, play, Fraction(1))))

        try:
            seen = instants(tell, lambda s: [id(x) for x in s.mobjects])
        except ValueError:  # a story may ask the impossible (see tests.scenes.outcome)
            reject()
        for start, end, before, play in plays:
            for t, members in seen.items():
                if start < t < end:
                    expected = held(before, play, (t - start) / (end - start))
                    assert members == [id(x) for x in expected], f"at {t} s"
        for got, expected in after:
            assert [id(x) for x in got] == [id(x) for x in expected], "as the play ends"


GATHERING: dict[str, Callable[[m.Mobject, m.Mobject], Animation]] = {
    "Add": lambda a, b: m.Add(a, b),
    "CyclicReplace": lambda a, b: m.CyclicReplace(a, b),
    "FadeIn": lambda a, b: m.FadeIn(a, b),
    "FadeOut": lambda a, b: m.FadeOut(a, b),
    "ShowSubmobjectsOneByOne": lambda a, b: m.ShowSubmobjectsOneByOne([a, b]),
    "Swap": lambda a, b: m.Swap(a, b),
}


@pytest.mark.parametrize(
    "grouped", [False, True], ids=["new", "in a group in the scene"]
)
@pytest.mark.parametrize("name", sorted(GATHERING))
def test_an_animation_of_several_mobjects_acts_on_them_where_they_are(
    name: str, grouped: bool
) -> None:
    a, b = m.Square(), m.Circle()
    group, first, last = m.VGroup(a, b), m.Dot(m.UP), m.Dot(m.DOWN)
    animation = GATHERING[name](a, b)

    def construct(s: m.Scene) -> None:
        s.add(first, *([group] if grouped else []), last)
        s.play(animation)

    seen = instants(construct, lambda s: [id(x) for x in s.mobjects])
    playing = [first, group, last] if grouped else [first, last, a, b]
    end = max(seen)
    for t, members in seen.items():
        if 0 < t < end:
            assert members == [id(x) for x in playing], f"at {t} s"
    left = [first, last] if animation.is_remover() else playing
    assert seen[end] == [id(x) for x in left]


speedinfos = st.dictionaries(
    st.floats(0.05, 0.95), st.floats(0.2, 4), min_size=1, max_size=4
)


def nodes(speedinfo: dict[float, float]) -> list[tuple[float, float, float]]:
    """(progress, speed, the time it is reached), per second of the animation's run time: by
    the stretches' constant accelerations."""
    speeds = dict(sorted(({0.0: 1.0} | speedinfo).items()))
    speeds.setdefault(1.0, speeds[max(speeds)])
    out, time = [], 0.0
    for (a, v), (b, w) in pairwise([*speeds.items(), (2.0, 0.0)]):
        out.append((a, v, time))
        time += 2 * (b - a) / (v + w) if b <= 1 else 0.0
    return out


def test_a_speed_profile_composes_its_duration_exactly() -> None:
    change = m.ChangeSpeed(m.Wait(2), speedinfo={0.4: 1, 0.5: 0.2, 0.8: 0.2, 1: 1})
    assert change._duration == Fraction(24, 5)
    assert m.Succession(change, m.Wait(0.2))._duration == 5


class TestProfile:
    @given(at=st.floats(0.05, 0.95), speed=st.floats(0.2, 4))
    def test_splitting_a_constant_speed_profile_preserves_its_duration(
        self, at: float, speed: float
    ) -> None:
        part = m.Wait(0.3)
        whole = m.ChangeSpeed(part, speedinfo={0: speed, 1: speed})
        split = m.ChangeSpeed(part, speedinfo={0: speed, at: speed, 1: speed})
        assert split._duration == whole._duration

    @given(speedinfo=speedinfos)
    @example(speedinfo={0.5954991299724285: 2.0, 0.3026788225275667: 2.318359375})
    def test_it_reaches_each_point_when_the_stretches_before_it_have_played(
        self, speedinfo: dict[float, float]
    ) -> None:
        change = m.ChangeSpeed(
            m.Animation(m.Mobject(), run_time=2), speedinfo, rate_func=rf.linear
        )
        at = nodes(speedinfo)
        total = at[-1][2]
        assert change.run_time == pytest.approx(2 * total)
        for progress, _, time in at:
            assert change.progress(time / total) == pytest.approx(progress, abs=1e-9)

    @given(speedinfo=speedinfos, where=st.floats(0.01, 0.99))
    def test_its_pace_is_the_profiles_speed(
        self, speedinfo: dict[float, float], where: float
    ) -> None:
        change = m.ChangeSpeed(m.Animation(m.Mobject()), speedinfo, rate_func=rf.linear)
        at = nodes(speedinfo)
        total, h = at[-1][2], 1e-6
        time = where * total
        (_, v, t0), (_, w, t1) = next(
            (x, y) for x, y in pairwise(at) if x[2] <= time <= y[2]
        )
        expected = v + (w - v) * (time - t0) / (
            t1 - t0
        )  # steadily, in the scene's time
        measured = (
            change.progress((time + h) / total) - change.progress((time - h) / total)
        ) / (2 * h)
        assert measured == pytest.approx(expected, rel=1e-4)


@given(leaf=leaves(2), where=st.floats(0.05, 0.95))
def test_at_speed_one_it_is_the_animation(leaf: Leaf, where: float) -> None:
    def story(changed: bool) -> Recorder:
        def tell(s: Recorder) -> None:
            s.stage = [
                m.Square(color=m.BLUE, fill_opacity=0.5),
                m.Circle(0.6).shift(2 * m.RIGHT),
            ]
            s.add(*s.stage)
            anim = leaf.build(s.stage)
            s.play(m.ChangeSpeed(anim, {where: 1}) if changed else anim)

        return record(tell)

    assert_same_frames(story(True).frames, story(False).frames)


def walk(s: Recorder, dts: list[float] | None = None) -> m.Dot:
    """A dot on the speed clock, walking right at a unit a second (keeping its dts)."""
    dot = m.Dot(m.DOWN)
    s.add(dot)

    def step(mob: m.Mobject, dt: float) -> None:
        mob.shift(dt * m.RIGHT)
        if dts is not None:
            dts.append(dt)

    m.ChangeSpeed.add_updater(dot, step)
    return dot


class TestSpeedClock:
    def test_a_nested_change_warps_from_when_it_begins(self) -> None:
        def story(s: Recorder) -> None:
            s.stage = [m.Square(), walk(s)]
            s.play(
                m.Succession(
                    m.Wait(1),
                    m.ChangeSpeed(
                        s.stage[0].animate.shift(m.UP), speedinfo={0: 2, 1: 2}
                    ),
                )
            )

        walker = record(story).stage[1]
        assert walker.get_x() == pytest.approx(
            2
        )  # 1 s at speed 1, then 0.5 s at speed 2

    @given(
        first=speedinfos,
        second=speedinfos,
        lag=st.floats(0, 1),
        rate=st.sampled_from([rf.smooth, rf.there_and_back, rf.wiggle]),
    )
    @example(first={0.5: 1.0}, second={0.5: 1.0}, lag=0.0, rate=rf.there_and_back)
    def test_its_clock_never_runs_backward(
        self,
        first: dict[float, float],
        second: dict[float, float],
        lag: float,
        rate: rf.RateFunction,
    ) -> None:
        dts: list[float] = []

        def story(s: Recorder) -> None:
            a, b = m.Square(), m.Circle()
            s.stage = [a, b, walk(s, dts)]
            s.add(a, b)
            s.play(m.LaggedStart(
                m.ChangeSpeed(a.animate(rate_func=rate).shift(m.UP), first),
                m.ChangeSpeed(m.Indicate(b), second),
                lag_ratio=lag,
            ))  # fmt: skip

        scene = record(story)
        assert min(dts) >= -1e-12
        assert sum(dts) == pytest.approx(clock.speed.at(scene.time))
        assert scene.stage[2].get_x() == pytest.approx(sum(dts))
        if all(v == 1 for v in (*first.values(), *second.values())):
            assert sum(dts) == pytest.approx(scene.time)  # at speed 1, the scene's time

    def test_while_two_changes_overlap_the_one_begun_last_rules(self) -> None:
        ends: list[float] = []

        def story(s: Recorder) -> None:
            a, b = m.Square(), m.Circle()
            s.stage = [a, b, walk(s)]
            s.add(a, b)
            s.play(m.LaggedStart(
                m.ChangeSpeed(a.animate.shift(m.UP), {0: 2, 1: 2}),  # 0.5 s at speed 2
                m.ChangeSpeed(b.animate.shift(m.UP), {0: 0.5, 1: 0.5}),  # from 0.25 s: 2 s at 0.5
                lag_ratio=0.5,
            ))  # fmt: skip
            ends.extend((s.time, s.stage[2].get_x()))  # as the play ends

        record(story)
        assert ends[0] == pytest.approx(2.25)
        assert ends[1] == pytest.approx(0.25 * 2 + 2 * 0.5)

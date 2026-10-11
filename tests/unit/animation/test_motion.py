"""Motions show what they say, as functions of their progress.

- Showing is visibility: ShowIncreasingSubsets shows the first ⌊p·n⌋ parts at progress p and
  leaves the rest out of the picture, changing no part, so each shows as it is (translucent,
  graded or unfilled parts stay so) whatever else plays on it: a move or a recolor played with
  it happens, listed before it or after, and the reveal holds (each undid the other while the
  reveal wrote paint). Played, it leaves every part as it was, those it ends hiding
  transparent, and a remover's text as it was. Its group joins the scene when it begins: words
  typed one after another appear in turn (the later ones used to show until their turn).
  ShowSubmobjectsOneByOne shows one part at a time; TypeWithCursor shows its cursor as it is
  (it used to make it opaque, filling an outline), where it was put, and leaves it in the text
  if told to.
- A target that moves (its updaters, which the scene does not run) moves from when the
  transform begins.
- A Rotate turns about the mobject's center as its updaters carry it: it is `.animate.rotate`.
- PhaseFlow carries points along a field as the field's own flow does.
- A procedure copies its mobject for its updaters (a model) only if it has updaters it
  suspends; a starting keyframe it is given is a snapshot, which a subclass can interpolate
  from again and again; a reveal's parts are its group's when it was made.

(Made, every animation changes nothing, and it is a function of its progress, so the same at
every frame rate: laws of test_timeline's registry.)
"""

from collections.abc import Iterator
from fractions import Fraction

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from tests.scenes import Recorder, assert_same_frames, record

import manimgx as m
from manimgx.animation import clock
from manimgx.animation import easing as rf


def parts() -> m.VGroup:
    """Four squares in their own paints: plain, translucent, graded, and stroked only."""
    group = m.VGroup(*(m.Square(0.5).shift(i * m.RIGHT) for i in range(4)))
    group[0].set_fill(m.BLUE, 1)
    group[1].set_fill(m.RED, 0.3)
    group[2].set_fill([m.GREEN, m.YELLOW], 0.8)
    group[3].set_stroke(m.TEAL, 6).set_fill(opacity=0)
    return group


def paints(group: m.Mobject) -> list[tuple[bytes, ...]]:
    return [
        tuple(getattr(p.paint, b).tobytes() for b in ("fill", "stroke")) for p in group
    ]


def shown(group: m.Mobject) -> list[bool]:
    return [bool(p.paint.fill[:, 3].any() or p.paint.stroke[:, 3].any()) for p in group]


def drawn(scene: Recorder) -> list[int]:
    """How many leaves each frame draws."""
    return [len(scene.frames[k]) for k in sorted(scene.frames)]


class TestShowIncreasingSubsets:
    @given(alpha=st.floats(0, 1))
    def test_at_a_progress_it_hides_the_parts_after_the_first_and_changes_none(
        self, alpha: float
    ) -> None:
        group = parts()
        own = paints(group)
        anim = m.ShowIncreasingSubsets(group, rate_func=rf.linear)
        anim.begin()
        anim.interpolate(alpha)
        assert anim.hidden == group.submobjects[int(np.floor(alpha * 4)) :]
        assert paints(group) == own

    def test_played_it_leaves_every_part_in_its_own_paint(self) -> None:
        def tell(s: Recorder) -> None:
            s.stage = [parts()]
            s.play(m.ShowIncreasingSubsets(s.stage[0]))

        group = parts()
        assert paints(record(tell).stage[0]) == paints(group)

    @pytest.mark.parametrize("before", [False, True])
    @pytest.mark.parametrize("change", ["move", "recolor"])
    def test_it_holds_whatever_else_plays_on_its_parts(
        self, change: str, before: bool
    ) -> None:
        def tell(s: Recorder, together: bool = True) -> None:
            s.stage = [parts()]
            reveal = m.ShowIncreasingSubsets(s.stage[0], rate_func=rf.linear)
            if not together:
                s.play(reveal)
                return
            other = (
                s.stage[0].animate.shift(m.UP)
                if change == "move"
                else s.stage[0].animate.set_color(m.RED)
            )
            s.play(*((other, reveal) if before else (reveal, other)))

        played = record(tell, fast=False)
        assert drawn(played) == drawn(record(lambda s: tell(s, False), fast=False))
        expected = parts().shift(m.UP) if change == "move" else parts().set_color(m.RED)
        np.testing.assert_allclose(played.stage[0].points, expected.points)
        assert paints(played.stage[0]) == paints(expected)

    def test_its_group_shows_nothing_before_it_begins(self) -> None:
        def tell(s: Recorder) -> None:
            s.stage = [parts()]
            s.play(m.Succession(m.Wait(0.5), m.ShowIncreasingSubsets(s.stage[0])))

        assert drawn(record(tell, fast=False))[:6] == [0] * 6

    def test_words_are_typed_one_after_another(self) -> None:
        def tell(s: Recorder) -> None:
            s.stage = [m.VGroup(parts(), parts().shift(m.DOWN))]
            s.play(m.AddTextWordByWord(s.stage[0], time_per_char=0.2))

        count = drawn(record(tell, fast=False))
        assert count == sorted(count)  # no word before its turn, nor taken back
        assert (count[0], count[-1]) == (0, 8)

    @given(alpha=st.floats(0, 1))
    def test_one_by_one_shows_one_part_at_a_time(self, alpha: float) -> None:
        group = parts()
        anim = m.ShowSubmobjectsOneByOne(group, rate_func=rf.linear)
        anim.begin()
        anim.interpolate(alpha)
        assert len(anim.hidden) >= len(group) - 1

    def test_played_one_by_one_leaves_the_parts_it_hides_transparent(self) -> None:
        def tell(s: Recorder) -> None:
            s.stage = [parts()]
            s.add(*s.stage)
            s.play(m.ShowSubmobjectsOneByOne(s.stage[0]))
            s.wait(0.2)

        played = record(tell, fast=False)
        assert drawn(played)[-1] == 1
        assert shown(played.stage[0]) == [False, False, False, True]
        assert paints(played.stage[0])[3] == paints(parts())[3]

    def test_a_text_removed_letter_by_letter_is_as_it_was(self) -> None:
        def tell(s: Recorder) -> None:
            s.stage = [parts()]
            s.add(*s.stage)
            s.play(m.RemoveTextLetterByLetter(s.stage[0]))
            s.play(m.AddTextLetterByLetter(s.stage[0]))

        played = record(tell, fast=False)
        assert paints(played.stage[0]) == paints(parts())
        assert drawn(played)[-1] == 4

    @pytest.mark.parametrize("fill", [0.0, 0.4])
    def test_the_cursor_shows_as_it_is(self, fill: float) -> None:
        cursor = m.Rectangle(m.YELLOW, height=0.6, width=0.1, fill_opacity=fill)

        def tell(s: Recorder) -> None:
            s.stage = [parts()]
            s.play(m.TypeWithCursor(s.stage[0], cursor))

        record(tell, fast=False)
        assert cursor.get_fill_opacity() == pytest.approx(fill)
        assert cursor.get_stroke_opacity() == 1


def test_a_moving_target_moves_from_when_the_transform_begins() -> None:
    def tell(s: Recorder) -> None:
        square, target = m.Square(), m.Circle().shift(2 * m.LEFT)
        target.add_updater(lambda mob, dt: mob.shift(dt * m.RIGHT))  # not in the scene
        s.stage = [square, target]
        s.add(square)
        s.wait(2)
        s.play(m.Transform(square, target, rate_func=rf.linear))

    square, target = record(tell).stage
    assert target.get_x() == pytest.approx(-1)  # a second of its time: the transform's
    assert square.get_x() == pytest.approx(-1)


@settings(max_examples=30)  # two films an example: the area's slowest test at 100
@given(
    angle=st.floats(-4, 4),
    rate=st.sampled_from([rf.linear, rf.smooth, rf.there_and_back]),
)
def test_a_rotate_of_a_drifting_mobject_is_its_animate_rotate(
    angle: float, rate: rf.RateFunction
) -> None:
    def told(by_rotate: bool) -> Recorder:
        def tell(s: Recorder) -> None:
            square = m.Square()
            square.add_updater(lambda mob, dt: mob.shift(dt * m.RIGHT))
            s.stage = [square]
            s.add(square)
            if by_rotate:
                s.play(m.Rotate(square, angle, rate_func=rate, run_time=2))
            else:
                s.play(square.animate(rate_func=rate, run_time=2).rotate(angle))

        return record(tell)

    assert_same_frames(told(True).frames, told(False).frames)


FLOWS = {  # a field, and its exact flow: where a point is after a time
    "turn": (
        lambda p: np.array([-p[1], p[0], 0.0]),
        lambda p, t: m.rotation_matrix(t, m.OUT) @ p,
    ),
    "growth": (lambda p: 0.5 * p, lambda p, t: p * np.exp(0.5 * t)),
}


@pytest.mark.parametrize("flow", FLOWS, ids=str)
@pytest.mark.parametrize("fps", [10, 60])
def test_a_phase_flow_is_its_fields_flow(flow: str, fps: int) -> None:
    field, exact = FLOWS[flow]
    start = np.array([1.0, 0.5, 0.0])

    def tell(s: Recorder) -> None:
        s.stage = [m.Dot(start)]
        s.add(*s.stage)
        s.play(m.PhaseFlow(field, s.stage[0], virtual_time=2 * np.pi, run_time=1))

    np.testing.assert_allclose(
        record(tell, fps).stage[0].get_center(), exact(start, 2 * np.pi), atol=1e-4
    )


_PROCEDURAL_FAMILIES = (
    "UpdateFromFunc",
    "UpdateFromAlphaFunc",
    "MaintainPositionRelativeTo",
    "PhaseFlow",
    "ChangingDecimal",
    "ShowIncreasingSubsets",
)


def _procedural_animation(name: str, suspend: bool = False) -> m.Animation:
    mob: m.Mobject = (
        m.DecimalNumber(2.5)
        if name == "ChangingDecimal"
        else m.Group(m.Square(), m.Group(m.Circle(), m.Dot(m.RIGHT)))
    )
    if name == "UpdateFromFunc":
        return m.UpdateFromFunc(
            mob, lambda obj: obj.set_color(m.RED), suspend_mobject_updating=suspend
        )
    if name == "UpdateFromAlphaFunc":
        return m.UpdateFromAlphaFunc(
            mob, lambda obj, alpha: obj.set_x(alpha), suspend_mobject_updating=suspend
        )
    if name == "MaintainPositionRelativeTo":
        return m.MaintainPositionRelativeTo(
            mob, m.Dot(3 * m.RIGHT), suspend_mobject_updating=suspend
        )
    if name == "PhaseFlow":
        return m.PhaseFlow(
            lambda p: np.array([-p[1], p[0], 0.0]),
            mob,
            suspend_mobject_updating=suspend,
        )
    if name == "ChangingDecimal":
        assert isinstance(mob, m.DecimalNumber)
        return m.ChangingDecimal(
            mob, lambda alpha: 2.5 + alpha, suspend_mobject_updating=suspend
        )
    assert name == "ShowIncreasingSubsets"
    return m.ShowIncreasingSubsets(mob, suspend_mobject_updating=suspend)


class TestProceduralKeyframes:
    """Procedures keep requested keyframes and necessary updater models only."""

    @pytest.fixture(autouse=True)
    def _reset_clock(self) -> Iterator[None]:
        clock.reset()
        yield
        clock.reset()

    @pytest.mark.parametrize("name", _PROCEDURAL_FAMILIES)
    @pytest.mark.parametrize("suspend", [False, True])
    @pytest.mark.parametrize("updating", [False, True])
    def test_procedure_copies_only_a_needed_updater_model(
        self, name: str, suspend: bool, updating: bool, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        animation = _procedural_animation(name, suspend)
        obj = animation.mobject
        if updating:
            obj.add_updater(lambda mob, dt: mob.shift(dt * m.RIGHT))
        originals = {id(member) for member in obj.get_family()}
        copied: list[int] = []
        deepcopy = m.Mobject.__deepcopy__

        def counted(mob: m.Mobject, memo: dict[int, object]) -> m.Mobject:
            copied.append(id(mob))
            return deepcopy(mob, memo)

        monkeypatch.setattr(m.Mobject, "__deepcopy__", counted)
        animation.begin()
        if suspend and updating:
            assert sorted(
                identity for identity in copied if identity in originals
            ) == sorted(originals)
            assert len(copied) == len(set(copied))
        else:
            assert not copied
        model = animation.model
        assert (model is not None) == (suspend and updating)
        if model is not None:
            assert model is not obj
            assert all(
                (
                    a is not b
                    for a, b in zip(obj.get_family(), model.get_family(), strict=True)
                )
            )
            copied.clear()
            animation.advance(Fraction(1, 4))
            assert not copied
            assert obj.get_x() == pytest.approx(model.get_x())

    @pytest.mark.parametrize("name", _PROCEDURAL_FAMILIES)
    def test_explicit_starting_keyframe_still_takes_an_independent_snapshot(
        self, name: str
    ) -> None:
        animation = _procedural_animation(name)
        obj = animation.mobject
        animation.keys = (None,)
        animation.begin()
        assert len(animation.frames) == 1
        before = animation.frames[0]
        assert before is not obj
        center = before.get_center().copy()
        obj.shift(3 * m.RIGHT)
        np.testing.assert_array_equal(before.get_center(), center)

    def test_subclass_can_use_its_declared_keyframe_for_repeated_interpolation(
        self,
    ) -> None:

        class FromStart(m.UpdateFromAlphaFunc):
            keys = (None,)

            def interpolate_mobject(self, alpha: float) -> None:
                self.mobject.become(self.frames[0]).shift(alpha * m.RIGHT)

        obj = m.Square()
        animation = FromStart(obj, lambda mob, alpha: None)
        animation.begin()
        animation.interpolate(0.8)
        animation.interpolate(0.2)
        assert obj.get_x() == pytest.approx(0.2)

    def test_reveal_keeps_its_constructor_members_and_changes_no_paint(self) -> None:
        shared = m.Dot(color=m.YELLOW, fill_opacity=0.4)
        first = m.Group(m.Square(), shared)
        last = m.Group(shared, m.Circle(color=m.BLUE))
        group = m.Group(first, last)
        animation = m.ShowIncreasingSubsets(group, rate_func=m.linear)
        group.remove(first)
        newcomer = m.Dot(2 * m.UP, color=m.PURPLE)
        group.add(newcomer)
        shared.set_fill(m.GREEN, opacity=0.3)
        paint = shared.paint
        animation.begin()
        animation.interpolate(0.5)
        assert animation.hidden == [last]  # with the dot it shares with the first
        assert shared.paint is paint
        animation.finish()
        assert not animation.hidden
        assert shared.paint is paint
        assert group.submobjects == [last, newcomer]

    @pytest.mark.parametrize("leave", [False, True])
    def test_cursor_keeps_its_placement_and_final_membership(self, leave: bool) -> None:
        text = m.Text("type")
        cursor = m.Rectangle(width=0.1, height=0.6).set_y(0.75)
        animation = m.TypeWithCursor(
            text, cursor, keep_cursor_y=True, leave_cursor_on=leave
        )
        animation.begin()
        assert cursor in text.submobjects
        animation.interpolate(0.5)
        assert cursor.get_y() == pytest.approx(0.75)
        animation.finish()
        assert (cursor in text.submobjects) == leave

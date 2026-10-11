"""Animation time: lifecycle, exact composition windows, and speed profiles.

The scalar lifecycle phases and vector schedules use the same group layout.
Scene chooses the instants; an animation tree evaluates what acts at each instant."""

from __future__ import annotations

import weakref
from collections.abc import Callable, Iterable, Iterator, Sequence
from fractions import Fraction
from itertools import pairwise
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Literal,
    NamedTuple,
    Self,
    TypeIs,
    Unpack,
)
from warnings import deprecated

import numpy as np
from typing_extensions import TypedDict

from manimgx.animation import clock
from manimgx.animation.easing import linear, smooth
from manimgx.caches import Memo
from manimgx.drawing.geometry import integer_interpolate
from manimgx.mobject import (
    Group,
    Mobject,
    _per_frame,
    flow,
    remove_list_redundancies,
    simulated,
)
from manimgx.typing import RateFunc

if TYPE_CHECKING:
    from manimgx.scene import Scene

if TYPE_CHECKING:
    from manimgx.mobject import VGroup

if TYPE_CHECKING:
    from manimgx.mobject import Updater

__all__ = [
    "Add",
    "Animation",
    "AnimationGroup",
    "ChangeSpeed",
    "LaggedStart",
    "LaggedStartMap",
    "Succession",
    "Wait",
]


class _Untimed(TypedDict, total=False):
    """Untimed's keys, open, for the keywords that add to them."""

    lag_ratio: float
    """How the parts of the mobject are staggered: each begins this fraction of its run
    after the one before it begins (default 0: all together; 1: one after another)."""
    rate_func: RateFunc
    """How the animation's progress runs with time: a function from [0, 1] to [0, 1]
    (default [`smooth`][manimgx.smooth]; see
    [rate functions][manimgx.animation.easing])."""
    reverse_rate_function: bool
    """Whether to run the animation backward (default False)."""
    name: str | None
    """A name for the animation."""
    remover: bool
    """Whether the mobject leaves the scene when the animation finishes
    (default False)."""
    suspend_mobject_updating: bool
    """Whether the mobject's updaters run beneath the animation (default True): they
    keep acting on the mobject, and each frame shows the animation applied to the result.
    If False, they act on the animated mobject itself."""
    introducer: bool
    """Whether the mobject joins the scene when the animation begins (default False);
    otherwise the play brings it in when the play begins, if the scene lacks it."""
    use_override: bool
    """Whether a mobject whose class plays another animation in place of this one
    does so (default True)."""


class Untimed(_Untimed, total=False, closed=True):
    """Every animation option but `run_time`, which [`Wait`][manimgx.Wait] takes by
    position."""


class _AnimationOptions(_Untimed, total=False):
    """AnimationOptions's keys, open, for the keywords that add to them."""

    run_time: float
    """How long the animation plays, in seconds (default 1)."""


class AnimationOptions(_AnimationOptions, total=False, closed=True):
    """The options every animation takes, by keyword.

    Each animation class sets its own defaults for them: [`Create`][manimgx.Create], for
    instance, draws the parts of a mobject one after another (`lag_ratio=1`).
    """


_CASCADES: Memo[type, AnimationOptions] = Memo(1 << 12)


def animation_defaults(cls: type[Animation]) -> AnimationOptions:
    """The options an animation class sets by default.

    Each class in its hierarchy adds only what it changes (its `defaults`), the most
    derived last.

    Args:
        cls: The animation class.

    Returns:
        Its default options.
    """
    cached = _CASCADES.get(cls)
    if cached is None:
        cached = AnimationOptions()
        for klass in reversed(cls.__mro__):
            if issubclass(klass, Animation) and "defaults" in vars(klass):
                cached = cached | klass.defaults
        _CASCADES.keep(cls, cached)
    return cached


type Key = "Mobject | Callable[[Mobject], Mobject] | None"


"""A keyframe as an animation declares it: its object as it begins (None), a function of a copy of
that, or an object of its own (copied when the animation begins)."""


def keyframe_at(steps: int, alpha: float) -> tuple[int, float]:
    """Where an eased progress falls among `steps` keyframe intervals: the interval, and
    how far along it. Past the ends (a rate function that overshoots, or backs up), the
    end intervals run on: the fraction is below 0 or above 1."""
    if alpha < 0:
        return 0, alpha * steps
    if alpha > 1:
        return steps - 1, 1 + (alpha - 1) * steps
    return integer_interpolate(0, steps, alpha)


class Animation[M: Mobject = Mobject]:
    """A change of mobjects over a stretch of scene time.

    An animation plays for `run_time` seconds of the scene's time. Its progress,
    `alpha`, goes from 0 at its start to 1 at its end, eased by its rate function (by
    default [`smooth`][manimgx.smooth]: slow, fast, slow). The parts of its mobject (the
    members of its family that have points) can be staggered: with a `lag_ratio`, each
    part begins that fraction of its run after the part before it, so 0 moves them all
    together and 1 one after another.

    [`Scene.play`][manimgx.Scene.play] plays it. An animation that brings its mobject in
    adds it to the scene as it starts, and one that takes its mobject out removes it as
    it ends. The mobject's own updaters keep running while it plays: each frame shows
    the animation applied to the mobject as its updaters have it then, and when the
    animation ends, the mobject is as its last frame showed it.

    To make an animation of your own, make a class from it, and override
    [`interpolate_mobject`][manimgx.Animation.interpolate_mobject]: it sets the whole
    mobject at the animation's progress, from 0 to 1, as it is before the rate function
    eases it, so apply `self.rate_func(alpha)` yourself. The options are attributes of
    the same names (`self.rate_func`, `self.lag_ratio`, …). An `Animation` itself
    changes nothing: it holds its mobject in the scene for its run time.

    Args:
        mobject: The mobject to animate; None for none, as a [`Wait`][manimgx.Wait] has.
        **options: [Animation options][manimgx.animation.timeline.AnimationOptions].

    Examples:
        ```python
        import manimgx as m


        class DropIn(m.Animation):
            def interpolate_submobject(
                self, submobject: m.Mobject, start: m.Mobject, alpha: float
            ) -> None:
                submobject.points = start.points
                submobject.shift((1 - alpha) * 2 * m.UP).set_opacity(alpha)


        class AnimationExample(m.Scene):
            def construct(self) -> None:
                word = m.Text("manimgx", font_size=144)
                self.play(DropIn(word, lag_ratio=0.3, run_time=2))
        ```
    """

    _call: tuple[tuple[object, ...], dict[str, object]]
    defaults: ClassVar[AnimationOptions] = {}
    """The options this class sets by default, only those it changes from its base
    classes' (they cascade down the class hierarchy)."""
    keys: Sequence[Key] = (None,)  # the base part-by-part hook's starting state
    _held: Sequence[Mobject] = ()  # the members whose updating it suspended (`take`)

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        """Construction makes the class it names (so it type-checks like any call), keeping the
        arguments for a mobject that plays something else (`override_animation`)."""
        animation = super().__new__(cls)
        animation._call = args, kwargs
        return animation

    def __init__(
        self,
        mobject: M | None,
        **options: Unpack[AnimationOptions],
    ) -> None:
        o = animation_defaults(type(self)) | options
        self.run_time = o.get("run_time", 1.0)
        self.rate_func = o.get("rate_func", smooth)
        self.reverse_rate_function = o.get("reverse_rate_function", False)
        self.name = o.get("name")
        self.remover = o.get("remover", False)
        self.introducer = o.get("introducer", False)
        self.suspend_mobject_updating = o.get("suspend_mobject_updating", True)
        self.lag_ratio = o.get("lag_ratio", 0.0)
        self.use_override = o.get("use_override", True)
        self.frames: list[Mobject] = []  # the keyframes, as derived (`derive`)
        self._model: M | None = None
        self._scene: Scene | None = None  # the scene it plays in (`_setup_scene`)
        self._mobject: M = (
            mobject if mobject is not None else Mobject()  # pyright: ignore[reportAttributeAccessIssue]  # ty: ignore[invalid-assignment]  # none: an Animation[Mobject]
        )

    # read-only, so an animation of a Circle is an animation of a Mobject (M is covariant)
    @property
    def mobject(self) -> M:
        """The mobject the animation changes."""
        return self._mobject

    @property
    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def model(self) -> M | None:
        """The mobject as its updaters have it while the animation plays.

        A copy they run on, taken when the animation begins; None if the mobject has no
        updaters, or they act on it directly (`suspend_mobject_updating` False).
        """
        return self._model

    @property
    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def hidden(self) -> Sequence[Mobject]:
        """The parts of its mobject the animation leaves out of the picture now.

        While the animation plays, the scene draws what it holds but these, with their
        families; the parts themselves are not changed, so whatever else acts on them
        shows once they are drawn again. Most animations hide nothing;
        [`ShowIncreasingSubsets`][manimgx.ShowIncreasingSubsets] hides the parts it has
        not shown yet.
        """
        return ()

    @property
    def run_time(self) -> float:
        """How long the animation plays, in seconds; never negative."""
        return self._run_time

    @run_time.setter
    def run_time(self, value: float) -> None:
        if value < 0:
            raise ValueError(
                f"The run_time of {type(self).__name__} cannot be negative. The given"
                f" value was {value}."
            )
        self._run_time = value

    @property
    def _duration(self) -> Fraction:
        """The scene's duration; compositions retain their computed rational exactly."""
        return clock.rational(self.run_time)

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def build(self) -> Animation:
        """Return what plays for this animation: itself, unless it stands for another.

        An [`.animate`][manimgx.Mobject.animate] call of a method that a mobject
        overrides with [`override_animate`][manimgx.override_animate] stands for the
        animation that method returns. [`Scene.play`][manimgx.Scene.play] calls it
        before playing.

        Returns:
            The animation to play.
        """
        return self

    # ── lifecycle ─────────────────────────────────────────────────────────
    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def begin(self) -> None:
        """Start the animation: derive its keyframes from the mobject as it is now, and
        take the mobject, changing nothing.

        [`Scene.play`][manimgx.Scene.play] calls it when the animation starts; a part of
        a composition, when its window opens. The animation acts only when interpolated,
        as a function of its progress: a part may begin between two frames, and its
        first frame then shows it past progress 0, so set nothing up at progress 0.
        Override it to set up an animation of your own, and call the base's.
        """
        # an animation is a function of α: one that set itself up at α = 0
        # (`if alpha == 0:`) would depend on where a play's frames fall
        self.derive(self.mobject)
        self.take()

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def take(self) -> None:
        """Take the mobject as it is now, changing nothing.

        If the mobject has updaters, the animation takes a copy for them to run on (its
        model), and the mobject's own updating is suspended while the animation plays
        (unless `suspend_mobject_updating` is False). So animations that begin together
        all begin from the world as it was before any of them acted. `begin` calls it.
        """
        if _updating(
            self.mobject
        ):  # as it is now: its time-based updaters brought here
            framing, clock.framing = clock.framing, False  # (its per-frame ones ran)
            self.mobject.advance(clock.now)
            clock.framing = framing
        if self.suspend_mobject_updating and _updating(self.mobject):
            self._model = self.mobject.copy()
        if self.suspend_mobject_updating:
            # what it suspends it resumes when it finishes: not what was suspended already
            self._held = [
                m for m in self.mobject.get_family() if not m.updating_suspended
            ]
            self.mobject.suspend_updating()

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def derive(self, source: Mobject) -> None:
        """Derive the animation's keyframes from `source` as it is now, and align the
        mobject with every one of them.

        `begin` calls it on the mobject, and `rederive` on its model.

        Args:
            source: The mobject, or its model.
        """
        own = [
            (
                None
                if key is None
                else key.copy()
                if isinstance(key, Mobject)
                else key(source.copy())
            )
            for key in self.keys
        ]
        for frame in own:
            if frame is not None:
                self.mobject.align_data(frame)
        self.frames = [source.copy() if frame is None else frame for frame in own]

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def finish(self) -> None:
        """End the animation: show progress 1, and resume the updaters it suspended
        (those suspended before it began stay so).

        [`Scene.play`][manimgx.Scene.play] calls it at the animation's end; a part of a
        composition, when its window closes.
        """
        self.interpolate(1)
        self._release()

    def _release(self) -> None:
        """Resume the updating it suspended when it began."""
        if self.suspend_mobject_updating:
            for member in self._held:
                member.resume_updating(recursive=False)

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def clean_up_from_scene(self, scene: Scene) -> None:
        """Leave the scene as the animation leaves it: a remover takes its mobject out.

        [`Scene.play`][manimgx.Scene.play] calls it after `finish`; a part of a
        composition, when its window closes.

        Args:
            scene: The scene the animation played in.
        """
        if self.is_remover():
            scene.remove(*_held(self.mobject))

    def _setup_scene(self, scene: Scene) -> None:
        self._scene = scene
        if self.is_introducer():
            scene._introduce(_held(self.mobject))

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def get_all_families_zipped(self) -> Iterable[tuple[Mobject, ...]]:
        """Return the parts of the animation's mobjects, matched up.

        Returns:
            For each part with points of the mobject, a tuple of it and the same part of
            each of the animation's keyframes.
        """
        families = [
            m.family_members_with_points() for m in (self.mobject, *self.frames)
        ]
        if any(len(f) != len(families[0]) for f in families[1:]):
            # another tween that began with this one restructured the mobject (aligning it
            # with its own keyframes): these follow, as alignment only adds parts
            for frame in self.frames:
                self.mobject.align_data(frame)
            families = [
                m.family_members_with_points() for m in (self.mobject, *self.frames)
            ]
        return zip(*families, strict=True)

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def advance(self, t: Fraction) -> None:
        """Bring the mobject's updaters to scene time `t`, on its model.

        Then it derives what the animation shows from the model again (`rederive`). The
        scene calls it at every instant it computes while the animation plays, before
        `interpolate`. At the end of the play, before `finish`, time alone brings the
        model there: the per-frame updaters then run once, on the mobject itself.

        Args:
            t: The scene time, in seconds, as an exact fraction.
        """
        if self.model is not None:
            self.model.advance(t)
            self.rederive()

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def rederive(self) -> None:
        """Derive the animation's keyframes again, from the mobject's model as it is now.

        The mobject then shows the model, and the animation acts on it: an animation acts
        on the mobject as its updaters have it at that frame. `advance` calls it.
        """
        model = self.model
        if model is None:
            return
        self.derive(model)
        self.mobject.become(model)

    # ── the per-frame function ────────────────────────────────────────────
    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def interpolate(self, alpha: float) -> None:
        """Show the animation at a progress.

        [`Scene.play`][manimgx.Scene.play] calls it at every frame; it hands the work to
        `interpolate_mobject`.

        Args:
            alpha: The animation's progress, from 0 at its start to 1 at its end, not
                yet eased by the rate function.
        """
        self.interpolate_mobject(alpha)

    def interpolate_mobject(self, alpha: float) -> None:
        """Set the whole mobject at a progress of the animation.

        By default, it sets each part at its own progress (`get_sub_alpha`: staggered by
        `lag_ratio`, eased by the rate function) through `interpolate_keyframes`.
        Override it to set the whole mobject at once, and apply `self.rate_func(alpha)`
        yourself.

        Args:
            alpha: The animation's progress, from 0 to 1, not yet eased.
        """
        families = list(self.get_all_families_zipped())
        for i, (submobject, *keys) in enumerate(families):
            self.interpolate_keyframes(
                submobject, keys, self.get_sub_alpha(alpha, i, len(families))
            )

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def interpolate_keyframes(
        self, submobject: Mobject, keys: Sequence[Mobject], alpha: float
    ) -> None:
        """Set one part of the mobject at its progress through its keyframes.

        The keyframes are the states of the part the animation passes through, in order.
        By default the only one is the part's starting state, and this calls
        `interpolate_submobject`.

        Args:
            submobject: The part of the mobject to set.
            keys: The same part of each keyframe.
            alpha: The part's progress, staggered and eased.
        """
        # with one keyframe (a start state) this is CE's `interpolate_submobject`, the
        # hook custom animations override
        self.interpolate_submobject(submobject, keys[0], alpha)

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def interpolate_submobject(
        self, submobject: Mobject, starting_submobject: Mobject, alpha: float
    ) -> None:
        """Set one part of the mobject at its own progress; the base does nothing.

        The hook to override for an animation that acts part by part:
        `interpolate_mobject` calls it for each part with points, at every frame.

        Args:
            submobject: The part of the mobject to set.
            starting_submobject: The same part as it was when the animation began.
            alpha: The part's progress, from 0 to 1: staggered by `lag_ratio` and eased
                by the rate function.
        """

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def get_sub_alpha(self, alpha: float, index: int, num_submobjects: int) -> float:
        """Return a part's progress at a progress of the animation.

        The parts are staggered by `lag_ratio`: each has a window of the animation's
        progress, the first opening at 0 and the last closing at 1, and runs through it
        (held at 0 before it, at 1 after it), eased by the rate function (run backward
        with `reverse_rate_function`). A part's window closes exactly: its progress there
        is 1, and a finished animation is exactly its end.

        Args:
            alpha: The animation's progress, from 0 to 1.
            index: The part's position among the parts, from 0.
            num_submobjects: How many parts there are.

        Returns:
            The part's progress, eased.
        """
        lag = self.lag_ratio
        opens = index * lag
        span = (num_submobjects - 1) * lag + 1  # the stagger's length, in part runs
        # the window [opens, opens + 1] of `span`, as fractions: the last one's end is
        # span / span, exactly 1
        start, end = opens / span, (opens + 1) / span
        value = min(max((alpha - start) / (end - start), 0.0), 1.0)
        return (
            self.rate_func(1 - value)
            if self.reverse_rate_function
            else self.rate_func(value)
        )

    # ── CE accessors ──────────────────────────────────────────────────────
    @deprecated("get_run_time() is run_time: use it", category=None)
    def get_run_time(self) -> float:
        """How long the animation plays.

        Returns:
            Its run time, in seconds.
        """
        return self.run_time

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def is_remover(self) -> bool:
        """Whether the mobject leaves the scene when the animation finishes."""
        return self.remover

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def is_introducer(self) -> bool:
        """Whether the mobject joins the scene when the animation begins."""
        return self.introducer


def _lacks(mob: Mobject, members: list[Mobject]) -> bool:
    """Do a scene's members lack a mobject with anything to draw or to run?"""
    return mob not in members and any(
        m.has_points() or m.updaters for m in mob.get_family()
    )


_GATHERED: weakref.WeakSet[Mobject] = weakref.WeakSet()


def _gathered(*mobjects: Mobject) -> Group:
    """A group an animation makes of the mobjects it is given, to act on them as one: no
    scene holds it (`_held`)."""
    group = Group(*mobjects)
    _GATHERED.add(group)
    return group


def _held(mob: Mobject) -> list[Mobject]:
    """What a scene holds of a mobject an animation acts on: the mobject, or the members
    of a group the animation gathered them in, each where it is or by itself."""
    return list(mob.submobjects) if mob in _GATHERED else [mob]


def _updating(mob: Mobject) -> bool:
    return any(m.updaters for m in mob.get_family())


def _flatten(items: Iterable[object]) -> list[object]:
    """Flatten nested iterables of animations into one list: a mobject, an animation or
    a string is one item, not an iterable to flatten.

    Args:
        items: The items, nested in lists, tuples or other iterables.

    Returns:
        The items, in order.
    """
    out: list[object] = []
    for item in items:
        if (
            isinstance(item, Iterable)
            and not isinstance(item, str)
            and not hasattr(item, "begin")
            and not hasattr(item, "points")
        ):
            out.extend(_flatten(item))
        else:
            out.append(item)
    return out


def prepare(anim: object) -> Animation:
    """Return what plays for an animation: as built, or what its mobject plays instead.

    The animation is built first (`build`); a mobject may play another animation in its
    place (see `override_animation`).

    Args:
        anim: The animation; anything else raises a TypeError.

    Returns:
        The animation to play.
    """
    if not isinstance(anim, Animation):
        raise TypeError(f"Object {anim} cannot be converted to an animation")
    anim = anim.build()
    override = (
        anim.mobject.animation_override_for(type(anim)) if anim.use_override else None
    )
    if override is None:
        return anim
    args, kwargs = anim._call
    extra = {k: v for k, v in kwargs.items() if k not in ("mobject", "use_override")}
    return prepare(override(anim.mobject, *args[1:], **extra))


class Wait(Animation[Mobject]):
    """Let the scene's time run on, animating nothing.

    The scene's updaters and its mobjects' keep running through it;
    [`Scene.wait`][manimgx.Scene.wait] plays one. Played alone, it can end early, at
    `stop_condition`, or freeze the frame; in a composition, it only takes up its time.

    Args:
        run_time: How long it lasts, in seconds.
        stop_condition: A function checked at every frame: the wait ends at the first
            frame at which it returns True. None: it lasts its whole run time.
        frozen_frame: Whether time stands still: one frame is held, and the updaters do
            not run, then go on as if no time had passed. It cannot be combined with a
            `stop_condition` (a ValueError).
        **kwargs: The other [animation options][manimgx.animation.timeline.AnimationOptions]
            (all but `run_time`).

    Examples:
        ```python
        import manimgx as m


        class WaitExample(m.Scene):
            def construct(self) -> None:
                finish = m.Line(3 * m.UP, 3 * m.DOWN, color=m.RED).shift(3 * m.RIGHT)
                dot = m.Dot(4 * m.LEFT, radius=0.3, color=m.YELLOW)
                dot.add_updater(lambda mob, dt: mob.shift(3 * dt * m.RIGHT))
                self.add(finish, dot)
                self.play(m.Wait(10, stop_condition=lambda: dot.get_x() >= 3))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": linear}

    def __init__(
        self,
        run_time: float = 1,
        stop_condition: Callable[[], bool] | None = None,
        frozen_frame: bool | None = None,
        **kwargs: Unpack[Untimed],
    ) -> None:
        if stop_condition and frozen_frame:
            raise ValueError("A static Wait animation cannot have a stop condition.")
        self.duration = run_time
        self.stop_condition = stop_condition
        self.is_static_wait = frozen_frame
        super().__init__(None, run_time=run_time, **kwargs)

    def begin(self) -> None: ...
    def finish(self) -> None: ...
    def clean_up_from_scene(self, scene: Scene) -> None: ...
    def advance(self, t: Fraction) -> None: ...
    def interpolate(self, alpha: float) -> None: ...


class Add(Animation[Mobject]):
    """Add mobjects to the scene at a moment of a composition.

    It adds its mobjects when it begins and, by default, takes no time: in a
    [`Succession`][manimgx.Succession], they appear when the animations before it have
    finished. With a `run_time`, it holds that long after adding them.

    Args:
        *mobjects: The mobjects to add; several are added as one group.

    Examples:
        ```python
        import manimgx as m


        class AddExample(m.Scene):
            def construct(self) -> None:
                words = m.VGroup(
                    *(m.Text(word, font_size=96) for word in ("one", "two", "three"))
                ).arrange(m.DOWN, buff=0.5)
                box = m.SurroundingRectangle(words, buff=0.5, color=m.BLUE)
                self.play(
                    m.Create(box, run_time=3),
                    m.Succession(*(m.Add(word, run_time=1) for word in words)),
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 0.0, "introducer": True}

    def __init__(self, *mobjects: Mobject, **kwargs: Unpack[AnimationOptions]) -> None:
        super().__init__(
            mobjects[0] if len(mobjects) == 1 else _gathered(*mobjects), **kwargs
        )

    def begin(self) -> None: ...
    def finish(self) -> None: ...
    def clean_up_from_scene(self, scene: Scene) -> None: ...
    def advance(self, t: Fraction) -> None: ...
    def interpolate(self, alpha: float) -> None: ...


prepare_animation = prepare


"""The same as `prepare`: what plays for an animation."""


DEFAULT_LAGGED_START_LAG_RATIO: float = 0.05


_0, _1 = Fraction(0), Fraction(1)


type Phase = Literal["run", "begin", "fresh"]


_PHASES: tuple[Phase, ...] = ("run", "begin", "fresh")


class Window(NamedTuple):
    """A part of an animation that acts itself, with where its window opens and closes in
    the whole's progress (None: with the whole), and its path (see `windows`)."""

    part: Animation
    opens: Fraction
    closes: Fraction | None
    path: tuple[int, ...]


type Route = dict[int, "Route | None"]


"""The parts of a group an instant concerns: each by its index, with the route into it if it
is a group (None: a part that acts itself)."""


type Placed = tuple[float, float, bool, Fraction, Fraction]


"""A part's window in a time: its ends, whether it closes before its group's end, and its
ends exactly."""


def warp(rate_func: RateFunc, alpha: np.ndarray) -> np.ndarray:
    """Apply a rate function to several progresses at once.

    Args:
        rate_func: The rate function.
        alpha: The progresses; NaN for a part that has not begun, which stays so.

    Returns:
        The eased progresses.
    """
    # the scalar function itself, so a frame computed alone gets the same bits
    return np.fromiter(
        (rate_func(float(a)) if a == a else np.nan for a in alpha), float, len(alpha)
    )


def stagger(time: np.ndarray, start: float, end: float) -> np.ndarray:
    """Return a part's progress through its window at several times of its group.

    Args:
        time: The group's times, as fractions of its run.
        start: Where the part's window opens, as a fraction of the group's run.
        end: Where it closes.

    Returns:
        The part's progress at each time; NaN (not begun) before its window, and held
        at 1 after it.
    """
    if end <= start:
        return np.where(time < start, np.nan, 1.0)
    return np.where(time < start, np.nan, np.clip((time - start) / (end - start), 0, 1))


def _through(time: float, start: float, end: float) -> float:
    """A begun part's progress through its window at a time of its group: held at 0
    before it (the group's time came back), at 1 after it."""
    if end <= start:
        return 1.0 if time >= end else 0.0
    return min(max((time - start) / (end - start), 0.0), 1.0)


def schedule(
    anim: Animation, alpha: np.ndarray
) -> Iterator[tuple[Animation, np.ndarray, np.ndarray]]:
    """Find every animation under `anim` that acts on its mobjects itself.

    Args:
        anim: The animation, a composition or not.
        alpha: Progresses of `anim`.

    Yields:
        Each such animation, with its progress at each of those of `anim` (NaN before its
        window opens), and whether its window has closed there: it has finished, and left
        the scene as it leaves it.
    """
    for node, progress, closed in walk(anim, alpha):
        if not isinstance(node, AnimationGroup):
            yield node, progress, closed


def walk(
    anim: Animation,
    time: np.ndarray,
    start: Fraction = Fraction(0),
    end: Fraction = Fraction(1),
    closed: np.ndarray | None = None,
) -> Iterator[tuple[Animation, np.ndarray, np.ndarray]]:
    """Every animation under `anim`, itself first, as `AnimationGroup.interpolate` plays it.

    Args:
        anim: The animation.
        time: The times it is given.
        start: Where its window opens in that time.
        end: Where it closes.
        closed: Where it has closed; None for nowhere.

    Yields:
        Each animation, with its progress at each time (NaN before its window), and
        whether its window has closed there.
    """
    closed = np.zeros(len(time), bool) if closed is None else closed
    progress = stagger(time, float(start), float(end))
    yield anim, progress, closed
    if isinstance(anim, AnimationGroup):
        eased, spans = anim._spans_in(start, end)
        own = warp(anim.rate_func, progress) if eased else time
        for part, (_, fb, early, a, b) in zip(anim.animations, spans, strict=True):
            yield from walk(part, own, a, b, closed | ((own >= fb) & early))


def windows(anim: Animation) -> list[Window]:
    """Every animation under `anim` that acts on its mobjects itself, with where, in `anim`'s
    progress, its window opens and closes: exact where the groups above it keep linear
    time; otherwise the first progress at which a group's eased time reaches the window, as
    `interpolate` finds it. A scene computes these instants, so that a part begins and
    finishes at its window, whatever the frame rate.

    Args:
        anim: The animation, a composition or not.

    Returns:
        Each such animation, where it opens, where it closes (None: with `anim`), and its
        path from `anim` (the indices of the parts that hold it).
    """
    found: list[Window] = []

    def first(time_of: Callable[[float], float], at: float) -> Fraction:
        # the first progress of the whole at which a group's time reaches `at` (its time
        # going forward), to the float
        if time_of(0.0) >= at:
            return _0
        if time_of(1.0) < at:
            return _1
        lo, hi = 0.0, 1.0
        while lo < (mid := (lo + hi) / 2) < hi:
            if time_of(mid) >= at:
                hi = mid
            else:
                lo = mid
        return Fraction(hi)

    def visit(
        group: AnimationGroup,
        time_of: Callable[[float], float] | None,
        start: Fraction,
        end: Fraction,
        opened: Fraction,
        closes: Fraction | None,
        path: tuple[int, ...],
    ) -> None:
        # time_of: the group's given time at the whole's progress (None: that progress);
        # opened: where the group itself opens (its parts, not before)
        if group.rate_func is linear:
            spans, inner = group._in(start, end), time_of
        else:
            spans, given = group._in(_0, _1), time_of or (lambda a: a)
            fs, fe, rate = float(start), float(end), group.rate_func
            inner = lambda a: rate(_through(given(a), fs, fe))  # noqa: E731
        for i, (part, (fa, fb, early, a, b)) in enumerate(
            zip(group.animations, spans, strict=True)
        ):
            opens = max(opened, a if inner is None else first(inner, fa))
            ends = (
                max(opens, b if inner is None else first(inner, fb))
                if early
                else closes
            )
            if _nested(part):
                visit(part, inner, a, b, opens, ends, (*path, i))
            else:
                found.append(Window(part, opens, ends, (*path, i)))

    if _nested(anim):
        visit(anim, None, _0, _1, _0, None, ())
    else:
        found.append(Window(anim, _0, None, ()))
    return found


def route(paths: Iterable[tuple[int, ...]]) -> Route:
    """The route to some parts of a group, from their paths (see `windows`)."""
    out: Route = {}
    for path in paths:
        at = out
        for i in path[:-1]:
            nxt = at.get(i)
            if nxt is None:
                nxt = at[i] = {}
            at = nxt
        at.setdefault(path[-1], None)
    return out


def _nested(anim: Animation) -> TypeIs[AnimationGroup]:
    """Is it a group whose parts are laid out in the time given it (as `_at` plays them)?"""
    return (
        isinstance(anim, AnimationGroup)
        and type(anim).interpolate is AnimationGroup.interpolate
    )


class AnimationGroup(Animation):
    """Play animations together, each in its own window of the group's time.

    The parts are laid out in time: each begins when the part before it has played
    `lag_ratio` of its run time (all together with the default 0, one after another at
    1, overlapping in between), and plays for its own run time. The group lasts until
    its last part ends, unless given a `run_time`, which stretches or squeezes the whole
    layout to fit. Its rate function (by default `linear`) warps the group's time, and
    each part still eases its own window with its own.

    A part begins when its window opens, taking its mobjects as they are then (and
    bringing its mobject into the scene, if it introduces it), and finishes when its
    window closes, whatever else is still playing, leaving the scene as it leaves it (a
    remover's mobject leaves it). A part whose window ends with the group's finishes with
    the group, where the group's rate function ends its time. Before its window a part has
    touched nothing; after it, what it did stays done. The group itself is not a mobject
    of the scene: it adds nothing of its own. [`Scene.play`][manimgx.Scene.play] plays
    several animations as such a group.

    Args:
        *animations: The animations, or iterables of them.
        group: The mobject the group animates; by default, a group of its parts'
            mobjects, but those that parts introduce.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions]:
            `lag_ratio` lays the parts out, `run_time` fits the whole, `rate_func` warps
            its time, and `remover` makes every part a remover.

    Examples:
        ```python
        import manimgx as m


        class AnimationGroupExample(m.Scene):
            def construct(self) -> None:
                shapes = (
                    m.VGroup(
                        m.Square(color=m.BLUE, fill_opacity=0.5),
                        m.Circle(color=m.YELLOW, fill_opacity=0.5),
                        m.Triangle(color=m.GREEN, fill_opacity=0.5),
                    )
                    .scale(1.2)
                    .arrange(buff=1)
                )
                self.play(
                    m.AnimationGroup(
                        m.Create(shapes[0]),
                        m.FadeIn(shapes[1], shift=m.UP),
                        m.GrowFromCenter(shapes[2]),
                        lag_ratio=0.5,
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": linear}

    def __init__(
        self,
        *animations: Animation
        | Iterable[Animation],  # of any mobjects (Animation is invariant in its)
        group: Group | VGroup | None = None,
        **kwargs: Unpack[AnimationOptions],
    ):
        self.animations = [prepare(a) for a in _flatten(animations)]
        self.group = group or Group(
            *remove_list_redundancies(
                [a.mobject for a in self.animations if not a.is_introducer()]
            )
        )
        super().__init__(self.group, **kwargs)
        self.scene: Scene | None = None
        self.begun: set[int] = set()
        self.done: set[int] = set()
        self._fresh: set[int] = set()  # the parts begun at the instant being computed
        # a run time given; None: the layout's own, where its last part ends
        self._given: float | Fraction | None = (
            animation_defaults(type(self)) | kwargs
        ).get("run_time")
        self._layout: tuple[tuple[object, ...], Fraction, list[Placed]] = ((), _0, [])
        self._playing = False  # between `begin` and `finish`: its layout fixed
        self._placed: tuple[tuple[object, ...], list[Placed]] = ((), [])

    def _laid_out(self) -> tuple[Fraction, list[Placed]]:
        """(where the last part ends, each part's window in the group's own time), from the
        lag and the parts' run times as they are now (a play's options set them after the
        group is made), fixed while it plays."""
        if self._playing:
            return self._layout[1], self._layout[2]
        lengths = tuple(anim._duration for anim in self.animations)
        key = (self.lag_ratio, *lengths)
        if key != self._layout[0]:
            spans, start = [], _0
            lag = clock.rational(self.lag_ratio)
            for length in lengths:
                spans.append((start, start + length))
                start += length * lag
            total = max((end for _, end in spans), default=_0)
            windows = [(a / total, b / total) if total else (_0, _0) for a, b in spans]
            placed = [(float(a), float(b), b < 1, a, b) for a, b in windows]
            self._layout = (key, total, placed)
        return self._layout[1], self._layout[2]

    def _in(self, start: Fraction, end: Fraction) -> list[Placed]:
        """Each part's window in a time in which the group's own is [start, end]: exact (so
        a group laid out in place is its parts, to the bit), with its ends as floats and
        whether it closes before the group's end."""
        if start == 0 and end == 1:
            return self._laid_out()[1]
        key = (self._layout[0], start, end)
        if key != self._placed[0]:
            span = end - start
            placed = []
            for *_, a, b in self._laid_out()[1]:
                a, b = start + a * span, start + b * span
                placed.append((float(a), float(b), b < end, a, b))
            self._placed = (key, placed)
        return self._placed[1]

    def _spans_in(self, start: Fraction, end: Fraction) -> tuple[bool, list[Placed]]:
        """(whether the group eases its time, its parts' windows in the time they are laid
        out in), where its own window is [start, end] in the time it is given: linear, that
        time; otherwise its own, eased."""
        if self.rate_func is linear:
            return False, self._in(start, end)
        return True, self._in(_0, _1)

    @property
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def max_end_time(self) -> float:
        """Where the last part ends, in seconds: the group's own run time."""
        return float(self._laid_out()[0])

    @property
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def hidden(self) -> Sequence[Mobject]:
        """What its parts leave out of the picture now (a part hides nothing until it
        begins, nor once it has ended)."""
        return [m for anim in self.animations for m in anim.hidden]

    @property
    def run_time(self) -> float:
        """How long the group plays, in seconds: the run time it was given, else where its
        last part ends."""
        return self.max_end_time if self._given is None else float(self._given)

    @run_time.setter
    def run_time(self, value: float) -> None:
        if value < 0:
            raise ValueError(
                f"The run_time of {type(self).__name__} cannot be negative. The given"
                f" value was {value}."
            )
        self._given = value

    @property
    def _duration(self) -> Fraction:
        if type(self).run_time is not AnimationGroup.run_time:
            return clock.rational(self.run_time)
        return (
            self._laid_out()[0] if self._given is None else clock.rational(self._given)
        )

    def _setup_scene(self, scene: Scene) -> None:
        self.scene = scene  # each part is set up when it begins

    def begin(self) -> None:
        if not self.animations:
            raise ValueError(
                f"Trying to play {self} without animations, this is not supported."
                " Please add at least one subanimation."
            )
        self.begun, self.done, self._fresh = set(), set(), set()
        if self.remover:  # every part a remover
            for anim in self.animations:
                anim.remover = True
        self._playing = False
        self._laid_out()
        self._playing = True
        # its parts begin as their windows open, at the instants computed (`_at`)

    def _begin(self, i: int) -> None:
        self.begun.add(i)
        self._fresh.add(i)  # brought to its progress at the instant's "fresh" phase
        if self.scene is not None:
            self.animations[i]._setup_scene(self.scene)
        self.animations[i].begin()

    def _end(self, i: int) -> None:
        """Part i's window has closed: it finishes, and leaves the scene as it leaves it."""
        self.done.add(i)
        self.animations[i].finish()
        if self.scene is not None:
            self.animations[i].clean_up_from_scene(self.scene)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def begin_all(self) -> None:
        """Begin every part at once, for a play the scene computes ahead of time.

        In such a play no part's mobjects change before its window opens, so each part
        takes what it would take then. Beginning changes no look (a tween acts only when
        interpolated; aligning a mobject with its keyframes restructures it invisibly), so
        each mobject shows its state from before the play until its window opens. The
        scene calls it.
        """
        for i, anim in enumerate(self.animations):
            if i not in self.begun:
                self._begin(i)
            if isinstance(anim, AnimationGroup):
                anim.begin_all()

    def interpolate(self, alpha: float) -> None:
        for phase in _PHASES:
            self._at(alpha, _0, _1, phase)

    def _at(
        self,
        given: float,
        start: Fraction,
        end: Fraction,
        phase: Phase,
        only: Route | None = None,
    ) -> None:
        """The group at a time it is given, in which its window is [start, end], in one of
        an instant's phases (in order, each over the whole tree): "run", the parts running
        are brought to it (and those whose windows close, closed); "begin", those whose
        windows open begin, taking the world as it is then (so those beginning together
        all find it as it was); "fresh", those are brought to it. `only`: the parts an
        instant concerns, the others left as they are; None for all."""
        eased, spans = self._spans_in(start, end)
        time = (
            self.rate_func(_through(given, float(start), float(end)))
            if eased
            else given
        )
        for i in range(len(self.animations)) if only is None else sorted(only):
            if i in self.done:
                continue
            anim, (fa, fb, early, a, b) = self.animations[i], spans[i]
            inner = None if only is None else only[i]
            if phase == "begin":
                if i not in self.begun:
                    if time < fa:
                        continue
                    self._begin(i)
                if _nested(anim):
                    anim._at(time, a, b, phase, inner)
            elif (i in self._fresh) == (phase == "fresh") and i in self.begun:
                if time >= fb and early:  # its window closed before the group's end
                    self._end(i)
                elif _nested(anim):
                    anim._at(time, a, b, phase, inner)
                else:
                    anim.interpolate(_through(time, fa, fb))
            elif _nested(anim) and i in self.begun:  # running: what opens in it
                anim._at(time, a, b, phase, inner)
        if phase == "fresh":
            self._fresh.clear()

    def _step(self, alpha: float, only: Route | None = None) -> Callable[[], None]:
        """An instant of the group, as a scene computes it: the parts running (of `only`, if
        given) are brought to it now; the returned function begins the parts whose windows
        open, once the world is at that instant."""
        self._at(alpha, _0, _1, "run", only)

        def opening() -> None:
            self._at(alpha, _0, _1, "begin", only)
            self._at(alpha, _0, _1, "fresh", only)

        return opening

    def finish(self) -> None:
        # the group's time where its rate function ends it: a part whose window it has
        # reached finishes; one it came back from stays where it puts it
        eased, spans = self._spans_in(_0, _1)
        time = self.rate_func(1.0) if eased else 1.0
        self.interpolate(1.0)
        for i, (anim, (_, fb, *_)) in enumerate(
            zip(self.animations, spans, strict=True)
        ):
            if i in self.begun and i not in self.done:
                if time >= fb:
                    self._end(i)
                else:
                    self.done.add(i)
                    anim._release()
        self._playing = False

    def _release(self) -> None:
        for i in self.begun - self.done:
            self.done.add(i)
            self.animations[i]._release()

    def advance(self, t: Fraction, only: Route | None = None) -> None:
        for i in self.begun - self.done if only is None else only.keys() - self.done:
            anim, inner = self.animations[i], None if only is None else only[i]
            if isinstance(anim, AnimationGroup):
                anim.advance(t, inner)
            elif i in self.begun:
                anim.advance(t)

    def clean_up_from_scene(self, scene: Scene) -> None:
        pass  # its parts left the scene as their windows closed


class Succession(AnimationGroup):
    """Play animations one after another.

    An [`AnimationGroup`][manimgx.AnimationGroup] whose `lag_ratio` is 1: each part
    begins when the one before it ends, from the state it left.

    Args:
        *animations: The animations, in order, or iterables of them.
        group: The mobject the group animates; by default, a group of its parts'
            mobjects, but those that parts introduce.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions] for
            the whole.

    Examples:
        ```python
        import manimgx as m


        class SuccessionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)
                square.shift(3 * m.LEFT)
                self.play(
                    m.Succession(
                        m.Create(square),
                        square.animate.shift(6 * m.RIGHT),
                        m.Rotate(square, m.PI / 4),
                        square.animate.set_color(m.YELLOW),
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"lag_ratio": 1.0}


class LaggedStart(AnimationGroup):
    """Play animations one shortly after another, overlapping.

    An [`AnimationGroup`][manimgx.AnimationGroup] whose `lag_ratio` is small (0.05 by
    default): each part begins when the one before it has played that fraction of its
    run time.

    Args:
        *animations: The animations, in order, or iterables of them.
        group: The mobject the group animates; by default, a group of its parts'
            mobjects, but those that parts introduce.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions] for
            the whole.

    Examples:
        ```python
        import manimgx as m


        class LaggedStartExample(m.Scene):
            def construct(self) -> None:
                dots = m.VGroup(*(m.Dot(radius=0.25, color=m.YELLOW) for _ in range(8)))
                dots.arrange(buff=0.8).shift(2 * m.UP)
                self.add(dots)
                self.play(
                    m.LaggedStart(
                        *(dot.animate.shift(4 * m.DOWN) for dot in dots), lag_ratio=0.2
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"lag_ratio": DEFAULT_LAGGED_START_LAG_RATIO}


class LaggedStartMap(LaggedStart):
    """Play an animation on each submobject of a mobject, one shortly after another.

    Each submobject's animation is `animation_class(*arg_creator(submobject), **kwargs)`
    (by default, `animation_class(submobject, **kwargs)`), and they play as a
    [`LaggedStart`][manimgx.LaggedStart]. `run_time` (2 seconds by default) and
    `lag_ratio` time the whole; every other option goes to each animation.

    Args:
        animation_class: The animation to play on each submobject: a class, or any
            function returning an animation.
        mobject: The mobject whose submobjects are animated.
        arg_creator: A function from a submobject to the animation's positional
            arguments; None for the submobject alone.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions]:
            `run_time` and `lag_ratio` for the whole, the others for each animation.

    Examples:
        ```python
        import manimgx as m


        class LaggedStartMapExample(m.Scene):
            def construct(self) -> None:
                dots = m.VGroup(*(m.Dot(radius=0.2) for _ in range(35)))
                dots.arrange_in_grid(rows=5, cols=7, buff=0.6)
                self.play(m.LaggedStartMap(m.GrowFromCenter, dots, lag_ratio=0.1))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 2.0}

    def __init__(
        self,
        animation_class: Callable[
            ..., Animation
        ],  # given each part's arguments (`arg_creator`)
        mobject: Mobject,
        arg_creator: Callable[[Mobject], Iterable[object]] | None = None,
        **kwargs: Unpack[AnimationOptions],
    ):
        timing: AnimationOptions = {}
        if "run_time" in kwargs:
            timing["run_time"] = kwargs.pop("run_time")
        if "lag_ratio" in kwargs:
            timing["lag_ratio"] = kwargs.pop("lag_ratio")
        arguments = arg_creator or (lambda part: (part,))
        super().__init__(
            *(animation_class(*arguments(part), **kwargs) for part in mobject), **timing
        )


class ChangeSpeed(AnimationGroup):
    """Play an animation faster or slower along the way: at speeds that change as it
    plays.

    `speedinfo` gives speeds at points of the animation's progress: `{0.5: 2}` plays it
    at its own speed at the start, speeding up to twice as fast at its middle, and twice
    as fast from there on. Between two points the speed changes steadily (at a constant
    acceleration, in the scene's time), so the stretch from progress `a` to `b`, at
    speeds `v` and `w`, takes `(b - a) · 2 / (v + w)` of the animation's run time; the
    play lasts as long as its stretches take. Unless given, the speed at the start is 1
    and the speed at the end the last point's.

    With `affects_speed_updaters`, the updaters added with
    [`ChangeSpeed.add_updater`][manimgx.ChangeSpeed.add_updater] run at the same speeds
    while it plays, so that whatever they move keeps pace with the animation.

    The speeds change only the animation's timing: it keeps its own rate function (and
    its parts' stagger), so at a speed of 1 throughout it is the animation itself.

    Args:
        anim: The animation to play.
        speedinfo: Speeds at points of the animation's progress, from 0 to 1: a speed of
            2 plays it twice as fast, 0.5 half as fast.
        affects_speed_updaters: Whether the updaters added with
            `ChangeSpeed.add_updater` follow the speeds while it plays.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions] for
            the whole: its `rate_func` (by default `linear`) eases the play's time before
            the speeds warp it. Its run time is what the speeds make it: a `run_time`
            given here is ignored.

    Examples:
        ```python
        import manimgx as m


        class ChangeSpeedExample(m.Scene):
            def construct(self) -> None:
                steady = m.Dot(5 * m.LEFT + m.UP, radius=0.25, color=m.BLUE)
                slowed = m.Dot(5 * m.LEFT + m.DOWN, radius=0.25, color=m.YELLOW)
                self.add(steady, slowed)
                self.play(
                    steady.animate(run_time=2, rate_func=m.linear).set_x(5),
                    m.ChangeSpeed(
                        slowed.animate(run_time=2, rate_func=m.linear).set_x(5),
                        speedinfo={0.3: 1, 0.4: 0.2, 0.6: 0.2, 0.7: 1},
                    ),
                )
        ```
    """

    def __init__(
        self,
        anim: Animation,
        speedinfo: dict[float, float],
        affects_speed_updaters: bool = True,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.anim = prepare(anim)
        speeds = dict(sorted(({0: 1} | speedinfo).items()))
        speeds.setdefault(1, speeds[max(speeds)])
        self.speedinfo = speeds
        self.affects_speed_updaters = affects_speed_updaters
        # each stretch: (from, to, speed at from, speed at to, where it starts in real time)
        self._stretches: list[tuple[float, float, float, float, float]] = []
        total = _0  # real time, per second of the wrapped animation
        for (a, v), (b, w) in pairwise(speeds.items()):
            self._stretches.append((a, b, v, w, float(total)))
            total += (
                2
                * (clock.rational(b) - clock.rational(a))
                / (clock.rational(v) + clock.rational(w))
            )
        self._total = float(total)
        self._before = kwargs.pop("rate_func", linear)
        kwargs["rate_func"] = self._rate
        duration = total * self.anim._duration
        kwargs["run_time"] = float(duration)
        super().__init__(self.anim, **kwargs)
        self._given = duration

    def _rate(self, t: float) -> float:
        """Its rate function: the wrapped animation's progress at the rate function given
        (a method, so that a copy reads its own stretches)."""
        return self.progress(self._before(t))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def progress(self, t: float) -> float:
        """The animation's progress at a time of the play.

        Within each stretch between two points of `speedinfo`, it is the distance
        covered by a speed that goes steadily from one point's to the other's.

        Args:
            t: The play's time, as a fraction of its run time, eased by its rate
                function.

        Returns:
            The animation's progress, from 0 to 1.
        """
        if t >= 1:
            return 1.0
        # at a node, the later stretch (CE's piecewise lets the last condition win)
        for a, b, v, w, start in reversed(self._stretches):
            if start / self._total <= t:
                x = (self._total * t - start) / (b - a)
                d = ((w**2 - v**2) * (x * x) / 4 + v * x) * (b - a)
                return min(max(d + a, a), b)  # never past its stretch's ends
        return 0.0

    @classmethod
    def add_updater(
        cls,
        mobject: Mobject,
        update_function: Updater[Mobject],
        index: int | None = None,
        call_updater: bool = False,
    ) -> None:
        """Add an updater to a mobject whose time follows the speed of any `ChangeSpeed`
        playing.

        A time-based updater added this way is handed, as `dt`, the time of a clock that
        runs with the scene's, except while a `ChangeSpeed` with
        `affects_speed_updaters` plays: then it runs at that `ChangeSpeed`'s speeds (its
        `speedinfo`, whatever its rate function eases), and while several play at once,
        at the speeds of the one that began last. The clock never runs backward. It
        keeps its kind: a [flow][manimgx.mobject.flow] stays a flow, and any other
        time-based updater still steps on the simulation clock. A per-frame updater has
        no time, and is added as it is.

        Args:
            mobject: The mobject to add it to.
            update_function: The updater: a function of the mobject, or of the mobject
                and `dt` (see [`add_updater`][manimgx.Mobject.add_updater]).
            index: Where it goes among the mobject's updaters, which run in order; None
                for last.
            call_updater: Whether to run it once right away; a time-based one is handed
                a `dt` of 0.
        """
        if not _per_frame(update_function):
            on_clock = _OnClock(update_function, clock.speed)
            update_function = on_clock if simulated(update_function) else flow(on_clock)
        mobject.add_updater(update_function, index=index, call_updater=call_updater)

    def begin(self) -> None:
        # from the instant it begins (a part of a composition begins inside the play),
        # at its speeds: the speed profile over the play's own time
        if self.affects_speed_updaters:
            clock.speed.warp(
                float(clock.now), self.run_time, self.anim.run_time, self.progress
            )
        super().begin()


class _OnClock:
    """A time-based updater that lives on another clock than scene time."""

    def __init__(
        self, function: Callable[[Mobject, float], object], on: clock.Clock
    ) -> None:
        self.function = function
        self.clock = on

    def __call__(self, mob: Mobject, dt: float) -> object:
        return self.function(mob, dt)

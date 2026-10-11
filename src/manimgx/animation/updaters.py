# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Continuous motion: updater tools, animated outlines and recorded paths."""

from __future__ import annotations

from warnings import deprecated

__all__ = [
    "AnimatedBoundary",
    "TracedPath",
    "always",
    "always_redraw",
    "always_rotate",
    "always_shift",
    "assert_is_mobject_method",
    "cycle_animation",
    "f_always",
    "turn_animation_into_updater",
]
import inspect
import itertools
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, Unpack

import numpy as np

from manimgx.animation import clock
from manimgx.animation.easing import RateFunction, smooth
from manimgx.constants import DEGREES, OUT, RIGHT
from manimgx.drawing.geometry import normalize
from manimgx.drawing.paint import (
    BLUE_B,
    BLUE_D,
    BLUE_E,
    GREY_BROWN,
    WHITE,
    ParsableManimColor,
    Style,
)
from manimgx.mobject import Mobject, Pivot, VGroup, VMobject, flow, record
from manimgx.typing import Point3DLike, Vector3DLike

if TYPE_CHECKING:
    from manimgx.animation.timeline import Animation


def _owner(method: Callable[..., object]) -> tuple[Mobject, Callable[..., object]]:
    """The mobject a bound method belongs to, and its plain function."""
    if not inspect.ismethod(method) or not isinstance(method.__self__, Mobject):
        raise TypeError("expected a method of a mobject, such as `square.move_to`")
    return method.__self__, method.__func__


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def assert_is_mobject_method(method: Callable[..., object]) -> None:
    """Check that `method` is a method of a mobject, bound to it (as `square.move_to`):
    anything else raises a TypeError.

    Args:
        method: The method to check.
    """
    _owner(method)


@deprecated(
    "always(mobject.method, *args) is mobject.always.method(*args): use it",
    category=None,
)
def always[**P](
    method: Callable[P, object], *args: P.args, **kwargs: P.kwargs
) -> Mobject:
    """Call a method of a mobject every frame, with the same arguments: the relation it
    sets is kept.

    `always(label.next_to, dot, UP)` keeps the label above the dot, wherever the dot
    goes. It adds a per-frame updater to the mobject the method belongs to (see
    [`add_updater`][manimgx.Mobject.add_updater]), which first runs at the next frame,
    not now. The arguments are taken once, as written: pass the mobject to follow
    (`dot`), not its position (`dot.get_center()`), which would stay where it was.
    [`Mobject.always`][manimgx.Mobject.always] does the same, as
    `label.always.next_to(dot, UP)`.

    Args:
        method: A method of a mobject, bound to it (`label.next_to`).
        *args: Its positional arguments.
        **kwargs: Its keyword arguments.

    Returns:
        The mobject the method belongs to.
    """
    mobject, func = _owner(method)
    mobject.add_updater(lambda m: func(m, *args, **kwargs))
    return mobject


@deprecated("use add_updater, or always_redraw", category=None)
def f_always(
    method: Callable[..., object],
    *arg_generators: Callable[[], object],
    **kwargs: object,
) -> Mobject:
    """Call a method of a mobject every frame, with arguments computed anew each time.

    Each positional argument is given as a function of no arguments, called every frame
    for the value to pass: `f_always(dot.set_x, tracker.get_value)` keeps the dot at the
    x the tracker holds. It adds a per-frame updater to the mobject the method belongs
    to (see [`add_updater`][manimgx.Mobject.add_updater]), which first runs at the next
    frame, not now.

    Args:
        method: A method of a mobject, bound to it (`dot.set_x`).
        *arg_generators: For each positional argument, a function of no arguments that
            gives its value.
        **kwargs: Keyword arguments, passed as they are.

    Returns:
        The mobject the method belongs to.
    """
    mobject, func = _owner(method)
    mobject.add_updater(
        lambda m: func(m, *(generate() for generate in arg_generators), **kwargs)
    )
    return mobject


def always_redraw[M: Mobject](func: Callable[[], M]) -> M:
    """Make a mobject that is built anew every frame, by a function.

    `func` builds the mobject now, and every frame the mobject becomes what `func`
    builds then (see [`become`][manimgx.Mobject.become]): it stays one object in the
    scene, and follows whatever `func` reads — value trackers, other mobjects. Use it
    for a shape that depends on others in a way no motion follows: a brace that fits a
    growing shape, a line between two moving dots, the area under a graph.

    Args:
        func: A function of no arguments that builds the mobject.

    Returns:
        The mobject, with its updater: add it to the scene.

    Examples:
        ```python
        import manimgx as m


        class AlwaysRedrawExample(m.Scene):
            def construct(self) -> None:
                width = m.ValueTracker(2)
                box = m.always_redraw(
                    lambda: m.Rectangle(width=width.get_value(), height=3, color=m.BLUE)
                )
                brace = m.always_redraw(lambda: m.Brace(box, m.DOWN, color=m.YELLOW))
                self.add(box, brace)
                self.play(width.animate.set_value(11), run_time=2)
                self.play(width.animate.set_value(5))
        ```
    """
    mob = func()
    mob.add_updater(lambda m: m.become(func()))
    return mob


def always_shift[M: Mobject](
    mobject: M, direction: Vector3DLike = RIGHT, rate: float = 0.1
) -> M:
    """Keep a mobject moving in a direction, at a steady speed.

    It adds a time-based updater, a [flow][manimgx.mobject.flow], so at every frame
    the mobject is exactly where its speed has brought it, through plays and waits
    alike.

    Args:
        mobject: The mobject to move.
        direction: The direction to move in; only its direction counts, not its length.
        rate: The speed, in scene units per second.

    Returns:
        The mobject, with its updater.

    Examples:
        ```python
        import manimgx as m


        class AlwaysShiftExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.8)
                square.shift(5 * m.LEFT)
                m.always_shift(square, m.RIGHT, rate=2.5)
                self.add(square)
                self.play(square.animate.set_color(m.YELLOW), run_time=2)
                self.wait(2)
        ```
    """
    unit = normalize(direction)
    mobject.add_updater(flow(lambda m, dt: m.shift(dt * rate * unit)))
    return mobject


def always_rotate[M: Mobject](
    mobject: M,
    rate: float = 20 * DEGREES,
    axis: Vector3DLike = OUT,
    **kwargs: Unpack[Pivot],
) -> M:
    """Keep a mobject turning, at a steady speed.

    It adds a time-based updater, a [flow][manimgx.mobject.flow], so at every frame
    the mobject is at exactly the angle its speed has brought it to, through plays and
    waits alike.

    Args:
        mobject: The mobject to turn.
        rate: The speed, in radians per second; a positive one turns counterclockwise.
        axis: The axis it turns about.
        **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point it turns
            about, its center unless given.

    Returns:
        The mobject, with its updater.

    Examples:
        ```python
        import manimgx as m


        class AlwaysRotateExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                square.shift(3.5 * m.LEFT)
                m.always_rotate(square, rate=m.PI / 2)  # a quarter turn a second
                center = m.Dot(3.5 * m.RIGHT, color=m.YELLOW)
                moon = m.Dot(3.5 * m.RIGHT + 2 * m.UP, radius=0.25, color=m.TEAL)
                m.always_rotate(moon, rate=-m.PI, about_point=center.get_center())
                self.add(square, center, moon)
                self.wait(4)
        ```
    """
    mobject.add_updater(flow(lambda m, dt: m.rotate(dt * rate, axis, **kwargs)))
    return mobject


def turn_animation_into_updater(
    animation: Animation, cycle: bool = False, delay: float = 0
) -> Mobject:
    """Play an animation from an updater of its mobject, on the mobject's own time,
    instead of in a play.

    The animation begins at once: it takes its mobject as it is now, and shows its
    start. Its time then runs with the scene's, from now or from when the mobject joins
    the scene; after `delay` seconds it plays, at its run time and rate function. When
    it ends, it finishes and its updater is removed; with `cycle`, it starts over from
    its beginning instead, again and again. Nothing is added to the scene or taken out
    of it: add the mobject yourself. The animation and its time are the mobject's: a
    copy of it plays a copy of them, on itself.

    Args:
        cycle: Whether it repeats forever.
        delay: How long it waits before it starts, in seconds.

    Returns:
        The animation's mobject, with its updater.

    Examples:
        ```python
        import manimgx as m


        class TurnAnimationIntoUpdaterExample(m.Scene):
            def construct(self) -> None:
                shape = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)
                squares = m.VGroup(*(shape.copy() for _ in range(3))).arrange(buff=1.5)
                self.add(squares)
                for i, square in enumerate(squares):  # half a second apart
                    m.turn_animation_into_updater(
                        m.Rotate(square, m.PI / 2, run_time=1), delay=0.5 * i
                    )
                self.wait(2.5)
        ```
    """
    mobject = animation.mobject
    animation.suspend_mobject_updating = False
    animation.begin()
    animation.interpolate(
        0
    )  # the object is the animation's from now: at its start, until then
    # the animation and its time are kept on the mobject, so that a copy of it plays a copy
    # of them: the updater holds only their key, and plays those of the mobject it runs on
    key = next(_PLAYED_KEYS)
    played: dict[int, _Played] = mobject.__dict__.setdefault("_played", {})
    played[key] = _Played(animation, -delay)

    def update(m: Mobject, dt: float) -> None:
        state = m.__dict__.get("_played", {}).get(key)
        if state is None:  # nothing of its own to play
            return
        state.elapsed += dt  # its time now: what this frame shows
        if state.elapsed < 0:
            return
        animation, elapsed = state.animation, state.elapsed
        run_time = animation.get_run_time()
        if run_time > 0 and (cycle or elapsed < run_time):
            animation.interpolate(
                (elapsed / run_time) % 1 if cycle else elapsed / run_time
            )
            animation.advance(clock.now)
        else:
            animation.finish()
            m.remove_updater(update)
            del m.__dict__["_played"][key]

    mobject.add_updater(flow(update))  # the animation at the time it has run
    return mobject


@dataclass
class _Played:
    """An animation [turn_animation_into_updater][manimgx.turn_animation_into_updater]
    plays, and the time it has run (before its delay, negative)."""

    animation: Animation
    elapsed: float


_PLAYED_KEYS = itertools.count()


def cycle_animation(animation: Animation, delay: float = 0) -> Mobject:
    """Play an animation over and over, from an updater of its mobject:
    [`turn_animation_into_updater`][manimgx.turn_animation_into_updater] with `cycle`.

    Each cycle starts the animation over from its beginning: an animation that does not
    end where it began jumps back at every cycle.

    Args:
        delay: How long it waits before its first cycle, in seconds.

    Returns:
        The animation's mobject, with its updater.

    Examples:
        ```python
        import manimgx as m


        class CycleAnimationExample(m.Scene):
            def construct(self) -> None:
                orbit = m.Circle(radius=3, color=m.BLUE)
                planet = m.Dot(orbit.get_start(), radius=0.25, color=m.YELLOW)
                m.cycle_animation(
                    m.MoveAlongPath(planet, orbit, rate_func=m.linear, run_time=2)
                )
                self.add(orbit, planet)
                self.wait(4)
        ```
    """
    return turn_animation_into_updater(animation, cycle=True, delay=delay)


class AnimatedBoundary(VGroup):
    """An outline that keeps drawing itself around a mobject, cycling through colors.

    Each cycle draws the mobject's outline in the next color, while the outline the
    cycle before drew thins away; with `back_and_forth`, every other cycle draws it the
    other way around. It follows the mobject: every frame, it takes the mobject's
    outline as it is then. It draws only the outline: add it to the scene with the
    mobject.

    Args:
        vmobject: The mobject to outline.
        colors: The colors, one per cycle, in turn.
        max_stroke_width: The outline's stroke width, in hundredths of a scene unit.
        cycle_rate: How many cycles a second.
        back_and_forth: Whether every other cycle draws the outline from its end back to
            its start.
        draw_rate_func: How each drawing is paced: a rate function.
        fade_rate_func: How each thinning away is paced: a rate function.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] of the group itself.

    Examples:
        ```python
        import manimgx as m


        class AnimatedBoundaryExample(m.Scene):
            def construct(self) -> None:
                word = m.Text("So shiny!", font_size=144)
                boundary = m.AnimatedBoundary(
                    word,
                    colors=[m.RED, m.YELLOW, m.BLUE],
                    max_stroke_width=8,
                    cycle_rate=1,  # a color a second
                )
                self.add(word, boundary)
                self.wait(3)
        ```
    """

    def __init__(
        self,
        vmobject: Mobject,
        colors: Sequence[ParsableManimColor] = (BLUE_D, BLUE_B, BLUE_E, GREY_BROWN),
        max_stroke_width: float = 3,
        cycle_rate: float = 0.5,
        back_and_forth: bool = True,
        draw_rate_func: RateFunction = smooth,
        fade_rate_func: RateFunction = smooth,
        **kwargs: Unpack[Style],
    ):
        super().__init__(**kwargs)
        self.colors = list(colors)  # its own: the default, or what was given, as it was
        self.max_stroke_width = max_stroke_width
        self.cycle_rate = cycle_rate
        self.back_and_forth = back_and_forth
        self.draw_rate_func = draw_rate_func
        self.fade_rate_func = fade_rate_func
        self.vmobject = vmobject
        self.boundary_copies = [
            vmobject.copy().set_style(stroke_width=0, fill_opacity=0) for x in range(2)
        ]
        self.add(*self.boundary_copies)
        self.total_time = 0.0
        self.add_updater(flow(lambda m, dt: m.update_boundary_copies(dt)))

    @deprecated("Manim CE's machinery: its updater calls it", category=None)
    def update_boundary_copies(self, dt: float) -> None:
        """Move the outline on by some time: its updater calls it every frame.

        Args:
            dt: The time since it last moved on, in seconds.
        """
        self.total_time += dt  # its time now: what this frame shows
        time = self.total_time * self.cycle_rate
        growing, fading = self.boundary_copies
        colors = self.colors
        msw = self.max_stroke_width
        vmobject = self.vmobject
        index = int(time % len(colors))
        alpha = time % 1
        draw_alpha = self.draw_rate_func(alpha)
        fade_alpha = self.fade_rate_func(alpha)
        if self.back_and_forth and int(time) % 2 == 1:
            bounds = (1.0 - draw_alpha, 1.0)
        else:
            bounds = (0.0, draw_alpha)
        self.full_family_become_partial(growing, vmobject, *bounds)
        growing.set_stroke(colors[index], width=msw)
        if time >= 1:
            self.full_family_become_partial(fading, vmobject, 0, 1)
            fading.set_stroke(color=colors[index - 1], width=(1 - fade_alpha) * msw)

    @deprecated("Manim CE's machinery: its updater calls it", category=None)
    def full_family_become_partial(
        self, mob1: Mobject, mob2: Mobject, a: float, b: float
    ) -> Self:
        """Make each drawn member of one mobject a stretch of its counterpart in
        another.

        The members with points are paired in family order; each member of `mob1` takes
        the stretch of its counterpart from proportion `a` to proportion `b` of its
        curves.

        Args:
            mob1: The mobject whose members change.
            mob2: The mobject whose members they take stretches of.
            a: Where each stretch starts, from 0 to 1.
            b: Where it ends, from `a` to 1.

        Returns:
            This boundary, for chaining.
        """
        family1 = mob1.family_members_with_points()
        family2 = mob2.family_members_with_points()
        for sm1, sm2 in zip(family1, family2, strict=False):
            sm1.pointwise_become_partial(sm2, a, b)
        return self


class TracedPath(VMobject):
    """The path a moving point traces: a line through everywhere it has been.

    `traced_point_func` gives the point. The path records where it is at every tick of
    the simulation clock
    ([`config.simulation_rate`][manimgx.config.Config.simulation_rate] times a second)
    and at the end of each play and wait, so it is the same path at any frame rate; at a
    frame between two ticks, it runs on to where the point is then. It traces while it
    is in the scene, from when it joins it, and at each instant once everything else
    has moved: its updater is a [recorder][manimgx.mobject.record].

    A per-frame updater moves the point at frames only, so what it moves the point by
    at a frame is its change over the frame that ends there: the path spreads that move
    over the frame, in proportion to time. A point that a play carries while a
    per-frame updater turns it traces one smooth curve, not stairs. With
    `dissipating_time`, only the stretch traced in the last that many seconds remains.

    Args:
        traced_point_func: A function of no arguments that gives the point to trace
            (`dot.get_center`).
        dissipating_time: How long each stretch of the path remains, in seconds; None:
            all of it remains.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] (by default a white stroke,
            2 wide).

    Examples:
        ```python
        import manimgx as m


        class TracedPathExample(m.Scene):
            def construct(self) -> None:
                wheel = m.Circle(radius=1, color=m.BLUE).shift(5 * m.LEFT)
                dot = m.Dot(wheel.get_bottom(), radius=0.12, color=m.YELLOW)
                rolling = m.VGroup(wheel, dot)
                path = m.TracedPath(
                    dot.get_center, stroke_color=m.YELLOW, stroke_width=4
                )

                def roll(mob: m.Mobject, dt: float) -> None:  # 2.5 radians a second
                    mob.rotate(-2.5 * dt, about_point=mob[0].get_center())

                rolling.add_updater(roll)
                self.add(path, rolling)
                # 2.5 units a second: the wheel rolls without slipping
                self.play(
                    rolling.animate.shift(10 * m.RIGHT), run_time=4, rate_func=m.linear
                )
        ```
    """

    def __init__(
        self,
        traced_point_func: Callable[[], Point3DLike],
        dissipating_time: float | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        if kwargs.get("stroke_color") is None:  # not given, None too
            kwargs["stroke_color"] = WHITE
        if kwargs.get("stroke_width") is None:  # not given, None too
            kwargs["stroke_width"] = 2
        super().__init__(**kwargs)
        self.traced_point_func = traced_point_func
        self.dissipating_time = dissipating_time
        self.time = 0.0  # the path's own time
        # when each curve's end was traced (its own time)
        self._traced: list[float] = []
        # the scene time of each curve's end since the last frame
        self._open: list[float] = []
        self._framed: float | None = None  # the scene time of the last frame (or event)
        self._last = np.zeros(3)  # the point as last traced
        self._loose = (
            False  # its last curve runs on to the point at a frame between two ticks
        )
        self.add_updater(
            _trace
        )  # (a function of the path it runs on: a copy traces itself)

    @record
    @deprecated("Manim CE's machinery: its updater calls it", category=None)
    def update_path(self, mob: Mobject, dt: float) -> None:
        """Trace the point where it is now: the path's updater, a
        [recorder][manimgx.mobject.record].

        At a tick of the simulation clock or at the end of a play or wait, the point is
        traced for good; at a frame between two ticks, the path runs on to it, a
        stretch the next instant takes back. A frame or an end runs it a second time
        once the per-frame updaters have run: what they moved the point by is spread
        over the frame that ends there, each stretch traced since the frame before
        moved by its share of the frame's time. A dissipating path then drops what it
        traced more than `dissipating_time` seconds ago.

        Args:
            mob: The path the updater runs on.
            dt: The time since it last ran, in seconds.
        """
        # the second run is the instant's second pass (`clock.framing`, see
        # `Scene._instant`): `_settle` spreads the move
        point = np.asarray(self.traced_point_func(), dtype=float)
        now = float(clock.now)
        if clock.framing:
            self._settle(point, now)
            return
        if self._loose:
            self._loose = False
            self.set_points(self.points[: -self.n_points_per_curve])
            self._open.pop()
            if self.has_points():
                self._last = self.points[-1].copy()
        self.time += dt
        if not clock.stepping:  # a frame between two ticks: loose, if the point moved
            if not self.has_points() or not np.array_equal(point, self._last):
                self._trace(point, now)
                self._loose = True
            return
        self._trace(point, now)
        if self.dissipating_time:
            self._traced.append(self.time)
            old = 0
            while self._traced[old] < self.time - self.dissipating_time:
                old += 1
            if old:
                del self._traced[:old]
                self.set_points(self.points[old * self.n_points_per_curve :])
                del self._open[: max(0, len(self._open) - len(self._traced))]

    def _trace(self, point: np.ndarray, now: float) -> None:
        if not self.has_points():
            self.start_new_path(point)
        self.add_line_to(point)
        self._open.append(now)
        self._last = point

    def _settle(self, point: np.ndarray, now: float) -> None:
        """The frame (or event) ending `now` moved the point on to `point`: each curve traced
        since the last one takes its share of that move, by when it was traced. A curve's
        handles move with its anchors, so it stays straight."""
        jump = point - self._last
        if jump.any():
            if not self._open or self._open[-1] != now:  # nothing traced here yet
                self._trace(self._last, now)
                self._loose = True
            start = self._open[0] if self._framed is None else self._framed
            span = now - start
            ends = np.array(
                [(t - start) / span if span > 0 else 1.0 for t in self._open]
            )
            first = ends[0] if self._framed is None else 0.0
            starts = np.concatenate(([first], ends[:-1]))
            weights = np.stack(
                (starts, (2 * starts + ends) / 3, (starts + 2 * ends) / 3, ends), axis=1
            ).reshape(-1, 1)
            points = self.points.copy()
            points[-len(weights) :] += weights * jump
            self.set_points(points)
            self._last = point
        self._open = [now] if self._loose else []
        self._framed = now


@record
def _trace(path: Mobject, dt: float) -> None:
    """A traced path's updater: it traces the path it runs on (its copies, a path that takes
    its updaters over), and holds nothing of the path it was made for."""
    if isinstance(path, TracedPath):
        path.update_path(path, dt)

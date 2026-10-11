# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Rate functions, ported from Manim CE 0.21 `utils/rate_functions.py` (MIT)."""

import functools
import math
from collections.abc import Callable
from typing import Concatenate

import numpy as np

from manimgx.typing import RateFunc

__all__ = [
    "RateFunction",
    "double_smooth",
    "ease_in_back",
    "ease_in_bounce",
    "ease_in_circ",
    "ease_in_cubic",
    "ease_in_elastic",
    "ease_in_expo",
    "ease_in_out_back",
    "ease_in_out_bounce",
    "ease_in_out_circ",
    "ease_in_out_cubic",
    "ease_in_out_elastic",
    "ease_in_out_expo",
    "ease_in_out_quad",
    "ease_in_out_quart",
    "ease_in_out_quint",
    "ease_in_out_sine",
    "ease_in_quad",
    "ease_in_quart",
    "ease_in_quint",
    "ease_in_sine",
    "ease_out_back",
    "ease_out_bounce",
    "ease_out_circ",
    "ease_out_cubic",
    "ease_out_elastic",
    "ease_out_expo",
    "ease_out_quad",
    "ease_out_quart",
    "ease_out_quint",
    "ease_out_sine",
    "exponential_decay",
    "linear",
    "lingering",
    "not_quite_there",
    "running_start",
    "rush_from",
    "rush_into",
    "slow_into",
    "smooth",
    "smootherstep",
    "smoothstep",
    "squish_rate_func",
    "there_and_back",
    "there_and_back_with_pause",
    "unit_interval",
    "wiggle",
    "zero",
]

RateFunction = RateFunc
"""The type of a rate function: a function of the time an animation has run, from 0 to
1, giving how far along it is."""


def unit_interval[**P](
    function: Callable[Concatenate[float, P], float],
) -> Callable[Concatenate[float, P], float]:
    """Make a rate function start exactly at 0 and end exactly at 1, and hold its ends
    outside [0, 1].

    Args:
        function: The rate function, as it runs from 0 to 1.

    Returns:
        The rate function: 0 up to 0, 1 from 1 on.
    """

    @functools.wraps(function)
    def wrapper(t: float, /, *args: P.args, **kwargs: P.kwargs) -> float:
        # its ends are exact, whatever rounding its formula does there: an animation lands
        if 0 < t < 1:
            return function(t, *args, **kwargs)
        return 0 if t <= 0 else 1

    return wrapper


def zero[**P](
    function: Callable[Concatenate[float, P], float],
) -> Callable[Concatenate[float, P], float]:
    """Make a rate function that comes back to 0 start and end exactly at 0, and hold 0
    outside [0, 1].

    Args:
        function: The rate function, as it runs from 0 to 1.

    Returns:
        The rate function, 0 up to 0 and from 1 on.
    """

    @functools.wraps(function)
    def wrapper(t: float, /, *args: P.args, **kwargs: P.kwargs) -> float:
        return function(t, *args, **kwargs) if 0 < t < 1 else 0

    return wrapper


@unit_interval
def linear(t: float) -> float:
    """Progress in step with time: t."""
    return t


@unit_interval
def smooth(t: float, inflection: float = 10.0) -> float:
    """Slow, fast, slow: a sigmoid curve, stretched to run from 0 to 1.

    The default rate function of animations.

    Args:
        t: The time, from 0 to 1.
        inflection: How steep its middle is: higher starts and ends slower and runs
            faster between.

    Returns:
        The progress, from 0 to 1.
    """
    error = 1.0 / (1 + np.exp(inflection / 2))  # the logistic curve's value at t = 0
    logistic = 1.0 / (1 + np.exp(-inflection * (t - 0.5)))
    return min(max((logistic - error) / (1 - 2 * error), 0), 1)


@unit_interval
def smoothstep(t: float) -> float:
    """3t² − 2t³: starts and ends at rest; gentler than [smooth][manimgx.smooth]."""
    return 3 * t**2 - 2 * t**3


@unit_interval
def smootherstep(t: float) -> float:
    """6t⁵ − 15t⁴ + 10t³: starts and ends at rest, and without acceleration there."""
    return 6 * t**5 - 15 * t**4 + 10 * t**3


@unit_interval
def rush_into(t: float, inflection: float = 10.0) -> float:
    """The first half of [smooth][manimgx.smooth], stretched over the whole time:
    starts slowly and ends at its greatest speed.

    Args:
        t: The time, from 0 to 1.
        inflection: How steep [smooth][manimgx.smooth] is.

    Returns:
        The progress, from 0 to 1.
    """
    return 2 * smooth(t / 2.0, inflection)


@unit_interval
def rush_from(t: float, inflection: float = 10.0) -> float:
    """The second half of [smooth][manimgx.smooth], stretched over the whole time:
    starts at its greatest speed and slows toward the end.

    Args:
        t: The time, from 0 to 1.
        inflection: How steep [smooth][manimgx.smooth] is.

    Returns:
        The progress, from 0 to 1.
    """
    return 2 * smooth(t / 2.0 + 0.5, inflection) - 1


@unit_interval
def slow_into(t: float) -> float:
    """√(1 − (1 − t)²), a quarter circle: starts sharply and slows to a
    stop."""
    return float(np.sqrt(1 - (1 - t) * (1 - t)))


@unit_interval
def double_smooth(t: float) -> float:
    """Two [smooth][manimgx.smooth] moves, each half the way in half the time: comes to
    its slowest speed at the middle."""
    return 0.5 * smooth(2 * t) if t < 0.5 else 0.5 * (1 + smooth(2 * t - 1))


@zero
def there_and_back(t: float, inflection: float = 10.0) -> float:
    """There and back: [smooth][manimgx.smooth] to the end by the middle, then back to
    the start.

    Args:
        t: The time, from 0 to 1.
        inflection: How steep [smooth][manimgx.smooth] is.

    Returns:
        The progress, 0 at the start and the end and 1 at the middle.
    """
    return smooth(2 * t if t < 0.5 else 2 * (1 - t), inflection)


@zero
def there_and_back_with_pause(t: float, pause_ratio: float = 1.0 / 3) -> float:
    """There and back with a pause: [smooth][manimgx.smooth] to the end, a pause there,
    then back to the start.

    Args:
        t: The time, from 0 to 1.
        pause_ratio: The fraction of the time spent at the end, in the middle.

    Returns:
        The progress, 0 at the start and the end and 1 during the pause.
    """
    a = 2.0 / (1.0 - pause_ratio)
    if t < 0.5 - pause_ratio / 2:
        return smooth(a * t)
    if t < 0.5 + pause_ratio / 2:
        return 1
    return smooth(a - a * t)


@unit_interval
def running_start(t: float, pull_factor: float = -0.5) -> float:
    """Backs up for a running start, then runs to the end: with the default pull, back
    to −0.18 at t ≈ 0.29.

    Args:
        t: The time, from 0 to 1.
        pull_factor: How far it pulls back: the third and fourth of its Bézier curve's
            seven control values (0, 0, pull, pull, 1, 1, 1).

    Returns:
        The progress, from 0 to 1, after dipping below 0.
    """
    mt = 1 - t
    return (
        15 * t**2 * mt**4 * pull_factor
        + 20 * t**3 * mt**3 * pull_factor
        + 15 * t**4 * mt**2
        + 6 * t**5 * mt
        + t**6
    )


@zero
def wiggle(t: float, wiggles: float = 2) -> float:
    """Swings to either side of the start and comes back: sin(`wiggles`·πt), swelling
    and fading as [there_and_back][manimgx.there_and_back] does.

    With the default 2 wiggles, it swings to 0.73 and then to −0.73.

    Args:
        t: The time, from 0 to 1.
        wiggles: How many swings, to one side or the other.

    Returns:
        The progress, 0 at the start and the end.
    """
    return there_and_back(t) * float(np.sin(wiggles * np.pi * t))


def squish_rate_func(func: RateFunc, a: float = 0.4, b: float = 0.6) -> RateFunc:
    """Squeeze a rate function into part of the time: it runs between `a` and `b`, and
    holds its ends before and after.

    Args:
        func: The rate function.
        a: When it starts, from 0 to 1.
        b: When it ends, from `a` to 1; if it is `a`, the function steps from its start to
            its end at `a`.

    Returns:
        The squeezed rate function.
    """

    def result(t: float) -> float:
        if t < a:
            return func(0.0)
        return func(1.0) if t >= b else func((t - a) / (b - a))

    return result


def not_quite_there(func: RateFunc = smooth, proportion: float = 0.7) -> RateFunc:
    """Scale a rate function so it goes only part of the way.

    Args:
        func: The rate function.
        proportion: How far it goes: its progress is scaled by this.

    Returns:
        The scaled rate function.
    """
    return lambda t: proportion * func(t)


@unit_interval
def lingering(t: float) -> float:
    """Runs evenly to the end by 0.8 of the time, then lingers there."""
    return squish_rate_func(lambda x: x, 0, 0.8)(t)


@unit_interval
def exponential_decay(t: float, half_life: float = 0.1) -> float:
    """1 − e^(−t / `half_life`), scaled to end at 1: shoots off, then closes in on the
    end, ever slower.

    With the default time constant, it reaches about 1 − 1/e ≈ 0.63 at t = 0.1.

    Args:
        t: The time, from 0 to 1.
        half_life: The time constant, as a fraction of the time.

    Returns:
        The progress, from 0 to 1.
    """
    return float(np.expm1(-t / half_life) / np.expm1(-1 / half_life))


# ── the ease family ──
@unit_interval
def ease_in_sine(t: float) -> float:
    """1 − cos(πt/2): starts slow and speeds up."""
    val: float = 1 - np.cos(t * np.pi / 2)
    return val


@unit_interval
def ease_out_sine(t: float) -> float:
    """sin(πt/2): starts fast and slows to a stop."""
    val: float = np.sin(t * np.pi / 2)
    return val


@unit_interval
def ease_in_out_sine(t: float) -> float:
    """(1 − cos(πt))/2: slow, fast, slow."""
    val: float = -(np.cos(np.pi * t) - 1) / 2
    return val


@unit_interval
def ease_in_quad(t: float) -> float:
    """t²: starts slow and speeds up."""
    return t * t


@unit_interval
def ease_out_quad(t: float) -> float:
    """1 − (1 − t)²: starts fast and slows to a stop."""
    return 1 - (1 - t) * (1 - t)


@unit_interval
def ease_in_out_quad(t: float) -> float:
    """[ease_in_quad][manimgx.ease_in_quad] up to the middle, then its mirror image:
    slow, fast, slow."""
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2


@unit_interval
def ease_in_cubic(t: float) -> float:
    """t³: starts slow and speeds up."""
    return t * t * t


@unit_interval
def ease_out_cubic(t: float) -> float:
    """1 − (1 − t)³: starts fast and slows to a stop."""
    return 1 - pow(1 - t, 3)


@unit_interval
def ease_in_out_cubic(t: float) -> float:
    """[ease_in_cubic][manimgx.ease_in_cubic] up to the middle, then its mirror image:
    slow, fast, slow."""
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


@unit_interval
def ease_in_quart(t: float) -> float:
    """t⁴: starts slow and speeds up."""
    return t * t * t * t


@unit_interval
def ease_out_quart(t: float) -> float:
    """1 − (1 − t)⁴: starts fast and slows to a stop."""
    return 1 - pow(1 - t, 4)


@unit_interval
def ease_in_out_quart(t: float) -> float:
    """[ease_in_quart][manimgx.ease_in_quart] up to the middle, then its mirror image:
    slow, fast, slow."""
    return 8 * t * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 4) / 2


@unit_interval
def ease_in_quint(t: float) -> float:
    """t⁵: starts slow and speeds up."""
    return t * t * t * t * t


@unit_interval
def ease_out_quint(t: float) -> float:
    """1 − (1 − t)⁵: starts fast and slows to a stop."""
    return 1 - pow(1 - t, 5)


@unit_interval
def ease_in_out_quint(t: float) -> float:
    """[ease_in_quint][manimgx.ease_in_quint] up to the middle, then its mirror image:
    slow, fast, slow."""
    return 16 * t * t * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 5) / 2


# Penner's exponential eases, 2^(10t − 10), jump by 2^−10 at their ends: here the exponential
# runs from 0 at 0 to 1 at 1, (2^(10t) − 1) / 1023 (written out in each: the module's functions
# are its rate functions)
@unit_interval
def ease_in_expo(t: float) -> float:
    """(2^(10t) − 1) / 1023: barely moves at first, then shoots to the end."""
    return (pow(2, 10 * t) - 1) / 1023


@unit_interval
def ease_out_expo(t: float) -> float:
    """[ease_in_expo][manimgx.ease_in_expo] turned around: shoots off, then creeps to
    the end."""
    return 1 - (pow(2, 10 - 10 * t) - 1) / 1023


@unit_interval
def ease_in_out_expo(t: float) -> float:
    """[ease_in_expo][manimgx.ease_in_expo] up to the middle, then its mirror image."""
    if t < 0.5:
        return (pow(2, 20 * t) - 1) / 2046
    return 1 - (pow(2, 20 - 20 * t) - 1) / 2046


@unit_interval
def ease_in_circ(t: float) -> float:
    """1 − √(1 − t²), a quarter circle: starts at rest and speeds up sharply."""
    return 1 - math.sqrt(1 - pow(t, 2))


@unit_interval
def ease_out_circ(t: float) -> float:
    """√(1 − (t − 1)²), a quarter circle: starts sharply and comes to rest."""
    return math.sqrt(1 - pow(t - 1, 2))


@unit_interval
def ease_in_out_circ(t: float) -> float:
    """[ease_in_circ][manimgx.ease_in_circ] up to the middle, then its mirror image."""
    return (
        (1 - math.sqrt(1 - pow(2 * t, 2))) / 2
        if t < 0.5
        else (math.sqrt(1 - pow(-2 * t + 2, 2)) + 1) / 2
    )


@unit_interval
def ease_in_back(t: float) -> float:
    """Pulls back first, to −0.1, then speeds to the end."""
    c1 = 1.70158
    c3 = c1 + 1
    return c3 * t * t * t - c1 * t * t


@unit_interval
def ease_out_back(t: float) -> float:
    """Overshoots the end, to 1.1, then settles back to it."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


@unit_interval
def ease_in_out_back(t: float) -> float:
    """Pulls back to −0.1, then overshoots to 1.1 and settles at the end."""
    c1 = 1.70158
    c2 = c1 * 1.525
    return (
        pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2) / 2
        if t < 0.5
        else (pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2
    )


@unit_interval
def ease_in_elastic(t: float) -> float:
    """Swings about the start, more and more widely (down to −0.37), then springs to the
    end: a sine under the envelope of [ease_in_expo][manimgx.ease_in_expo]."""
    return float(
        -(pow(2, 10 * t) - 1) / 1023 * np.sin((t * 10 - 10.75) * 2 * np.pi / 3)
    )


@unit_interval
def ease_out_elastic(t: float) -> float:
    """Springs past the end (to 1.37), then swings about it, less and less widely, like
    a spring: [ease_in_elastic][manimgx.ease_in_elastic] turned around."""
    return 1 - ease_in_elastic(1 - t)


@unit_interval
def ease_in_out_elastic(t: float) -> float:
    """Swings about the start, more and more widely (down to −0.12), springs across the
    middle, then swings about the end, less and less widely (up to 1.12)."""
    u = 2 * t if t < 0.5 else 2 - 2 * t  # the half's own time, from its outer end
    half = -(pow(2, 10 * u) - 1) / 1023 * np.sin((10 * u - 11.125) * 2 * np.pi / 4.5)
    return float(half / 2 if t < 0.5 else 1 - half / 2)


@unit_interval
def ease_in_bounce(t: float) -> float:
    """[ease_out_bounce][manimgx.ease_out_bounce] turned around: bounces off the start,
    higher each time (to 0.02, 0.06 and 0.25), then rises to the end."""
    return 1 - ease_out_bounce(1 - t)


@unit_interval
def ease_out_bounce(t: float) -> float:
    """Falls to the end and bounces off it like a ball: reaches it at t ≈ 0.36, then
    bounces back to 0.75, 0.94 and 0.98."""
    n1 = 7.5625
    d1 = 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        return n1 * (t - 1.5 / d1) * (t - 1.5 / d1) + 0.75
    elif t < 2.5 / d1:
        return n1 * (t - 2.25 / d1) * (t - 2.25 / d1) + 0.9375
    else:
        return n1 * (t - 2.625 / d1) * (t - 2.625 / d1) + 0.984375


@unit_interval
def ease_in_out_bounce(t: float) -> float:
    """[ease_in_bounce][manimgx.ease_in_bounce] up to the middle, then
    [ease_out_bounce][manimgx.ease_out_bounce]."""
    if t < 0.5:
        return (1 - ease_out_bounce(1 - 2 * t)) / 2
    else:
        return (1 + ease_out_bounce(2 * t - 1)) / 2

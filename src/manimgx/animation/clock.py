"""Scene time: one exact clock, and the clocks that run off it.

A frame shows the world at one instant (frame k at k/fps). An animation is evaluated at its own
window of scene time; a time-based updater gets the time its clock ran since it last stepped; a
per-frame updater re-establishes its relation. A flow (an updater whose steps compose) is exact
at any instant; any other time-based updater is simulated on the simulation clock
(`config.simulation_rate` ticks a second, plus the scene's events), so it behaves the same at
every frame rate. `speed` runs off scene time, warped by ChangeSpeed."""

from collections.abc import Callable
from fractions import Fraction
from itertools import pairwise
from math import inf, nextafter, ulp


def _rounding_cell(value: float) -> tuple[Fraction, Fraction, bool]:
    """The binary64 rounding interval, and whether its ties belong to this value."""
    magnitude = abs(value)
    exact = Fraction(magnitude)
    low = (exact + Fraction(nextafter(magnitude, -inf))) / 2
    high = exact + Fraction(ulp(magnitude)) / 2
    closed = float(low) == magnitude
    return (-high, -low, closed) if value < 0 else (low, high, closed)


def rational(value: float | Fraction) -> Fraction:
    """Recover the simplest rational that rounds to an authored float.

    A duration such as 5/6 keeps its frame boundary, while distinct floats stay distinct
    and a positive duration never becomes zero. Integers and explicit fractions are exact.
    """
    exact = Fraction(value)
    if not isinstance(value, float) or exact.denominator == 1:
        return exact
    low, high, _ = _rounding_cell(abs(value))
    # Both midpoints have larger denominators than exact itself, so excluding ties
    # cannot exclude the simplest candidate and avoids either neighbor's tie rule.
    # The continued fractions of the rounding interval share these integer parts.
    # The first integer strictly inside it gives the smallest possible denominator.
    a, b, c, d = low.numerator, low.denominator, high.numerator, high.denominator
    before, denominator = 1, 0
    while True:
        whole = a // b
        if (whole + 1) * d < c:
            denominator = (whole + 1) * denominator + before
            return Fraction(round(exact * denominator), denominator)
        before, denominator = denominator, whole * denominator + before
        a, b, c, d = d, c - whole * d, b, a - whole * b


def frame_at(time: float | Fraction, rate: Fraction, *, after: bool = False) -> int:
    """First frame at this observed instant or later (strictly later with `after`)."""
    low, high, closed = _rounding_cell(float(time))
    at = (high if after else low) * rate
    return int(at // 1 + 1 if closed == after else -(-at // 1))


now = Fraction(0)
"""The instant being computed — or, between plays, the end of the last one (where the scene's
own code runs)."""
stepping: bool = True
"""Do simulated updaters (time-based, not flows) step at `now`? At every instant — unless the
scene is simulating: then at the ticks of its simulation clock and at its events only."""
framing: bool = True
"""Do per-frame updaters run at `now`? At frames and events — not at a tick between frames: an
updater that takes no time is called once a frame, whatever else the scene simulates."""


class Clock:
    """Local time as a function of scene time: scene time, except over its warps (from `start`, for
    `duration`, covering `span` of local time along `progress`, a monotone map of [0, 1] onto
    itself). Where warps overlap, the one begun last rules while it lasts, so the clock only ever
    runs forward."""

    def __init__(self) -> None:
        self.warps: list[tuple[float, float, float, Callable[[float], float]]] = []

    def warp(
        self,
        start: float,
        duration: float,
        span: float,
        progress: Callable[[float], float],
    ) -> None:
        self.warps.append((start, duration, span, progress))
        self.warps.sort(key=lambda w: w[0])

    def at(self, t: float) -> float:
        # scene time cut at every warp's start and end; each piece runs at the pace of the
        # warp begun last among those covering it, or at scene time's own
        cuts = sorted({0.0, t, *(x for w in self.warps for x in (w[0], w[0] + w[1]))})
        local = 0.0
        for a, b in pairwise(cuts):
            if b > t:
                break
            ruling = None
            for w in self.warps:  # sorted by start: the last one covering (a, b) rules
                if w[0] <= a and b <= w[0] + w[1]:
                    ruling = w
            if ruling is None:
                local += b - a
            else:
                start, duration, span, progress = ruling
                if duration > 0:
                    local += span * (
                        progress((b - start) / duration)
                        - progress((a - start) / duration)
                    )
        return local


speed = Clock()


def reset() -> None:
    """A new scene: its clock at 0, no warps."""
    global now, stepping, framing
    now, stepping, framing = Fraction(0), True, True
    speed.warps.clear()

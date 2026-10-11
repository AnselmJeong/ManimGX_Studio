"""A clock's local time is scene time, warped where its warps say, and it only runs forward.

- With no warps it is scene time; over a warp it covers the warp's span, and outside every
  warp it runs at scene time's pace.
- However its warps overlap, it never runs backward and never jumps: where warps overlap, the
  one begun last rules while it lasts.
"""

import math
from fractions import Fraction

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from manimgx.animation import easing as rf
from manimgx.animation.clock import Clock, frame_at, rational


@given(value=st.floats(allow_nan=False, allow_infinity=False))
@example(value=math.ulp(0.0))
@example(value=-math.ulp(0.0))
@example(value=float.fromhex("0x1.fffffffffffffp+1023"))
@example(value=1.0000004191481406)
def test_rational_time_preserves_the_supplied_float(value: float) -> None:
    exact = rational(value)
    assert float(exact) == value
    assert rational(-value) == -exact
    if exact.denominator > 1:
        # Independent nearest-rational oracle: a smaller denominator cannot round-trip.
        nearer = Fraction(value).limit_denominator(exact.denominator - 1)
        assert float(nearer) != value


@given(numerator=st.integers(-10000, 10000), denominator=st.integers(1, 10000))
def test_small_rational_times_keep_their_exact_boundaries(
    numerator: int, denominator: int
) -> None:
    value = Fraction(numerator, denominator)
    assert rational(float(value)) == value
    assert rational(value) == value


@given(exponent=st.integers(-1074, 52))
def test_adjacent_times_at_a_binary_exponent_boundary_stay_ordered(
    exponent: int,
) -> None:
    value = math.ldexp(1.0, exponent)
    before, after = math.nextafter(value, -math.inf), math.nextafter(value, math.inf)
    assert rational(before) < rational(value) < rational(after)


@given(
    time=st.fractions(min_value=-1000, max_value=1000),
    rate=st.fractions(min_value=1, max_value=1000),
    after=st.booleans(),
)
@example(time=Fraction(1), rate=Fraction(2**54), after=False)
@example(time=Fraction(1) + Fraction(1, 2**53), rate=Fraction(2**54), after=True)
@example(time=Fraction(1) + Fraction(3, 2**53), rate=Fraction(2**54), after=False)
def test_sampling_chooses_the_first_representable_instant_not_before_the_event(
    time: Fraction, rate: Fraction, after: bool
) -> None:
    frame = frame_at(time, rate, after=after)
    before, here = float((frame - 1) / rate), float(frame / rate)
    if after:
        assert before <= float(time) < here
    else:
        assert before < float(time) <= here


# monotone maps of [0, 1] onto itself, of bounded slope (at most 10)
PROGRESSES = [rf.linear, rf.smooth, rf.rush_into, rf.rush_from, rf.ease_out_quad, rf.double_smooth,
              rf.ease_in_sine, rf.ease_out_sine, rf.ease_in_out_cubic, rf.ease_in_expo]  # fmt: skip

Warp = tuple[float, float, float, rf.RateFunction]
warps = st.tuples(
    st.floats(0, 5), st.floats(0.05, 3), st.floats(0, 3), st.sampled_from(PROGRESSES)
)
times = st.floats(0, 12)


def clock(*ws: Warp) -> Clock:
    c = Clock()
    for w in ws:
        c.warp(*w)
    return c


@given(t=times)
def test_without_warps_it_is_scene_time(t: float) -> None:
    assert Clock().at(t) == t


@given(w=warps, t=times)
def test_over_a_warp_it_covers_the_warps_span(w: Warp, t: float) -> None:
    start, duration, span, progress = w
    local = clock(w).at(t)
    if t <= start:
        assert local == pytest.approx(t)
    elif t >= start + duration:
        assert local == pytest.approx(t - duration + span)
    else:
        assert local == pytest.approx(start + span * progress((t - start) / duration))


@given(ws=st.lists(warps, max_size=4), a=times, b=times)
def test_it_never_runs_backward(ws: list[Warp], a: float, b: float) -> None:
    a, b = sorted((a, b))
    c = clock(*ws)
    assert c.at(a) <= c.at(b) + 1e-12


@given(ws=st.lists(warps, max_size=4), t=times)
def test_it_never_jumps(ws: list[Warp], t: float) -> None:
    c, h = clock(*ws), 1e-7
    pace = max([1.0, *(10 * span / duration for _, duration, span, _ in ws)])
    assert abs(c.at(t + h) - c.at(t)) <= pace * h + 1e-12


@given(first=warps, second=warps, a=st.floats(0, 1), b=st.floats(0, 1))
def test_where_warps_overlap_the_one_begun_last_rules(
    first: Warp, second: Warp, a: float, b: float
) -> None:
    s1, d1, span1, p1 = first
    _, _, span2, p2 = second
    s2 = s1 + d1 / 4  # the second begins inside the first, and ends before it
    d2 = d1 / 2
    c = clock(first, (s2, d2, span2, p2))
    a, b = sorted((a, b))
    inside = c.at(s2 + b * d2) - c.at(s2 + a * d2)
    assert inside == pytest.approx(span2 * (p2(b) - p2(a)), abs=1e-9)
    # after it, the first rules again, at its own pace
    after = c.at(s1 + d1) - c.at(s2 + d2)
    assert after == pytest.approx(span1 * (p1(1.0) - p1(0.75)), abs=1e-9)

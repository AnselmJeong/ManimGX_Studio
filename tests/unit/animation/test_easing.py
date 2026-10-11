"""Rate functions map an animation's time, from 0 to 1, to its progress.

- Each starts exactly at 0 and ends exactly at 1 (the there-and-back family at 0), and holds
  its ends outside [0, 1]: an animation lands exactly where it is going.
- Each is continuous, the exponential and elastic eases at their ends too; the designated
  monotone functions never go backward.
- An ease-out is its ease-in turned around, and an ease-in-out runs its ease-in at double
  speed up to the middle: the thirty formulas are one family.
- The extremes their docstrings give are their extremes.
- `squish_rate_func` runs a rate function in a window of the time and holds its ends outside it.
- `not_quite_there` scales a rate function to part of the way: seven tenths, unless told.
"""

from collections.abc import Callable

import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from tests.strategies import MONOTONE, RATE_FUNCTIONS

from manimgx.animation import easing as rf

RETURNING = {rf.there_and_back, rf.there_and_back_with_pause, rf.wiggle}
KINDS = ("sine", "quad", "cubic", "quart", "quint", "expo", "circ", "back", "elastic")
MIRRORED = ("sine", "quad", "cubic", "quart", "quint", "expo", "circ")
by_name = pytest.mark.parametrize("f", RATE_FUNCTIONS, ids=lambda f: f.__name__)
grid = np.linspace(0, 1, 100_001)


class TestEveryRateFunction:
    @by_name
    def test_it_starts_and_ends_exactly(self, f: Callable[[float], float]) -> None:
        assert f(0.0) == 0
        assert f(1.0) == (0 if f in RETURNING else 1)

    @by_name
    @given(beyond=st.floats(0, 1e6, exclude_min=True))
    def test_it_holds_its_ends_outside_the_unit_interval(
        self, f: Callable[[float], float], beyond: float
    ) -> None:
        assert f(-beyond) == f(0.0)
        assert f(1 + beyond) == f(1.0)

    @by_name
    @given(t=st.floats(0, 1 - 1e-10))
    def test_it_is_continuous(self, f: Callable[[float], float], t: float) -> None:
        # a quarter circle rises as √h at its vertical ends; the steepest of the rest
        # climbs 10 per unit of time (exponential_decay at 0)
        h = 1e-10
        assert abs(f(t + h) - f(t)) <= 2 * h**0.5 + 40 * h


@pytest.mark.parametrize("f", MONOTONE, ids=lambda f: f.__name__)
def test_the_easing_family_never_goes_back(f: Callable[[float], float]) -> None:
    values = np.array([f(t) for t in grid[::10]])
    assert np.all(np.diff(values) >= -1e-15)


@pytest.mark.parametrize("kind", KINDS)
@given(t=st.floats(0, 1))
def test_an_ease_out_is_its_ease_in_turned_around(kind: str, t: float) -> None:
    ease_in, ease_out = getattr(rf, f"ease_in_{kind}"), getattr(rf, f"ease_out_{kind}")
    assert ease_out(t) == pytest.approx(1 - ease_in(1 - t), abs=1e-12)


@pytest.mark.parametrize("kind", MIRRORED)
@given(t=st.floats(0, 1))
def test_an_ease_in_out_runs_its_ease_in_at_double_speed(kind: str, t: float) -> None:
    ease_in, both = getattr(rf, f"ease_in_{kind}"), getattr(rf, f"ease_in_out_{kind}")
    expected = ease_in(2 * t) / 2 if t < 0.5 else 1 - ease_in(2 - 2 * t) / 2
    assert both(t) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize(
    ("f", "lowest", "highest"),
    [
        (rf.running_start, -0.18, 1),
        (rf.wiggle, -0.73, 0.73),
        (rf.ease_in_back, -0.10, 1),
        (rf.ease_out_back, 0, 1.10),
        (rf.ease_in_out_back, -0.10, 1.10),
        (rf.ease_in_elastic, -0.37, 1),
        (rf.ease_out_elastic, 0, 1.37),
        (rf.ease_in_out_elastic, -0.12, 1.12),
    ],
    ids=lambda v: getattr(v, "__name__", ""),
)
def test_the_extremes_its_docstring_gives_are_its_extremes(
    f: Callable[[float], float], lowest: float, highest: float
) -> None:
    values = np.array([f(t) for t in grid])
    assert round(values.min(), 2) == lowest
    assert round(values.max(), 2) == highest


class TestSquishRateFunc:
    @given(a=st.floats(0, 1), b=st.floats(0, 1), s=st.floats(0, 1))
    def test_it_runs_the_function_through_its_window(
        self, a: float, b: float, s: float
    ) -> None:
        a, b = min(a, b), max(a, b)
        assume(b - a > 1e-6)
        squished = rf.squish_rate_func(rf.smooth, a, b)
        assert squished(a + s * (b - a)) == pytest.approx(rf.smooth(s), abs=1e-9)

    @given(a=st.floats(0, 1), b=st.floats(0, 1), t=st.floats(-1, 2))
    def test_it_holds_its_ends_outside_its_window(
        self, a: float, b: float, t: float
    ) -> None:
        a, b = min(a, b), max(a, b)
        assume(t < a or t >= b)
        assert rf.squish_rate_func(rf.smooth, a, b)(t) == (0 if t < a else 1)

    def test_its_window_is_the_middle_fifth_unless_given(self) -> None:
        squished = rf.squish_rate_func(rf.linear)
        assert [squished(t) for t in (0.3, 0.4, 0.5, 0.6)] == pytest.approx(
            [0, 0, 0.5, 1]
        )

    def test_an_empty_window_is_a_step(self) -> None:
        squished = rf.squish_rate_func(rf.smooth, 0.3, 0.3)
        assert [squished(t) for t in (0.0, 0.29, 0.3, 0.8)] == [0, 0, 1, 1]


@given(t=st.floats(0, 1), proportion=st.none() | st.floats(0, 1))
def test_not_quite_there_goes_part_of_the_way(
    t: float, proportion: float | None
) -> None:
    """Seven tenths of the way unless told."""
    scaled = (
        rf.not_quite_there(rf.linear)
        if proportion is None
        else rf.not_quite_there(rf.linear, proportion)
    )
    assert scaled(t) == (0.7 if proportion is None else proportion) * t

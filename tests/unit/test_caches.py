"""What an object holds, compared: an array assigned again is the one held when their bits are.

- `unchanged(value, held)` is bit equality: true exactly when `held` is an array of the
  value's shape and type with the value's bytes, however either is laid out in memory. So a
  NaN is itself and -0.0 is not 0.0, the same bits read as another type are not the same
  array, and nothing but an array is ever what is held. An array past 1,024 items is probed
  at 16 items first, which changes no answer (an item between the probes counts too).
"""

from collections.abc import Callable

import numpy as np
from hypothesis import example, given
from hypothesis import strategies as st
from tests.strategies import arrays

from manimgx.caches import unchanged

# compared whole, whole, and probed first (400 × 3 is past 1,024 items)
held_arrays = st.sampled_from([(7, 3), (40, 3), (400, 3)]).flatmap(arrays)


def one_changed(held: np.ndarray, at: int, by: float) -> np.ndarray:
    changed = held.copy()
    changed.reshape(-1)[at % held.size] += by
    return changed


# each: (the value assigned, what is held), from a held array and an item and an amount
VARIANTS: dict[str, Callable[[np.ndarray, int, float], tuple[np.ndarray, object]]] = {
    "itself": lambda h, at, by: (h, h),
    "a copy": lambda h, at, by: (h.copy(), h),
    "Fortran order": lambda h, at, by: (np.asfortranarray(h), h),
    "a transposed copy": lambda h, at, by: (h.T.copy().T, h),
    "one item changed": lambda h, at, by: (one_changed(h, at, by), h),
    "another shape": lambda h, at, by: (h.reshape(3, -1), h),
    "one row fewer": lambda h, at, by: (h[:-1], h),
    "another type": lambda h, at, by: (h.astype(np.float32), h),
    "the same bits as integers": lambda h, at, by: (h.view(np.int64), h),
    "-0.0 for 0.0": lambda h, at, by: (-np.zeros_like(h), np.zeros_like(h)),
    "NaN for NaN": lambda h, at, by: (np.full_like(h, np.nan), np.full_like(h, np.nan)),
    "a list held": lambda h, at, by: (h.copy(), h.tolist()),
    "nothing held": lambda h, at, by: (h.copy(), None),
}


@given(
    held=held_arrays,
    how=st.sampled_from(sorted(VARIANTS)),
    at=st.integers(0),
    by=st.floats(0.5, 10.0),
)
@example(held=np.zeros(3000), how="-0.0 for 0.0", at=0, by=1.0)
@example(held=np.zeros(3000), how="NaN for NaN", at=0, by=1.0)
@example(
    held=np.zeros((400, 3)), how="one item changed", at=1, by=1.0
)  # not one probed
def test_unchanged_is_bit_equality(
    held: np.ndarray, how: str, at: int, by: float
) -> None:
    value, kept = VARIANTS[how](held, at, by)
    bits = (
        isinstance(kept, np.ndarray)
        and value.shape == kept.shape
        and value.dtype == kept.dtype
        and value.tobytes() == kept.tobytes()
    )
    assert unchanged(value, kept) == bits

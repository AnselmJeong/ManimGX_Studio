"""What ManimGX remembers: values it has worked out once, kept to be read again.

Every such memory is a `Memo`: bounded (past its limit it forgets everything at once) and
invisible (forgetting changes no result, only the time one takes). `clear` forgets them all,
as the tests do to show that nothing depends on what is remembered.

What an object holds is remembered the same way: a value assigned equal to the one it holds
(`unchanged`) keeps the one held, and so all that was derived from it — an upload, normals, a
frame's record."""

from collections.abc import Callable, Hashable

import numpy as np

_FORGETTERS: list[Callable[[], None]] = []


def unchanged(value: np.ndarray, held: object) -> bool:
    """Is `value` the array `held`, bit for bit (so that keeping the one held changes nothing)?
    An array of up to 1,024 items is compared whole; a bigger one at 16 items spread over it
    first, so that one that changed is told at once."""
    if value is held:
        return True
    if not (
        isinstance(held, np.ndarray)
        and value.shape == held.shape
        and value.dtype == held.dtype
    ):
        return False
    if value.size <= 1024:
        return value.tobytes() == held.tobytes()
    bits = f"u{value.itemsize}"  # the items' bits, compared as unsigned integers
    items, kept = value.reshape(-1).view(bits), held.reshape(-1).view(bits)
    step = len(items) // 16
    return bool(
        np.array_equal(items[::step], kept[::step]) and np.array_equal(items, kept)
    )


class Memo[K: Hashable, V](dict[K, V]):
    """A value for each key, worked out once: `memo.recall(key, make)`.

    Args:
        limit: How many values it keeps; past it, it forgets them all.
    """

    __slots__ = ("limit",)

    def __init__(self, limit: int) -> None:
        super().__init__()
        self.limit = limit
        _FORGETTERS.append(self.clear)

    def recall(self, key: K, make: Callable[[], V]) -> V:
        """The value for `key`: remembered, or made now by `make` and remembered."""
        value = self.get(key)
        return self.keep(key, make()) if value is None else value

    def keep(self, key: K, value: V) -> V:
        """Remember `value` for `key` (forgetting everything first, past the limit)."""
        if len(self) >= self.limit:
            self.clear()
        self[key] = value
        return value


def forgets[F: Callable[..., object]](cached: F) -> F:
    """Have `clear` forget a function's own cache too (a `functools.cache`)."""
    _FORGETTERS.append(getattr(cached, "cache_clear"))  # noqa: B009
    return cached


def clear() -> None:
    """Forget everything remembered."""
    for forget in _FORGETTERS:
        forget()

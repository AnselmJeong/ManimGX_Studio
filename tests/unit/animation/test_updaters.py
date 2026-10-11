"""An updater acts on the mobject it runs on: a replica of an updating mobject is a mobject of
its own.

- For every built-in updater (`always_redraw`, `always`, `f_always`, `always_shift`,
  `always_rotate`, `turn_animation_into_updater`, an `AnimatedBoundary`'s, a `TracedPath`'s) and
  a method of the mobject's own: a replica (a copy, a target, a saved state, or a mobject that
  took the updaters over with `match_updaters`) runs them on itself, and leaves its original
  as it was.
- A replica does not keep its original alive.
"""

import gc
import weakref
from collections.abc import Callable

import numpy as np
import pytest
from tests.oracles import look

import manimgx as m

type Updating = tuple[m.Mobject, Callable[[], object]]


def redrawn() -> Updating:
    x = m.ValueTracker(0.0)
    return m.always_redraw(lambda: m.Dot([x.get_value(), 0, 0])), lambda: x.set_value(1)


def following() -> Updating:
    dot = m.Dot(m.RIGHT)
    return m.always(m.Square().next_to, dot, m.UP), lambda: dot.shift(m.RIGHT)


def tracking() -> Updating:
    x = m.ValueTracker(0.0)
    return m.f_always(m.Square().set_x, x.get_value), lambda: x.set_value(1)


def traced() -> Updating:
    dot = m.Dot()
    return m.TracedPath(lambda: dot.get_center()), lambda: dot.shift(m.RIGHT)


class Stepping(m.Square):
    """A square whose updater is a method of its own, acting on itself."""

    def step(self, mob: m.Mobject, dt: float) -> None:
        self.shift(dt * m.RIGHT)


def stepping() -> Updating:
    square = Stepping()
    return square.add_updater(square.step), lambda: None


# an updating mobject, and a change of what its updaters read
UPDATING: dict[str, Callable[[], Updating]] = {
    "always_redraw": redrawn,
    "always": following,
    "f_always": tracking,
    "always_shift": lambda: (m.always_shift(m.Square(), m.RIGHT, 1.0), lambda: None),
    "always_rotate": lambda: (m.always_rotate(m.Square()), lambda: None),
    "turn_animation_into_updater": lambda: (
        m.turn_animation_into_updater(m.Rotate(m.Square(), 1.0)),
        lambda: None,
    ),
    "AnimatedBoundary": lambda: (m.AnimatedBoundary(m.Square()), lambda: None),
    "TracedPath": traced,
    "a method of its own": stepping,
}
REPLICAS: dict[str, Callable[[m.Mobject], m.Mobject | None]] = {
    "copy": lambda mob: mob.copy(),
    "target": lambda mob: mob.generate_target(),
    "saved state": lambda mob: mob.save_state().saved_state,
    "match_updaters": lambda mob: mob.copy().clear_updaters().match_updaters(mob),
}


def cases(replicas: list[str]) -> list[tuple[str, str]]:
    return [
        (name, replica)
        for name in UPDATING
        for replica in replicas
        # match_updaters gives the same functions: a user's method stays its mobject's
        if not (name == "a method of its own" and replica == "match_updaters")
    ]


@pytest.mark.parametrize(("name", "replica"), cases(list(REPLICAS)))
def test_a_replica_updates_itself_and_leaves_its_original(
    name: str, replica: str
) -> None:
    original, change = UPDATING[name]()
    clone = REPLICAS[replica](original)
    assert clone is not None
    before, start = look(original), look(clone)
    change()
    clone.update(0.5)
    assert look(clone) != start, "the replica's updaters did not run on it"
    assert look(original) == before


@pytest.mark.parametrize(("name", "replica"), cases(["copy", "match_updaters"]))
def test_a_replica_does_not_keep_its_original_alive(name: str, replica: str) -> None:
    original, change = UPDATING[name]()
    clone = REPLICAS[replica](original)
    assert clone is not None
    alive = weakref.ref(original)
    del original
    gc.collect()
    assert alive() is None
    change()
    clone.update(0.25)
    assert np.isfinite(clone.get_center()).all()

"""What a run asks of ManimGX, counted: work, which is the same on every machine, where time is
not.

`count(fn)` runs `fn` and counts, in ManimGX's own code:

- `calls`, the Python functions run, and `loops`, the loops' iterations (a jump back), with
  `sys.monitoring`: the interpreter's work;
- `points`, the points computed from a geometry's pieces (`Blend.points`): the numpy work a
  path or mesh costs to read;
- `hashed`, the bytes hashed (`digest`) to name shapes and uploads;
- `uploaded`, the bytes handed to the engine to keep: shapes, meshes, rows, textures.

Counts are exact and the same on every system; `loops` also depends on the bytecode, so on
the Python version. Counting slows a run down by about half.

    python -m tests.benchmarks.work OUT.json ARGS…

runs the command line `manimgx ARGS…` in this process, counting, and writes its work to OUT.json
(what the timed benchmarks show beside a change).
"""

import importlib
import json
import runpy
import sys
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from types import CodeType
from typing import TYPE_CHECKING

import manimgx

# The compiler remains beside Film in either compared package layout.
feed = importlib.import_module(manimgx.Film.__module__.removesuffix(".film") + ".feed")
if TYPE_CHECKING:
    from manimgx.drawing.geometry import Blend
else:
    Blend = feed.Blend

_PACKAGE = Path(manimgx.__file__).parent
_ROOTS = (str(_PACKAGE), str(_PACKAGE.resolve()))
"""Where manimgx's code is, as its code objects name it: the path it was imported from, and
that path resolved (they differ under a link, /tmp's on macOS)."""
_UPLOADS = (
    "add_path",
    "grow_path",
    "add_points",
    "add_mesh",
    "add_rows",
    "add_texture",
)


@dataclass(frozen=True, slots=True)
class Work:
    """Counts of what a run did (see the module's docstring)."""

    calls: int = 0
    loops: int = 0
    points: int = 0
    hashed: int = 0
    uploaded: int = 0

    def __add__(self, other: "Work") -> "Work":
        return Work(
            *(getattr(self, f.name) + getattr(other, f.name) for f in fields(self))
        )

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class _Tally:
    def __init__(self) -> None:
        self.calls = self.loops = self.points = self.hashed = self.uploaded = 0

    def work(self) -> Work:
        return Work(self.calls, self.loops, self.points, self.hashed, self.uploaded)


def count[T](fn: Callable[[], T], strict: bool = True) -> tuple[T, Work]:
    """Run `fn`; its result and the work it did. With `strict`, a function counted that
    this ManimGX lacks (renamed, say) is an error; else it counts nothing (an older ManimGX,
    compared with this one)."""
    with counting(strict) as tally:
        result = fn()
    return result, tally.work()


@contextmanager
def counting(strict: bool = True) -> Iterator[_Tally]:
    """Count the work done inside the block (read `.work()` after it)."""
    tally = _Tally()
    with ExitStack() as stack:
        _count_python(tally, stack)
        _count_geometry(tally, stack, strict)
        _count_uploads(tally, stack, strict)
        yield tally


def _count_python(tally: _Tally, stack: ExitStack) -> None:
    monitoring = sys.monitoring
    events = monitoring.events
    tool = next(
        t for t in (2, 3, 4) if monitoring.get_tool(t) is None
    )  # a profiler's id
    monitoring.use_tool_id(tool, "manimgx benchmarks")
    disable = monitoring.DISABLE

    def started(code: CodeType, _offset: int) -> object:
        if not code.co_filename.startswith(_ROOTS):
            return disable  # never asked again for this code
        tally.calls += 1
        return None

    def jumped(code: CodeType, source: int, destination: int) -> object:
        if not code.co_filename.startswith(_ROOTS):
            return disable
        if destination <= source:  # back to a loop's head
            tally.loops += 1
        return None

    monitoring.register_callback(tool, events.PY_START, started)
    monitoring.register_callback(tool, events.JUMP, jumped)
    monitoring.set_events(tool, events.PY_START | events.JUMP)

    def stop() -> None:
        monitoring.set_events(tool, 0)
        monitoring.register_callback(tool, events.PY_START, None)
        monitoring.register_callback(tool, events.JUMP, None)
        monitoring.free_tool_id(tool)
        monitoring.restart_events()  # what was disabled for this tool runs again

    stack.callback(stop)


def _counted(owner: object, name: str, strict: bool) -> object | None:
    found = getattr(owner, name, None)
    if found is None and strict:
        msg = f"{owner!r} has no {name} to count: tests/benchmarks/work.py must follow"
        raise AttributeError(msg)
    return found


def _count_geometry(tally: _Tally, stack: ExitStack, strict: bool) -> None:
    points = _counted(Blend, "points", strict)
    if callable(points):

        def counted_points(self: Blend) -> object:
            if getattr(self, "_points", None) is None:  # computed now
                tally.points += self.n
            return points(self)

        stack.enter_context(_patched(Blend, "points", counted_points))
    geometry = sys.modules[
        Blend.__module__
    ]  # the compared tree's owner, wherever it lives
    for owner in (geometry, feed):  # what names shapes, and what names uploads
        digest = _counted(owner, "digest", strict)
        if callable(digest):
            stack.enter_context(_patched(owner, "digest", _hashing(tally, digest)))


def _hashing(tally: _Tally, digest: Callable[..., object]) -> Callable[..., object]:
    def counted_digest(*parts: bytes) -> object:
        tally.hashed += sum(len(p) for p in parts)
        return digest(*parts)

    return counted_digest


def _count_uploads(tally: _Tally, stack: ExitStack, strict: bool) -> None:
    player = _counted(feed, "Player", strict)
    if not callable(player):
        return

    class Counted:
        """Stands for the engine's Player, counting the bytes each upload hands it."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            self._player = player(*args, **kwargs)

        def __getattr__(self, name: str) -> object:
            attribute = getattr(self._player, name)
            if name not in _UPLOADS or not callable(attribute):
                return attribute

            def upload(*args: object, **kwargs: object) -> object:
                given = (*args, *kwargs.values())
                tally.uploaded += sum(_size(a) for a in given)
                return attribute(*args, **kwargs)

            return upload

    stack.enter_context(_patched(feed, "Player", Counted))


def _size(value: object) -> int:
    if isinstance(value, bytes | bytearray | memoryview):
        return len(value)
    nbytes = getattr(value, "nbytes", None)
    return nbytes if isinstance(nbytes, int) else 0


@contextmanager
def _patched(owner: object, name: str, value: object) -> Iterator[None]:
    saved = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        setattr(owner, name, saved)


def main() -> None:
    out, *args = sys.argv[1:]
    sys.argv = ["manimgx", *args]
    with counting(strict=False) as tally:  # the ManimGX compared with may lack a count
        try:
            runpy.run_module("manimgx", run_name="__main__", alter_sys=True)
        except SystemExit as done:
            if done.code:
                raise
    Path(out).write_text(json.dumps(tally.work().as_dict()), encoding="utf-8")


if __name__ == "__main__":
    main()

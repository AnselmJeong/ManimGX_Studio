"""`manimgx preview`: the scene recorded as a take and sent to a window, which plays it; made
again when its file is saved, the new take after the old; an error, as a note between takes; a
scene the viewer asks for, run next; closing the window ends it. Driven as its user does — the
command, then the file edited — with the window a stand-in that keeps what it is sent.
"""

import importlib
import json
import queue
import struct
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Self

import pytest

from manimgx import _engine
from manimgx.rendering.film import Cut

# the module: `manimgx.cli.preview` is also the command's name in its package
command = importlib.import_module("manimgx.cli.preview")
START, NOTE, END = 14, 9, 12

SCENE = """
import manimgx as m


class Dot(m.Scene):
    def construct(self):
        self.play(m.Create(m.Circle(){extra}))


class Other(m.Scene):
    def construct(self):
        self.wait(0.5)
"""


class Viewer:
    """A window as `manimgx preview` uses one: what it is sent, read as messages (op, fields);
    a scene its viewer asks for; its viewer closing it."""

    def __init__(self, title: str, *, time: float = 0.0) -> None:
        self.buffer = b""
        self.seen: list[tuple[int, bytes]] = []
        self.wants: queue.Queue[str] = queue.Queue()
        self.closed = threading.Event()
        self.failure: str | None = None
        self.lock = threading.Lock()

    def __call__(self, data: bytes) -> None:
        if self.closed.is_set():
            raise Cut
        with self.lock:
            self.buffer += data
            while len(self.buffer) >= 4:
                (n,) = struct.unpack_from("<I", self.buffer)
                if len(self.buffer) < 4 + n:
                    break
                self.seen.append((self.buffer[4], self.buffer[5 : 4 + n]))
                self.buffer = self.buffer[4 + n :]

    def scenes(self, names: list[str], playing: str) -> None:
        self(_engine.note(json.dumps({"scenes": names, "scene": playing})))

    def failed(self, error: BaseException, trace: str, line: int | None = None) -> None:
        fault = {"type": type(error).__name__, "trace": trace, "line": line}
        self(_engine.note(json.dumps({"error": fault})))

    @property
    def open(self) -> bool:
        return not self.closed.is_set()

    def asked(self) -> str | None:
        return None if self.wants.empty() else self.wants.get()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.closed.set()

    def notes(self) -> list[dict[str, object]]:
        with self.lock:
            return [json.loads(fields[4:]) for op, fields in self.seen if op == NOTE]

    def until(
        self, wanted: str, count: int = 1, timeout: float = 60.0
    ) -> dict[str, object]:
        """Wait until the `count`th note with key `wanted`; return it."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            found = [n for n in self.notes() if wanted in n]
            if len(found) >= count:
                return found[count - 1]
            time.sleep(0.01)
        raise TimeoutError(f"no {wanted!r} note #{count}")

    def ended(self, count: int = 1, timeout: float = 60.0) -> None:
        """Wait until the `count`th take ends (its END message)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self.lock:
                if sum(op == END for op, _ in self.seen) >= count:
                    return
            time.sleep(0.01)
        raise TimeoutError(f"take #{count} never ended")

    def starts(self) -> int:
        with self.lock:
            return sum(op == START for op, _ in self.seen)


SLOW = """
import time

import manimgx as m


class Slow(m.Scene):
    def construct(self):
        for _ in range(40):
            time.sleep(0.1)  # a scene that takes its time: four seconds
            self.play(m.Create(m.Circle(){extra}), run_time=0.1)
"""


@pytest.fixture(params=[SCENE])
def previewed(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[Viewer, Path]]:
    """`manimgx preview scene.py` running, its window the stand-in: the window, the file."""
    scene = tmp_path / "scene.py"
    scene.write_text(request.param.format(extra=""), encoding="utf-8")
    windows: list[Viewer] = []

    def window(title: str, *, time: float = 0.0) -> Viewer:
        windows.append(Viewer(title, time=time))
        return windows[-1]

    monkeypatch.setattr(command, "Window", window)
    running = threading.Thread(
        target=command.preview, args=(scene, None, 0.0, None, None), daemon=True
    )
    running.start()
    while not windows:
        time.sleep(0.01)
    yield windows[0], scene
    windows[0].closed.set()
    running.join(10)
    assert not running.is_alive(), "closing the window ends the preview"


def test_a_saved_edit_sends_a_new_take_and_a_mistake_a_note(
    previewed: tuple[Viewer, Path],
) -> None:
    window, scene = previewed
    assert window.until("scenes") == {"scenes": ["Dot", "Other"], "scene": "Dot"}
    window.ended()
    assert window.starts() == 1
    scene.write_text(SCENE.format(extra=", run_time=2"), encoding="utf-8")
    window.ended(2)
    assert window.starts() == 2
    scene.write_text(SCENE.format(extra=".no_such_method()"), encoding="utf-8")
    error = window.until("error")["error"]
    assert isinstance(error, dict)
    assert error["type"] == "AttributeError"
    assert error["line"] == 7


def test_a_scene_the_viewer_asks_for_runs_next(previewed: tuple[Viewer, Path]) -> None:
    window, _ = previewed
    window.ended()
    window.wants.put("Other")
    assert window.until("scenes", 2) == {"scenes": ["Dot", "Other"], "scene": "Other"}
    window.ended(2)


@pytest.mark.parametrize("previewed", [SLOW], indirect=True)
def test_a_save_cuts_the_run_it_makes_out_of_date(
    previewed: tuple[Viewer, Path],
) -> None:
    window, scene = previewed
    window.until("scenes")
    time.sleep(0.5)  # well into the run's four seconds
    saved = time.monotonic()
    scene.write_text(SLOW.format(extra=".set_color(m.RED)"), encoding="utf-8")
    while window.starts() < 2 and time.monotonic() - saved < 10:
        time.sleep(0.01)
    assert time.monotonic() - saved < 1.5  # at once, not once the old run was done
    with window.lock:
        ops = [op for op, _ in window.seen]
    first = ops[: ops.index(START, 1)]
    assert END not in first  # the old take was cut short, not ended

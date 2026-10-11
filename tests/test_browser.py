"""The browser worker's Python source lifetime, exercised by the real Python interpreter."""

import linecache
import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

Run = Callable[[int, str, str | None, Callable[[bytes], None], list[str]], str | None]
Drop = Callable[[int], None]


@pytest.fixture
def runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[Run, Drop]]:
    ffi = ModuleType("pyodide.ffi")
    ffi.__dict__["to_js"] = lambda data: data
    monkeypatch.setitem(sys.modules, "pyodide.ffi", ffi)
    # This is the actual Python program shipped inside the browser worker. Only Pyodide's
    # byte transport and its virtual filesystem root differ from the native interpreter.
    source = (
        Path("browser/src/director.ts")
        .read_text(encoding="utf-8")
        .split("const RUNNER = `\n", 1)[1]
    )
    module = ModuleType("browser_runner")
    exec(source.split("\n`;", 1)[0], module.__dict__)
    module.__dict__["FILMS"] = tmp_path
    run = cast(Run, module.__dict__["run"])
    drop = cast(Drop, module.__dict__["drop"])
    previous = sys.modules.get("scene")
    try:
        yield run, drop
    finally:
        for directory in tmp_path.iterdir():
            if directory.is_dir():
                drop(int(directory.name))
        if previous is not None:
            sys.modules["scene"] = previous


SCENE = """
from pathlib import Path
from manimgx import Scene

class Film(Scene):
    def render(self, *, take):
        path = Path(__file__).with_name("cache.txt")
        with path.open("a", encoding="utf-8") as stream:
            stream.write("one")
        take(b"one")
"""


def test_film_drop_owns_its_source_cache_and_module(
    runner: tuple[Run, Drop], tmp_path: Path
) -> None:
    run, drop = runner
    out: list[bytes] = []
    assert run(1, SCENE, None, out.append, []) is None
    assert out[-1] == b"one"
    first = tmp_path / "1" / "scene.py"
    assert linecache.getline(str(first), 2) == "from pathlib import Path\n"
    assert run(2, SCENE, None, out.append, []) is None
    second = sys.modules["scene"]
    drop(1)
    drop(1)  # a repeated detach does not own any new work
    assert not first.parent.exists()
    assert str(first) not in linecache.cache
    assert sys.modules["scene"] is second
    assert (tmp_path / "2" / "cache.txt").read_text(encoding="utf-8") == "one"
    drop(2)
    assert not (tmp_path / "2").exists()
    assert "scene" not in sys.modules


def test_same_film_edits_preserve_files_and_execute_the_supplied_source(
    runner: tuple[Run, Drop], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run, _ = runner
    write_text = Path.write_text

    def write(path: Path, source: str, *, encoding: str) -> int:
        size = write_text(path, source, encoding=encoding)
        # Browser edits routinely have the same length and land within one filesystem clock
        # tick. Python's timestamp bytecode cache must not substitute the previous source.
        os.utime(path, (1_700_000_000, 1_700_000_000))
        return size

    monkeypatch.setattr(Path, "write_text", write)
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    out: list[bytes] = []
    run(1, SCENE, None, out.append, [])
    assert out[-1] == b"one"
    run(1, SCENE.replace("one", "two"), None, out.append, [])
    assert out[-1] == b"two"
    assert (tmp_path / "1" / "cache.txt").read_text(encoding="utf-8") == "onetwo"


def test_failed_and_retrying_films_release_their_source_on_drop(
    runner: tuple[Run, Drop], tmp_path: Path
) -> None:
    run, drop = runner
    out: list[bytes] = []
    assert run(1, "raise ValueError('bad scene')", None, out.append, []) is None
    assert out
    assert run(
        2, "import nonexistent_browser_scene_dependency", None, out.append, []
    ) == ("nonexistent_browser_scene_dependency")
    for film in [1, 2]:
        assert (tmp_path / str(film) / "scene.py").is_file()
        drop(film)
        assert not (tmp_path / str(film)).exists()

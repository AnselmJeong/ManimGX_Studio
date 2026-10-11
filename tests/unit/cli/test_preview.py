"""Each preview generation owns its author modules and preserves its hosting process."""

import importlib
import os
import py_compile
import sys
from pathlib import Path
from types import ModuleType
from typing import cast
from unittest.mock import Mock

import pytest

from manimgx.cli.preview import News, imports
from manimgx.cli.scenes import load
from manimgx.rendering.window import Window


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_same_timestamp_helper_edits_bypass_but_preserve_existing_bytecode(
    tmp_path: Path,
) -> None:
    entry, helper = tmp_path / "entry.py", tmp_path / "nearby.py"
    write(entry, "from nearby import value\n")
    write(helper, "value = 'one'\n")
    stamp = helper.stat()
    cached = py_compile.compile(str(helper), doraise=True)
    assert cached is not None
    bytecode = Path(cached)
    original = bytecode.read_bytes()
    before = sys.meta_path.copy(), sys.path.copy()
    for value in ("two", "six"):
        write(helper, f"value = '{value}'\n")
        os.utime(helper, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with imports(entry) as source:
            assert load(entry).value == value
        assert source.files == {entry, helper}
        assert "nearby" not in sys.modules
        assert "entry" not in sys.modules
        assert bytecode.read_bytes() == original
        assert (sys.meta_path, sys.path) == before


def test_relative_package_imports_use_current_encoded_source_and_resources(
    tmp_path: Path,
) -> None:
    entry = tmp_path / "entry.py"
    write(entry, "from own_package import value\n")
    write(tmp_path / "own_package/__init__.py", "from .part import value\n")
    part = tmp_path / "own_package/part.py"
    part.write_bytes(
        b"# coding: latin-1\nfrom importlib.resources import files\n"
        b"value = 'caf\xe9' + files(__package__).joinpath('note.txt').read_text(encoding='utf-8')\n"
    )
    write(tmp_path / "own_package/note.txt", "!")
    with imports(entry) as source:
        assert load(entry).value == "café!"
    assert part in source.files
    assert not (tmp_path / "own_package/__pycache__").exists()
    assert "own_package" not in sys.modules
    assert "own_package.part" not in sys.modules
    entry.write_bytes(b"\xef\xbb\xbfvalue = 'bom'\n")
    with imports(entry):
        assert load(entry).value == "bom"


@pytest.mark.parametrize("failure", ["entry", "compile", "execute", "render"])
def test_failed_generations_restore_host_state_and_keep_source_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    entry, helper = tmp_path / "entry.py", tmp_path / "broken.py"
    previous = ModuleType("entry")
    monkeypatch.setitem(sys.modules, "entry", previous)
    write(entry, "!\n" if failure == "entry" else "import broken\n")
    write(
        helper,
        "!\n"
        if failure == "compile"
        else "raise RuntimeError('execution')\n"
        if failure == "execute"
        else "value = 1\n",
    )
    before = sys.meta_path.copy(), sys.path.copy()

    def render() -> None:
        load(entry)
        raise RuntimeError("render")

    with pytest.raises((SyntaxError, RuntimeError)), imports(entry) as source:
        render()
    assert entry in source.files
    if failure != "entry":
        assert helper in source.files
    assert sys.modules["entry"] is previous
    assert "broken" not in sys.modules
    assert (sys.meta_path, sys.path) == before


def test_host_packages_and_new_installed_dependencies_keep_their_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = tmp_path / "entry.py"
    write(tmp_path / "resident/__init__.py", "class Base: pass\n")
    write(tmp_path / "resident/lazy.py", "class Child: pass\n")
    site = tmp_path / ".venv/lib/site-packages"
    write(site / "dependency.py", "class Base: pass\n")
    monkeypatch.syspath_prepend(str(site))
    monkeypatch.syspath_prepend(str(tmp_path))
    resident = importlib.import_module("resident")
    write(entry, "import resident, resident.lazy, dependency\n")
    try:
        for _ in range(2):
            with imports(entry) as source:
                module = load(entry)
                assert module.resident is resident
            assert source.files == {entry}
            assert sys.modules["resident"] is resident
            assert sys.modules["resident.lazy"] is module.resident.lazy
            assert sys.modules["dependency"] is module.dependency
    finally:
        for name in ("resident", "resident.lazy", "dependency"):
            sys.modules.pop(name, None)


def test_package_resolution_and_circular_imports_stay_with_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = tmp_path / "entry.py"
    external = tmp_path / "installed"
    write(external / "shared/elsewhere.py", "value = 19\n")
    write(tmp_path / "shared/nearby.py", "value = 23\n")
    write(tmp_path / "cycle_a.py", "value = 2\nimport cycle_b\n")
    write(tmp_path / "cycle_b.py", "import cycle_a\nvalue = cycle_a.value + 1\n")
    write(
        entry,
        "import shared.elsewhere, shared.nearby, cycle_a\n"
        "value = shared.elsewhere.value + shared.nearby.value + cycle_a.cycle_b.value\n",
    )
    monkeypatch.syspath_prepend(str(external))
    for _ in range(2):
        with imports(entry):
            assert load(entry).value == 45
        assert all(
            name not in sys.modules
            for name in (
                "shared",
                "shared.elsewhere",
                "shared.nearby",
                "cycle_a",
                "cycle_b",
            )
        )


def test_a_helper_edit_during_the_first_run_is_observed(tmp_path: Path) -> None:
    entry, helper = tmp_path / "entry.py", tmp_path / "fresh_helper.py"
    write(entry, "import fresh_helper\n")
    write(helper, "value = 1\n")
    window = cast("Window", Mock(spec=Window, asked=lambda: None))
    news = News([entry], window)
    with imports(entry, news.watch):
        load(entry)
        stamp = helper.stat().st_mtime_ns
        write(helper, "value = 2\n")
        os.utime(helper, ns=(stamp + 1_000_000_000, stamp + 1_000_000_000))
        news.looked = 0  # Observe the saved edit at the next polling opportunity.
        assert news()


def test_explicit_entry_reload_uses_current_source_and_restores_its_host_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = tmp_path / "entry.py"
    previous = ModuleType("entry")
    monkeypatch.setitem(sys.modules, "entry", previous)
    write(entry, "value = 1\n")
    with imports(entry):
        module = load(entry)
        write(entry, "value = 2\n")
        assert importlib.reload(module).value == 2
    assert sys.modules["entry"] is previous


def test_a_symlinked_author_helper_uses_current_source_and_is_watched(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    entry, helper = root / "entry.py", root / "linked_helper.py"
    target = tmp_path / "shared.py"
    write(entry, "from linked_helper import value\n")
    write(target, "value = 'one'\n")
    try:
        helper.symlink_to(target)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("this Windows account cannot create symbolic links")
        raise
    stamp = helper.stat()
    py_compile.compile(str(helper), doraise=True)
    write(target, "value = 'two'\n")
    os.utime(target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    with imports(entry) as source:
        assert load(entry).value == "two"
    assert helper in source.files


def test_mixed_namespace_children_reload_together_across_source_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, external = tmp_path / "project", tmp_path / "external"
    entry = root / "entry.py"
    helper = external / "shared_namespace/elsewhere.py"
    write(helper, "value = 19\n")
    stamp = helper.stat()
    write(root / "shared_namespace/nearby.py", "value = 23\n")
    write(
        entry,
        "import shared_namespace.elsewhere, shared_namespace.nearby\n"
        "value = shared_namespace.elsewhere.value + shared_namespace.nearby.value\n",
    )
    monkeypatch.syspath_prepend(str(external))
    for value in (19, 20):
        write(helper, f"value = {value}\n")
        os.utime(helper, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with imports(entry) as source:
            assert load(entry).value == value + 23
        assert all(
            name not in sys.modules
            for name in (
                "shared_namespace",
                "shared_namespace.elsewhere",
                "shared_namespace.nearby",
            )
        )
    assert helper in source.files

"""Each scene-file load starts from shipped settings, then applies the file's own."""

import os
import py_compile
import sys
from pathlib import Path

import pytest

from manimgx.cli.scenes import load, report_error, scene
from manimgx.config import Config, config


def test_scene_edits_are_read_even_when_bytecode_metadata_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "edited_cli_source.py"
    source.write_text("value = 'one'\n", encoding="utf-8")
    stamp = source.stat()
    py_compile.compile(
        str(source), invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP
    )
    source.write_text("value = 'two'\n", encoding="utf-8")
    os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    monkeypatch.setattr(sys, "path", sys.path.copy())
    try:
        assert load(source).value == "two"
    finally:
        sys.modules.pop(source.stem, None)


def test_scene_errors_show_the_current_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "failing_cli_source.py"
    monkeypatch.setattr(sys, "path", sys.path.copy())
    try:
        for value in ("one", "two"):
            line = f"raise ValueError('{value}')"
            source.write_text(line, encoding="utf-8")
            os.utime(source, (1_700_000_000, 1_700_000_000))
            with pytest.raises(ValueError, match=value) as error:
                load(source)
            assert line in report_error(error.value)
    finally:
        sys.modules.pop(source.stem, None)


@pytest.mark.parametrize("pick_scene", [False, True])
def test_a_loaded_file_starts_from_defaults_and_sets_its_own_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pick_scene: bool
) -> None:
    source = tmp_path / "fresh_cli_source.py"
    source.write_text(
        "import manimgx as m\n"
        "m.config.pixel_width = 640\n"
        "class Only(m.Scene):\n"
        "    pass\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "path", sys.path.copy())
    try:
        for _ in range(2):
            config.pixel_width, config.pixel_height, config.frame_rate = 320, 180, 12
            if pick_scene:
                assert scene(source, None).__name__ == "Only"
            else:
                load(source)
            assert config.pixel_width == 640
            assert config.pixel_height == Config().pixel_height
            assert config.frame_rate == Config().frame_rate
    finally:
        sys.modules.pop(source.stem, None)

"""New lights read current files; live lights own immutable decoded pictures."""

import os
from pathlib import Path

import numpy as np
from tests.integration.test_light import radiance_file

import manimgx as m
from manimgx.caches import clear


def test_replacing_an_environment_preserves_existing_lights_only(
    tmp_path: Path,
) -> None:
    path = radiance_file(tmp_path / "room.hdr", np.full((2, 4), 0.25))
    original = m.EnvironmentLight(path).picture
    assert original is not None
    before = original.rgbe
    metadata = path.stat()
    radiance_file(path, np.full((2, 4), 0.5))
    os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
    assert path.stat().st_size == metadata.st_size
    current = m.EnvironmentLight(path).picture
    assert current is not None
    assert current.rgbe != before
    assert original.rgbe == before


def test_identical_environment_contents_share_their_decoding(tmp_path: Path) -> None:
    first = radiance_file(tmp_path / "first.hdr", np.full((2, 4), 0.25))
    second = tmp_path / "second.hdr"
    second.write_bytes(first.read_bytes())
    assert m.EnvironmentLight(first).picture is m.EnvironmentLight(second).picture


def test_forgetting_pictures_preserves_their_contents(tmp_path: Path) -> None:
    path = radiance_file(tmp_path / "room.hdr", np.full((2, 4), 0.25))
    original = m.EnvironmentLight(path).picture
    clear()
    current = m.EnvironmentLight(path).picture
    assert original is not None
    assert current is not None
    assert current is not original
    assert (current.width, current.height, current.rgbe) == (
        original.width,
        original.height,
        original.rgbe,
    )

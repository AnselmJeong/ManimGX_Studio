"""Malformed Radiance dimensions report ordinary errors at the native decoder boundary."""

from pathlib import Path

import pytest

import manimgx as m
from manimgx import _engine


@pytest.mark.parametrize(
    ("width", "height"),
    [(0, 1), (1, 0), (65536, 16384), (8, 2**29), (2**32 - 1, 2**32 - 1)],
)
def test_invalid_hdr_dimensions_are_value_errors(
    width: int, height: int, tmp_path: Path
) -> None:
    data = f"#?RADIANCE\n\n-Y {height} +X {width}\n".encode()
    with pytest.raises(ValueError, match="Radiance"):
        _engine.read_hdr(data)
    path = tmp_path / "invalid.hdr"
    path.write_bytes(data)
    with pytest.raises(ValueError, match="Radiance"):
        m.EnvironmentLight(path)


def test_decoded_hdr_pixels_keep_their_bytes() -> None:
    pixels = bytes(range(64))
    header = b"#?RADIANCE\n\n-Y 1 +X 16\n"
    encoded = header + bytes([2, 2, 0, 16])
    for channel in range(4):
        encoded += bytes([16]) + pixels[channel::4]
    for data in (header + pixels, encoded):
        assert _engine.read_hdr(data) == (16, 1, pixels)


def test_narrowing_keeps_a_single_row_and_the_last_odd_pixel() -> None:
    pixel = bytes([128, 64, 32, 129])
    data = b"#?RADIANCE\n\n-Y 1 +X 8192\n" + pixel * 8192
    assert _engine.read_hdr(data) == (4096, 1, pixel * 4096)
    edge = bytes([128, 0, 0, 133])
    data = b"#?RADIANCE\n\n-Y 3 +X 4097\n" + bytes(4097 * 3 * 4 - 4) + edge
    assert _engine.read_hdr(data) == (2049, 2, bytes(2049 * 2 * 4 - 4) + edge)

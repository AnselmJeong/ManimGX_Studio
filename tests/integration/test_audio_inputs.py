"""Audio time and interleaved frames are validated before native size arithmetic."""

import io
import math
import wave

import numpy as np
import pytest

import manimgx as m
from manimgx import _engine


@pytest.mark.parametrize("rate", [0, -1])
def test_sample_rate_is_positive_where_samples_are_given(rate: int) -> None:
    with pytest.raises(ValueError, match="sample rate"):
        m.Sound(np.ones(1, np.float32), rate=rate)


@pytest.mark.parametrize("factor", [0, -1, math.nan, math.inf, -math.inf])
def test_speed_is_finite_and_positive_where_it_is_edited(factor: float) -> None:
    sound = m.Sound(np.ones(1, np.float32), rate=48_000)
    with pytest.raises(ValueError, match="speed"):
        sound.speed(factor)


@pytest.mark.parametrize("factor", [1e-200, 1e200])
def test_composed_speed_must_remain_representable(factor: float) -> None:
    sound = m.Sound(np.ones(1, np.float32), rate=48_000).speed(factor)
    with pytest.raises(ValueError, match="speed"):
        sound.speed(factor)


@pytest.mark.parametrize(
    ("channels", "rate", "to"),
    [
        (0, 48_000, 48_000),
        (2, 48_000, 48_000),  # one sample cannot form a stereo frame
        (1, 0, 48_000),
        (1, 48_000, 0),
        (1, -1, 48_000),
        (1, math.nan, 48_000),
        (1, 48_000, math.nan),
        (1, math.inf, 48_000),
        (1, 48_000, math.inf),
        (1, 1e-100, 48_000),  # finite metadata, unrepresentable output length
    ],
)
def test_native_resampling_rejects_invalid_frames_and_time(
    channels: int, rate: float, to: float
) -> None:
    with pytest.raises(ValueError, match="audio"):
        _engine.resample_audio(np.ones(1, np.float32).tobytes(), channels, rate, to)


def test_decoding_uses_the_same_sample_rate_contract() -> None:
    encoded = io.BytesIO()
    with wave.open(encoded, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(48_000)
        out.writeframes(bytes(16))
    with pytest.raises(ValueError, match="sample rates"):
        _engine.decode_audio(encoded.getvalue(), 0)


@pytest.mark.parametrize("channels", [1, 2, 3])
def test_valid_empty_and_identity_resampling_remain_exact(channels: int) -> None:
    samples = np.arange(5 * channels, dtype=np.float32).tobytes()
    assert _engine.resample_audio(samples, channels, 48_000, 48_000) == samples
    assert _engine.resample_audio(b"", channels, 24_000, 48_000) == b""

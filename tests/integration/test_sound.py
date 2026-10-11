"""A film's sound, heard through a player: in its MP4, to the sample, as long as the film.

- The MP4 carries the film's sound as AAC; a decoder (FFmpeg's) finds each sound at its sample,
  the encoder's priming skipped, at any frame rate; the sound lasts exactly as long as the film.
- A film with no sound has no sound track.
- The engine reads audio files (WAV, FLAC, MP3…) as they are, and resamples band-limited: a
  tone keeps its level, and its images are gone.
"""

import wave
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
import pytest

import manimgx as m
from manimgx._engine import decode_audio, resample_audio
from manimgx.audio.sound import RATE
from manimgx.config import config
from manimgx.rendering.film import X264Preset


def impulse() -> m.Sound:
    x = np.zeros(4800, np.float32)
    x[0] = 0.9
    return m.Sound(x, rate=RATE)


class Beats(m.Scene):
    def construct(self) -> None:
        square = m.Square()
        self.play(m.Create(square))
        self.play(m.FadeOut(square), impulse())  # at 1 s
        self.add_sound(impulse(), time_offset=1.5)  # at 3.5 s
        self.wait(2)


def decoded(path: Path) -> np.ndarray:
    """The MP4's sound as a player hears it (FFmpeg's decoder, through PyAV): from the
    encoder's priming, which the decoder skips, to the end of the edit list, which the stream's
    duration says; the first channel."""
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="flt", layout="mono", rate=RATE)
        frames = [
            out.to_ndarray().reshape(-1)
            for frame in container.decode(stream)
            for out in resampler.resample(frame)
        ]
        heard = stream.duration
    assert heard is not None
    return np.concatenate(frames)[:heard]


def streams(path: Path) -> list[str]:
    with av.open(str(path)) as container:
        return [stream.codec_context.name for stream in container.streams]


pytestmark = pytest.mark.config(pixel_width=320, pixel_height=180)


@pytest.mark.parametrize("fps", [10, 24, 60])
@pytest.mark.parametrize("preset", ["ultrafast", "slow"])
def test_each_sound_is_at_its_sample_and_lasts_the_film(
    tmp_path: Path, fps: int, preset: X264Preset
) -> None:
    config.frame_rate = fps
    film = Beats().render(tmp_path / "beats.mp4", preset=preset)
    assert streams(tmp_path / "beats.mp4") == ["h264", "aac"]
    x = decoded(tmp_path / "beats.mp4")
    assert len(x) == film.frame_count * RATE // fps
    for want in (RATE, 7 * RATE // 2):
        window = np.abs(x[want - 4000 : want + 4000])
        assert int(np.argmax(window)) + want - 4000 == want


def test_a_film_without_sound_has_no_sound_track(tmp_path: Path) -> None:
    class Silent(m.Scene):
        def construct(self) -> None:
            self.play(m.Create(m.Square()))

    Silent().render(tmp_path / "silent.mp4")
    assert streams(tmp_path / "silent.mp4") == ["h264"]


def test_audio_files_are_read_as_they_are(tmp_path: Path) -> None:
    rate, t = 44_100, np.arange(44_100) / 44_100
    tone = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype("<i2")
    with wave.open(str(tmp_path / "tone.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(tone.tobytes())
    with (
        av.open(str(tmp_path / "tone.wav")) as wav,
        av.open(str(tmp_path / "tone.flac"), "w") as flac,
    ):
        out = flac.add_stream("flac", rate=rate, layout="mono")
        for frame in wav.decode(audio=0):
            for packet in out.encode(frame):
                flac.mux(packet)
        for packet in out.encode(None):
            flac.mux(packet)
    for name in ("tone.wav", "tone.flac"):
        samples, channels = decode_audio((tmp_path / name).read_bytes(), RATE)
        x = np.frombuffer(samples, np.float32)
        assert channels == 1
        assert len(x) == RATE
        assert np.abs(x[1000:-1000]).max() == pytest.approx(0.5, abs=2e-3)
    with pytest.raises(ValueError, match="not an audio file"):
        decode_audio(b"not audio at all", RATE)


CLICKS = (12_000, 36_000)  # where the clicks are, in a second of sound at RATE


def clicks(channels: int) -> np.ndarray:
    """A second of near-silence with a short burst at each of CLICKS, in every channel."""
    x = np.zeros((RATE, channels), np.float32)
    burst = (0.4 * np.hanning(64) * np.sin(np.arange(64) * 0.7)).astype(np.float32)
    for at in CLICKS:
        x[at - 32 : at + 32] = burst[:, None]
    return x


def encoded(path: Path, codec: str, layout: str, x: np.ndarray) -> bytes:
    """`x` (RATE, as `layout`) encoded by FFmpeg (PyAV's), in the container `path` names."""
    with av.open(str(path), "w") as file:
        stream = file.add_stream(codec, rate=RATE, layout=layout)
        assert isinstance(stream, av.AudioStream)
        frame = av.AudioFrame.from_ndarray(
            np.ascontiguousarray(x.T), format="fltp", layout=layout
        )
        # from time 0: the encoder's priming before it, which the file then declares
        frame.rate, frame.pts, frame.time_base = RATE, 0, Fraction(1, RATE)
        for packet in (*stream.encode(frame), *stream.encode(None)):
            file.mux(packet)
    return path.read_bytes()


@pytest.mark.parametrize(
    ("name", "codec", "layout"),
    [
        ("aac.m4a", "aac", "stereo"),
        ("lame.mp3", "libmp3lame", "stereo"),
        ("opus.ogg", "libopus", "stereo"),
        ("opus.webm", "libopus", "mono"),
        ("flac.flac", "flac", "stereo"),
        ("alac.m4a", "alac", "mono"),
        ("surround.wav", "pcm_s16le", "5.1"),
    ],
)
def test_audio_files_start_and_end_where_they_declare(
    tmp_path: Path, name: str, codec: str, layout: str
) -> None:
    """Each container and codec: the sound exactly as long as it was, each click on its
    sample (the encoder's delay and padding trimmed as the file declares them), and surround
    mixed down to stereo without clipping."""
    channels = av.AudioLayout(layout).nb_channels
    x = clicks(channels) * 1.5
    samples, got = decode_audio(encoded(tmp_path / name, codec, layout, x), RATE)
    y = np.frombuffer(samples, np.float32).reshape(-1, got)
    assert got == min(channels, 2)
    assert len(y) == RATE
    assert np.abs(y).max() <= 1
    for at in CLICKS:
        peak = [int(np.argmax(np.abs(s[at - 2000 : at + 2000, 0]))) for s in (x, y)]
        assert abs(peak[0] - peak[1]) <= 2


def test_a_sound_manimgx_does_not_decode_is_named(tmp_path: Path) -> None:
    data = encoded(tmp_path / "dolby.mkv", "ac3", "stereo", clicks(2))
    with pytest.raises(
        ValueError, match="its sound is ac3, which ManimGX doesn't decode"
    ):
        decode_audio(data, RATE)


def level(y: np.ndarray, hz: float) -> float:
    """A tone's level in `y` (at RATE), in decibels of a 0.5 sine."""
    w = np.hanning(len(y))
    spectrum = np.abs(np.fft.rfft(y * w)) / (w.sum() / 2)
    at = round(hz * len(y) / RATE)
    return float(20 * np.log10(spectrum[at - 2 : at + 3].max() / 0.5 + 1e-12))


def test_resampling_keeps_the_band_and_drops_its_images() -> None:
    t = np.arange(24_000) / 24_000
    for f in (100, 1_000, 5_000, 10_000):
        x = (0.5 * np.sin(2 * np.pi * f * t)).astype(np.float32)
        y = np.frombuffer(resample_audio(x.tobytes(), 1, 24_000, RATE), np.float32)
        y = y[2400:-2400]
        assert level(y, f) == pytest.approx(0, abs=0.1)
        assert level(y, 24_000 - f) < -80

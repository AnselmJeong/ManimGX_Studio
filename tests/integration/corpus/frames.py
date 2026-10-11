"""Frames: their identity (a hash of their pixels) and their storage (lossless video).

A frame is identified by its RGB pixels alone, never by the bytes of a file, so a video is
rewritten only when its pixels change: re-rendering an unchanged scene changes no file.
Videos are x264 in RGB at QP 0 — lossless, and byte-reproducible for a given encoder (one
thread, bit-exact muxing) — written and read with PyAV (FFmpeg's libraries, in its wheel).
"""

import hashlib
from collections.abc import Generator
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from tests.integration.corpus.case import Run

type Pixels = np.ndarray[tuple[int, int, int], np.dtype[np.uint8]]
"""One frame: height × width × RGB."""


def frame_hash(rgb: bytes) -> str:
    return hashlib.sha256(rgb).hexdigest()[:16]


def rgb(pixels: bytes | np.ndarray, size: tuple[int, int]) -> bytes:
    """RGB bytes of a frame given as RGBA (or RGB) rows, top to bottom."""
    width, height = size
    array = np.frombuffer(pixels, np.uint8) if isinstance(pixels, bytes) else pixels
    channels = array.size // (width * height)
    frame = array.reshape(height, width, channels)
    return np.ascontiguousarray(frame[:, :, :3]).tobytes()


class Recorder:
    """Frames as an engine draws them: their hashes, as runs, and, given a path, a video."""

    def __init__(
        self,
        size: tuple[int, int],
        fps: int,
        video: Path | None,
        *,
        compact: bool = True,
    ) -> None:
        self.size = size
        self.runs: list[list[str | int]] = []
        self.count = 0
        self._video = None if video is None else _Video(video, size, fps, compact)

    def add(self, frame: bytes, repeat: int = 1) -> None:
        """One drawn frame (RGB bytes), shown `repeat` times."""
        if repeat <= 0:
            return
        h = frame_hash(frame)
        if self.runs and self.runs[-1][0] == h:
            self.runs[-1][1] = int(self.runs[-1][1]) + repeat
        else:
            self.runs.append([h, repeat])
        self.count += repeat
        if self._video is not None:
            self._video.write(frame, repeat)

    def close(self) -> tuple[Run, ...]:
        if self._video is not None:
            self._video.close()
        return tuple((str(h), int(n)) for h, n in self.runs)


class _Video:
    """Lossless RGB video, compressed for archiving or for immediate comparison."""

    def __init__(
        self, path: Path, size: tuple[int, int], fps: int, compact: bool
    ) -> None:
        self.size, self.rate, self.shown = size, Fraction(1, fps), 0
        self.container = av.open(str(path), "w", options={"fflags": "+bitexact"})
        options = {
            "preset": "veryslow" if compact else "ultrafast",
            "qp": "0",
            "threads": "1",
            "flags": "+bitexact",
        }
        self.stream = self.container.add_stream("libx264rgb", fps, options=options)
        self.stream.width, self.stream.height = size
        self.stream.pix_fmt = "rgb24"

    def write(self, frame: bytes, repeat: int) -> None:
        width, height = self.size
        pixels = np.frombuffer(frame, np.uint8).reshape(height, width, 3)
        picture = av.VideoFrame.from_ndarray(pixels, format="rgb24")
        picture.time_base = self.rate
        for _ in range(repeat):
            picture.pts = self.shown
            self.shown += 1
            self.container.mux(self.stream.encode(picture))

    def close(self) -> None:
        self.container.mux(self.stream.encode(None))
        self.container.close()


def decode(path: Path, size: tuple[int, int]) -> Generator[Pixels]:
    """Every frame of a video, in order. A reader may stop early; a video that fails to decode
    to its end raises."""
    width, height = size
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            if (frame.width, frame.height) != size:
                msg = f"{path}: a frame of {frame.width}x{frame.height}"
                raise RuntimeError(msg)
            pixels = frame.to_ndarray(format="rgb24").astype(np.uint8, copy=False)
            yield pixels.reshape(height, width, 3)

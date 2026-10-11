"""Verified reference packages and exact streaming comparisons on the current host.

A reference wheel runs in its own process through the ordinary corpus runner. Its transient
lossless movie is compared with today's pixels; reviewed canonical movies remain the anchor.
"""

import hashlib
import json
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

import numpy as np
from tests.integration.corpus.case import FPS, SIZE, Frames
from tests.integration.corpus.frames import decode, rgb


class RecordedFilm(Protocol):
    size: tuple[int, int]
    frames: int
    fps: float
    timeline: list[tuple[int, int]]

    def render(self, frame: int) -> bytes: ...


@dataclass(frozen=True, slots=True)
class Difference:
    first: int
    repeat: int
    changed_pixels: int
    max_channel_difference: int


class Comparison:
    """Compare complete frame streams, independently of how either stream groups holds.

    A callback receives differing RGB pairs while they are available. Only one reference
    image is retained, and each recorded shot is drawn once, even across several callbacks.
    Indexes and holds must partition the film: skipped, repeated and missing frames fail.
    """

    def __init__(
        self,
        reference: RecordedFilm,
        difference: Callable[[Difference, bytes, bytes], object],
    ) -> None:
        end = 0
        for start, repeat in reference.timeline:
            if start != end or repeat <= 0:
                raise ValueError("the reference timeline must cover consecutive frames")
            end += repeat
        if end != reference.frames or min(reference.size) <= 0:
            raise ValueError("the reference timeline or image size is inconsistent")
        self.reference = reference
        self.difference = difference
        self.frames = 0
        self.changed_frames = 0
        self._shot = 0
        self._wanted: bytes | None = None

    def add(self, index: int, repeat: int, actual: bytes) -> None:
        """Compare RGB pixels shown at `index` for `repeat` frames."""
        if index != self.frames or repeat <= 0:
            raise ValueError("the actual timeline must cover consecutive frames")
        end = index + repeat
        if end > self.reference.frames:
            raise ValueError("the actual film has more frames than its reference")
        width, height = self.reference.size
        if len(actual) != width * height * 3:
            raise ValueError("the actual frame has the wrong RGB image size")
        while self.frames < end:
            start, held = self.reference.timeline[self._shot]
            if self._wanted is None:
                self._wanted = rgb(self.reference.render(start), self.reference.size)
            stop = min(end, start + held)
            if actual != self._wanted:
                old = np.frombuffer(self._wanted, np.uint8).reshape(height, width, 3)
                new = np.frombuffer(actual, np.uint8).reshape(height, width, 3)
                delta = np.abs(old.astype(np.int16) - new)
                difference = Difference(
                    self.frames,
                    stop - self.frames,
                    int(np.any(delta, axis=2).sum()),
                    int(delta.max()),
                )
                self.changed_frames += difference.repeat
                self.difference(difference, self._wanted, actual)
            self.frames = stop
            if stop == start + held:
                self._shot += 1
                self._wanted = None

    def finish(self, frames: int) -> None:
        """Require the callbacks and the exported film to cover the entire reference."""
        if frames != self.frames or frames != self.reference.frames:
            raise ValueError(
                f"frame coverage differs: callbacks={self.frames}, film={frames}, "
                f"reference={self.reference.frames}"
            )


def verify(path: Path, sha256: str) -> None:
    """Check an artifact's independently supplied identity before using its contents."""
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != sha256:
        raise ValueError(f"{path.name}: SHA256 {digest}, expected {sha256}")


def prepare(wheel: Path, sha256: str, directory: Path) -> Path:
    """Extract a verified wheel, retaining the native module's adjacent resources."""
    verify(wheel, sha256)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("the reference wheel directory must be empty")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
                raise ValueError(f"unsafe wheel member: {name}")
        engines = [
            name
            for name in names
            if PurePosixPath(name).parent == PurePosixPath("manimgx")
            and PurePosixPath(name).name.startswith("_engine.")
            and name.endswith((".so", ".pyd"))
        ]
        if len(engines) != 1:
            raise ValueError(
                f"a reference wheel needs one native engine, found {engines}"
            )
        directory.mkdir(parents=True, exist_ok=True)
        archive.extractall(directory)
    (directory / "reference-wheel.json").write_text(
        json.dumps({"wheel": wheel.name, "sha256": sha256, "engine": engines[0]}),
        encoding="utf-8",
    )
    return directory


def dependencies(lock: Path, current: Path) -> str:
    """Require the reference's frozen dependency lock before sharing a numerical runtime."""
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    if lock.read_bytes() != current.read_bytes():
        raise ValueError(
            "the reference dependency lock differs: compare with its frozen dependencies "
            "or review a new baseline before accepting dependency changes"
        )
    return digest


class Movie:
    """A sequential lossless reference, decoded once and checked through its last frame."""

    def __init__(self, path: Path, facts: Frames) -> None:
        self.size, self.frames = SIZE, facts.count
        self.fps = float(FPS)
        self.timeline = [(i, 1) for i in range(self.frames)]
        self._decoded = decode(path, SIZE)
        self._index = 0

    def render(self, frame: int) -> bytes:
        if frame != self._index:
            raise ValueError("reference movies are read in consecutive frame order")
        try:
            pixels = next(self._decoded)
        except StopIteration as error:
            raise ValueError(
                "the reference movie ends before its recorded frames"
            ) from error
        self._index += 1
        return pixels.tobytes()

    def finish(self) -> None:
        if self._index != self.frames or next(self._decoded, None) is not None:
            raise ValueError(
                "the reference movie's frame count differs from its record"
            )

    def close(self) -> None:
        self._decoded.close()

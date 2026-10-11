"""What both engine runners share: a deterministic random regime, loading a scene from the exact
bytes that were hashed, and the result file they hand back."""

import json
import random
import sys
import types
from pathlib import Path

import numpy as np
from tests.integration.corpus.case import (
    FPS,
    SIZE,
    Frames,
    Json,
    frames_to_json,
    source_hash,
)

_default_rng = np.random.default_rng


def _seeded_default_rng(
    seed: int | None = None,
) -> np.random.Generator:
    return _default_rng(0 if seed is None else seed)


def seed() -> None:
    """Seed every random source a scene or engine may draw from, before the scene is loaded."""
    random.seed(0)
    np.random.seed(0)
    # an unseeded generator (CE's QuickHull makes one) draws from seed 0
    setattr(np.random, "default_rng", _seeded_default_rng)  # noqa: B010


def load(path: Path, source: bytes, name: str) -> types.ModuleType:
    """Execute `source` (the bytes of `path` that were hashed) as a fresh module."""
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module  # dataclasses and typing resolve names through it
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def the_scene[T](module: types.ModuleType, base: type[T]) -> type[T]:
    """The one class the module defines that derives from `base`."""
    found = [
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and issubclass(value, base)
        and value.__module__ == module.__name__
    ]
    if len(found) != 1:
        msg = f"expected exactly one scene class, found {len(found)}"
        raise ValueError(msg)
    return found[0]


def write_result(
    out: Path, source: bytes, frames: Frames, extra: dict[str, Json] | None = None
) -> None:
    result: dict[str, Json] = {
        "source": source_hash(source),
        "size": list(SIZE),
        "fps": FPS,
        "render": frames_to_json(frames),
        "duration_exact": str(frames.duration),
    }
    out.write_text(json.dumps(result | (extra or {})), encoding="utf-8")

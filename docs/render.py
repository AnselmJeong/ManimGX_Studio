"""How documentation scenes become media, independent of discovery, caching and HTML."""

import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docs.examples import Example

    from manimgx import Scene

# At the films' own rate, slow and CRF 28 make a tenth of the default's file (ultrafast,
# 18), alike to the eye, in the same time. This module is a shared rendering input.
SIZE, FPS = (1280, 720), 60
PRESET, CRF = "slow", 28
FORMAT = f"{SIZE[0]}x{SIZE[1]} at {FPS} fps, {PRESET}, CRF {CRF}"


def load(example: "Example") -> "type[Scene]":
    """Run an example as a module in docs/, so its narration reads docs/voice/."""
    import manimgx as m

    module = types.ModuleType("__example__")
    module.__file__ = __file__
    sys.modules[module.__name__] = module
    exec(compile(example.code, example.where, "exec"), module.__dict__)
    scene = module.__dict__[str(example.scene)]
    if not (isinstance(scene, type) and issubclass(scene, m.Scene)):
        raise TypeError(f"{example.scene} is not a scene")
    return scene


def draw(example: "Example", folder: Path, readme: bool) -> None:
    """Render a scene in its own process, with SVGs too for the README's examples."""
    from docs import svg
    from PIL import Image

    import manimgx as m
    from manimgx.rendering.film import Frame

    m.config.pixel_width, m.config.pixel_height = SIZE
    m.config.frame_rate = FPS
    scene = load(example)
    drawn, poster = 0, b""

    def keep(frame: Frame) -> None:
        """Keep the last nonempty frame: a scene that ends empty is shown as it was."""
        nonlocal drawn, poster
        drawn += 1
        pixels = frame.pixels()
        if not poster or pixels.count(pixels[:4]) * 4 != len(pixels):
            poster = pixels

    video = folder / f"{example.stem}.mp4"
    size = m.config.pixel_width, m.config.pixel_height
    scene().render(video, frames=keep, preset=PRESET, crf=CRF)
    still = Image.frombytes("RGBA", size, poster).convert("RGB")
    still.save(folder / f"{example.stem}.webp", quality=90, method=6)
    if drawn == 1:  # nothing moves: the still is the film
        video.unlink()
    if readme:
        recording = svg.record(scene)
        svg.write(recording, folder / f"{example.stem}.svg")
        svg.write(recording, folder / f"{example.stem}-light.svg", light=True)

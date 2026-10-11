"""The README and docs share nine GIF previews, each linked to its film.

`uv run --frozen python -m scripts.showcase.wall` runs each film in `CLIPS` and keeps
five seconds at 50 fps, cropped around what moves and without fixed titles or readouts.
Each preview is 320 × 180 pixels on #0d1117. Premultiplied pixels are resized before
compositing, keeping translucent edges intact. Both pages use the same opaque images.

Gifski encodes all 250 source frames at full quality, combining visually equivalent
samples into longer holds on the same 20 ms timeline. Every file must stay strictly below 12 MB and all
nine together below 24 MB. The complete set is staged; its dimensions, duration, timing,
opacity, looping and budgets are validated before any published file is replaced. Install
Gifski and put `gifski` on PATH to regenerate the committed images.
`scripts/showcase/logo.py` draws their SVG logo.
"""

import importlib.util
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image
from PIL.GifImagePlugin import GifImageFile

import manimgx as m
from manimgx.rendering.film import Cut, Frame

ROOT = Path(__file__).parents[2]
EXAMPLES = ROOT / "examples"
SHOWCASE = ROOT / "docs" / "content" / "showcase"
FILM = 1920, 1080  # the films' size, in which the clips' boxes are
TILE = 320, 180  # one image size, shared by the README and the docs
FPS, SECONDS = 50, 5
BACKGROUND = 13, 17, 23  # #0d1117
MAX_BYTES = 12_000_000  # each image, strictly less
MAX_TOTAL_BYTES = 24_000_000  # the complete wall, strictly less


@dataclass(frozen=True)
class Clip:
    """A moment of an example film: `SECONDS` from `start`, framed by the 16:9 box `width`
    pixels wide whose top left corner is (`left`, `top`), which keeps what moves."""

    name: str
    start: float
    left: int
    top: int
    width: int

    @property
    def box(self) -> tuple[int, int, int, int]:
        """The box, as (left, top, right, bottom) in the film's pixels."""
        height = self.width * 9 // 16
        if self.left + self.width > FILM[0] or self.top + height > FILM[1]:
            raise ValueError(f"{self.name}: the box leaves the film")
        return self.left, self.top, self.left + self.width, self.top + height


CLIPS = [  # the wall's, three a row
    Clip("quadratic_formula", 9.6, 240, 60, 1440),
    Clip("fourier_pi", 5, 310, 90, 1300),
    Clip("linear_maps", 5, 0, 0, 1920),
    Clip("derivative", 17.6, 0, 0, 1920),
    Clip("complex_maps", 2.4, 0, 0, 1920),
    Clip("lorenz_attractor", 7.5, 320, 150, 1280),
    Clip("heavy_top", 24, 0, 0, 1920),
    Clip("hopf_fibration", 17, 410, 210, 1120),
    Clip("catenoid_helicoid", 9, 320, 180, 1280),
]


def scene(name: str) -> type[m.Scene]:
    """The scene an example film's file defines."""
    spec = importlib.util.spec_from_file_location(name, EXAMPLES / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    found = [
        v
        for v in vars(module).values()
        if isinstance(v, type) and issubclass(v, m.Scene) and v.__module__ == name
    ]
    return found[0]


def composite(crop: Image.Image) -> Image.Image:
    """Resize premultiplied pixels, then put them on the preview's opaque background."""
    if crop.mode != "RGBa":
        raise ValueError("the renderer's pixels must be premultiplied RGBa")
    small = np.asarray(crop.resize(TILE, Image.Resampling.LANCZOS), dtype=np.float32)
    alpha = small[..., 3:4] / 255
    rgb = small[..., :3] + np.asarray(BACKGROUND) * (1 - alpha)
    return Image.fromarray(np.clip(np.rint(rgb), 0, 255).astype(np.uint8))


def frames(clip: Clip) -> list[Image.Image]:
    """Render directly at the preview's frame rate, crop, resize and composite each frame."""
    first = math.ceil(clip.start * FPS - 1e-9)
    last = first + SECONDS * FPS
    m.config.frame_rate = FPS
    m.config.pixel_width, m.config.pixel_height = FILM
    m.config.background_opacity = 0.0
    film = scene(clip.name)
    kept: list[Image.Image] = []

    def display_list(self: m.Scene) -> list[m.Mobject]:
        fixed = {id(mob) for mob in self.camera.fixed_in_frame_mobjects}
        return [mob for mob in film.display_list(self) if id(mob) not in fixed]

    def keep(frame: Frame) -> None:
        if frame.index >= last:
            raise Cut
        shown = min(frame.index + frame.repeat, last) - max(frame.index, first)
        if shown <= 0:
            return
        pixels = np.frombuffer(frame.pixels(), np.uint8).reshape(FILM[1], FILM[0], 4)
        left, top, right, bottom = clip.box
        crop = Image.fromarray(pixels[top:bottom, left:right].copy(), "RGBa")
        kept.extend([composite(crop)] * shown)

    bare = type(film.__name__, (film,), {"display_list": display_list})
    bare().render(frames=keep)
    if len(kept) != last - first:
        raise RuntimeError(f"{clip.name}: the film ends before its clip does")
    return kept


def name(clip: Clip) -> str:
    """The single animated image used by both pages for a film."""
    return f"{clip.name}.gif"


def validate(path: Path) -> None:
    """Reject a GIF that exceeds the budget or changes the preview's playback."""
    if path.stat().st_size >= MAX_BYTES:
        raise ValueError(f"{path.name}: must be below {MAX_BYTES:,} bytes")
    try:
        with Image.open(path) as image:
            if not isinstance(image, GifImageFile) or image.size != TILE:
                raise ValueError(f"{path.name}: must be a {TILE[0]} × {TILE[1]} GIF")
            if not image.is_animated:
                raise ValueError(f"{path.name}: must remain animated")
            if image.info.get("loop") != 0:
                raise ValueError(f"{path.name}: must loop forever")
            total = 0
            for index in range(image.n_frames):
                image.seek(index)
                image.load()
                duration = image.info.get("duration", 0)
                if duration <= 0 or duration % (1000 // FPS):
                    raise ValueError(
                        f"{path.name}: frame {index} must last a positive multiple "
                        f"of {1000 // FPS} ms"
                    )
                total += duration
                # GIF may use transparency to reuse the preceding frame's pixels; its
                # fully composited display must still be opaque, including the first frame.
                if image.convert("RGBA").getchannel("A").getextrema() != (255, 255):
                    raise ValueError(f"{path.name}: frame {index} must be opaque")
            if total != SECONDS * 1000:
                raise ValueError(f"{path.name}: must last exactly {SECONDS * 1000} ms")
    except (EOFError, IndexError, OSError) as error:
        raise ValueError(f"{path.name}: cannot decode the complete GIF") from error


def validate_set(paths: list[Path]) -> None:
    """Validate every image and the combined budget before publishing any of them."""
    for path in paths:
        validate(path)
    total = sum(path.stat().st_size for path in paths)
    if total >= MAX_TOTAL_BYTES:
        raise ValueError(f"the complete wall must be below {MAX_TOTAL_BYTES:,} bytes")


def encode(tiles: list[Image.Image], path: Path, gifski: str) -> None:
    """Encode ordered lossless source frames, preserving their 50 fps presentation times."""
    if len(tiles) != FPS * SECONDS:
        raise ValueError(f"{path.name}: must encode {FPS * SECONDS} source frames")
    with TemporaryDirectory(prefix=".frames-", dir=path.parent) as directory:
        inputs = []
        for index, image in enumerate(tiles):
            frame = Path(directory) / f"frame{index:04d}.png"
            image.save(frame, compress_level=1)
            inputs.append(str(frame))
        result = subprocess.run(
            [
                gifski,
                "--quiet",
                "--fps",
                str(FPS),
                "--repeat",
                "0",
                "--no-sort",
                "--quality",
                "100",
                "--motion-quality",
                "100",
                "--lossy-quality",
                "100",
                "--output",
                str(path),
                *inputs,
            ],
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(
                f"Gifski failed: {result.stderr.decode(errors='replace')}"
            )


def main() -> None:
    gifski = shutil.which("gifski")
    if gifski is None:
        raise RuntimeError(
            "Install Gifski and put gifski on PATH to regenerate the GIFs"
        )
    SHOWCASE.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".wall-", dir=SHOWCASE) as directory:
        paths = []
        for clip in CLIPS:
            path = Path(directory) / name(clip)
            encode(frames(clip), path, gifski)
            paths.append(path)
        validate_set(paths)
        for path in paths:
            destination = SHOWCASE / path.name
            path.replace(destination)
            print(
                f"{destination.name}: {destination.stat().st_size:,} bytes", flush=True
            )


if __name__ == "__main__":
    main()

"""Render the linked-rings frame at 2.5 seconds, and the part of it the README shows on
dark and light backgrounds."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from benchmarks.run import executable
from PIL import Image

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "scenes"
# what the README shows of each frame: the 302 × 524 pixels from (810, 326), which hold
# the rings
CROP = (810, 326, 1112, 850)


def website_images(frame: Path) -> dict[str, Image.Image]:
    """What the README shows of a transparent 1080p frame, on the site's dark (`""`) and
    light (`"-light"`) backgrounds."""
    with Image.open(frame) as source:
        foreground = source.convert("RGBA")
    if (
        foreground.size != (1920, 1080)
        or foreground.getchannel("A").getextrema()[0] != 0
    ):
        raise ValueError(f"Expected a transparent 1080p frame: {frame}")
    pictures = {}
    for suffix, color in (("", "#0B0C0F"), ("-light", "#FFFFFF")):
        background = Image.new("RGBA", foreground.size, color)
        background.alpha_composite(foreground)
        pictures[suffix] = background.convert("RGB").crop(CROP)
    return pictures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--gx-python", default=sys.executable)
    parser.add_argument("--ce-python", default=sys.executable)
    parser.add_argument("--gl-python", required=True)
    parser.add_argument("--blender", default="blender")
    args = parser.parse_args()
    for option in ("gx_python", "ce_python", "gl_python", "blender"):
        setattr(args, option, executable(getattr(args, option)))
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    native = args.out / "native"
    native.mkdir()
    images = args.out / "images"
    images.mkdir()
    env = os.environ | {"PYTHONPATH": str(SOURCES), "PYTHONDONTWRITEBYTECODE": "1"}
    for engine in (
        "manimgx",
        "manim_ce",
        "manimgl",
        "blender_workbench",
        "blender_eevee",
    ):
        target = native / f"{engine}.png"
        if engine.startswith("blender_"):
            command = [
                args.blender,
                "-b",
                "--factory-startup",
                "--python-exit-code",
                "1",
                "-P",
                str(SOURCES / "linked_rings_blender.py"),
                "--",
                "--engine",
                engine.removeprefix("blender_"),
                "--out",
                str(target),
            ]
        else:
            python = {
                "manimgx": args.gx_python,
                "manim_ce": args.ce_python,
                "manimgl": args.gl_python,
            }[engine]
            command = [
                python,
                str(SOURCES / "quality_manim.py"),
                "--engine",
                engine,
                "--out",
                str(target),
            ]
        print(engine, flush=True)
        (native / f"{engine}-command.json").write_text(
            json.dumps(command, indent=2) + "\n", encoding="utf-8"
        )
        with (native / f"{engine}.log").open("wb") as log:
            subprocess.run(
                command,
                cwd=native,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=120,
            )
        for suffix, image in website_images(target).items():
            image.save(images / f"{engine}{suffix}.png")
    print(images)


if __name__ == "__main__":
    main()

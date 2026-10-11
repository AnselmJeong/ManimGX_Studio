"""Render scenes with ManimGX in this process, reading every frame back from the player.

    python -m tests.integration.corpus.run_manimgx SCENE --out RESULT [--video OUT.mkv] [--mp4]

One scene per process: a scene rendered after another can differ (the engine may leak state
between scenes), so references and checks render each scene alone. `--mp4` also sends the
scene through the product's exporter and counts the frames of the MP4 it writes. `--sequence`
renders several scenes in one process, in order, to find exactly such leaks.
"""

import argparse
import contextlib
import dataclasses
import json
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import av
from PIL import Image
from tests.integration.corpus.case import FPS, SIZE, Frames, Json, frames_from_json
from tests.integration.corpus.frames import Recorder, rgb
from tests.integration.corpus.frozen import Comparison, Difference, Movie
from tests.integration.corpus.runtime import load, seed, the_scene, write_result

import manimgx
from manimgx import _engine
from manimgx.config import Config, config
from manimgx.rendering.film import Frame


def render(
    scene_path: Path,
    video: Path | None,
    mp4: Path | None,
    *,
    comparison: Comparison | None = None,
    source: bytes | None = None,
    compact_video: bool = True,
) -> tuple[bytes, Frames, int]:
    """(source, frames, frame count of the film)."""
    source = scene_path.read_bytes() if source is None else source
    seed()
    config.pixel_width, config.pixel_height = SIZE
    config.frame_rate = FPS
    module = load(scene_path, source, f"corpus_scene_{scene_path.parent.name}")
    scene = the_scene(module, manimgx.Scene)()
    recorder = Recorder(SIZE, FPS, video, compact=compact_video)

    def observe(frame: Frame) -> None:
        pixels = rgb(frame.pixels(), SIZE)
        recorder.add(pixels, frame.repeat)
        if comparison is not None:
            comparison.add(frame.index, frame.repeat, pixels)

    film = scene.render(mp4, frames=observe)
    if comparison is not None:
        comparison.finish(film.frame_count)
    runs = recorder.close()
    frames = Frames(
        runs=runs, duration=scene.clock, timeline=((Fraction(0), recorder.count),)
    )
    return source, frames, film.frame_count


def mp4_frames(path: Path) -> int:
    """The decoded presentation's end at the corpus rate, including its final held picture.

    Packet durations advance the decode clock, which differs from presentation order with
    B-frames. Every picture lasts until the next presentation timestamp; the final picture
    lasts for its own sample duration.
    """
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        samples, decoded, previous, end = 0, 0, -1, 0
        for packet in container.demux(stream):
            samples += bool(packet.size)  # the empty final packet drains the decoder
            for frame in packet.decode():
                if (
                    frame.pts is None
                    or frame.pts <= previous
                    or (decoded == 0 and frame.pts != 0)
                ):
                    raise ValueError(f"{path}: invalid presentation timestamps")
                decoded += 1
                previous, end = frame.pts, frame.pts + frame.duration
        time_base = stream.time_base
    if decoded != samples:
        msg = f"{path}: {decoded} of its {samples} samples decode"
        raise ValueError(msg)
    if previous < 0 or end <= previous:
        raise ValueError(f"{path}: missing final picture duration")
    assert time_base is not None
    shown = time_base * end * FPS
    if shown.denominator != 1:
        msg = f"{path} lasts {shown} frames"
        raise ValueError(msg)
    return int(shown)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--mp4", action="store_true")
    parser.add_argument("--sequence", action="store_true")
    parser.add_argument("--package", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--reference-video", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--differences", type=Path)
    parser.add_argument("--fast-video", action="store_true")
    args = parser.parse_args()
    if args.package is not None and any(
        not Path(module.__file__).resolve().is_relative_to(args.package.resolve())
        for module in (manimgx, _engine)
    ):
        raise RuntimeError(
            "the corpus runner did not import the requested reference package and engine"
        )

    if args.sequence:
        # each scene starts from the same config: only the engine's own state may carry over
        defaults = {f.name: getattr(config, f.name) for f in dataclasses.fields(Config)}
        results: dict[str, Json] = {}
        for path in args.scene:
            for name, value in defaults.items():
                setattr(config, name, value)
            _, frames, _ = render(path, None, None)
            results[path.parent.name] = [[h, n] for h, n in frames.runs]
        args.out.write_text(json.dumps(results), encoding="utf-8")
        return

    (scene_path,) = args.scene
    extra: dict[str, Json] = {}
    differences: list[Json] = []

    def changed(difference: Difference, old: bytes, new: bytes) -> None:
        differences.append(dataclasses.asdict(difference))
        if args.differences is not None and len(differences) <= 3:
            args.differences.mkdir(parents=True, exist_ok=True)
            for prefix, pixels in (("reference", old), ("actual", new)):
                Image.frombytes("RGB", SIZE, pixels).save(
                    args.differences / f"{prefix}-{difference.first:05}.png"
                )

    with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
        mp4 = Path(tmp) / "product.mp4" if args.mp4 else None
        movie, comparison = None, None
        if args.reference is not None:
            expected = frames_from_json(
                json.loads(args.reference.read_text(encoding="utf-8"))
            )
            if not isinstance(expected, Frames):
                raise ValueError("the reference must be a successfully rendered film")
            movie = stack.enter_context(
                contextlib.closing(
                    Movie(
                        args.reference_video or args.reference.with_suffix(".mkv"),
                        expected,
                    )
                )
            )
            comparison = Comparison(movie, changed)
        source, frames, film_frames = render(
            scene_path,
            args.video,
            mp4,
            comparison=comparison,
            source=None if args.source is None else args.source.read_bytes(),
            compact_video=not args.fast_video,
        )
        if movie is not None:
            movie.finish()
            extra["differences"] = differences
        if mp4 is not None:
            extra |= {"film_frames": film_frames, "mp4_frames": mp4_frames(mp4)}
        extra["adapter"] = dict[str, Json](_engine.adapter_info())
    if "manim" in sys.modules:
        msg = "the scene imported Manim CE; a manimgx render must not"
        raise RuntimeError(msg)
    write_result(args.out, source, frames, extra)


if __name__ == "__main__":
    main()

"""Render a scene with Manim CE in this process: the same bytes ManimGX runs, with `manimgx`
resolving to `manim`.

    python -m tests.integration.corpus.run_ce SCENE --out RESULT [--video OUT.mkv]

Frames are taken where CE makes them (its renderer's `add_frame`), losslessly, each with the
scene time it shows: a play's frames are 1/fps apart from the play's start, and a frozen wait
repeats one frame. CE's own PNG and MP4 writers are bypassed (a dry run): its PNGs keep one
image per frozen wait and its MP4s are lossy. The run fails if the real ManimGX is ever
imported, so a CE render can never be a ManimGX render in disguise.
"""

import argparse
import importlib
import importlib.abc
import importlib.machinery
import sys
import tempfile
import types
from collections.abc import Sequence
from fractions import Fraction
from pathlib import Path

from tests.integration.corpus.case import FPS, PACKAGE, SIZE, Frames, exact
from tests.integration.corpus.frames import Recorder, rgb
from tests.integration.corpus.runtime import load, seed, the_scene, write_result

# where CE keeps names that ManimGX has at its top level and CE's top level lacks: a scene names
# them as ManimGX's (`from manimgx import polylabel`), and CE finds them here
HOMES = (
    "manim.utils.paths",
    "manim.utils.space_ops",
    "manim.utils.unit",
    "manim.utils.polylabel",
    "manim.utils.qhull",
    "manim.utils.rate_functions",
    "manim.animation.transform_matching_parts",
)


def _from_homes(name: str) -> object:
    """`manim`'s module `__getattr__` (PEP 562): CE's object of that name in `HOMES`."""
    if not name.startswith("_"):
        for home in HOMES:
            module = importlib.import_module(home)
            if hasattr(module, name):
                return getattr(module, name)
    msg = f"module 'manim' has no attribute {name!r}"
    raise AttributeError(msg)


class ManimgxIsManim(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Resolves `manimgx` and `manimgx.X…` to the modules `manim` and `manim.X…` themselves (not
    copies), so a scene's `import manimgx as m` is CE; `manimgx`'s top-level names that CE keeps
    only in `HOMES` resolve there."""

    def __init__(self) -> None:
        self._specs: dict[str, importlib.machinery.ModuleSpec | None] = {}

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: types.ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if fullname == "manimgx" or fullname.startswith("manimgx."):
            # not a package spec: that would give plain manim modules an empty __path__
            return importlib.machinery.ModuleSpec(fullname, self, is_package=False)
        return None

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> types.ModuleType:
        module = importlib.import_module("manim" + spec.name.removeprefix("manimgx"))
        if spec.name == "manimgx":
            vars(module)["__getattr__"] = _from_homes
        self._specs[spec.name] = module.__spec__
        return module

    def exec_module(self, module: types.ModuleType) -> None:
        # the import system gave CE's module the alias's spec; give it its own back
        alias = module.__spec__
        assert alias is not None
        module.__spec__ = self._specs.pop(alias.name)


def render(scene_path: Path, video: Path | None, media: Path) -> tuple[bytes, Frames]:
    source = scene_path.read_bytes()
    seed()
    sys.meta_path.insert(0, ManimgxIsManim())

    import manim
    import manim.scene.scene
    from manim.animation.animation import Animation
    from manim.mobject.mobject import Mobject, _AnimationBuilder
    from manim.renderer.cairo_renderer import CairoRenderer
    from manim.typing import PixelArray

    config = manim.config
    config.pixel_width, config.pixel_height = SIZE
    config.frame_rate = FPS
    config.media_dir = str(media)
    # what CE still writes (its subtitles) goes to the temporary media directory
    config.output_file = str(media / "scene")
    config.dry_run = True
    config.disable_caching = True
    config.progress_bar = "none"
    config.verbosity = "WARNING"
    config.seed = 0

    recorder = Recorder(SIZE, FPS, video)
    timeline: list[tuple[Fraction, int]] = []

    class Recording(CairoRenderer):
        """CE's renderer, keeping each frame it makes and the scene time the frame shows."""

        clock = Fraction(0)  # the scene time at which the next play starts
        playing = False  # inside a play
        stretch = False  # the play's frames have begun a stretch of the timeline

        def play(
            self,
            scene: manim.Scene,
            *args: Animation | Mobject | _AnimationBuilder,
            **kwargs: object,
        ) -> None:
            start = self.clock
            self.playing, self.stretch = True, False
            try:
                super().play(scene, *args, **kwargs)
            finally:
                self.playing = False
            self.clock = start + exact(scene.duration)

        def add_frame(self, frame: PixelArray, num_frames: int = 1) -> None:
            if self.skip_animations:
                return
            self.time += num_frames / self.camera.frame_rate
            if self.stretch:
                start, count = timeline[-1]
                timeline[-1] = (start, count + num_frames)
            else:
                timeline.append((self.clock, num_frames))
                self.stretch = self.playing
            recorder.add(rgb(frame, SIZE), num_frames)

        def scene_finished(self, scene: manim.Scene) -> None:
            super().scene_finished(scene)
            if recorder.count == 0:  # a scene that never plays is its last frame
                timeline.append((self.clock, 1))
                recorder.add(rgb(self.get_frame(), SIZE), 1)

    # CE's Scene makes its renderer by this name, with the camera its class needs
    setattr(manim.scene.scene, "CairoRenderer", Recording)  # noqa: B010

    module = load(scene_path, source, f"corpus_scene_{scene_path.parent.name}")
    scene = the_scene(module, manim.Scene)()
    scene.render()
    runs = recorder.close()

    impostors = [
        name
        for name, loaded in sys.modules.items()
        if (file := getattr(loaded, "__file__", None))
        and Path(file).resolve().is_relative_to(PACKAGE)
    ]
    if impostors:
        msg = f"the real manimgx was imported during a CE render: {impostors[:3]}"
        raise RuntimeError(msg)
    renderer = scene.renderer
    assert isinstance(renderer, Recording)
    return source, Frames(runs=runs, duration=renderer.clock, timeline=tuple(timeline))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--video", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as media:
        source, frames = render(args.scene, args.video, Path(media))
    import manim  # imported by `render`, after the random sources were seeded

    write_result(args.out, source, frames, {"manim": manim.__version__})


if __name__ == "__main__":
    main()

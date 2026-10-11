"""A command-line scene run: its arguments, source file, format, film and author-facing errors."""

import dataclasses
import difflib
import importlib.util
import linecache
import os
import re
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import CodeType, ModuleType
from typing import Annotated, Self

import typer
from rich.console import Console

import manimgx
from manimgx.animation.timeline import Animation
from manimgx.config import Config, config
from manimgx.rendering.film import (
    DEFAULT_ENCODER_CRF,
    DEFAULT_ENCODER_PRESET,
    Film,
    FrameSink,
    Play,
    X264Preset,
)
from manimgx.scene import Scene


@dataclass(frozen=True, slots=True)
class Size:
    """A picture's size in pixels."""

    width: int
    height: int

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"


def size(text: str) -> Size:
    """`WIDTHxHEIGHT` as a size."""
    width, _, height = text.lower().partition("x")
    try:
        parsed = Size(int(width), int(height))
    except ValueError:
        raise typer.BadParameter(
            f"{text!r} is not WIDTHxHEIGHT, e.g. 1280x720"
        ) from None
    if parsed.width <= 0 or parsed.height <= 0 or parsed.width % 2 or parsed.height % 2:
        raise typer.BadParameter(
            f"{text!r}: width and height must be even and positive"
        )
    return parsed


File = Annotated[
    Path,
    typer.Argument(
        metavar="FILE",
        help="The scene file: a Python file defining ManimGX scenes.",
        show_default=False,
    ),
]
SceneName = Annotated[
    str | None,
    typer.Argument(
        metavar="SCENE",
        help=(
            "The scene (a class in the file); needed only if the file defines several."
        ),
        show_default=False,
    ),
]
# a scene's format is its own — what its file sets in `config`, else 1920x1080 at 60 fps — unless
# an option says otherwise
Resolution = Annotated[
    Size | None,
    typer.Option(
        "--resolution",
        "-r",
        parser=size,
        metavar="WxH",
        help=(
            "Pixels, e.g. 1280x720. [default: the scene's config, 1920x1080 unless set]"
        ),
        show_default=False,
    ),
]
Fps = Annotated[
    int | None,
    typer.Option(
        min=1,
        help="Frames per second. [default: the scene's config, 60 unless set]",
        show_default=False,
    ),
]


PACKAGE = str(Path(manimgx.__file__).parent)

# names from older Manim (CE before 0.x renames, manimgl) and what ManimGX has instead
RENAMED = {
    "ShowCreation": "Create",
    "ShowCreationThenDestruction": "ShowPassingFlash",
    "ShowCreationThenFadeOut": "ShowPassingFlash",
    "CircleIndicate": "Circumscribe",
    "WiggleOutThenIn": "Wiggle",
    "TextMobject": "Text (plain text) or Tex (text with LaTeX)",
    "TexText": "Tex",
    "OldTexText": "Tex",
    "TexMobject": "MathTex",
    "OldTex": "MathTex",
    "FadeInFrom": "FadeIn(mobject, shift=direction)",
    "FadeInFromDown": "FadeIn(mobject, shift=UP)",
    "FadeOutAndShift": "FadeOut(mobject, shift=direction)",
    "FadeInFromLarge": "FadeIn(mobject, scale=factor)",
    "GraphScene": "a Scene with Axes (axes.plot(f))",
    "ParametricSurface": "Surface",
    "ContinualAnimation": "mobject.add_updater(function)",
}


def _names() -> list[str]:
    return [name for name in dir(manimgx) if not name.startswith("_")]


def hints(error: BaseException) -> list[str]:
    """What to write instead, for the mistakes a scene's author makes in names."""
    text = str(error)
    if isinstance(error, AttributeError) and (
        match := re.search(r"module 'manimgx' has no attribute '(\w+)'", text)
    ):
        return [_instead(match.group(1))]
    if isinstance(error, AttributeError) and error.obj is not None and error.name:
        close = difflib.get_close_matches(error.name, dir(error.obj), n=3, cutoff=0.6)
        if close:
            return [f"did you mean {' or '.join(close)}?"]
    if isinstance(error, NameError) and error.name:
        if error.name in _names():
            return [
                f"{error.name} is manimgx.{error.name}: `import manimgx as m`, then "
                f"m.{error.name}"
            ]
        if error.name in RENAMED:
            return [_instead(error.name)]
    if isinstance(error, ModuleNotFoundError) and error.name in ("manim", "manimlib"):
        return ["manimgx is the module: `import manimgx as m` (its API is Manim CE's)"]
    return []


def _instead(name: str) -> str:
    if name in RENAMED:
        return f"{name} is {RENAMED[name]} in ManimGX"
    close = difflib.get_close_matches(name, _names(), n=3, cutoff=0.6)
    if close:
        return f"ManimGX has no {name}; did you mean {' or '.join(close)}?"
    return f"ManimGX has no {name}"


def report_error(error: BaseException) -> str:
    """The error as it went through the scene's code: its last frames there (and where ManimGX
    raised it), the error, and hints."""
    frames = traceback.extract_tb(error.__traceback__)
    own = [
        f
        for f in frames
        if not f.filename.startswith(PACKAGE)
        and "/typer/" not in f.filename
        and not f.filename.startswith("<")
    ]
    lines: list[str] = []
    for f in own[-3:]:
        lines.append(f"{Path(f.filename).name}:{f.lineno}: in {f.name}")
        if f.line:
            lines.append(f"    {f.line}")
    inside = [f for f in frames if f.filename.startswith(PACKAGE)]
    if inside and frames[-1].filename.startswith(PACKAGE):
        last = inside[-1]
        where = Path(last.filename).relative_to(PACKAGE)
        lines.append(f"  (raised in manimgx/{where}:{last.lineno}, in {last.name})")
    lines.append(f"{type(error).__name__}: {error}")
    lines += [f"hint: {h}" for h in hints(error)]
    return "\n".join(lines)


class Mistake(Exception):
    """The command was given wrong; the message says how to give it."""


class Source(SourceFileLoader):
    """Current authoring source, with no timestamp-bytecode reuse or cache writes."""

    def get_code(self, fullname: str) -> CodeType:
        linecache.cache.pop(self.path, None)
        return self.source_to_code(self.get_data(self.path), self.path)


def load(path: Path) -> ModuleType:
    """Run the file as a module named by its stem, with its directory first on the path (so it
    imports its neighbours) — not as `__main__`, so its own `if __name__ == "__main__":` block
    stays put."""
    defaults = Config()
    for field in dataclasses.fields(Config):
        setattr(config, field.name, getattr(defaults, field.name))
    if not path.is_file():
        raise Mistake(f"{path}: no such file")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise Mistake(f"{path}: not a Python file")
    spec.loader = Source(path.stem, str(path.resolve()))
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module  # dataclasses and pickles resolve names through it
    sys.path.insert(0, str(path.resolve().parent))
    spec.loader.exec_module(module)
    return module


def scenes(module: ModuleType) -> list[type[Scene]]:
    """The scenes the module defines, in the order it defines them."""
    return [
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and issubclass(value, Scene)
        and value.__module__ == module.__name__
    ]


def pick(path: Path, module: ModuleType, name: str | None) -> type[Scene]:
    """The scene `name` names — or, unnamed, the file's only scene."""
    found = scenes(module)
    names = [scene.__name__ for scene in found]
    if name is not None:
        for scene in found:
            if scene.__name__ == name:
                return scene
        close = difflib.get_close_matches(name, names, n=3)
        hint = f" Did you mean {' or '.join(close)}?" if close else ""
        raise Mistake(
            f"{path} has no scene {name!r}.{hint} Its scenes: {', '.join(names)}"
        )
    if len(found) == 1:
        return found[0]
    if not found:
        raise Mistake(f"{path} defines no scene (a subclass of manimgx.Scene)")
    raise Mistake(
        f"{path} defines {len(found)} scenes ({', '.join(names)}): name one after the"
        " file"
    )


@dataclass(frozen=True, slots=True)
class Format:
    """The picture a take makes: its size in pixels and frames per second."""

    width: int
    height: int
    fps: float

    @classmethod
    def own(cls, size: Size | None = None, fps: float | None = None) -> Self:
        """The scene's own format — as its file leaves `config` — unless `size` or `fps` say
        otherwise."""
        shape = size or Size(config.pixel_width, config.pixel_height)
        return cls(shape.width, shape.height, fps or config.frame_rate)

    def __str__(self) -> str:
        return f"{self.width}x{self.height} at {self.fps:g} fps"


def fail(message: str, code: int = 2) -> typer.Exit:
    """Say what went wrong (on stderr) and end with `code`: 2 the command was wrong, 1 the scene
    failed."""
    typer.echo(message, err=True)
    return typer.Exit(code)


def scene(file: Path, name: str | None) -> type[Scene]:
    """The scene the command names: its file run on ManimGX's own config (whatever the file
    sets there is the scene's, not a take's before it), and it picked."""
    try:
        return pick(file, load(file), name)
    except Mistake as mistake:
        raise fail(f"error: {mistake}") from None
    except Exception as error:
        raise fail(report_error(error), 1) from None


type Watch = Callable[[Scene, Play, tuple[Animation, ...]], object]
"""What a command does when a play ends: the scene (as the play left it), the play, and what it
played."""


def take(
    kind: type[Scene],
    look: Format,
    *,
    video: str | os.PathLike[str] | None = None,
    frames: FrameSink | None = None,
    plays: Watch | None = None,
    preset: X264Preset = DEFAULT_ENCODER_PRESET,
    crf: float = DEFAULT_ENCODER_CRF,
) -> tuple[Scene, Film]:
    """Run the scene at `look`, making its film (and video, frames and plays, as asked). On a
    terminal, a status line on stderr follows the plays as they end."""
    config.pixel_width, config.pixel_height = look.width, look.height
    config.frame_rate = look.fps
    shown = Console(stderr=True)
    try:
        with shown.status(f"{kind.__name__}…", spinner="dots") as status:
            # after the config: its camera frame follows the picture's shape
            made = kind()

            def hook(play: Play, did: tuple[Animation, ...]) -> None:
                if shown.is_terminal:
                    status.update(
                        f"{kind.__name__}  t = {float(play.end):.1f} s, play"
                        f" #{play.index}"
                    )
                if plays is not None:
                    plays(made, play, did)

            return made, made.render(
                video, frames=frames, plays=hook, preset=preset, crf=crf
            )
    except Exception as error:
        raise fail(report_error(error), 1) from None

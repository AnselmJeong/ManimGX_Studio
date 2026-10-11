"""`manimgx preview`: a scene in ManimGX's player, in a window of its own, made again each time
its code is saved.

The scene runs here, as `manimgx render` runs it, but its film is recorded as a take (see
[`Film`][manimgx.Film]) and sent to a [`Window`][manimgx.Window], which plays it as it is made.
On a save the scene runs again — at once: a run a save has made out of date is cut — and its new
take replaces the old at the same moment, once it gets there: an edit never loses the place. An
error is shown over the last good take.
"""

import importlib
import sys
import time
import traceback
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader
from pathlib import Path
from types import ModuleType
from typing import Annotated

import typer

from manimgx.cli.scenes import (
    File,
    Format,
    Fps,
    Mistake,
    Resolution,
    SceneName,
    Size,
    Source,
    fail,
    load,
    pick,
    report_error,
    scenes,
)
from manimgx.config import config
from manimgx.rendering.film import Cut
from manimgx.rendering.window import Window

POLL = 0.02  # seconds between looks at the files


def preview(
    file: File,
    name: SceneName = None,
    time_: Annotated[
        float,
        typer.Option(
            "--time", "-t", min=0, help="Where the playhead starts, in seconds."
        ),
    ] = 0.0,
    resolution: Resolution = None,
    fps: Fps = None,
) -> None:
    """Preview a scene live: in a window, made again each time its code is saved.

    The window plays the scene as it is made. Saving the file, or a module it imports from
    beside it, runs the scene again, and the window keeps its place; an error shows over the
    last good picture. A file of several scenes plays the one named, or its first; N and P go
    to the others. Keys: Space play/pause, ← → 5 s, , . a frame, Option (or Ctrl) with ← → a
    play, ? all of them. Closing the window, or Ctrl+C, stops."""
    if not file.is_file():
        raise fail(f"error: {file}: no such file")
    with Window(f"{file.name} — ManimGX", time=time_) as window:
        try:
            files = [file]
            while window.open:
                news = News(files, window)  # the files as this run reads them
                files = run(file, name, resolution, fps, window, news)
                news.watch(files)
                while window.open and not news():
                    time.sleep(POLL)
                if news.asked is not None:
                    name = news.asked
                else:
                    time.sleep(POLL)  # an editor saving in steps: let it finish
        except KeyboardInterrupt:
            pass
    if window.failure is not None:
        raise fail(f"error: the window: {window.failure}", 1)


class News:
    """What makes a run out of date: a file it reads saved again, or another scene asked for
    in the window. Called, whether there is any (it looks every `POLL` seconds)."""

    def __init__(self, files: list[Path], window: Window) -> None:
        self.seen = dict(zip(files, stamps(files), strict=True))
        self.window = window
        self.asked: str | None = None
        self.any = False  # there was some
        self.looked = time.monotonic()

    def watch(self, files: list[Path]) -> None:
        """Watch `files` too: those not watched yet as they are now."""
        new = [f for f in files if f not in self.seen]
        self.seen.update(zip(new, stamps(new), strict=True))

    def __call__(self) -> bool:
        now = time.monotonic()
        if now - self.looked < POLL:
            return False
        self.looked = now
        self.asked = self.window.asked() or self.asked
        files = list(self.seen)
        self.any = self.asked is not None or stamps(files) != list(self.seen.values())
        return self.any


def run(
    file: Path,
    name: str | None,
    resolution: Size | None,
    fps: int | None,
    window: Window,
    news: News,
) -> list[Path]:
    """Run the scene once, its take (or its error) into `window`, and cut it once `news`
    makes it out of date. Returns the files to watch: the scene's, and the modules it imported
    from beside it."""
    root = file.resolve().parent
    started = time.perf_counter()

    def take(data: bytes) -> None:
        if news():
            raise Cut  # out of date: run again
        window(data)

    with imports(file, news.watch) as source:
        try:
            module = load(file)
            found = [s.__name__ for s in scenes(module)]
            # unnamed, the file's first scene: its viewer goes to the others in the window (N, P)
            kind = pick(
                file, module, found[0] if name is None and len(found) > 1 else name
            )
            window.scenes(found, kind.__name__)
            look = Format.own(resolution, fps)
            config.pixel_width, config.pixel_height = look.width, look.height
            config.frame_rate = look.fps
            film = kind().render(take=take)
            cut = "cut: " if news.any or not window.open else ""
            typer.echo(
                f"{kind.__name__}: {cut}{film.frame_count} frames in"
                f" {time.perf_counter() - started:.2f} s",
                err=True,
            )
        except Exception as error:
            text = str(error) if isinstance(error, Mistake) else report_error(error)
            typer.echo(text, err=True)
            own = [
                f
                for f in traceback.extract_tb(error.__traceback__)
                if Path(f.filename).resolve().is_relative_to(root)
            ]
            window.failed(
                error, text, own[-1].lineno if own else getattr(error, "lineno", None)
            )
    return list(source.files)


class Sources(MetaPathFinder):
    """The scene-directory imports owned by one authoring generation."""

    def __init__(
        self, file: Path, host: set[str], watch: Callable[[list[Path]], None] | None
    ) -> None:
        self.root = file.resolve().parent
        self.host = host
        self.watch = watch
        self.modules = {file.stem}
        self.files = {file.resolve()}

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        top = fullname.partition(".")[0]
        if top in self.host and top not in self.modules:
            return None
        spec = PathFinder.find_spec(fullname, path, target)
        if spec is None:
            return None
        if "." not in fullname:
            local = PathFinder.find_spec(fullname, [str(self.root)])
            if local is None or local.origin != spec.origin:
                return None
            if spec.origin is None and not set(
                local.submodule_search_locations or ()
            ) & set(spec.submodule_search_locations or ()):
                return None
        elif fullname.rpartition(".")[0] not in self.modules:
            return None
        self.modules.add(fullname)
        if isinstance(spec.loader, SourceFileLoader):
            file = Path(spec.loader.path).absolute()
            # Ownership follows the import entry, including symlinks and namespace portions.
            self.files.add(file)
            if self.watch is not None:
                self.watch([file])
            spec.loader = Source(fullname, str(file))
        return spec


@contextmanager
def imports(
    file: Path, watch: Callable[[list[Path]], None] | None = None
) -> Iterator[Sources]:
    """Load the scene's modules for one run; preserve the process that hosts it."""
    before, path = dict(sys.modules), sys.path.copy()
    source = Sources(file, {name.partition(".")[0] for name in before}, watch)
    sys.meta_path.insert(sys.meta_path.index(PathFinder), source)
    importlib.invalidate_caches()
    try:
        yield source
    finally:
        sys.meta_path.remove(source)
        sys.path[:] = path
        for name in source.modules:
            if name in before:
                sys.modules[name] = before[name]
            else:
                sys.modules.pop(name, None)


def stamps(paths: list[Path]) -> list[float]:
    """The files' modification times (0 for one that is gone, for now)."""
    return [p.stat().st_mtime if p.exists() else 0.0 for p in paths]

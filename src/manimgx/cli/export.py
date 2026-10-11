"""Offline scene exports: video, inspections and presentations."""

import json
import os
import re
import time
import webbrowser
from fractions import Fraction
from html import escape
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Annotated
from urllib.parse import quote

import typer
from PIL import Image

from manimgx.animation import clock
from manimgx.animation.timeline import Animation
from manimgx.cli.diagnostics import Names, names, written_frame
from manimgx.cli.scenes import (
    File,
    Format,
    Fps,
    Resolution,
    SceneName,
    fail,
    scene,
    take,
)
from manimgx.cli.storyboard import Sheets, Watch, line
from manimgx.config import config
from manimgx.rendering.film import (
    DEFAULT_ENCODER_CRF,
    DEFAULT_ENCODER_PRESET,
    Cut,
    Film,
    Frame,
    Play,
    X264Preset,
)
from manimgx.scene import Scene

if TYPE_CHECKING:
    from manimgx.animation.transform import Transform
    from manimgx.drawing.geometry import Path as MotionPath


def render(
    file: File,
    name: SceneName = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="The video (.mp4). [default: <Scene>.mp4 beside the file]",
        ),
    ] = None,
    resolution: Resolution = None,
    fps: Fps = None,
    preset: Annotated[
        X264Preset,
        typer.Option(
            help="Encoding speed: faster presets encode sooner but produce larger files."
        ),
    ] = DEFAULT_ENCODER_PRESET,
    crf: Annotated[
        float,
        typer.Option(
            min=0,
            max=51,
            help="Video quality: lower values give higher quality and larger files.",
        ),
    ] = DEFAULT_ENCODER_CRF,
) -> None:
    """Render a scene to an MP4 video, with its sound.

    Also writes a storyboard beside the video (the frame at each play's end, layout problems
    outlined and numbered) and lists those problems — see `manimgx inspect` — and, if the
    scene speaks or has subcaptions, its subtitles (.srt)."""
    kind = scene(file, name)
    video = output or file.with_name(f"{kind.__name__}.mp4")
    if video.suffix.lower() != ".mp4":
        raise fail(f"error: {video}: ManimGX writes MP4 video; name the output *.mp4")
    look = Format.own(resolution, fps)
    watch = Watch(Sheets(video.with_name(f"{video.stem}.storyboard.png")))
    started = time.perf_counter()
    try:
        made, _ = take(kind, look, video=video, plays=watch, preset=preset, crf=crf)
    finally:
        sheets = watch.storyboard.close()
    took = time.perf_counter() - started
    megabytes = video.stat().st_size / 1e6
    typer.echo(
        f"{video}  {float(made.clock):.2f} s, {look}, {megabytes:.1f} MB "
        f"(rendered in {took:.1f} s)"
    )
    typer.echo(f"storyboard: {', '.join(str(s) for s in sheets)}")
    subtitles = made.film.subtitles()
    if subtitles:
        srt = video.with_suffix(".srt")
        srt.write_text(subtitles, encoding="utf-8")
        typer.echo(f"subtitles: {srt}")
    typer.echo(watch.report(timeline=False, film=made.film))


def moments(given: list[str]) -> set[Fraction | None]:
    """Distinct times in seconds; None means `end`. `-t 1,2` is `-t 1 -t 2`."""
    out: set[Fraction | None] = set()
    for part in (p.strip() for text in given for p in text.split(",")):
        if not part:
            continue
        try:
            moment = None if part == "end" else Fraction(part)
            if moment is not None and moment < 0:
                raise ValueError
        except (ValueError, ZeroDivisionError):
            raise fail(
                f"error: {part!r} is not a time: non-negative seconds or 'end'"
            ) from None
        out.add(moment)
    if given and not out:
        raise fail("error: --time needs seconds from the start, or 'end'")
    return out


def inspect(
    file: File,
    name: SceneName = None,
    time: Annotated[
        list[str] | None,
        typer.Option(
            "--time",
            "-t",
            metavar="TIME",
            help=(
                "Seconds from the start, or 'end'; several: repeat -t or separate with"
                " commas."
            ),
            show_default=False,
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="The storyboard (.png). [default: <Scene>.storyboard.png beside the file]",
        ),
    ] = None,
) -> None:
    """Inspect a scene: annotated PNGs, timeline and 2D layout checks, without video.

    Samples play and wait endings by default. With -t, inspects the frames a video player
    shows at those times; 'end' is the last frame. Checks for clipped content, overlapping
    text, lines or fills over text, and small labels. 3D scenes get pictures and a timeline;
    layout checks are skipped. Only sampled moments are checked.

    Pictures are chronological, captioned #play t=… file:line, with problems outlined and
    numbered. Six fit on each sheet (more go on `<name>-2.png`, …). Default sampling omits
    consecutive identical pictures. With -t, only the requested frames are drawn, and the
    scene stops after the last requested frame's play unless 'end' is included.

    Exits 1 for layout problems; notes, such as a graph leaving the frame, do not count.
    """
    kind = scene(file, name)
    wanted = moments(time or [])
    target = output or file.with_name(f"{kind.__name__}.storyboard.png")
    if target.suffix.lower() != ".png":
        raise fail(
            f"error: {target}: a storyboard is a PNG image; name the output *.png"
        )
    look = Format.own()
    fps = clock.rational(look.fps)
    # The last sample no later than the requested observed instant.
    pending = sorted(
        ((clock.frame_at(t, fps, after=True) - 1, t) for t in wanted if t is not None),
        reverse=True,
    )
    known: Names | None = None
    watch = Watch(Sheets(target))

    class Sampling(Scene):
        """Observe selected frames through the scene's existing evaluation methods."""

        def _emit(self, repeat: int = 1) -> None:
            while pending and pending[-1][0] < self.frame + repeat:
                when = Fraction(pending.pop()[0]) / fps
                watch.see(self, when, known=known)
            super()._emit(repeat)

        def _pure_tweens(
            self, anim: Animation, alpha: list[float]
        ) -> "tuple[list[tuple[Transform, MotionPath]], set[int]] | None":
            if pending and pending[-1][0] < self.frame + len(alpha):
                return None  # this play needs its mutable world at the selected frames
            return super()._pure_tweens(anim, alpha)

    def ended(made: Scene, play: Play, animations: tuple[Animation, ...]) -> None:
        nonlocal known
        if not made.three_d:
            known = names(made, written_frame())
        watch.lines.append(line(play, animations))
        if None not in wanted and not pending:
            raise Cut  # the play showing the last frame asked for is over

    try:
        # Only an inspection with selected frames uses the adapter. Scene and render
        # keep their ordinary evaluation path, including subclasses' overrides.
        observed = (
            type(kind.__name__, (kind, Sampling), {"__module__": kind.__module__})
            if pending
            else kind
        )
        made, film = take(observed, look, plays=ended if wanted else watch)
        if pending:
            raise fail(
                f"error: the scene ends at {float(made.clock):.2f} s; there is no frame at"
                f" {pending[-1][1]} s",
                1,
            )
        if None in wanted or (not wanted and not film.plays):
            watch.see(made, Fraction(film.frame_count - 1) / fps, known=known)
    finally:
        sheets = watch.storyboard.close()
    typer.echo(
        f"{file}: {kind.__name__}, {float(made.clock):.2f} s, {len(film.plays)} plays"
    )
    typer.echo(f"storyboard: {', '.join(str(s) for s in sheets)}")
    typer.echo(watch.report(film=film if not wanted or None in wanted else None))
    if watch.layout.numbers:
        raise typer.Exit(1)


def present(
    file: File,
    name: SceneName = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="The video (.mp4); the page is written beside it (.html). [default:"
            " <Scene>.mp4 beside the file]",
        ),
    ] = None,
    resolution: Resolution = None,
    fps: Fps = None,
    pdf: Annotated[
        bool,
        typer.Option(
            help="Also write a PDF: the picture each slide ends on, a page each."
        ),
    ] = False,
    show: Annotated[
        bool, typer.Option("--open/--no-open", help="Open the page in the browser.")
    ] = True,
) -> None:
    """Present a scene: its sections are the slides.

    Renders the video, writes a page that plays it (it stops at the end of each section,
    until you go on), and opens it. Keys: → or Space next, ← back, F full screen, B black,
    Shift+P presenter view (notes, the next slide, a timer), C captions, ? help. A clicker
    works: it sends the same keys. Begin a section with `self.next_section(...)` in the scene.
    """
    kind = scene(file, name)
    video = output or file.with_name(f"{kind.__name__}.mp4")
    if video.suffix.lower() != ".mp4":
        raise fail(f"error: {video}: ManimGX writes MP4 video; name the output *.mp4")
    look = Format.own(resolution, fps)
    pictures: list[bytes] = []  # the pictures slides end on, for the PDF
    last: list[Frame] = []

    def keep(frame: Frame) -> None:
        if frame.key and frame.index > 0:
            pictures.append(frame.pixels())
        last[:] = [frame]

    started = time.perf_counter()
    made, film = take(kind, look, video=video, frames=keep if pdf else None)
    if pdf and last:
        pictures.append(last[0].pixels())  # the film's last picture ends the last slide
    html = video.with_suffix(".html")
    html.write_text(page(film, Path(video.name), kind.__name__), encoding="utf-8")
    slides = len(film.sections)
    typer.echo(
        f"{video}  {float(made.clock):.2f} s, {look}, {slides} slides (rendered in"
        f" {time.perf_counter() - started:.1f} s)"
    )
    typer.echo(f"{html}")
    if pdf:
        size = (config.pixel_width, config.pixel_height)
        images = [Image.frombytes("RGBA", size, p).convert("RGB") for p in pictures]
        handout = video.with_suffix(".pdf")
        images[0].save(handout, save_all=True, append_images=images[1:])
        typer.echo(f"{handout}")
    if show:
        webbrowser.open(html.resolve().as_uri())


def page(film: Film, video: str | os.PathLike[str], title: str = "ManimGX") -> str:
    """The page that presents `film`, whose video is `video` (a path or URL, as the page
    will find it: relative to the page, typically).

    Args:
        film: The film, rendered.
        video: Where the page finds its video: a URL string, or a filesystem path
            (relative to the page, unless absolute).
        title: The page's title.

    Returns:
        The page's HTML.
    """
    deck = {
        "fps": float(film.fps),
        "frames": film.frame_count,
        "sections": [
            {"name": s.name, "frame": s.frame, "type": s.type, "notes": s.notes}
            for s in film.sections
        ],
        "captions": [[c.start, c.end, c.text] for c in film.captions()],
    }
    html = (files("manimgx") / "cli" / "present.html").read_text(encoding="utf-8")
    if not isinstance(video, str):
        path = Path(video)
        video = path.as_uri() if path.is_absolute() else quote(path.as_posix())
    values = {
        "DECK_TITLE": escape(title),
        "DECK_VIDEO": escape(video),
        "DECK_JSON": json.dumps(deck).replace("</", "<\\/"),
    }
    return re.sub(r"DECK_(?:TITLE|VIDEO|JSON)", lambda match: values[match[0]], html)

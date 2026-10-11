"""Play reports, annotated pictures and storyboard sheets."""

import math
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from manimgx.animation.timeline import Animation, AnimationGroup, Succession, Wait
from manimgx.animation.transform import Animate
from manimgx.audio import Speech
from manimgx.audio.sound import Sound
from manimgx.cli.diagnostics import (
    Layout,
    Names,
    Problem,
    View,
    report,
    text_of,
    view,
)
from manimgx.config import config
from manimgx.rendering.film import Film, Play
from manimgx.scene import Scene, _written

# a tile's area: 1080p halved each way (reduced exactly: sharp text), two to a sheet's row — in
# the scene's shape, so a sheet costs the same image tokens whatever the shape
TILE = 960 * 540
# more to a sheet would shrink tiles past reading (probes: 330 px tiles miss defects)
PER_SHEET = 6
GAP, CAPTION = 8, 28


def tile(rgba: bytes, width: int, height: int) -> Image.Image:
    """A picture at tile size: reduced by a whole factor (exact and fast), resized only for the
    rest."""
    image = Image.frombuffer(
        "RGBA", (width, height), rgba, "raw", "RGBA", 0, 1
    ).convert("RGB")
    scale = math.sqrt(TILE / (width * height))
    size = (round(width * scale), round(height * scale))
    if (factor := int(1 / scale + 1e-9)) >= 2:
        image = image.reduce(factor)
    if image.size != size:
        image = image.resize(size, Image.Resampling.BILINEAR)
    return image


@dataclass
class Sheets:
    """Captioned tiles, six to a sheet, each sheet written as it fills: `path`, `…-2`, …"""

    path: Path
    written: list[Path] = field(default_factory=list[Path])
    _tiles: list[tuple[str, Image.Image]] = field(
        default_factory=list[tuple[str, Image.Image]]
    )
    # sheets are encoded beside the take (PNG encoding releases the GIL)
    _writer: ThreadPoolExecutor = field(default_factory=lambda: ThreadPoolExecutor(1))
    _writes: list[Future[None]] = field(default_factory=list[Future[None]])

    def add(self, text: str, picture: Image.Image) -> None:
        self._tiles.append((text, picture))
        if len(self._tiles) == PER_SHEET:
            self._flush()

    def close(self) -> list[Path]:
        """The last sheet out; every sheet written."""
        with self._writer:
            if self._tiles:
                self._flush()
            for write in self._writes:
                write.result()
        return self.written

    def _flush(self) -> None:
        n = len(self.written) + 1
        out = self.path.with_name(
            self.path.name if n == 1 else f"{self.path.stem}-{n}{self.path.suffix}"
        )
        self._writes.append(
            self._writer.submit(_sheet(self._tiles).save, out, compress_level=3)
        )
        self.written.append(out)
        self._tiles = []


def _sheet(tiles: list[tuple[str, Image.Image]]) -> Image.Image:
    columns = 1 if len(tiles) == 1 else 2
    rows = -(-len(tiles) // columns)
    width, height = tiles[0][1].size
    sheet = Image.new(
        "RGB",
        (columns * (width + GAP) - GAP, rows * (height + CAPTION + GAP) - GAP),
        (32, 32, 32),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=20)
    for i, (text, picture) in enumerate(tiles):
        row, column = divmod(i, columns)
        x, y = column * (width + GAP), row * (height + CAPTION + GAP)
        draw.text((x + 6, y + 4), text, fill=(235, 235, 235), font=font)
        sheet.paste(picture, (x, y + CAPTION))
    return sheet


RED = (255, 64, 64)


@dataclass
class Watch:
    """A take's timeline, annotated pictures and layout report. As a `plays` hook it samples
    play endings; `see` inspects the live scene at any moment."""

    storyboard: Sheets
    layout: Layout = field(default_factory=Layout)
    lines: list[str] = field(default_factory=list[str])
    checked: int = 0
    three_d: bool = False
    _last: bytes = b""

    def __call__(
        self, made: Scene, play: Play, animations: tuple[Animation, ...]
    ) -> None:
        self.lines.append(line(play, animations))
        self.see(made, play.end, play=play, distinct=True)

    def see(
        self,
        made: Scene,
        time: Fraction,
        *,
        play: Play | None = None,
        distinct: bool = False,
        known: Names | None = None,
    ) -> None:
        """Check and draw the scene now; optionally omit a consecutive identical picture."""
        play = play or (made.film.plays[-1] if made.film.plays else None)
        index = None if play is None else play.index
        where = None if play is None else play.where
        # Inside a play that has not ended yet, its source is still on the stack.
        if made.num_plays > len(made.film.plays):
            index, where = made.num_plays - 1, _written()
        self.three_d = made.three_d
        seen = None if made.three_d else view(made, known)
        marked = [] if seen is None else self.layout.see((time, where), seen)
        self.checked += seen is not None
        rgba = made.film.picture(made.camera, made.display_list())
        picture = tile(rgba, config.pixel_width, config.pixel_height)
        pixels = picture.tobytes()
        if distinct and pixels == self._last:
            return
        self._last = pixels
        if seen is not None and marked:
            _mark(picture, seen, marked)
        caption = f"t={float(time):g}s"
        if index is not None:
            caption = f"#{index} {caption}"
        if where is not None:
            caption += f" {Path(where[0]).name}:{where[1]}"
        self.storyboard.add(caption, picture)

    def report(self, *, timeline: bool = True, film: "Film | None" = None) -> str:
        """The timeline (if asked), then the layout, then the sounds the film's end cuts
        short (given the film)."""
        layout = (
            "layout: not checked (a 3D scene)"
            if self.three_d
            else report(self.layout, self.checked)
        )
        cut = [] if film is None else film.cut()
        sounds = [
            f"sound: {describe(clip.sound)} at {float(clip.start):.2f}s is cut"
            f" {lost:.2f}s short: the film ends first"
            for clip, lost in cut
        ]
        return "\n".join([*(self.lines if timeline else []), layout, *sounds])


def _mark(picture: Image.Image, seen: View, marked: list[tuple[int, Problem]]) -> None:
    """The problems seen now, outlined in red with their numbers."""
    draw = ImageDraw.Draw(picture)
    x0, y0, x1, y1 = seen.frame
    sx, sy = picture.width / (x1 - x0), picture.height / (y1 - y0)
    px = 18
    font = ImageFont.load_default(size=px)
    for number, problem in marked:
        if not number:
            continue  # a note
        for thing in (problem.subject, problem.other):
            if thing is None:
                continue
            a, b, c, d = thing.box
            box = (
                (a - x0) * sx - 3,
                (y1 - d) * sy - 3,
                (c - x0) * sx + 3,
                (y1 - b) * sy + 3,
            )
            draw.rectangle(box, outline=RED, width=2)
            tag = str(number)
            tx, ty = max(0.0, box[0]), max(0.0, box[1] - px - 4)
            draw.rectangle((tx, ty, tx + 8 + 10 * len(tag), ty + px + 4), fill=RED)
            draw.text((tx + 4, ty + 1), tag, fill="white", font=font)


def said(text: str, limit: int = 28) -> str:
    text = " ".join(text.split())
    return repr(text if len(text) <= limit else text[: limit - 1] + "…")


def _named(function: Callable[..., object]) -> str:
    """A recorded method's name (an edit, `mob.animate(lambda m: …)`, has none)."""
    name = getattr(function, "__name__", None)
    return name if isinstance(name, str) else "edit"


def describe(animation: Animation) -> str:
    """An animation as the code wrote it: `Create(Circle)`, `title.animate.shift(…)`,
    `LaggedStart(4× FadeIn)`; a speech as what it says, `say 'Here is…'`, and a sound as
    `sound 0.8 s`."""
    if isinstance(animation, Speech):
        return f"say {said(animation.text)}"
    if isinstance(animation, Sound):
        return f"sound {animation.duration:.1f} s"
    if (  # a line said with its animations (`Scene.say`)
        type(animation) is AnimationGroup
        and animation.animations
        and isinstance(animation.animations[0], Speech)
    ):
        speech, *rest = animation.animations
        return " with ".join([describe(speech), *(_waited(part) for part in rest)])
    kind = type(animation).__name__
    target = type(animation.mobject).__name__
    words = text_of(animation.mobject)
    if words:
        target += f" {said(words)}"
    if isinstance(animation, Animate) and animation.methods:
        calls = ".".join(f"{_named(call.function)}(…)" for call in animation.methods)
        return f"{target}.animate.{calls}"
    if isinstance(animation, AnimationGroup) and animation.animations:
        inner = [describe(part) for part in animation.animations]
        kinds = {i.split("(")[0] for i in inner}
        if len(inner) > 3 and len(kinds) == 1:
            return f"{kind}({len(inner)}× {inner[0].split('(')[0]})"
        more = ", …" if len(inner) > 4 else ""
        return f"{kind}({', '.join(inner[:4])}{more})"
    return f"{kind}({target})"


def _waited(animation: Animation) -> str:
    """A part of a said line: one that waits for its words, as what it plays."""
    parts = animation.animations if isinstance(animation, Succession) else []
    if len(parts) == 2 and isinstance(parts[0], Wait):
        return describe(parts[1])
    return describe(animation)


def line(play: Play, animations: tuple[Animation, ...]) -> str:
    where = (
        "" if play.where is None else f"{Path(play.where[0]).name}:{play.where[1]}  "
    )
    what = (
        "wait"
        if len(animations) == 1 and isinstance(animations[0], Wait)
        else ", ".join(describe(a) for a in animations)
    )
    return (
        f"  #{play.index:<2d} {float(play.start):5.2f}–{float(play.end):5.2f}s "
        f" {where}{what}"
    )

"""Visible scene content and its layout diagnostics."""

import inspect
from dataclasses import dataclass, field, replace
from fractions import Fraction
from pathlib import Path
from types import FrameType

import numpy as np

import manimgx
from manimgx.config import config
from manimgx.constants import DL, UR
from manimgx.drawing.geometry import subpath_ranges
from manimgx.mobject import Mobject
from manimgx.scene import Scene

PACKAGE = str(Path(manimgx.__file__).parent)

TEXTS: tuple[type[Mobject], ...] = (
    manimgx.Typst,
    manimgx.DecimalNumber,
    manimgx.Code,
)
# what the player draws (a plain Mobject with points — a ValueTracker's value — is not drawn)
DRAWN: tuple[type[Mobject], ...] = (
    manimgx.VMobject,
    manimgx.PMobject,
    manimgx.MeshMobject,
    manimgx.ImageMobject,
)
SCENE_OWN = {"mobjects", "foreground_mobjects", "camera", "film", "compositor"}
# an extent this small is none (a shape scaled to 0, where a GrowFromCenter starts): a fill needs
# area to be seen, a stroke length
EMPTY = 1e-9

type Box = tuple[float, float, float, float]  # x0, y0, x1, y1 in scene units


@dataclass(frozen=True, slots=True)
class Thing:
    """A text, or another drawn part, as it is on screen."""

    name: str  # the code's name for it, or its kind
    kind: str
    text: str | None  # what a text says (None: not a text)
    box: Box
    outline: np.ndarray | None  # a shape's curves as polylines: (curves, samples, 2)
    fill: float  # fill opacity
    stroked: bool  # a visible outline
    closed: bool  # every subpath closes (not a line or a graph)
    order: int  # draw order
    root: str  # the outermost group the code names that holds it (else its top object's kind)
    root_kind: str
    backdrop: int | None  # a text's own opaque background: its draw order
    ink: int  # a text's glyphs, fingerprinted: equal ink in one place is one text


def written_frame() -> FrameType | None:
    """The innermost frame of the scene's own code on the stack (outside ManimGX)."""
    here = inspect.currentframe()
    frame = None if here is None else here.f_back
    while frame is not None and frame.f_code.co_filename.startswith(PACKAGE):
        frame = frame.f_back
    return frame


type Names = tuple[dict[int, str], dict[str, Mobject]]


def names(scene: Scene, frame: FrameType | None) -> Names:
    """The code's names for the scene's objects — its running variables, then the scene's
    attributes, and indices into the groups they name, a few levels deep — and the groups by
    their bare names."""
    named: dict[int, str] = {}
    bare: dict[str, Mobject] = {}

    def visit(mob: Mobject, name: str, depth: int) -> None:
        if id(mob) in named:
            return
        named[id(mob)] = name
        if "[" not in name:
            bare.setdefault(name, mob)
        if depth < 3:
            for i, sub in enumerate(mob.submobjects[:64]):
                visit(sub, f"{name}[{i}]", depth + 1)

    scopes: list[tuple[str, dict[str, object]]] = []
    while frame is not None:
        if not frame.f_code.co_filename.startswith(PACKAGE):
            scopes.append(("", dict(frame.f_locals)))
        frame = frame.f_back
    own = {k: v for k, v in vars(scene).items() if k not in SCENE_OWN}
    scopes.append(("self.", own))
    for prefix, scope in scopes:
        for key, value in scope.items():
            if key.startswith("_") or key == "self":
                continue
            if isinstance(value, Mobject):
                visit(value, prefix + key, 0)
            elif isinstance(value, list | tuple) and 0 < len(value) <= 64:
                for i, item in enumerate(value):
                    if isinstance(item, Mobject):
                        visit(item, f"{prefix}{key}[{i}]", 1)
    return named, bare


def text_of(mob: Mobject) -> str:
    """What a text says (empty if it keeps no source)."""
    if isinstance(mob, manimgx.DecimalNumber):
        return f"{mob.get_value():g}"
    for attr in ("text", "tex_string", "original_text", "source"):
        value = getattr(mob, attr, None)
        if isinstance(value, str) and value:
            return value
    return ""


def _paint(mob: Mobject) -> tuple[float, bool]:
    """How much it fills (opacity), and whether its outline shows (a hairline of opacity ×
    width below 0.02 does not)."""
    fill = float(np.max(np.atleast_1d(mob.get_fill_opacity())))
    stroke = float(np.max(np.atleast_1d(mob.get_stroke_opacity())))
    width = float(np.max(np.atleast_1d(mob.get_stroke_width())))
    return fill, stroke * width > 0.02


def _visible(mob: Mobject) -> bool:
    fill, stroked = _paint(mob)
    return fill > 0.02 or stroked


def outline(mob: Mobject) -> np.ndarray | None:
    """A path's cubic curves as polylines (17 samples each): (curves, 17, 2)."""
    points = mob.points
    if len(points) < 4:
        return points[None, :, :2] if len(points) >= 2 else None
    curves = points[: len(points) // 4 * 4].reshape(-1, 4, points.shape[1])[:, :, :2]
    t = np.linspace(0, 1, 17)
    basis = np.stack(
        [(1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t**2, t**3], axis=1
    )
    return np.einsum("tk,ckd->ctd", basis, curves)


@dataclass(frozen=True, slots=True)
class View:
    """What the viewer sees at a moment: the camera's frame (scene units) and the things in
    it, in draw order."""

    frame: Box
    things: list[Thing]
    framed: bool  # the camera has moved or zoomed: it frames part of a larger world


def view(scene: Scene, known: Names | None = None) -> View:
    """What the viewer sees now. Names from the running code take precedence over `known`,
    which preserves local names after `construct` returns."""
    (x0, y0), (x1, y1) = (scene.camera.frame.get_corner(c)[:2] for c in (DL, UR))
    frame = (float(x0), float(y0), float(x1), float(y1))
    w, h = config.frame_width / 2, config.frame_height / 2
    framed = max(abs(a - b) for a, b in zip(frame, (-w, -h, w, h), strict=True)) > 1e-3
    current = names(scene, written_frame())
    if known is not None:
        current = (known[0] | current[0], known[1] | current[1])
    return View(frame, seen(scene, current), framed)


def seen(scene: Scene, scope: Names) -> list[Thing]:
    """What the viewer sees now, in draw order."""
    named, bare = scope
    order = {id(leaf): i for i, leaf in enumerate(scene.display_list())}
    out: list[Thing] = []

    def name_of(mob: Mobject, chain: list[Mobject]) -> str:
        for m in reversed(chain):
            if id(m) in named:
                return named[id(m)] + ("" if m is mob else "…")
        return type(mob).__name__

    def root_of(name: str, chain: list[Mobject]) -> tuple[str, str]:
        group = bare.get(name.split("[")[0].rstrip("…"))
        if group is not None:
            return name.split("[")[0].rstrip("…"), type(group).__name__
        top = chain[0]
        return named.get(id(top), type(top).__name__), type(top).__name__

    def visit(mob: Mobject, chain: list[Mobject]) -> None:
        chain = [*chain, mob]
        if isinstance(mob, TEXTS):
            leaves = [m for m in mob.family_members_with_points() if _visible(m)]
            if not leaves:
                return
            points = np.concatenate([m.points for m in leaves])[:, :2]
            (x0, y0), (x1, y1) = points.min(axis=0), points.max(axis=0)
            if min(x1 - x0, y1 - y0) <= EMPTY:
                return  # glyphs without area
            backs = [
                order.get(id(m), 0)
                for m in leaves
                if isinstance(m, manimgx.BackgroundRectangle) and _paint(m)[0] >= 0.9
            ]
            name = name_of(mob, chain)
            root, root_kind = root_of(name, chain)
            out.append(
                Thing(
                    name=name,
                    kind=type(mob).__name__,
                    text=text_of(mob),
                    box=(x0, y0, x1, y1),
                    outline=None,
                    fill=1.0,
                    stroked=False,
                    closed=True,
                    order=min(order.get(id(m), 0) for m in leaves),
                    root=root,
                    root_kind=root_kind,
                    backdrop=min(backs) if backs else None,
                    ink=hash(np.round(points, 3).tobytes()),
                )
            )
            return
        if (
            mob.has_points()
            and id(mob) in order
            and isinstance(mob, DRAWN)
            and _visible(mob)
            and (thing := shape(mob, chain)) is not None
        ):
            out.append(thing)
        for sub in mob.submobjects:
            visit(sub, chain)

    def shape(mob: Mobject, chain: list[Mobject]) -> Thing | None:
        curves = outline(mob) if isinstance(mob, manimgx.VMobject) else None
        extent = curves.reshape(-1, 2) if curves is not None else mob.points[:, :2]
        (x0, y0), (x1, y1) = extent.min(axis=0), extent.max(axis=0)
        fill, stroked = _paint(mob)
        if min(x1 - x0, y1 - y0) <= EMPTY and not (
            stroked and max(x1 - x0, y1 - y0) > EMPTY
        ):
            return None  # no area to fill, no length to stroke
        closed = isinstance(mob, manimgx.VMobject) and all(
            c for _, _, c in subpath_ranges(mob.points, 1e-6)
        )
        name = name_of(mob, chain)
        root, root_kind = root_of(name, chain)
        return Thing(
            name=name,
            kind=type(mob).__name__,
            text=None,
            box=(x0, y0, x1, y1),
            outline=curves,
            fill=fill,
            stroked=stroked,
            closed=closed,
            order=order[id(mob)],
            root=root,
            root_kind=root_kind,
            backdrop=None,
            ink=0,
        )

    for mob in scene.mobjects:
        visit(mob, [])
    for mob in scene.foreground_mobjects:
        if mob not in scene.mobjects:
            visit(mob, [])
    return out


GRIDS = {
    "NumberPlane",
    "ComplexPlane",
    "PolarPlane",
    "ArrowVectorField",
    "StreamLines",
    "VectorField",
}
# sized to sit behind text: their edges are no collision
BACKDROPS = {"BackgroundRectangle"}
# scene units (4 px at 1080p): a line this close to a glyph's box touches it
TOUCH = 0.03
# pixels tall at 1080p: text below this is hard to read
SMALL = 20


type Moment = tuple[Fraction, tuple[str, int] | None]  # time and source location


@dataclass
class Problem:
    kind: str  # cut, runs off (a note), overlap, crossing, covered, small
    subject: Thing
    other: Thing | None
    detail: str
    moments: list[Moment] = field(default_factory=list[Moment])

    @property
    def note(self) -> bool:
        return self.kind == "runs off"

    def key(self) -> tuple[str, str, str | None, str | None]:
        other = None if self.other is None else self.other.name
        return (self.kind, self.subject.name, self.subject.text, other)


def _area(b: Box) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _common(a: Box, b: Box) -> Box:
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def _meet(a: Box, b: Box) -> bool:
    """Do two boxes share a point? (A line's box has no height; it still meets a text's.)"""
    x0, y0, x1, y1 = _common(a, b)
    return x0 <= x1 and y0 <= y1


def _grow(b: Box, by: float) -> Box:
    return (b[0] - by, b[1] - by, b[2] + by, b[3] + by)


def crosses(curves: np.ndarray, box: Box) -> bool:
    """Does any segment of these polylines pass through the box (Liang–Barsky, all at once)?"""
    a = curves[:, :-1].reshape(-1, 2)
    d = curves[:, 1:].reshape(-1, 2) - a
    x0, y0, x1, y1 = box
    enter, leave = np.zeros(len(a)), np.ones(len(a))
    inside = np.ones(len(a), bool)
    for p, q in (
        (-d[:, 0], a[:, 0] - x0),
        (d[:, 0], x1 - a[:, 0]),
        (-d[:, 1], a[:, 1] - y0),
        (d[:, 1], y1 - a[:, 1]),
    ):
        parallel = p == 0
        inside &= ~(parallel & (q < 0))
        r = np.divide(q, p, out=np.zeros_like(q), where=~parallel)
        enter = np.where(~parallel & (p < 0), np.maximum(enter, r), enter)
        leave = np.where(~parallel & (p > 0), np.minimum(leave, r), leave)
    return bool(np.any(inside & (enter <= leave)))


def covers(curves: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Which points the region these closed polylines bound covers (even-odd rule)."""
    a = curves[:, :-1].reshape(-1, 2)
    b = curves[:, 1:].reshape(-1, 2)
    px, py = points[:, 0:1], points[:, 1:2]
    straddle = (a[:, 1] > py) != (b[:, 1] > py)
    with np.errstate(divide="ignore", invalid="ignore"):
        x = a[:, 0] + (py - a[:, 1]) * (b[:, 0] - a[:, 0]) / (b[:, 1] - a[:, 1])
    return np.sum(straddle & (px < x), axis=1) % 2 == 1


def _grid(box: Box, n: int) -> np.ndarray:
    xs, ys = np.linspace(box[0], box[2], n), np.linspace(box[1], box[3], n)
    return np.array([(x, y) for x in xs for y in ys])


def _cut(box: Box, frame: Box) -> str | None:
    x0, y0, x1, y1 = box
    f0, g0, f1, g1 = frame
    past = [
        (f0 - x0, "left"),
        (x1 - f1, "right"),
        (y1 - g1, "top"),
        (g0 - y0, "bottom"),
    ]
    sides = [f"{d:.2f} past the {side} edge" for d, side in past if d > 0.02]
    if not sides:
        return None
    if x1 < f0 or x0 > f1 or y1 < g0 or y0 > g1:
        return "outside the frame (not visible)"
    return ", ".join(sides)


def at(seen: View) -> list[Problem]:
    """The problems a viewer sees in this view."""
    frame, things = seen.frame, seen.things
    px_per_unit = 1080 / (frame[3] - frame[1])
    now: list[Problem] = []
    texts = [t for t in things if t.text is not None]
    shapes = [t for t in things if t.outline is not None]
    groups: dict[str, list[Thing]] = {}
    for t in things:
        groups.setdefault(t.root, []).append(t)
    for root, parts in groups.items():
        if parts[0].root_kind in GRIDS:
            continue
        box = (
            min(p.box[0] for p in parts),
            min(p.box[1] for p in parts),
            max(p.box[2] for p in parts),
            max(p.box[3] for p in parts),
        )
        detail = _cut(box, frame)
        if detail is None:
            continue
        whole = replace(
            parts[0],
            name=root,
            kind=parts[0].root_kind,
            box=box,
            text=parts[0].text if len(parts) == 1 else None,
        )
        # meant often enough to be notes: a line or a graph leaving the frame, what is out of
        # sight altogether, and what a moved or zoomed camera shows only part of
        lines = all(p.outline is not None and not p.closed for p in parts)
        gone = detail.startswith("outside")
        partial = seen.framed and not (len(parts) == 1 and parts[0].text is not None)
        note = lines or gone or partial
        now.append(Problem("runs off" if note else "cut", whole, None, detail))
    for i, a in enumerate(texts):
        for b in texts[i + 1 :]:
            if a.ink == b.ink or max(abs(u - v) for u, v in zip(a.box, b.box)) < 0.01:
                continue  # the same glyphs in one place (a transform's copy): one text
            common = _area(_common(a.box, b.box))
            if common > 1e-4 and common > 0.05 * min(_area(a.box), _area(b.box)):
                now.append(Problem("overlap", a, b, "texts overlap"))
    for a in texts:
        tall = (a.box[3] - a.box[1]) * px_per_unit
        if tall < SMALL:
            now.append(
                Problem("small", a, None, f"text is {tall:.0f} px tall at 1080p")
            )
        near = _grow(a.box, TOUCH)
        samples = _grid(a.box, 7)
        corners = _grid(near, 2)
        # opaque fills under the text that cover it: lines drawn before them are hidden
        backs = [
            s.order
            for s in shapes
            if s.outline is not None
            and s.fill >= 0.9
            and s.order < a.order
            and covers(s.outline, corners).all()
        ]
        if a.backdrop is not None:
            backs.append(a.backdrop)
        for s in shapes:
            if s.outline is None or not _meet(near, s.box):
                continue
            under = s.order < a.order
            edged = s.stroked or (s.fill >= 0.2 and s.kind not in BACKDROPS)
            if edged and crosses(s.outline, near):
                if under and (s.root_kind in GRIDS or any(s.order < b for b in backs)):
                    continue  # a grid line, or one behind the text's backdrop
                what = "runs through" if s.stroked else "has its edge through"
                now.append(Problem("crossing", a, s, f"{s.kind} {what} the text"))
            elif s.fill >= 0.5 and not under:
                share = float(np.mean(covers(s.outline, samples)))
                if share > 0.3:
                    detail = f"{s.kind} is drawn over {share:.0%} of it"
                    now.append(Problem("covered", a, s, detail))
    return now


class Layout:
    """A take's problems at sampled moments: each once, with the moments it appears in; the
    problems (not the notes) numbered from 1 in the order they first appear — as the report
    and the storyboard number them."""

    def __init__(self) -> None:
        self.found: dict[tuple[str, str, str | None, str | None], Problem] = {}
        self.numbers: dict[tuple[str, str, str | None, str | None], int] = {}

    def see(self, moment: Moment, seen: View) -> list[tuple[int, Problem]]:
        """The problems at this moment, and their numbers (0: a note)."""
        out = []
        for problem in at(seen):
            key = problem.key()
            self.found.setdefault(key, problem).moments.append(moment)
            if not problem.note and key not in self.numbers:
                self.numbers[key] = len(self.numbers) + 1
            out.append((self.numbers.get(key, 0), problem))
        return out


def _label(t: Thing) -> str:
    said = " ".join((t.text or "").split())
    said = said if len(said) <= 30 else said[:29] + "…"
    what = f"{t.kind} {said!r}" if t.text else t.kind
    return f"{t.name} ({what})" if t.name != t.kind else what


def _when(moments: list[Moment]) -> str:
    """When a problem is seen, and the line that played its first sample."""
    first, last = f"{float(moments[0][0]):g}", f"{float(moments[-1][0]):g}"
    span = f"t={first}s" if first == last else f"t={first}–{last}s"
    where = moments[0][1]
    return span if where is None else f"{span} ({Path(where[0]).name}:{where[1]})"


def report(layout: Layout, checked: int, similar: int = 3) -> str:
    """A line per problem, by number; more than `similar` alike in a row (a label on each of
    four planets) show the first and fold the rest; then the notes."""
    found = layout.found
    if not checked:
        return "layout: not checked (no samples)"
    if not found:
        return f"layout: no problems in {checked} sample{'' if checked == 1 else 's'}"
    real = sorted((n, found[k]) for k, n in layout.numbers.items())
    notes = [p for p in found.values() if p.note]
    head = f"layout: {len(real)} problem{'' if len(real) == 1 else 's'}"
    if notes:
        head += f", {len(notes)} note{'' if len(notes) == 1 else 's'} (likely meant)"
    lines = [head]
    runs: list[list[tuple[int, Problem]]] = []
    for n, p in real:
        if runs and _alike(runs[-1][-1][1], p):
            runs[-1].append((n, p))
        else:
            runs.append([(n, p)])
    for run in runs:
        for n, p in run if len(run) <= similar else run[:1]:
            lines.append(f"  [{n}] {_line(p)}")
        if len(run) > similar:
            names = ", ".join(p.subject.name for _, p in run[1:])
            lines.append(f"      [{run[1][0]}–{run[-1][0]}] the same for {names}")
    lines += [f"  note: {_line(p)}" for p in notes]
    return "\n".join(lines)


def _alike(a: Problem, b: Problem) -> bool:
    """Problems of one kind between the same two named groups."""

    def shape(p: Problem) -> tuple[object, ...]:
        other = None if p.other is None else (p.other.root, p.other.kind)
        return (p.kind, p.subject.root, p.subject.kind, other)

    return shape(a) == shape(b)


def _line(p: Problem) -> str:
    other = "" if p.other is None else f" and {_label(p.other)}"
    return f"{_when(p.moments)}  {_label(p.subject)}{other}: {p.detail}"

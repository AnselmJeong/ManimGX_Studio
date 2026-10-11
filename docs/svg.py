"""Scenes as animated SVGs: what ManimGX draws, frame by frame, as paths an SVG plays.

GitHub and PyPI show a README's images but play no video, and a video made into an animated
image is large and soft. A scene made of paths (curves, shapes, text; no surfaces, meshes or
point clouds) is shown instead as an SVG that plays itself (SMIL), sharp at any size:
`record` runs the scene and reads, at every frame, its view and each path's paint (the
stretch of it drawn, its stroke, its fill), and `write` turns the recording into the SVG.
Each path is written at its whole shape, seen through the camera at keyframes the browser
interpolates (if the camera moves), drawn as far as its reveal has come by an animated
dash, and painted as its frames paint it. A path must keep its shape (the camera may move):
a scene whose paths change shape is refused. The SVG has no background: the page's shows
through, and a light page takes its own variant, whose white ink is dark.
"""

import itertools
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

import manimgx as m
from manimgx.rendering import feed

KEYFRAME = 0.6  # seconds between the views of a moving camera that are written
SAMPLES = 16  # points a long subpath seen by a moving camera is written through
EXACT = 24  # curves a subpath may have to be written as it is, however the camera moves
INK = "#1F2328"  # GitHub's text on a light page: what a scene's white ink is drawn in there

type Paint = tuple[float, float, np.ndarray, float, np.ndarray]
"""A path's paint at a frame: the stretch drawn (from, to, in curve parameter), its stroke
(RGBA), its stroke's width (pixels) and its fill (RGBA)."""


@dataclass
class Drawn:
    """A path the scene draws: its control points (four a curve), whether it is fixed in
    the frame, and its paint at each frame it is drawn."""

    points: np.ndarray
    fixed: bool
    paints: dict[int, Paint] = field(default_factory=dict)


@dataclass
class Recording:
    """What a scene drew: its size in pixels and frame rate, the view of what is fixed in
    the frame, its length in frames, its view (world → clip) at each frame, and its paths,
    in the order they are drawn."""

    size: tuple[int, int]
    fps: int
    overlay: np.ndarray
    frames: int = 0
    three_d: bool = False
    views: dict[int, np.ndarray] = field(default_factory=dict)
    paths: dict[int, Drawn] = field(default_factory=dict)

    def capture(
        self, frame: int, repeat: int, camera: m.Camera, mobjects: list[m.Mobject]
    ) -> None:
        """Keep a frame, shown `repeat` times: its view, and each path's paint."""
        width, height = self.size
        unit = height / camera.frame_height  # pixels a scene unit, as the engine's
        _, self.views[frame], self.three_d = feed.view(camera, width, height)
        fixed = camera.fixed_in_frame_mobjects
        for mob in mobjects:
            if isinstance(mob, m.PMobject | m.MeshMobject):  # (an image is a mesh)
                raise ValueError(f"an SVG shows paths only, not a {type(mob).__name__}")
            if not isinstance(mob, m.VMobject):
                continue  # nothing the engine draws either (a value tracker)
            drawn = self.paths.setdefault(id(mob), Drawn(mob.points, mob in fixed))
            if mob.points is not drawn.points and not (  # a tween's rounding aside
                mob.points.shape == drawn.points.shape
                and np.allclose(mob.points, drawn.points, rtol=0, atol=1e-9)
            ):
                raise ValueError(f"a {type(mob).__name__} changes shape")
            paint = mob.paint
            lo, hi = paint.window(len(mob.points) // 4)
            stroke, fill = paint.stroke[0].copy(), paint.fill[0].copy()
            drawn.paints[frame] = (
                lo,
                hi,
                stroke,
                paint.stroke_width * 0.01 * unit,
                fill,
            )
        self.frames = frame + repeat


def record(scene: type[m.Scene]) -> Recording:
    """Run a scene, keeping every frame it draws. None is played at once: a scene updater
    that does nothing has every frame computed, and those are the same frames."""
    width, height = m.config.pixel_width, m.config.pixel_height
    hw, hh = m.config.frame_width / 2, m.config.frame_height / 2
    recording = Recording(
        (width, height),
        int(m.config.frame_rate),
        np.diag([1 / hw, 1 / hh, 0.0, 1.0]),
    )

    def setup(self: m.Scene) -> None:
        scene.setup(self)
        self.add_updater(lambda dt: None)

    def emit(self: m.Scene, repeat: int = 1) -> None:
        if repeat > 0:
            recording.capture(self.frame, repeat, self.camera, self.display_list())
        scene._emit(self, repeat)

    type(scene.__name__, (scene,), {"setup": setup, "_emit": emit})().render()
    return recording


def write(
    recording: Recording, file: Path, fade: float = 0.4, light: bool = False
) -> None:
    """Write a recording as an SVG that loops, fading out over its last `fade` seconds, on
    no background. For a light page (`light`), the scene's white ink (a color whose every
    channel is at least 0.75: its text, say) is drawn in the page's (`INK`)."""
    width, height = recording.size
    total, fps = recording.frames, recording.fps
    first = recording.views[0]
    moving = any(not np.array_equal(v, first) for v in recording.views.values())
    step = max(1, round(KEYFRAME * fps))
    keys = sorted({*range(0, total, step), total - 1} & recording.views.keys())
    timing = Timing(total, total / fps)
    body = []
    for drawn in _order(recording, keys):
        body += _elements(drawn, recording, timing, keys if moving else [0], light)
    out = timing.frames - round(fade * fps)
    fading = timing.animate("opacity", ["1", "1", "0"], [0, out, timing.frames])
    file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"'
        f' viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f"<g>{fading}{''.join(body)}</g></svg>\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class Timing:
    """A film's length, in frames and in seconds: an attribute's values at frames, as an
    animation that loops with it."""

    frames: int
    seconds: float

    def animate(
        self, name: str, values: list[str], at: list[int], discrete: bool = False
    ) -> str:
        times = ";".join(f"{f / self.frames:.5g}" for f in at)
        mode = ' calcMode="discrete"' if discrete else ""
        return (
            f'<animate attributeName="{name}" dur="{self.seconds:g}s"'
            f' repeatCount="indefinite"{mode} keyTimes="{times}"'
            f' values="{";".join(values)}"/>'
        )

    def track(
        self, name: str, texts: list[str], values: np.ndarray, tolerance: float
    ) -> tuple[str, str]:
        """An attribute through the frames: its first value, and its animation (none if
        it holds), through the frames that keep it within `tolerance` of every frame."""
        if all(t == texts[0] for t in texts):
            return texts[0], ""
        keep = _breakpoints(values, tolerance)
        return texts[0], self.animate(
            name, [texts[k] for k in keep] + [texts[-1]], keep + [self.frames]
        )


def _elements(
    drawn: Drawn, recording: Recording, timing: Timing, keys: list[int], light: bool
) -> list[str]:
    """A path's elements: its fill (one element for all its subpaths, so that holes stay
    holes), then its stroke (one element a subpath, dashed as far as it is drawn)."""
    frames = sorted(drawn.paints)
    everything = np.arange(timing.frames)
    # a frame the path is not drawn at takes the paint of the last it is drawn at
    at = np.maximum(np.searchsorted(frames, everything, side="right") - 1, 0)
    paints = [drawn.paints[frames[i]] for i in at]
    stroke = np.array([p[2] for p in paints])
    width = np.array([p[3] for p in paints])
    fill = np.array([p[4] for p in paints])
    curves = drawn.points.reshape(-1, 4, 3)
    parts = _subpaths(curves)
    keys = [0] if drawn.fixed else keys
    views = [_view(drawn, recording, f) for f in keys]
    digits = 0 if len(keys) > 1 else 1  # whole pixels for a moving camera's paths
    shapes = [
        [_shape(curves[a:b], v, recording.size, digits) for v in views]
        for a, b in parts
    ]
    shown = np.isin(everything, frames)
    common = []
    if not shown.all():
        states = ["visible" if s else "hidden" for s in shown]
        changes = [0, *(k for k in everything[1:] if states[k] != states[k - 1])]
        common.append(
            timing.animate(
                "visibility",
                [states[k] for k in changes] + [states[-1]],
                [*changes, timing.frames],
                discrete=True,
            )
        )
    elements = []
    if (fill[:, 3] > 0).any():
        data = [" ".join(shape[i] for shape in shapes) for i in range(len(keys))]
        attributes = {"d": data[0], "stroke": "none"}
        animations = [_keyframes("d", data, keys, timing), *common]
        _paint("fill", fill, timing, attributes, animations, light)
        elements.append(_element(attributes, animations))
    if (stroke[:, 3] > 0).any() and (width > 0).any():
        lo_hi = np.array([(p[0], p[1]) for p in paints])
        for (a, b), shape in zip(parts, shapes, strict=True):
            attributes = {"d": shape[0], "fill": "none", "stroke-linejoin": "round"}
            animations = [_keyframes("d", shape, keys, timing), *common]
            _paint("stroke", stroke, timing, attributes, animations, light)
            texts = [_number(w, 2) for w in width]
            attributes["stroke-width"], moving = timing.track(
                "stroke-width", texts, width[:, None], 0.05
            )
            animations.append(moving)
            windows = _windows(drawn, a, b, lo_hi, recording)
            if not ((windows[:, 0] <= 1e-4) & (windows[:, 1] >= 1 - 1e-4)).all():
                attributes["pathLength"] = "1"
                texts = [f"0 {_number(x, 4)} {_number(y - x, 4)} 2" for x, y in windows]
                attributes["stroke-dasharray"], moving = timing.track(
                    "stroke-dasharray", texts, windows, 0.002
                )
                animations.append(moving)
            elements.append(_element(attributes, animations))
    return elements


def _order(recording: Recording, keys: list[int]) -> list[Drawn]:
    """The paths in the order an SVG draws them: as the scene draws them in 2D; in 3D,
    which has a depth test and an SVG none, from the farthest on average to the nearest,
    then what is fixed in the frame, over everything."""
    paths = list(recording.paths.values())
    if not recording.three_d:
        return paths

    def distance(drawn: Drawn) -> float:  # clip w grows with the distance from the eye
        anchors = drawn.points[::4]
        views = [recording.views[f] for f in keys]
        return float(np.mean([anchors @ v[3, :3] + v[3, 3] for v in views]))

    seen = sorted((d for d in paths if not d.fixed), key=distance, reverse=True)
    return seen + [d for d in paths if d.fixed]


def _paint(
    name: str,
    rgba: np.ndarray,
    timing: Timing,
    attributes: dict[str, str],
    animations: list[str],
    light: bool,
) -> None:
    """A fill's or a stroke's color and opacity, each animated if it changes: on a light
    page, white ink in the page's."""
    colors = [
        INK if light and (c[:3] >= 0.75).all() else m.ManimColor(c[:3]).to_hex()
        for c in rgba
    ]
    attributes[name], moving = timing.track(name, colors, rgba[:, :3], 1 / 255)
    animations.append(moving)
    opacity = [_number(a, 3) for a in rgba[:, 3]]
    attributes[f"{name}-opacity"], moving = timing.track(
        f"{name}-opacity", opacity, rgba[:, 3:], 0.004
    )
    animations.append(moving)


def _keyframes(name: str, values: list[str], keys: list[int], timing: Timing) -> str:
    """An attribute through its values at keyframes (none if it has one), the last held."""
    if len(values) < 2:
        return ""
    return timing.animate(name, [*values, values[-1]], [*keys, timing.frames])


def _element(attributes: dict[str, str], animations: list[str]) -> str:
    text = "".join(f' {name}="{value}"' for name, value in attributes.items())
    inner = "".join(animations)
    return f"<path{text}>{inner}</path>" if inner else f"<path{text}/>"


def _view(drawn: Drawn, recording: Recording, frame: int) -> np.ndarray:
    """The view a path is seen through at a frame: the frame's own, fixed in the frame."""
    if drawn.fixed:
        return recording.overlay
    return recording.views[max(f for f in recording.views if f <= frame)]


def _windows(
    drawn: Drawn, a: int, b: int, lo_hi: np.ndarray, recording: Recording
) -> np.ndarray:
    """The stretch of the subpath of curves a … b drawn at each frame, from and to, as
    fractions of its length on screen."""
    curves = drawn.points.reshape(-1, 4, 3)[a:b]
    u = np.linspace(0, b - a, 4 * (b - a) + 1)  # four samples a curve
    dense = _evaluate(curves, u)
    local = np.clip(lo_hi - a, 0, b - a)
    windows = np.where(local[:, 1:] > local[:, :1], [0.0, 1.0], [0.0, 0.0])
    for k in np.flatnonzero(
        (local[:, 1] > local[:, 0]) & ((local[:, 0] > 0) | (local[:, 1] < b - a))
    ):
        screen = _screen(dense, _view(drawn, recording, int(k)), recording.size)
        steps = np.linalg.norm(np.diff(screen, axis=0), axis=1)
        length = np.concatenate([[0.0], np.cumsum(steps)])
        windows[k] = np.interp(local[k], u, length) / max(length[-1], 1e-9)
    return windows


def _subpaths(curves: np.ndarray) -> list[tuple[int, int]]:
    """Where a path's subpaths are: the ranges of its curves that join end to start."""
    gaps = np.linalg.norm(curves[1:, 0] - curves[:-1, 3], axis=1) > 1e-6
    edges = [0, *(int(g) + 1 for g in np.flatnonzero(gaps)), len(curves)]
    return list(itertools.pairwise(edges))


def _shape(
    curves: np.ndarray, view: np.ndarray, size: tuple[int, int], digits: int
) -> str:
    """A subpath as SVG path data, on screen through a view: its own curves if they are
    few, else a smooth curve through points evenly spaced along it (the same points at
    every keyframe, so that the browser interpolates between them)."""
    closed = bool(np.linalg.norm(curves[0, 0] - curves[-1, 3]) < 1e-6)
    if len(curves) <= EXACT:
        points = _screen(curves.reshape(-1, 3), view, size).reshape(-1, 4, 2)
        data = "M" + _pair(points[0, 0], digits)
        data += "".join("C" + " ".join(_pair(q, digits) for q in c[1:]) for c in points)
        return data + ("Z" if closed else "")
    u = np.arange(len(curves) + 1, dtype=float)
    anchors = _evaluate(curves, u)
    steps = np.linalg.norm(np.diff(anchors, axis=0), axis=1)
    length = np.concatenate([[0.0], np.cumsum(steps)])
    count = SAMPLES if closed else SAMPLES + 1
    at = np.linspace(0, length[-1], count, endpoint=not closed)
    p = _screen(_evaluate(curves, np.interp(at, length, u)), view, size)
    if closed:  # Catmull-Rom's tangents, as Bézier handles
        before, after, beyond = (np.roll(p, s, axis=0) for s in (1, -1, -2))
    else:
        before = np.vstack([p[:1], p[:-1]])
        after = np.vstack([p[1:], p[-1:]])
        beyond = np.vstack([p[2:], p[-1:], p[-1:]])
    first, second = p + (after - before) / 6, after - (beyond - p) / 6
    data = "M" + _pair(p[0], digits)
    for i in range(len(p) if closed else len(p) - 1):
        data += "C" + " ".join(
            _pair(q, digits) for q in (first[i], second[i], after[i])
        )
    return data + ("Z" if closed else "")


def _evaluate(curves: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Points of a path's cubic Bézier curves at curve parameters u ∈ [0, curves]."""
    i = np.clip(np.floor(u).astype(int), 0, len(curves) - 1)
    t = (u - i)[:, None]
    c = curves[i]
    return (
        (1 - t) ** 3 * c[:, 0]
        + 3 * (1 - t) ** 2 * t * c[:, 1]
        + 3 * (1 - t) * t**2 * c[:, 2]
        + t**3 * c[:, 3]
    )


def _screen(points: np.ndarray, view: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Scene points on screen, in pixels from the top left, through a view (world → clip)."""
    clip = points @ view[:, :3].T + view[:, 3]
    ndc = clip[:, :2] / clip[:, 3:4]
    width, height = size
    return np.column_stack([(ndc[:, 0] + 1) / 2 * width, (1 - ndc[:, 1]) / 2 * height])


def _breakpoints(values: np.ndarray, tolerance: float) -> list[int]:
    """The frames to keep of a series (frames × dimensions) for the lines between them to
    stay within `tolerance` of every frame (Ramer–Douglas–Peucker)."""
    keep = {0, len(values) - 1}
    stack = [(0, len(values) - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        t = (np.arange(a + 1, b) - a) / (b - a)
        line = values[a] + t[:, None] * (values[b] - values[a])
        error = np.abs(values[a + 1 : b] - line).max(axis=1)
        worst = int(np.argmax(error))
        if error[worst] > tolerance:
            k = a + 1 + worst
            keep.add(k)
            stack += [(a, k), (k, b)]
    return sorted(keep)


def _pair(p: np.ndarray, digits: int) -> str:
    return f"{_number(p[0], digits)} {_number(p[1], digits)}"


def _number(v: float, digits: int) -> str:
    text = f"{v:.{digits}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text

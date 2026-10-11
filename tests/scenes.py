"""Scenes made of functions, and stories to tell: the kit for what scenes show.

`scene(construct)` is a scene whose `construct` is a function (`scene_3d`, a 3D scene's);
`frames(scene)` draws a scene and keeps every frame it shows; `instants(construct, probe)`
keeps what `probe` sees of a scene at every instant it computes.

A scene with no video and no pixel sink counts its frames without drawing them, so a story
costs milliseconds. `record(story, fps, fast)` tells a story and keeps what each frame shows of
the stage (the mobjects the story puts on it), leaf by leaf, on the path the scene takes: a play
computed ahead of time ("fast", as the film receives it) or frame by frame (`fast=False`).
`stories()` draws random stories: a stage of shapes, then plays of animation trees, as data
Hypothesis can shrink.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING, NamedTuple

import numpy as np
from hypothesis import strategies as st

import manimgx as m
from manimgx.animation import easing as rf
from manimgx.config import config
from manimgx.drawing.geometry import bezier_remap
from manimgx.drawing.paint import Paint
from manimgx.rendering.film import Frame
from manimgx.scene import _tracks

if TYPE_CHECKING:
    from manimgx.animation.transform import Transform
    from manimgx.drawing.geometry import Path
    from manimgx.scene import Act


def scene(construct: Callable[[m.Scene], None]) -> m.Scene:
    """A scene whose `construct` is `construct`."""

    class Told(m.Scene):
        def construct(self) -> None:
            construct(self)

    return Told()


def scene_3d(construct: Callable[[m.ThreeDScene], None]) -> m.ThreeDScene:
    """A 3D scene whose `construct` is `construct`."""

    class Told(m.ThreeDScene):
        def construct(self) -> None:
            construct(self)

    return Told()


def frames(scene: m.Scene) -> list[np.ndarray]:
    """Every frame `scene` shows, drawn at the configured size: (height, width, 4) rows of
    red, green, blue and opacity, 0 to 255; a frame shown n times, n times."""
    shape = (config.pixel_height, config.pixel_width, 4)
    shown: list[np.ndarray] = []

    def keep(frame: Frame) -> None:
        pixels = np.frombuffer(frame.pixels(), np.uint8).reshape(shape)
        shown.extend([pixels] * frame.repeat)

    scene.render(None, frames=keep)
    return shown


def instants[T](
    construct: Callable[[m.Scene], None], probe: Callable[[m.Scene], T]
) -> dict[Fraction, T]:
    """What `probe` sees of the scene at every instant it computes (frames, plays' ends, the
    closing frame), every frame computed (none ahead): the world at each instant, once what
    opens at it has begun."""
    seen: dict[Fraction, T] = {}

    class Probed(m.Scene):
        def construct(self) -> None:
            construct(self)

        def _instant(
            self,
            t: Fraction,
            act: "Act | None" = None,
            stepping: bool = True,
            framing: bool = True,
        ) -> None:
            super()._instant(t, act, stepping, framing)
            seen[t] = probe(self)

        def _pure_tweens(self, anim: m.Animation, alpha: list[float]) -> None:
            return None

    Probed().render()
    return seen


class Look(NamedTuple):
    """What a leaf shows: its points (compared by `same_look`), and its paint, rounded."""

    points: np.ndarray
    brushes: tuple[bytes, ...]  # fill, stroke, background, and the trim window
    widths: tuple[float, float]
    dash: tuple[float, ...] | None


type Shot = tuple[Look, ...]
"""What a frame shows: the looks of the leaves it draws, in drawing order."""


def look(leaf: m.Mobject) -> Look:
    p = leaf.paint
    return Look(
        np.array(leaf.points),
        tuple(
            np.round(getattr(p, name), 9).tobytes()
            for name in ("fill", "stroke", "background", "trim")
        ),
        (round(float(p.stroke_width), 9), round(float(p.background_width), 9)),
        None if p.dash is None else tuple(round(x, 9) for x in p.dash),
    )


def same_look(a: Look, b: Look) -> bool:
    """Do two looks draw the same? The same paint, and the same curves: a path cut into more
    curves (as aligning it for a transform cuts it) is the same path."""
    if (a.brushes, a.widths, a.dash) != (b.brushes, b.widths, b.dash):
        return False
    pa, pb = (
        (a.points, b.points) if len(a.points) <= len(b.points) else (b.points, a.points)
    )
    if len(pa) != len(pb) and len(pa) % 4 == 0 and len(pa) and len(pb) % 4 == 0:
        pa = bezier_remap(pa.reshape(-1, 4, 3), len(pb) // 4).reshape(-1, 3)
    return pa.shape == pb.shape and np.allclose(pa, pb, rtol=0, atol=1e-9)


def assert_same_shots(x: Shot, y: Shot, where: str) -> None:
    assert len(x) == len(y), f"{where}: {len(x)} leaves drawn, not {len(y)}"
    for i, (p, q) in enumerate(zip(x, y, strict=True)):
        assert same_look(p, q), f"{where}: leaf {i} differs"


def assert_same_frames(a: dict[int, Shot], b: dict[int, Shot]) -> None:
    """Two recordings show the same frames: the same leaves drawn in the same order, alike."""
    assert sorted(a) == sorted(b)
    for k in a:
        assert_same_shots(a[k], b[k], f"frame {k}")


def outcome(
    story: Callable[["Recorder"], None], fps: int = 10, fast: bool = True
) -> "Recorder | type":
    """What telling a story comes to: its recording, or the kind of error it raises (a story
    may ask the impossible, as two replacements of one mobject in one play)."""
    try:
        return record(story, fps, fast)
    except ValueError as error:
        return type(error)


def _frames_alike(a: "Recorder", b: "Recorder") -> None:
    assert_same_frames(a.frames, b.frames)


def assert_same_outcome(
    a: "Recorder | type",
    b: "Recorder | type",
    alike: "Callable[[Recorder, Recorder], None]" = _frames_alike,
) -> None:
    """Two outcomes alike: recordings alike (by default, the same frames), or the same error."""
    if isinstance(a, Recorder) and isinstance(b, Recorder):
        alike(a, b)
    else:
        assert a == b


def assert_same_instants(a: "Recorder", b: "Recorder") -> None:
    """Two recordings at different frame rates show the same world at every instant both
    have a frame at: the world at an instant does not depend on the frame rate."""
    common = sorted(
        {Fraction(k, a.fps) for k in a.frames} & {Fraction(k, b.fps) for k in b.frames}
    )
    assert common
    for t in common:
        assert_same_shots(
            a.frames[int(t * a.fps)], b.frames[int(t * b.fps)], f"at {t} s"
        )


def seen(looks: list[Look | None], paints: list[Paint]) -> Shot:
    """What a frame shows: the looks of the leaves drawn, in drawing order, but those no one
    can see (every brush transparent, to the 9 decimals looks are compared to: an invisible
    part alignment added, a rounding past its fading in)."""
    return tuple(
        x
        for x, p in zip(looks, paints, strict=True)
        if x is not None
        and max(p.fill[:, 3].max(), p.stroke[:, 3].max(), p.background[:, 3].max())
        > 1e-9
    )


class Recorder(m.Scene):
    """Tells `story(self)`; `frames[k]` is what frame k shows: the looks of the leaves it
    draws, in drawing order (see `seen`), however their families are structured."""

    def __init__(
        self, story: Callable[["Recorder"], None], fast: bool, fps: int
    ) -> None:
        super().__init__()
        self.story, self.fast, self.fps = story, fast, fps
        self.stage: list[m.Mobject] = []
        self.frames: dict[int, Shot] = {}

    def construct(self) -> None:
        self.story(self)

    def shot(
        self, looks: dict[int, Look | None], paints: dict[int, Paint] | None = None
    ) -> Shot:
        drawn, paints = self.display_list(), paints or {}
        return seen(
            [looks[id(leaf)] if id(leaf) in looks else look(leaf) for leaf in drawn],
            [paints.get(id(leaf), leaf.paint) for leaf in drawn],
        )

    def _emit(self, repeat: int = 1) -> None:
        shot = self.shot({})
        for k in range(self.frame, self.frame + max(repeat, 0)):
            self.frames[k] = shot
        super()._emit(repeat)

    def _pure_tweens(
        self, anim: m.Animation, alpha: list[float]
    ) -> "tuple[list[tuple[Transform, Path]], set[int]] | None":
        return super()._pure_tweens(anim, alpha) if self.fast else None

    def _advance_tweens(
        self,
        anim: m.Animation,
        tweens: "list[tuple[Transform, Path]]",
        alpha: list[float],
        introduced: set[int],
    ) -> None:
        # each frame of a play computed ahead, as the film receives it: a leaf between its
        # keyframes at its t, as it was before its part began (-1), or absent (-2)
        tracks = {
            id(leaf): (keys, path, index, t)
            for leaf, keys, path, index, t in _tracks(
                anim, tweens, np.array(alpha), introduced
            )
        }
        for f in range(len(alpha)):
            looks: dict[int, Look | None] = {}
            paints: dict[int, Paint] = {}
            for leaf in self.display_list():
                track = tracks.get(id(leaf))
                if track is None:
                    continue
                keys, path, index, t = track
                if index[f] == -1:
                    continue
                if index[f] == -2:
                    looks[id(leaf)] = None
                    continue
                saved = leaf._geometry, leaf.paint
                leaf.interpolate(keys[index[f]], keys[index[f] + 1], float(t[f]), path)
                looks[id(leaf)], paints[id(leaf)] = look(leaf), leaf.paint
                leaf._geometry, leaf.paint = saved
            self.frames[self.frame + f] = self.shot(looks, paints)
        super()._advance_tweens(anim, tweens, alpha, introduced)


def record(
    story: Callable[[Recorder], None], fps: int = 10, fast: bool = True
) -> Recorder:
    """Tell a story at `fps` on the scene's path (or frame by frame) and keep its frames."""
    saved = config.frame_rate
    config.frame_rate = fps
    try:
        scene = Recorder(story, fast, fps)
        scene.render()
    finally:
        config.frame_rate = saved
    return scene


# ── stories ─────────────────────────────────────────────────────────────────────────────
SHAPES: dict[str, Callable[[], m.Mobject]] = {
    "square": lambda: m.Square(1.2, color=m.BLUE, fill_opacity=0.5),
    "circle": lambda: m.Circle(0.7, color=m.RED),
    "triangle": lambda: m.Triangle(color=m.GREEN, fill_opacity=1),
    "dots": lambda: m.VGroup(*(m.Dot(i * m.RIGHT * 0.5) for i in range(3))),
    "line": lambda: m.Line(m.LEFT, m.RIGHT, color=m.YELLOW),
}
MONOTONE = [
    "linear",
    "smooth",
    "rush_into",
    "double_smooth",
    "ease_out_cubic",
    "slow_into",
    "lingering",
]
ANY_RATE = [
    *MONOTONE,
    "there_and_back",
    "wiggle",
    "ease_out_back",
    "running_start",
    "ease_in_elastic",
]
COLORS = [m.RED, m.YELLOW, m.TEAL]


@dataclass
class Leaf:
    kind: str
    mob: int
    shape: str = "circle"
    v: tuple[float, float] = (1.0, 0.0)
    angle: float = 1.0
    rate: str | None = None
    run_time: float | None = None
    lag: float | None = None

    def build(self, stage: list[m.Mobject]) -> m.Animation:
        mob, v = stage[self.mob % len(stage)], np.array([*self.v, 0.0])
        kw: dict = {}  # the options drawn
        if self.rate is not None:
            kw["rate_func"] = getattr(rf, self.rate)
        if self.run_time is not None:
            kw["run_time"] = self.run_time
        if self.lag is not None:
            kw["lag_ratio"] = self.lag
        return {
            "transform": lambda: m.Transform(mob, SHAPES[self.shape]().shift(v), **kw),
            "replace": lambda: m.ReplacementTransform(
                mob, SHAPES[self.shape]().shift(v), **kw
            ),
            "shift": lambda: mob.animate(**kw).shift(v),
            "turn": lambda: mob.animate(**kw).rotate(self.angle),
            "recolor": lambda: mob.animate(**kw).set_color(COLORS[int(self.angle) % 3]),
            "rotate": lambda: m.Rotate(mob, self.angle, **kw),
            "fade_in": lambda: m.FadeIn(mob, shift=v, **kw),
            "fade_out": lambda: m.FadeOut(mob, shift=v, **kw),
            "create": lambda: m.Create(mob, **kw),
            "write": lambda: m.Write(mob, **kw),
            "grow": lambda: m.GrowFromCenter(mob, **kw),
            "indicate": lambda: m.Indicate(mob, **kw),
            "reveal": lambda: m.ShowIncreasingSubsets(mob, **kw),
            "wait": lambda: m.Wait(self.run_time or 0.5),
        }[self.kind]()


@dataclass
class Node:
    kind: str  # "group" | "succession" | "lagged"
    parts: list["Leaf | Node"]
    lag: float | None = None
    rate: str | None = None

    def build(self, stage: list[m.Mobject]) -> m.Animation:
        kw: dict = {}
        if self.lag is not None:
            kw["lag_ratio"] = self.lag
        if self.rate is not None:
            kw["rate_func"] = getattr(rf, self.rate)
        group = {
            "group": m.AnimationGroup,
            "succession": m.Succession,
            "lagged": m.LaggedStart,
        }
        return group[self.kind](*(p.build(stage) for p in self.parts), **kw)


@dataclass
class Story:
    stage: list[str]
    added: list[bool]
    plays: list[list[Leaf | Node]] = field(default_factory=list)

    def __call__(self, scene: Recorder) -> None:
        scene.stage = self.tell(scene)

    def tell(self, scene: m.Scene) -> list[m.Mobject]:
        """Tell the story on `scene`; its stage."""
        stage = [
            SHAPES[s]().shift([i - 2.0, 0.5 * (i % 2), 0])
            for i, s in enumerate(self.stage)
        ]
        scene.add(*(mob for mob, added in zip(stage, self.added, strict=True) if added))
        for play in self.plays:
            scene.play(*(tree.build(stage) for tree in play))
        return stage


KINDS = ["transform", "replace", "shift", "turn", "recolor", "rotate", "fade_in", "fade_out",
         "create", "write", "grow", "indicate", "reveal", "wait"]  # fmt: skip


def leaves(
    stage: int, rates: list[str] = MONOTONE, kinds: list[str] = KINDS
) -> st.SearchStrategy[Leaf]:
    """An animation of one of `stage` mobjects, of a kind, with options drawn."""
    return st.builds(
        Leaf,
        kind=st.sampled_from(kinds),
        mob=st.integers(0, stage - 1),
        shape=st.sampled_from(sorted(SHAPES)),
        v=st.tuples(*[st.sampled_from([0.0, 0.5, 1.0, 1.5])] * 2),
        angle=st.sampled_from([0.5, 1.0, np.pi / 2, np.pi, -1.0]),
        rate=st.none() | st.sampled_from(rates),
        run_time=st.none() | st.sampled_from([0.3, 0.5, 1.0, 1.3]),
        lag=st.none() | st.sampled_from([0.0, 0.1, 0.25, 0.5, 1.0]),
    )


def trees(
    stage: int, rates: list[str], kinds: list[str]
) -> st.SearchStrategy[Leaf | Node]:
    """An animation tree: leaves under groups, successions and lagged starts."""
    return st.recursive(
        leaves(stage, rates, kinds),
        lambda parts: st.builds(
            Node,
            kind=st.sampled_from(["group", "succession", "lagged"]),
            parts=st.lists(parts, min_size=1, max_size=3),
            lag=st.none() | st.sampled_from([0.0, 0.25, 0.5, 1.0]),
            rate=st.none() | st.sampled_from(MONOTONE),
        ),
        max_leaves=5,
    )


@st.composite
def stories(
    draw: st.DrawFn, rates: list[str] = MONOTONE, kinds: list[str] = KINDS
) -> Story:
    """A stage of 1 to 4 shapes, some added, and 1 to 3 plays of animation trees."""
    stage = draw(st.lists(st.sampled_from(sorted(SHAPES)), min_size=1, max_size=4))
    added = draw(st.lists(st.booleans(), min_size=len(stage), max_size=len(stage)))
    plays = draw(
        st.lists(
            st.lists(trees(len(stage), rates, kinds), min_size=1, max_size=3),
            min_size=1,
            max_size=3,
        )
    )
    return Story(stage, added, plays)

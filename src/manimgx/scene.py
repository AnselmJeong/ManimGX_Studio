# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Scenes and their cameras: mutable worlds evaluated in exact time."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal, overload

from typing_extensions import TypedDict

from manimgx.config import config
from manimgx.constants import DEGREES, DOWN, LEFT, OUT, RIGHT, UP
from manimgx.drawing.paint import ManimColor, ParsableManimColor
from manimgx.mobject import Mobject, ValueTracker

if TYPE_CHECKING:
    from manimgx.animation.transform import Animate
import inspect
import os
import pathlib
from collections.abc import Callable, Sequence
from fractions import Fraction
from typing import TYPE_CHECKING, NamedTuple, Self, Unpack, cast
from warnings import deprecated

import numpy as np

from manimgx.animation import clock
from manimgx.constants import (
    DEFAULT_MOBJECT_TO_EDGE_BUFFER,
    DEFAULT_WAIT_TIME,
    ORIGIN,
    UR,
)
from manimgx.drawing.paint import WHITE
from manimgx.mobject import (
    Group,
    _family,
    _has_updater,
    _per_frame,
    _Recorder,
    flow,
    records,
    remove_list_redundancies,
    simulated,
)
from manimgx.rendering.film import (
    DEFAULT_ENCODER_CRF,
    DEFAULT_ENCODER_PRESET,
    Caption,
    Cut,
    Film,
    FrameSink,
    Play,
    PlayHook,
    SectionType,
    Take,
    X264Preset,
)
from manimgx.typing import Point3D, Point3DLike, Vector3DLike

if TYPE_CHECKING:
    from manimgx.animation.timeline import Animation, Route, Window
    from manimgx.animation.transform import Compositor, Transform, TransformOptions
    from manimgx.audio import Speech, Voice
    from manimgx.audio.sound import Clip, Sound
    from manimgx.drawing.geometry import Path
    from manimgx.mobject import ValueTracker
    from manimgx.mobjects.images import ImageCameraOptions
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

import numpy.typing as npt

from manimgx.animation.motion import (
    ApplyPointwiseFunction,
    Create,
    DrawBorderThenFill,
    GrowArrow,
    Write,
)
from manimgx.animation.timeline import Animation
from manimgx.animation.transform import Transform, TransformOptions
from manimgx.constants import DL, LARGE_BUFF, SMALL_BUFF
from manimgx.drawing.geometry import angle_of_vector
from manimgx.drawing.paint import (
    BLUE_D,
    GREEN_C,
    GREY,
    PURE_YELLOW,
    RED_C,
    Colors,
)
from manimgx.mobject import VGroup, VMobject
from manimgx.mobjects.grid import Matrix, MatrixOptions
from manimgx.mobjects.plotting import (
    Axes,
    NumberPlane,
    NumberPlaneOptions,
    merged_axis_config,
)
from manimgx.mobjects.shapes import (
    Arrow,
    ArrowTips,
    ArrowTipsBase,
    Line,
    Rectangle,
    Vector,
)
from manimgx.mobjects.text import MathTex, SingleStringMathTex, Tex

if TYPE_CHECKING:
    from typing import Self

    from manimgx.typing import (
        ManimTextLabel,
        MappingFunction,
        Point3D,
        Vector3DLike,
    )

__all__ = [
    "Camera",
    "LinearTransformationScene",
    "MovingCameraScene",
    "Scene",
    "ThreeDScene",
    "VectorScene",
    "ZoomedScene",
]


def _view_rectangle(height: float, width: float) -> Mobject:
    from manimgx.mobject import VMobject

    w, h = width / 2, height / 2
    return VMobject(stroke_width=0).set_points_as_corners(
        [[-w, h, 0], [w, h, 0], [w, -h, 0], [-w, -h, 0], [-w, h, 0]]
    )


class Camera:
    """What a frame shows: a view of the scene, made of mobjects, so that whatever moves
    a mobject moves the view.

    Its [`frame`][manimgx.Camera.frame] is a rectangle in the scene whose center and
    size are the view: move it, scale it or animate it, and the view pans and zooms. In
    three dimensions (a [`ThreeDScene`][manimgx.ThreeDScene]'s camera), it also orbits
    the frame's center, with perspective: five [value trackers][manimgx.ValueTracker]
    hold its angles `phi` and `theta`, its roll `gamma`, its `zoom` and its
    `focal_distance` (`phi_tracker`, `theta_tracker`, `gamma_tracker`, `zoom_tracker`
    and `focal_distance_tracker`), and its light is a point,
    [`light_source`][manimgx.Camera.light_source]. A camera only describes the view: it
    never draws.

    Args:
        three_d: Whether it sees in three dimensions: with perspective and depth, from
            its orbit.
        frame_width: The width of its frame, in scene units; None for the configured one
            (about 14.2 at 16:9). Its height is the configured one; a width out of the
            video's proportions stretches the picture.
        phi: The angle between its line of sight and the z axis, in radians: 0 looks
            straight down on the xy plane.
        theta: Its angle around the z axis, in radians, counterclockwise from the x
            axis: at −90° it looks from the side of negative y, so that x points right.
        gamma: How far it turns about its line of sight, in radians.
        focal_distance: Its distance from the frame's center, in scene units: the
            nearer, the stronger the perspective.
        zoom: How much it magnifies: 2 shows everything twice as large.
        light_source_start_point: Where the light is, in scene coordinates.
    """

    def __init__(
        self,
        *,
        three_d: bool = False,
        frame_width: float | None = None,
        phi: float = 0,
        theta: float = -90 * DEGREES,
        gamma: float = 0,
        focal_distance: float = 20.0,
        zoom: float = 1,
        light_source_start_point: Point3D = 9 * DOWN + 7 * LEFT + 10 * OUT,
    ) -> None:
        from manimgx.mobject import Point

        self.three_d = three_d
        """Whether the camera sees in three dimensions: with perspective and depth, from
        its orbit."""
        self.frame = _view_rectangle(
            config.frame_height, frame_width or config.frame_width
        )
        """The view: a rectangle in the scene, centered on the point the camera looks
        at, as wide and as tall as what it shows.

        Move it, scale it or animate it to pan and zoom:
        `self.play(self.camera.frame.animate.scale(0.5))` zooms in, showing half as
        much, twice as large. Its outline is not drawn (a stroke width of 0).
        """
        self.phi_tracker, self.theta_tracker, self.gamma_tracker = (
            ValueTracker(phi),
            ValueTracker(theta),
            ValueTracker(gamma),
        )
        self.focal_distance_tracker, self.zoom_tracker = (
            ValueTracker(focal_distance),
            ValueTracker(zoom),
        )
        self.light_source = Point(light_source_start_point)
        """Where the light comes from: a point in the scene, which lights the mobjects
        shaded in three dimensions (`shade_in_3d`). Move it like any mobject."""
        # the mobjects pinned to the screen, as they were given: what they are made of
        # is read every frame (see `fixed_in_frame_mobjects`)
        self._fixed_in_frame: dict[Mobject, None] = {}
        self.background_color = config.background_color
        self.background_opacity = config.background_opacity
        """The opacity of the background, from 0 to 1: the configured one unless
        changed."""
        self.exposure = 1.0
        """How much the light that mobjects with a [material][manimgx.Material] reflect
        is scaled before it is shown: 2 is twice as bright (one stop)."""
        self.tone_mapping: Literal["linear", "agx"] = "linear"
        """How light brighter than white is shown: "linear" clips it (a lit surface's
        colors as they are, up to white), "agx" rolls it off as film does (AgX: highlights
        desaturate toward white, and nothing clips). The light lit surfaces send into a
        pixel is averaged first and shown once, as a camera records it."""
        self.ambient_occlusion = 0.0
        """How strongly the light from all around (an ambient or an environment light) is
        shut out of corners, creases and the ground under things, where the surfaces near
        them block it: 0 not at all (off), 1 the standard strength, more darker. Only
        mobjects with a [material][manimgx.Material] are lit by that light, and only opaque
        ones shut it out or are darkened; a sun's, a point's or a spot's light is left as it
        is.

        It is found from what the view shows (screen-space ambient obscurance): a
        surface the view cannot see, such as a wall seen edge-on, shuts nothing out.
        Light bounces between the surfaces that shut it out, so light-colored ones
        darken less, and white ones hardly at all."""
        self.ambient_occlusion_radius = 0.3
        """How far around a point the surfaces that shut light out of it are sought, in
        scene units: about the size of the creases and contacts to darken."""
        self.bloom = 0.0
        """How much of the light that mobjects with a [material][manimgx.Material] send
        into the view the lens spreads around it, as a glow (bloom), from 0 to 1: 0 none
        (off), 0.05 a lens's faint glow, plain around light brighter than white, 1 all of
        it. What the glow spreads, the light leaves: the view keeps the light it has,
        spread.

        It is spread from the light the view shows: what lies nearer, a mobject fixed in
        the frame too, hides the light behind it. It falls off with the distance from
        the light: half of it lies within a twentieth of the view's height, nearly all of
        it within a quarter. It is light, over everything the view shows: over a lit
        surface, it adds to the surface's light before the tone mapping shows them; over
        display paint (the background, mobjects without a material, mobjects fixed in the
        frame), the tone mapping shows it on its own and it adds to the paint, as a screen
        adds light (white stays white); where the view shows nothing (a transparent
        background), it shows alone, as opaque as it is bright. Mobjects without a material
        send no light: they never glow."""

    @property
    def background_color(self) -> ManimColor:
        """The color of the background: the configured one unless changed. Set it to any
        color."""
        return self._background_color

    @background_color.setter
    def background_color(self, color: ParsableManimColor) -> None:
        self._background_color = ManimColor(color)

    # ── the view (CE MovingCamera semantics: the frame mobject is the truth) ────
    @property
    def frame_center(self) -> Point3D:
        """The point the camera looks at: its frame's center. Set it to move the frame
        there."""
        return self.frame.get_center()

    @frame_center.setter
    def frame_center(self, point: Point3D) -> None:
        self.frame.move_to(point)

    @property
    def frame_width(self) -> float:
        """The width of the view, in scene units: its frame's."""
        return self.frame.width

    @property
    def frame_height(self) -> float:
        """The height of the view, in scene units: its frame's."""
        return self.frame.height

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_mobjects_indicating_movement(self) -> list[Mobject]:
        """The mobjects the view is made of: moving any of them moves the camera.

        Returns:
            The frame, the five trackers of the orbit, and the light, in a new list.
        """
        # the view (`feed.view`) reads nothing else a tween can move
        return [self.frame, *self.get_value_trackers(), self.light_source]

    @overload
    def auto_zoom(
        self,
        mobjects: Iterable[Mobject],
        margin: float = 0,
        animate: Literal[True] = True,
    ) -> Animate[Mobject]: ...
    @overload
    def auto_zoom(
        self, mobjects: Iterable[Mobject], margin: float = 0, *, animate: Literal[False]
    ) -> Mobject: ...
    @overload
    def auto_zoom(
        self, mobjects: Iterable[Mobject], margin: float, animate: Literal[False]
    ) -> Mobject: ...
    def auto_zoom(
        self,
        mobjects: Iterable[Mobject],
        margin: float = 0,
        animate: bool = True,
    ) -> Animate[Mobject] | Mobject:
        """Fit the view around mobjects, in two dimensions: center the frame on them,
        and size it to fit them.

        The frame keeps its proportions: its width fits the mobjects, or its height,
        whichever of the two they fill more of, and `margin` is added to it.

        Args:
            mobjects: The mobjects to fit, the frame itself left out; at least one must
                remain (a ValueError otherwise).
            margin: How much wider (or taller) than the mobjects the view is, in scene
                units.
            animate: Whether to return an animation of the frame, to play, rather than
                fit it at once.

        Returns:
            The animation, to play; with `animate` False, the frame, fitted.
        """
        mobs = [m for m in mobjects if m is not self.frame]
        if not mobs:
            raise ValueError(
                "Could not determine bounding box of the mobjects given to 'auto_zoom'."
            )
        left, right = (
            min(m.get_critical_point(LEFT)[0] for m in mobs),
            max(m.get_critical_point(RIGHT)[0] for m in mobs),
        )
        up, down = (
            max(m.get_critical_point(UP)[1] for m in mobs),
            min(m.get_critical_point(DOWN)[1] for m in mobs),
        )
        target = (
            (self.frame.animate if animate else self.frame)
            .set_x((left + right) / 2)
            .set_y((up + down) / 2)
        )
        if (right - left) / self.frame.width > (up - down) / self.frame.height:
            return target.set(width=right - left + margin)
        return target.set(height=up - down + margin)

    # ── the 3D orbit ───────────────────────────────────────────────────────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_value_trackers(self) -> list[ValueTracker]:
        """The five trackers of the camera's orbit.

        Returns:
            The trackers of `phi`, `theta`, the focal distance, `gamma` and the zoom, in
            that order, in a new list.
        """
        return [
            self.phi_tracker,
            self.theta_tracker,
            self.focal_distance_tracker,
            self.gamma_tracker,
            self.zoom_tracker,
        ]

    def get_phi(self) -> float:
        """The angle between the camera's line of sight and the z axis.

        Returns:
            The angle, in radians.
        """
        return self.phi_tracker.get_value()

    def get_theta(self) -> float:
        """The camera's angle around the z axis, counterclockwise from the x axis.

        Returns:
            The angle, in radians.
        """
        return self.theta_tracker.get_value()

    def get_gamma(self) -> float:
        """How far the camera turns about its line of sight.

        Returns:
            The angle, in radians.
        """
        return self.gamma_tracker.get_value()

    def get_zoom(self) -> float:
        """How much the camera magnifies.

        Returns:
            The zoom: 1 for none.
        """
        return self.zoom_tracker.get_value()

    def get_focal_distance(self) -> float:
        """The camera's distance from its frame's center.

        Returns:
            The distance, in scene units.
        """
        return self.focal_distance_tracker.get_value()

    def set_phi(self, value: float) -> None:
        """Set the angle between the camera's line of sight and the z axis, at once.

        Args:
            value: The angle, in radians: 0 looks straight down on the xy plane.
        """
        self.phi_tracker.set_value(value)

    def set_theta(self, value: float) -> None:
        """Set the camera's angle around the z axis, at once.

        Args:
            value: The angle, in radians, counterclockwise from the x axis.
        """
        self.theta_tracker.set_value(value)

    def set_gamma(self, value: float) -> None:
        """Set how far the camera turns about its line of sight, at once.

        Args:
            value: The angle, in radians.
        """
        self.gamma_tracker.set_value(value)

    # ── objects pinned to the screen ─────────────────────────────────────────────
    @property
    def fixed_in_frame_mobjects(self) -> set[Mobject]:
        """The mobjects pinned to the screen: those given to
        [`add_fixed_in_frame_mobjects`][manimgx.Camera.add_fixed_in_frame_mobjects],
        with every member of their families as they are now: a part one gains later (a
        number's new digits, what an updater or a Transform makes) is pinned with it."""
        return {m for mob in self._fixed_in_frame for m in mob.get_family()}

    def add_fixed_in_frame_mobjects(self, *mobjects: Mobject) -> None:
        """Pin mobjects to the screen: each is drawn where its points are, as in a
        two-dimensional view centered on the origin, over everything else.

        They stay where they are on the screen whatever the camera's angles, zoom and
        center: a title placed with `to_corner` stays in its corner. Everything in them
        is pinned, now and later: a member added later (a number's new digits, what an
        updater or a Transform makes) is pinned too.

        Args:
            *mobjects: The mobjects to pin, with their families.
        """
        self._fixed_in_frame.update(dict.fromkeys(mobjects))


type Act = Callable[[Fraction, "Route | None"], Callable[[], None] | None]
"""A play's step at an instant: it brings what runs there (of the parts given, if any), and
returns what opens there (to run once the world is there), if anything."""


class Concern(NamedTuple):
    """What an instant of a play concerns (`Scene._exact`): the route to its parts, and the
    mobjects whose time-based updaters are brought there."""

    parts: Route
    mobjects: list[Mobject]


class ZoomedCameraConfig(TypedDict, total=False):
    """The zoomed camera's look: its frame's stroke and its picture's background."""

    default_frame_stroke_width: float
    """The width of the zoomed camera frame's outline, in hundredths of a scene unit
    (default 2)."""
    default_frame_stroke_color: ParsableManimColor
    """The color of the zoomed camera frame's outline (default white)."""
    background_opacity: float
    """The opacity of the zoomed picture's background, from 0 to 1 (default 1: it hides
    what is behind the display)."""


class Scene:
    """A scene: one video, and what happens in it.

    Make a class from it, and write what happens in its
    [`construct`][manimgx.Scene.construct] method: ManimGX runs it once, from top to
    bottom, and [`render`][manimgx.Scene.render] records the video. A mobject shows from
    the moment the scene holds it ([`add`][manimgx.Scene.add] puts one in). Time passes
    only in [`play`][manimgx.Scene.play] and [`wait`][manimgx.Scene.wait]: whatever
    `construct` does between them happens at one moment.

    Each frame shows the scene at its own exact time, so a scene is the same at every
    frame rate: a second of animation is 60 frames at 60 frames a second, and 30 at 30.
    When `construct` ends, a last frame shows the scene as it ends, so that its last
    animation is seen landing. The methods that change a scene give it back, so that
    their calls chain.

    Examples:
        ```python
        import manimgx as m


        class SceneExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                self.play(m.Create(square))  # from 0 s to 1 s
                self.wait()  # from 1 s to 2 s
                self.play(square.animate.rotate(m.PI / 4))  # from 2 s to 3 s
        ```
    """

    three_d: bool = False
    """Whether the scene's camera sees in three dimensions: True for a
    [`ThreeDScene`][manimgx.ThreeDScene]."""
    compositor: Compositor | None = None  # a play's: its tweens' leaves (`play`)

    def __init__(self) -> None:
        clock.reset()  # a new world: its clock at 0
        self.camera = Camera(three_d=self.three_d)
        """The scene's camera: what a frame shows. Move, scale or animate its
        [`frame`][manimgx.Camera.frame] to pan and zoom."""
        self.mobjects: list[Mobject] = []
        """The mobjects the scene holds, in drawing order: each is drawn over those
        before it, at an equal z-index. [`add`][manimgx.Scene.add] and
        [`remove`][manimgx.Scene.remove] change it."""
        self.foreground_mobjects: list[Mobject] = []
        """The mobjects kept in front: drawn over all the others, at an equal z-index
        (see [`add_foreground_mobjects`][manimgx.Scene.add_foreground_mobjects]). They
        are among the scene's [`mobjects`][manimgx.Scene.mobjects] too."""
        self.updaters: list[Callable[[float], object]] = []
        """The scene's own updaters, in the order they run (see
        [`add_updater`][manimgx.Scene.add_updater])."""
        self._since: dict[object, Fraction] = {}  # when each scene updater was last run
        self.clock = Fraction(0)
        """The scene's time, exact: a fraction of seconds (see
        [`time`][manimgx.Scene.time])."""
        self.frame = 0
        """How many frames the scene has recorded: the number of the next one, which
        shows the world at `frame / fps` seconds."""
        self._records = False  # does anything record the world (`_recording`), this run
        # the play's instants no frame shows, with what each concerns (`_exact`, `_ticks`)
        self._events: dict[Fraction, Concern | None] = {}
        self._playing: list[Mobject] = []  # what the play running acts on (`_running`)
        # while animations begin together (`_together`): what the scene held, by id, and
        # the list of mobjects it was found in (`_introduce`)
        self._beginning = False
        self._holding: tuple[list[Mobject], set[int]] | None = None
        # the play running: its animations may hide parts of the scene (`display_list`)
        self._animation: Animation | None = None
        self.num_plays = 0
        """How many plays and waits the scene has run."""
        self.film = Film()
        """The film the scene records: [`render`][manimgx.Scene.render] makes a new one,
        and returns it."""

    @property
    @deprecated(
        "Manim CE's: the scene is its own renderer: use the scene", category=None
    )
    def renderer(self) -> Self:
        """The scene itself: Manim code reaches the camera and the time through
        `self.renderer`, and a scene has both."""
        return self

    @property
    def time(self) -> float:
        """The scene's time, in seconds.

        In `construct`, it is 0 when the scene begins, and the end of each play or wait
        once it returns. During a play, while animations and updaters run, it is the time
        of the frame being made.
        """
        return float(clock.now)

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def setup(self) -> None:
        """Prepare the scene: [`render`][manimgx.Scene.render] calls it before
        `construct`.

        It does nothing unless overridden: override it for what several scenes share, in
        a class they derive from.
        """

    def construct(self) -> None:
        """Describe the scene, what happens and when: override it.

        [`render`][manimgx.Scene.render] runs it once, from top to bottom, and the film
        is what it leaves behind. It is ordinary Python: loops, functions and variables
        work as they do anywhere.
        """

    def tear_down(self) -> None:
        """Finish the scene: [`render`][manimgx.Scene.render] calls it after
        `construct`, before the closing frame.

        It does nothing unless overridden.
        """

    @staticmethod
    def _fps() -> Fraction:
        return clock.rational(config.frame_rate)

    def render(
        self,
        video: str | os.PathLike[str] | None = None,
        *,
        preset: X264Preset = DEFAULT_ENCODER_PRESET,
        crf: float = DEFAULT_ENCODER_CRF,
        frames: FrameSink | None = None,
        plays: PlayHook | None = None,
        take: Take | None = None,
    ) -> Film:
        """Run the scene and record its film: `setup`, `construct` and `tear_down`, then
        a closing frame.

        Each frame is sent as it is made: encoded into `video`, an MP4 file, and handed to
        `frames`, if given; each play or wait, as it ends, is handed to `plays`, if given.
        A frame is drawn only for the video, or when `frames` asks for its pixels: with
        neither, the frames are counted, not drawn, which checks a scene quickly. Frames
        `k = 0, 1, …` sample `k / fps` seconds, after events at the same float instant;
        the closing frame then shows it at its own instant: the scene's end if a frame falls
        there, or else the first frame time after it. So the scene's last animation is
        seen landing.

        Either function, and a take, may raise [`Cut`][manimgx.rendering.film.Cut] to end the
        film there: the scene stops, and the video is written up to the last frame sent.
        If the scene fails, the video is not written. A scene renders once: make a new
        one to render it again.

        Args:
            video: The MP4 file to write, if any, at the size and frame rate of
                [`config`][manimgx.config.config] (a whole number of frames a second,
                and an even width and height).
            preset: The x264 encoding preset; faster presets make larger files.
            crf: The x264 constant rate factor, from 0 to 51; lower values give
                higher quality.
            frames: A function handed each frame as it is sent (a
                [`FrameSink`][manimgx.rendering.film.FrameSink]): a [`Frame`][manimgx.rendering.film.Frame],
                which knows its place in the film and draws its pixels when asked.
            plays: A function called as each play or wait ends (a
                [`PlayHook`][manimgx.rendering.film.PlayHook]), with the [`Play`][manimgx.rendering.film.Play]
                and the animations it played, the world as the play left it.
            take: Record the film as a take instead, for ManimGX's player to draw: a
                function handed its bytes as they are recorded (a
                [`Take`][manimgx.rendering.film.Take]). A take has no video, and no frames for
                `frames`.

        Returns:
            The film: how many frames it has, its plays, sections, sounds and captions,
            and how its video was made.
        """
        self.film = Film(
            video, frames=frames, plays=plays, take=take, preset=preset, crf=crf
        )
        clock.reset()
        try:
            self.setup()
            self.construct()
            self.tear_down()
            closing = Fraction(self.frame) / self._fps()
            if float(closing) > float(
                clock.now
            ):  # the scene ended between frames: the world at frame N
                self._records = self._recording()
                self._frame(closing, self._simulation_rate())
            self._emit()
        except Cut:
            pass  # the film ends where it was cut
        except BaseException:
            self.film.abort()
            raise
        self.film.close()
        return self.film

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def display_list(self) -> list[Mobject]:
        """The mobjects a frame draws, in the order it draws them.

        They are the members with points of the scene's mobjects, in family order (a
        mobject before its submobjects), the foreground mobjects last, but the parts the
        play running hides (its animations' [`hidden`][manimgx.Animation.hidden]); then
        sorted by z-index, which keeps that order among equal ones. A member held twice
        is drawn once, at its last place.

        Returns:
            A new list.
        """
        members = _family([*self.mobjects, *self.foreground_mobjects])
        if self._animation is not None and (parts := self._animation.hidden):
            hidden = {id(m) for m in _family(parts)}
            members = [m for m in members if id(m) not in hidden]
        leaves = [m for m in members if m.has_points()]
        leaves.sort(key=lambda m: m.z_index)
        return leaves

    def _emit(self, repeat: int = 1) -> None:
        """Record frames self.frame … self.frame + repeat − 1 (identical: one packet, repeated)."""
        if repeat > 0:
            self.film.record(self.camera, self.display_list(), repeat)
            self.frame += repeat

    def _run(
        self,
        end: Fraction,
        act: Act | None = None,
        stop: Callable[[], bool] | None = None,
        frozen: bool = False,
        boundaries: dict[float, Fraction] | None = None,
    ) -> None:
        """Run to `end`: frames in the observed [clock, end) show the world at their instants (`act` is
        the play's step, before the updaters); then the world is brought to `end`. `stop` ends the run
        at the frame it holds after. A frozen run, or one where nothing can change, is one held frame;
        while anything is simulated, the world also steps at the simulation clock's ticks.
        """
        fps, stopped = self._fps(), False
        limit = clock.frame_at(end, fps)
        if frozen or (act is None and stop is None and not self._anything_runs()):
            self._emit(limit - self.frame)
            if frozen:
                for mob in self.mobjects:
                    mob._stamp(end)
                self._since = dict.fromkeys(self._since, end)
                clock.now = end
        else:
            rate = self._simulation_rate()
            self._records = self._recording()
            while self.frame < limit:
                t = self._sample(Fraction(self.frame) / fps, boundaries)
                self._frame(t, rate, act)
                self._emit()
                if stop is not None and stop():
                    end, stopped = t, True
                    break
            self._ticks(end, rate, act)
        if act is not None or end != clock.now:  # a play's end, even one of no duration
            self._instant(end, act)
        elif (
            stopped
        ):  # a wait's end at a frame: an event, where what is simulated steps
            self._instant(end, act, framing=False)
        self.clock = end

    def _sample(
        self, t: Fraction, boundaries: dict[float, Fraction] | None = None
    ) -> Fraction:
        # A frame observes all events at the same binary64 instant, in exact order.
        # It must not rewind an event just beyond its mathematical grid time.
        return max(t, self.clock, boundaries.get(float(t), t) if boundaries else t)

    def _simulation_rate(self) -> int | None:
        """The simulation clock's rate, if anything in the scene is simulated (a time-based
        updater that is not a flow — an integrator, a traced path), or in what the play
        running will bring into it or run; else None."""
        if any(simulated(u) for u in self.updaters) or any(
            simulated(u) for m in self._running() for u in m.updaters
        ):
            return config.simulation_rate
        return None

    def _recording(self) -> bool:
        """Does anything in the scene, or that the play running runs, record the world (a
        traced path)?"""
        return any(records(u) for m in self._running() for u in m.updaters)

    def _running(self) -> list[Mobject]:
        """The scene's members, and the mobjects the play running acts on and their
        families (it may bring them into the scene, or run a target's updaters)."""
        return self.get_mobject_family_members() + [
            m for mob in self._playing for m in mob.get_family()
        ]

    def _ticks(
        self,
        until: Fraction,
        rate: int | None,
        act: Act | None = None,
    ) -> None:
        """The world at every instant after now and before `until` that no frame shows: the
        simulation clock's ticks, where what is simulated steps, and the play's events (its
        parts' windows opening and closing), where it does not (a simulation's steps are its
        clock's, whatever the plays)."""
        ticks = (
            set()
            if rate is None
            else {
                Fraction(k, rate)
                for k in range(clock.now * rate // 1 + 1, -(-until * rate // 1))
            }
        )
        events = {e: c for e, c in self._events.items() if clock.now < e < until}
        for t in sorted(ticks | events.keys()):
            concern = events.get(t)
            if act is None or t in ticks or concern is None:
                self._instant(
                    t, act, stepping=t in ticks or rate is None, framing=False
                )
            else:
                self._event(t, act, concern)

    def _frame(
        self,
        t: Fraction,
        rate: int | None,
        act: Act | None = None,
    ) -> None:
        """The world a frame at `t` shows: the simulation clock's ticks until then, then `t` —
        where what is simulated steps only if `t` is a tick."""
        self._ticks(t, rate, act)
        self._instant(t, act, rate is None or (t * rate).denominator == 1)

    def _anything_runs(self) -> bool:
        return bool(self.updaters) or any(
            m.updaters for m in self.get_mobject_family_members()
        )

    def _instant(
        self,
        t: Fraction,
        act: Act | None = None,
        stepping: bool = True,
        framing: bool = True,
    ) -> None:
        """The world at `t`: the play's step, then every updater brought to `t` (simulated ones only
        where `stepping`, per-frame ones only where `framing`), then the recorders. In a scene
        that records (`_records`), a frame or an event is computed twice: the world as time
        brought it there (as a tick sees it), then with its per-frame updaters run; the
        recorders record both (`TracedPath` spreads what the per-frame updaters changed over the
        frame)."""
        if framing and self._records:
            self._pass(t, act, stepping, False)
            self._pass(t, act, False, True)
        else:
            self._pass(t, act, stepping, framing)
        clock.stepping = clock.framing = True

    def _pass(
        self,
        t: Fraction,
        act: Act | None,
        stepping: bool,
        framing: bool,
    ) -> None:
        clock.now, clock.stepping, clock.framing = t, stepping, framing
        # the play brings what runs to `t`, then the updaters; then what opens at `t` begins,
        # the world at `t`
        opening = act(t, None) if act is not None else None
        recorders: list[_Recorder] | None = [] if self._records else None
        for mob in self.mobjects:
            mob.advance(t, recorders=recorders)
        updaters = self.updaters
        for func in updaters:
            if updaters is not self.updaters and not _has_updater(self.updaters, func):
                continue
            if not stepping and simulated(func):
                continue
            since = self._since.get(func, t)
            self._since[func] = t
            func(float(t - since))
        if opening is not None:
            self._together(opening)
        for mob, recorder, _ in recorders or ():  # if still there when its turn comes
            if not mob.updating_suspended and _has_updater(mob.updaters, recorder):
                mob._bring(recorder, t)

    def _pure_tweens(
        self, anim: Animation, alpha: list[float]
    ) -> tuple[list[tuple[Transform, Path]], set[int]] | None:
        """A play that is a pure function of time — its tweens (Transforms along a `Path` between
        fixed keyframes, one per leaf, under compositions that only time them, going forward) and the
        objects it introduces; None if anything else acts (updaters, procedures, a camera's picture),
        and then every frame is computed. Its groups begin every part now (`begin_all`): nothing a
        part reads when it begins can change before its window opens."""
        from manimgx.animation.timeline import (
            Animation,
            AnimationGroup,
            Wait,
            _held,
            _updating,
            walk,
        )
        from manimgx.animation.transform import Transform
        from manimgx.audio.sound import Sound
        from manimgx.drawing.geometry import Path

        members = self.get_mobject_family_members()
        if self.updaters or any(
            m.updaters or isinstance(m.paint.texture, Camera) for m in members
        ):
            return None
        tweens: list[tuple[Transform, Path]] = []
        begins: list[int] = []  # the frame each tween begins at
        for node, progress, closes in walk(anim, np.array(alpha)):
            if not _forward(progress):
                return None
            if isinstance(node, AnimationGroup):  # it only times its parts
                if type(node).interpolate is not AnimationGroup.interpolate or (
                    closes.any()  # and closes before the play ends, changing the
                    and type(node).clean_up_from_scene  # scene only as its parts do
                    is not AnimationGroup.clean_up_from_scene
                ):
                    return None
                continue
            if isinstance(node, Sound | Wait):  # acts on nothing
                continue
            if not isinstance(node, Transform):
                return None
            kind, path = type(node), node.path_func
            if not (
                isinstance(path, Path)
                and kind.interpolate is Animation.interpolate
                and kind.interpolate_mobject is Animation.interpolate_mobject
                and kind.interpolate_keyframes is Transform.interpolate_keyframes
                and kind.hidden is Animation.hidden  # (it hides nothing)
                and not _updating(node.mobject)  # (no updaters act while it plays)
                and not node.moving_target()
            ):
                return None
            if closes.any() and (  # it leaves before the play ends: as a remover
                node.replace_mobject_with_target_in_scene  # (showing nothing as it
                or not (  # leaves), or changing nothing
                    node.is_remover()
                    or kind.clean_up_from_scene is Transform.clean_up_from_scene
                )
            ):
                return None
            tweens.append((node, path))
            begun = progress == progress
            begins.append(int(np.argmax(begun)) if begun.any() else len(alpha))
        driven = [id(m) for tween, _ in tweens for m in tween.mobject.get_family()]
        if len(driven) != len(
            set(driven)
        ):  # a leaf two tweens drive: every frame computed
            return None
        for (tween, _), first in zip(tweens, begins, strict=True):
            target = {
                id(m)
                for key in tween.keys
                if isinstance(key, Mobject)
                for m in key.get_family()
            }
            if first == 0 or not target:
                continue
            if any(
                begin < first
                and not target.isdisjoint(id(m) for m in other.mobject.get_family())
                for (other, _), begin in zip(tweens, begins, strict=True)
            ):  # its target is moved before it begins: every frame computed
                return None
        present = {id(m) for m in self.mobjects}
        if isinstance(anim, AnimationGroup):
            self._together(anim.begin_all)
        # what the parts brought into the scene as they began (not the parts aligning a
        # mobject split out of it: those were there, and show until their part's window
        # opens), in the order they begin, as frame by frame
        opens = {
            id(mob): b
            for (t, _), b in zip(tweens, begins, strict=True)
            for mob in _held(t.mobject)
        }
        new = [root for root in self.mobjects if id(root) not in present]
        new.sort(key=lambda root: opens.get(id(root), 0))
        self.mobjects = [r for r in self.mobjects if id(r) in present] + new
        introduced = {id(x) for root in new for x in root.get_family()}
        # each tween's path as its beginning decided it (`.animate` makes its turns a motion
        # when it begins): read now, not before its part began (a Path stays a Path)
        return [
            (tween, cast("Path", tween.path_func)) for tween, _ in tweens
        ], introduced

    def _advance_tweens(
        self,
        anim: Animation,
        tweens: list[tuple[Transform, Path]],
        alpha: list[float],
        introduced: set[int],
    ) -> None:
        """A pure play at once: each tween's alpha at every frame from its compositions' clocks
        (`schedule`); the film mixes the frames."""
        leaves = _tracks(anim, tweens, np.array(alpha), introduced)
        self.film.tween(self.camera, self.display_list(), leaves)
        self.frame += len(alpha)

    # ── membership (CE semantics, including group restructuring) ────────────────
    def add(self, *mobjects: Mobject) -> Self:
        """Put mobjects in the scene, from now on, in front of those it holds.

        Each is drawn over the mobjects added before it (at an equal z-index), and under
        the foreground mobjects. A mobject the scene holds already moves to the front.
        One that is part of a group the scene holds is taken out of the group's place:
        the group is split, its other members staying where they are, each on its own
        (and the group's own updaters no longer run); a group added takes its members
        from wherever the scene held them. The updaters of the mobjects added run from
        now on: a time-based one's first `dt` counts from the moment its mobject joins
        the scene.

        Args:
            *mobjects: The mobjects, in order: the last is drawn on top.

        Examples:
            ```python
            import manimgx as m


            class SceneAddExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(side_length=3.5, color=m.BLUE, fill_opacity=1)
                    circle = m.Circle(radius=1.8, color=m.YELLOW, fill_opacity=1)
                    circle.shift(1.8 * m.RIGHT)
                    self.add(square, circle)  # the circle, added last, is on top
                    self.wait()
                    self.add(square)  # adding it again brings it to the front
                    self.wait()
            ```
        """
        if any(m.updaters for mob in mobjects for m in mob.get_family()):
            present = {id(m) for m in self.get_mobject_family_members()}
            for mob in mobjects:  # joining the world: its updaters are live from now
                for m in mob.get_family():
                    if id(m) not in present:
                        m._stamp(clock.now, recursive=False)
        new = remove_list_redundancies([*mobjects, *self.foreground_mobjects])
        self.mobjects = _restructure(self.mobjects, new) + new
        return self

    def remove(self, *mobjects: Mobject) -> Self:
        """Take mobjects out of the scene: they are no longer drawn, and their updaters
        stop.

        A mobject that is part of a group the scene holds is taken out the same way: the
        group is split, its other members staying in the scene, each on its own. A
        mobject the scene does not hold is ignored. The mobjects themselves are not
        changed: adding one again shows it as it is then.

        Args:
            *mobjects: The mobjects to take out.
        """
        self.mobjects = _restructure(self.mobjects, mobjects, extract=False)
        self.foreground_mobjects = _restructure(
            self.foreground_mobjects, mobjects, extract=False
        )
        return self

    def add_foreground_mobjects(self, *mobjects: Mobject) -> Self:
        """Put mobjects in the scene, in front: drawn over all the others, at an equal
        z-index, even those added after them.

        Args:
            *mobjects: The mobjects, in order: the last is drawn on top.
        """
        self.foreground_mobjects = remove_list_redundancies(
            [*self.foreground_mobjects, *mobjects]
        )
        return self.add(*mobjects)

    @deprecated(
        "add_foreground_mobject is add_foreground_mobjects: use it", category=None
    )
    def add_foreground_mobject(self, *mobjects: Mobject) -> Self:
        """The same as
        [`add_foreground_mobjects`][manimgx.Scene.add_foreground_mobjects]."""
        return self.add_foreground_mobjects(*mobjects)

    def remove_foreground_mobjects(self, *mobjects: Mobject) -> Self:
        """Take mobjects out of the front: they stay in the scene, where they are in its
        drawing order, and mobjects added later are drawn over them.
        """
        self.foreground_mobjects = _restructure(self.foreground_mobjects, mobjects)
        return self

    @deprecated(
        "remove_foreground_mobject is remove_foreground_mobjects: use it", category=None
    )
    def remove_foreground_mobject(self, *mobjects: Mobject) -> Self:
        """The same as
        [`remove_foreground_mobjects`][manimgx.Scene.remove_foreground_mobjects]."""
        return self.remove_foreground_mobjects(*mobjects)

    def bring_to_front(self, *mobjects: Mobject) -> Self:
        """Draw mobjects over the others, but under the foreground mobjects: the same as
        [`add`][manimgx.Scene.add].

        Args:
            *mobjects: The mobjects, in order: the last is drawn on top.
        """
        return self.add(*mobjects)

    def bring_to_back(self, *mobjects: Mobject) -> Self:
        """Draw mobjects under all the others, at an equal z-index: they move to the
        start of the scene's mobjects, out of the foreground if they were in it.

        A mobject the scene does not hold is added there, at the bottom.

        Args:
            *mobjects: The mobjects, in order: the first is drawn at the bottom.
        """
        self.remove(*mobjects)
        self.mobjects = [*mobjects, *self.mobjects]
        return self

    def clear(self) -> Self:
        """Take every mobject out of the scene, the foreground ones too; the scene's own
        updaters stay.
        """
        self.mobjects, self.foreground_mobjects = [], []
        return self

    def replace(self, old: Mobject, new: Mobject) -> None:
        """Put a mobject in the scene in another's place: where the other is drawn, even
        inside a group, which then holds the new one.

        `new` is first taken out of the list it joins, if it is there.
        [`ReplacementTransform`][manimgx.ReplacementTransform] ends with it. A mobject
        the scene does not hold raises a ValueError.

        Args:
            old: The mobject to replace: one the scene holds, or a part of one.
            new: The mobject to put in its place.
        """

        def replace_in(lst: list[Mobject]) -> bool:
            if new in lst:
                lst.remove(new)
            for i, m in enumerate(lst):
                if m is old:
                    lst[i] = new
                    return True
            return any(replace_in(m.submobjects) for m in lst)

        if not (replace_in(self.mobjects) or replace_in(self.foreground_mobjects)):
            raise ValueError(f"Could not find {old} in scene")
        self._holding = None  # (what it holds changed in place)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_mobject_family_members(self) -> list[Mobject]:
        """Every mobject in the scene, with all its submobjects, each once.

        Returns:
            A new list, in family order, then sorted by z-index (which keeps that order
            among equal ones).
        """
        members = _family(self.mobjects)
        members.sort(key=lambda m: m.z_index)
        return members

    def add_updater(self, func: Callable[[float], object]) -> None:
        """Add an updater to the scene itself: a function it calls with the time that
        passed.

        It is handed `dt`, the scene time in seconds since it last ran (or was added),
        at each instant the scene computes, after the updaters of the mobjects. It steps
        as a mobject's time-based updater does: on the simulation clock
        ([`config.simulation_rate`][manimgx.config.Config.simulation_rate] ticks a
        second, and the end of each play and wait), unless it is a
        [flow][manimgx.mobject.flow], which runs at every frame. What it returns is
        ignored.

        Args:
            func: The updater: a function of one parameter, named `dt`.
        """
        self.updaters.append(func)
        self._since[func] = clock.now

    def remove_updater(self, func: Callable[[float], object]) -> None:
        """Remove an updater from the scene, every time it was added.

        This also cancels calls that have not yet run in the current update.

        Args:
            func: The updater.
        """
        self.updaters = [f for f in self.updaters if f is not func]
        if func not in self.updaters:
            self._since.pop(func, None)

    # ── time ─────────────────────────────────────────────────────────────────────
    def play(self, *animations: Animation, **options: Unpack[TransformOptions]) -> None:
        """Play animations, together, from the scene's present time.

        Each animation starts now and lasts its own run time, and ends when its time is up,
        whatever else still plays: the play lasts as long as the longest one. Then
        `construct` goes on, at the time the play ended. To play animations one after
        another, or each a little after the one before it, play a
        [`Succession`][manimgx.Succession] or a [`LaggedStart`][manimgx.LaggedStart].

        A play brings into the scene what its animations change, if the scene doesn't
        hold it yet, in the order given. An animation that brings its mobject in
        ([`Create`][manimgx.Create], [`FadeIn`][manimgx.FadeIn], …) adds it as it starts,
        and a replacement adds the mobject it turns into as it ends. One that takes its
        mobject out ([`FadeOut`][manimgx.FadeOut], …) removes it as it ends. A
        [`Wait`][manimgx.Wait] played alone is a [`wait`][manimgx.Scene.wait].

        Args:
            *animations: The animations, or iterables of them; at least one.
            **options: [Transform options][manimgx.animation.transform.TransformOptions]
                for every animation: each option given replaces that animation's own. So
                `run_time=2` plays each for 2 seconds, and a `lag_ratio` staggers the
                parts of each (a [`LaggedStart`][manimgx.LaggedStart] staggers the
                animations).

        Examples:
            ```python
            import manimgx as m


            class ScenePlayExample(m.Scene):
                def construct(self) -> None:
                    colors = (m.BLUE, m.YELLOW, m.GREEN)
                    dots = m.VGroup(*(m.Dot(radius=0.3, color=c) for c in colors))
                    dots.arrange(m.DOWN, buff=1.5).shift(5 * m.LEFT)
                    self.add(dots)
                    self.play(  # all three begin now; the play lasts 3 s
                        dots[0].animate(run_time=1).shift(10 * m.RIGHT),
                        dots[1].animate(run_time=2).shift(10 * m.RIGHT),
                        dots[2].animate(run_time=3).shift(10 * m.RIGHT),
                        rate_func=m.linear,  # for each of the three
                    )
            ```
        """
        from manimgx.animation.timeline import AnimationGroup, Wait, _flatten, prepare
        from manimgx.animation.transform import Compositor

        anims = [prepare(a) for a in _flatten(animations)]
        if not anims:
            raise ValueError("Called Scene.play with no animations")
        for anim in anims:
            for key, value in options.items():
                if value is not None:
                    setattr(anim, key, value)
        start, index, where = self.clock, self.num_plays, _written()
        wait = anims[0] if len(anims) == 1 and isinstance(anims[0], Wait) else None
        self.num_plays += 1
        if wait is not None:
            end = start + wait._duration
            self._run(end, stop=wait.stop_condition, frozen=bool(wait.is_static_wait))
        else:
            anim = (
                anims[0]
                if len(anims) == 1
                else AnimationGroup(
                    *anims, group=Group(), suspend_mobject_updating=False
                )
            )
            end = start + anim._duration
            self.compositor, self._animation = Compositor(), anim
            try:
                self._play(anim, start, end)
            finally:
                self.compositor, self._animation = None, None
        self.film.played(Play(index, start, self.clock, where), tuple(anims))

    def _play(self, anim: Animation, start: Fraction, end: Fraction) -> None:
        from manimgx.animation.timeline import AnimationGroup, Wait, windows
        from manimgx.audio.sound import Clip, Sound

        self._bring(anim)
        anim._setup_scene(self)
        anim.begin()
        # its sounds start as their windows open: where the layout puts them, whatever path
        # computes the frames
        if _sounds(anim):
            for window in windows(anim):
                if isinstance(window.part, Sound):
                    at = start + window.opens * (end - start)
                    self.film.clips.append(Clip(window.part, at))
        if all(isinstance(p, Sound | Wait) for p in _leaves(anim)):
            self._run(end)  # nothing on screen moves: as a wait
            anim.finish()
            anim.clean_up_from_scene(self)
            return
        finished = False

        def act(t: Fraction, only: Route | None) -> Callable[[], None] | None:
            nonlocal finished
            if finished:  # the end again, with its per-frame updaters (`_instant`)
                return None
            if t < end:
                alpha = float((t - start) / (end - start))
                if (  # its parts open once all is at t
                    isinstance(anim, AnimationGroup)
                    and type(anim).interpolate is AnimationGroup.interpolate
                ):
                    anim.advance(t, only)
                    return anim._step(alpha, only)
                anim.advance(t)
                anim.interpolate(alpha)
                return None
            # the end: the model as time brought it here; the object's per-frame updaters run
            # once, in this instant's pass, not on the model as well
            framing, clock.framing = clock.framing, False
            anim.advance(t)
            clock.framing = framing
            anim.finish()
            anim.clean_up_from_scene(self)
            finished = True
            return None

        fps = self._fps()
        parts = windows(anim)
        boundaries: dict[float, Fraction] = {}
        for part in parts:
            for at in (part.opens, part.closes):
                if at is not None:
                    time = start + at * (end - start)
                    boundaries[float(time)] = max(
                        boundaries.get(float(time), time), time
                    )
        frames = range(self.frame, clock.frame_at(end, fps))
        alpha = [
            float((self._sample(Fraction(k) / fps, boundaries) - start) / (end - start))
            for k in frames
        ]
        pure = self._pure_tweens(anim, alpha)
        if pure is None:
            # its parts begin and finish at their windows, whatever the frame rate: at
            # instants of their own where that shows (then the first at its start)
            self._playing = _acted_on(anim)
            self._events = {
                start + x * (end - start): concern
                for x, concern in self._exact(parts).items()
            }
            try:
                if self._events and Fraction(self.frame) / fps != start:
                    self._instant(start, act, framing=False)
                self._run(end, act, boundaries=boundaries)
            finally:
                self._events, self._playing = {}, []
        else:
            tweens, introduced = pure
            self._advance_tweens(anim, tweens, alpha, introduced)
            self._instant(end, act)
            self.clock = end

    def _exact(self, parts: list[Window]) -> dict[Fraction, Concern | None]:
        """Where in the play (its progress) its parts begin and finish: each an instant the
        scene computes, a frame there or not, with what it concerns: the parts beginning or
        finishing there, the parts running across it that drive what those read or drive,
        and, among what those read or drive, the mobjects with time-based updaters. None:
        everything (a scene's own time-based updater may move anything)."""
        full = any(not _per_frame(u) for u in self.updaters)
        moving = {
            id(m): m
            for m in self._running()
            if any(not _per_frame(u) for u in m.updaters)
        }
        from manimgx.animation.timeline import route

        writers: dict[int, list[tuple[int, Fraction, Fraction | None]]] = {}
        for part, opens, closes, _ in parts:
            for m in part.mobject.get_family():
                writers.setdefault(id(m), []).append((id(part), opens, closes))
        paths = {id(window.part): window.path for window in parts}
        found: dict[Fraction, tuple[set[int], dict[int, Mobject]]] = {}

        def concern(at: Fraction, part: Animation, touched: list[Mobject]) -> None:
            ids, mobs = found.setdefault(at, (set(), {}))
            ids.add(id(part))
            for m in touched:
                ids.update(
                    other
                    for other, o, c in writers.get(id(m), ())
                    if o < at and (c is None or at < c)  # running across it
                )
                if id(m) in moving:
                    mobs[id(m)] = m

        for part, opens, closes, _ in parts:
            if 0 < opens < 1:
                reads = [part.mobject] + [
                    k for k in part.keys if isinstance(k, Mobject)
                ]
                concern(opens, part, [m for key in reads for m in key.get_family()])
            if closes is not None and 0 < closes < 1:
                concern(closes, part, part.mobject.get_family())
        return {
            at: (
                None
                if full
                else Concern(route(paths[i] for i in ids), list(mobs.values()))
            )
            for at, (ids, mobs) in sorted(found.items())
        }

    def _event(self, t: Fraction, act: Act, concern: Concern) -> None:
        """An instant no frame shows, where parts of the play begin or finish: only what it
        concerns is brought to `t` (see `_exact`); the rest waits for the next frame, where
        nothing can have read it meanwhile. What is simulated does not step here (its steps
        are its clock's), and no per-frame updater runs."""
        clock.now, clock.stepping, clock.framing = t, False, False
        opening = act(t, concern.parts)
        for mob in concern.mobjects:
            mob.advance(t, recursive=False)
        if opening is not None:
            self._together(opening)
        clock.stepping = clock.framing = True

    def _together(self, begin: Callable[[], object]) -> None:
        """Run `begin`, in which animations begin together: they all find the scene as it
        was, and what they bring in (`_introduce`) is looked for in what it holds, found
        once for them all."""
        self._beginning, self._holding = True, None
        try:
            begin()
        finally:
            self._beginning, self._holding = False, None

    def _introduce(self, mobjects: Sequence[Mobject]) -> None:
        """Bring in, as an animation that introduces them begins, those of `mobjects` the
        scene lacks (with something to draw or to run), each by itself, as `add` does: one
        none of whose family the scene holds joins it without its being searched again."""
        holding = self._holding
        if holding is None or holding[0] is not self.mobjects:
            holding = (self.mobjects, {id(m) for m in _family(self.mobjects)})
        held = holding[1]
        lacking = [
            mob
            for mob in mobjects
            if id(mob) not in held
            and any(m.has_points() or m.updaters for m in mob.get_family())
        ]
        if lacking:
            family = _family(lacking)
            if self.foreground_mobjects or any(id(m) in held for m in family):
                self.add(*lacking)  # (what the scene held of them leaves its place)
                holding = None
            else:
                if any(m.updaters for m in family):  # their updaters run from now on
                    for m in family:
                        m._stamp(clock.now, recursive=False)
                self.mobjects = [*self.mobjects, *remove_list_redundancies(lacking)]
                held.update(id(m) for m in family)
                holding = (self.mobjects, held)
        if self._beginning:
            self._holding = holding

    def _bring(self, anim: Animation) -> None:
        """Bring into the scene, as a play begins, what its animations act on that it lacks,
        in their order, each by itself (what it holds stays in place): all but what an
        animation introduces (it joins as that animation begins) and what a replacement
        puts in (as it finishes)."""
        from manimgx.animation.timeline import AnimationGroup, _held, _lacks
        from manimgx.animation.transform import Transform

        promised: set[int] = set()
        members = self.get_mobject_family_members()

        def visit(anim: Animation) -> None:
            if isinstance(anim, AnimationGroup):
                for part in anim.animations:
                    visit(part)
            elif anim.is_introducer():
                promised.update(id(mob) for mob in _held(anim.mobject))
            else:
                for mob in _held(anim.mobject):
                    if id(mob) not in promised and _lacks(mob, members):
                        self.add(mob)
                        members.extend(mob.get_family())
                if (
                    isinstance(anim, Transform)
                    and anim.replace_mobject_with_target_in_scene
                    and anim.target_mobject is not None
                ):
                    promised.add(id(anim.target_mobject))

        visit(anim)

    def wait(
        self,
        duration: float = DEFAULT_WAIT_TIME,
        stop_condition: Callable[[], bool] | None = None,
        frozen_frame: bool | None = None,
    ) -> None:
        """Let time pass, playing nothing: the updaters keep running.

        The video goes on for `duration` seconds, and `construct` goes on at their end.
        With a `stop_condition`, the wait ends at the first frame at which the condition
        holds, and the scene goes on from that frame's time. With `frozen_frame`, the
        picture holds instead: the video goes on for `duration`, but nothing moves, no
        updater runs, and time-based updaters go on afterward as if no time had passed
        (see [`pause`][manimgx.Scene.pause]).

        Args:
            duration: How long, in seconds.
            stop_condition: A function of no arguments, checked at every frame once it
                is drawn: the wait ends at the first at which it returns True. None: the
                wait lasts its whole duration.
            frozen_frame: Whether the picture holds while the world stands still; it
                cannot be combined with a `stop_condition` (a ValueError). None or
                False: time runs.

        Examples:
            ```python
            import manimgx as m


            class SceneWaitExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                    square.add_updater(lambda mob, dt: mob.rotate(dt * m.PI / 3))
                    self.add(square)
                    self.wait(2)  # time passes: the updater turns the square
                    self.wait(1, frozen_frame=True)  # the picture holds
                    self.wait(2)  # it turns on from where it stopped
            ```
        """
        from manimgx.animation.timeline import Wait

        self.play(
            Wait(
                run_time=duration,
                stop_condition=stop_condition,
                frozen_frame=frozen_frame,
            )
        )

    def pause(self, duration: float = DEFAULT_WAIT_TIME) -> None:
        """Hold the picture while the world stands still: a [`wait`][manimgx.Scene.wait]
        with `frozen_frame`.

        The video goes on for `duration`; no updater runs, and time-based updaters go on
        afterwards as if no time had passed.

        Args:
            duration: How long, in seconds.
        """
        self.wait(duration, frozen_frame=True)

    def wait_until(
        self, stop_condition: Callable[[], bool], max_time: float = 60
    ) -> None:
        """Let time pass until a condition holds: a [`wait`][manimgx.Scene.wait] that
        ends at the first frame at which `stop_condition` returns True, or after
        `max_time` seconds.

        Args:
            stop_condition: A function of no arguments, checked at every frame once it
                is drawn.
            max_time: The longest it waits, in seconds.
        """
        self.wait(max_time, stop_condition=stop_condition)

    def next_section(
        self,
        name: str = "unnamed",
        section_type: SectionType = "default.normal",
        skip_animations: bool = False,
        *,
        notes: str = "",
    ) -> None:
        """Begin a section of the film here: a slide, when the film is presented.

        A film is a row of sections, each lasting until the next begins (the first begins
        with the film). Presented (`manimgx present`), the film plays a section and, by
        its type, stops at its end until the presenter goes on, goes on by itself, or
        plays it again and again until the presenter goes on. A section begins at a
        frame, whose picture a presentation stops on: if the scene's time falls between
        two frames, the world holds still until the next one. Rendered, a film just plays
        through its sections.

        Args:
            name: The section's name.
            section_type: How a presentation plays the section that begins here:
                `"default.normal"` (or `"presentation.normal"`) stops at its end;
                `"presentation.skip"` goes on by itself; `"presentation.loop"` plays it
                again until the presenter goes on; `"presentation.complete_loop"` too,
                finishing its round first.
            skip_animations: Accepted for Manim compatibility; ignored.
            notes: What the presenter reads during the section.
        """
        fps = self._fps()
        at = Fraction(self.frame) / fps
        if at != self.clock:  # to its frame, the world held still
            self._run(at, frozen=True)
        self.film.section(name, self.clock, section_type, notes)

    def add_subcaption(
        self, content: str, duration: float = 1, offset: float = 0
    ) -> None:
        """Caption the film: `content` shown from now plus `offset`, for `duration` seconds.

        The film's [`captions`][manimgx.Film.captions] hold it, with those of its
        speech; `manimgx render` writes them beside the video, as subtitles.

        Args:
            content: The caption's text.
            duration: How long it shows, in seconds.
            offset: How long after now it begins, in seconds.
        """
        start = float(clock.now) + offset
        self.film.subcaptions.append(Caption(start, start + duration, content))

    def say(
        self, script: str, *animations: Animation, voice: Voice | None = None
    ) -> Speech:
        """Speak a script, playing animations as it is said; the scene waits for both.

        Mark in brackets the words an animation belongs to: the animations given play,
        in order, during the bracketed words, each starting as its words start and
        lasting as long as they take to say, or its own run time if that is longer (an
        empty `[]` starts one where it stands). Without brackets, the animations play
        during the whole speech. The brackets are not spoken.

        Args:
            script: What to say, with a bracketed span for each animation (or none).
            *animations: The animations, one per span.
            voice: Who says it; by default the scene's [`voice`][manimgx.Scene.voice].

        Returns:
            The speech, with its words and when each is said.

        Examples:
            ```python
            import manimgx as m


            class SayExample(m.Scene):
                def construct(self) -> None:
                    x2 = m.MathTex("x^2").shift(2 * m.LEFT)
                    dx = m.MathTex("2x").shift(2 * m.RIGHT)
                    self.add(x2)
                    self.say(
                        "The derivative of [x squared] is [two x].",
                        m.Indicate(x2),
                        m.Write(dx),
                    )
            ```
        """
        from manimgx.animation.timeline import AnimationGroup, Succession, Wait
        from manimgx.audio import spans, times

        text, found = spans(script)
        if found and len(found) != len(animations):
            raise ValueError(
                f"{len(found)} bracketed spans for {len(animations)} animations: give"
                " one animation per span"
            )
        speech = self.speech(text, voice)
        parts: list[Animation] = [speech]
        for anim, span in zip(
            animations, found or [None] * len(animations), strict=True
        ):
            start, end = (0.0, speech.duration) if span is None else times(speech, span)
            anim.run_time = max(anim.run_time, end - start)
            parts.append(Succession(Wait(start), anim) if start > 0 else anim)
        self.play(AnimationGroup(*parts))
        return speech

    def speech(self, text: str, voice: Voice | None = None) -> Speech:
        """What the scene's voice says for `text`, without playing it.

        Spoken once, then kept in `voice/` beside the scene's file (named by the text), so
        the scene renders again without speaking again; replace a file there with your
        own recording of the same words, and it is used instead. Play the speech, add it
        ([`add_sound`][manimgx.Scene.add_sound]: it speaks while the scene goes on), or
        read its [`words`][manimgx.Speech.words].

        Args:
            text: What to say.
            voice: Who says it; by default the scene's [`voice`][manimgx.Scene.voice].

        Returns:
            The speech.
        """
        from manimgx.audio import Fal, cached

        # the scene's voice, as given: a function set on the class is not a method of it
        own = self.__dict__.get("voice", inspect.getattr_static(type(self), "voice"))
        if isinstance(own, staticmethod):
            own = own.__func__
        return cached(voice or own or Fal(), text, _voice_folder(self))

    voice: Voice | None = None
    """Who speaks the scene's [`say`][manimgx.Scene.say]: any
    [voice][manimgx.audio.Voice]; None for fal.ai's default model
    ([`Fal()`][manimgx.audio.fal.Fal])."""

    def add_sound(
        self,
        sound: str | os.PathLike[str] | Sound,
        time_offset: float = 0,
        gain: float | None = None,
    ) -> Clip:
        """Start a sound: now, or `time_offset` seconds from now; it takes no time.

        The scene goes on at once, and the sound plays over whatever follows, until it
        ends (or the film does, or its clip is stopped). Called by an updater, it starts
        at the instant the updater runs for: a bounce sounds exactly at the bounce. To
        wait for a sound, [`play`][manimgx.Scene.play] it instead.

        Args:
            sound: The sound, or its file.
            time_offset: How long after now it starts, in seconds.
            gain: How much louder it plays, in decibels (negative: quieter).

        Returns:
            Its clip: [`stop`][manimgx.audio.sound.Clip.stop] it to end it early.
        """
        from manimgx.audio.sound import Clip, Sound

        if not isinstance(sound, Sound):
            sound = Sound(sound)
        if gain:
            sound = sound.gain(gain)
        # decoded now: a file it cannot read fails here, not at the end of the render
        _ = sound.samples
        clip = Clip(sound, clock.now + clock.rational(time_offset))
        self.film.clips.append(clip)
        return clip


@deprecated(
    "MovingCameraScene is Scene: every scene's camera moves (self.camera.frame)",
    category=None,
)
class MovingCameraScene(Scene):
    """A scene whose camera moves: the name Manim CE knows it by. Every scene's camera
    moves, so it is a [`Scene`][manimgx.Scene]: animate `self.camera.frame` to pan and
    zoom.
    """


class ZoomedScene(Scene):
    """A scene with a second camera, whose picture is shown in the frame: a magnifying
    glass.

    `zoomed_camera` sees what its frame, a small rectangle in the scene
    (`zoomed_camera.frame`), covers, and `zoomed_display` shows its picture, larger, in
    a corner of the frame. Both appear with
    [`activate_zooming`][manimgx.ZoomedScene.activate_zooming]; move, scale or animate
    the zoomed camera's frame to look elsewhere, and the picture follows.

    Args:
        zoomed_display_height: The display's height, in scene units.
        zoomed_display_width: The display's width, in scene units.
        zoomed_display_center: Where the display's center is; None for a corner of the
            frame.
        zoomed_display_corner: Which corner of the frame the display is in, when it has
            no `zoomed_display_center`: a direction, such as [`UR`][manimgx.UR].
        zoomed_display_corner_buff: The display's distance from the edges at that
            corner, in scene units.
        zoomed_camera_config: [The zoomed camera's look][manimgx.scene.ZoomedCameraConfig]:
            its frame's outline, and its picture's background.
        zoomed_camera_image_mobject_config: Keywords for the display, the picture of
            what the zoomed camera sees: its style, and its outline's
            (`default_display_frame_config`).
        zoomed_camera_frame_starting_position: Where the zoomed camera's frame starts.
        zoom_factor: The size of the zoomed camera's frame, as a fraction of the
            display's: the display magnifies `1 / zoom_factor` times.
        image_frame_stroke_width: Accepted for Manim compatibility; ignored.
        zoom_activated: Whether zooming is active:
            [`activate_zooming`][manimgx.ZoomedScene.activate_zooming] sets it, and it
            shows nothing by itself.

    Examples:
        ```python
        import manimgx as m


        class ZoomedSceneExample(m.ZoomedScene):
            def construct(self) -> None:
                title = m.Text("manimgx", font_size=120).shift(m.LEFT)
                note = m.Text("exact in time, typed throughout", font_size=14)
                note.next_to(title, m.DOWN)
                self.add(title, note)
                frame = self.zoomed_camera.frame
                frame.move_to(note.get_left())
                self.activate_zooming(animate=True)
                self.play(frame.animate.move_to(note.get_right()), run_time=2)
        ```
    """

    def __init__(
        self,
        zoomed_display_height: float = 3,
        zoomed_display_width: float = 3,
        zoomed_display_center: Point3DLike | None = None,
        zoomed_display_corner: Vector3DLike = UR,
        zoomed_display_corner_buff: float = DEFAULT_MOBJECT_TO_EDGE_BUFFER,
        zoomed_camera_config: ZoomedCameraConfig | None = None,
        zoomed_camera_image_mobject_config: ImageCameraOptions | None = None,
        zoomed_camera_frame_starting_position: Point3DLike = ORIGIN,
        zoom_factor: float = 0.15,
        image_frame_stroke_width: float = 3,
        zoom_activated: bool = False,
    ) -> None:
        self.zoomed_display_height = zoomed_display_height
        self.zoomed_display_width = zoomed_display_width
        self.zoomed_display_center = zoomed_display_center
        self.zoomed_display_corner = zoomed_display_corner
        self.zoomed_display_corner_buff = zoomed_display_corner_buff
        self.zoomed_camera_config = ZoomedCameraConfig(
            default_frame_stroke_width=2, background_opacity=1
        ) | (zoomed_camera_config or ZoomedCameraConfig())
        self.zoomed_camera_image_mobject_config: ImageCameraOptions = (
            zoomed_camera_image_mobject_config or {}
        )
        self.zoomed_camera_frame_starting_position = (
            zoomed_camera_frame_starting_position
        )
        self.zoom_factor = zoom_factor
        self.image_frame_stroke_width = (
            image_frame_stroke_width  # CE stores it and never reads it
        )
        self.zoom_activated = zoom_activated
        super().__init__()

    def setup(self) -> None:
        """Make the zoomed camera and its display: [`render`][manimgx.Scene.render]
        calls it before `construct`. A subclass that overrides it calls this one first.
        """
        from manimgx.mobjects.images import ImageMobjectFromCamera

        super().setup()
        options = self.zoomed_camera_config
        camera = Camera()
        camera.background_opacity = options.get("background_opacity", 1)
        camera.frame.set_stroke(
            options.get("default_frame_stroke_color", WHITE),
            options.get("default_frame_stroke_width", 2),
        )
        display = ImageMobjectFromCamera(
            camera, **self.zoomed_camera_image_mobject_config
        ).add_display_frame()
        for mob in (camera.frame, display):
            mob.stretch_to_fit_height(self.zoomed_display_height)
            mob.stretch_to_fit_width(self.zoomed_display_width)
        camera.frame.scale(self.zoom_factor)
        camera.frame.move_to(self.zoomed_camera_frame_starting_position)
        if self.zoomed_display_center is not None:
            display.move_to(self.zoomed_display_center)
        else:
            display.to_corner(
                self.zoomed_display_corner, buff=self.zoomed_display_corner_buff
            )
        self.zoomed_camera = camera
        self.zoomed_display = display

    def activate_zooming(self, animate: bool = False) -> None:
        """Show the zoomed camera's frame and its display, in front of everything else.

        Args:
            animate: Whether to animate their coming first, in two plays: the frame
                shrinks from the whole view to its place (`get_zoom_in_animation`), then
                the display grows out of it to its own
                (`get_zoomed_display_pop_out_animation`).
        """
        self.zoom_activated = True
        if animate:
            self.play(self.get_zoom_in_animation())
            self.play(self.get_zoomed_display_pop_out_animation())
        self.add_foreground_mobjects(self.zoomed_camera.frame, self.zoomed_display)

    def get_zoom_in_animation(self, **kwargs: Unpack[TransformOptions]) -> Animation:
        """Make the animation in which the zoomed camera's frame shrinks from the whole
        view to its place.

        The frame moves to its start at once: it covers the view, centered on the
        origin, without its outline, until the animation plays.

        Args:
            **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] (2
                seconds long unless given a `run_time`).

        Returns:
            The animation, to play.
        """
        from manimgx.animation.motion import Restore

        kwargs.setdefault("run_time", 2)
        frame = self.zoomed_camera.frame
        frame.save_state()
        frame.stretch_to_fit_width(self.camera.frame_width)
        frame.stretch_to_fit_height(self.camera.frame_height)
        frame.center()
        frame.set_stroke(width=0)
        return Restore(frame, **kwargs)

    def get_zoomed_display_pop_out_animation(
        self, **kwargs: Unpack[TransformOptions]
    ) -> Animation:
        """Make the animation in which the display grows out of the zoomed camera's
        frame to its place.

        The display moves to its start at once: over the zoomed camera's frame, until
        the animation plays.

        Args:
            **kwargs: [Transform options][manimgx.animation.transform.TransformOptions].

        Returns:
            The animation, to play.
        """
        from manimgx.animation.motion import Restore

        display = self.zoomed_display
        display.save_state()
        display.replace(self.zoomed_camera.frame, stretch=True)
        return Restore(display, **kwargs)

    def get_zoom_factor(self) -> float:
        """How small the zoomed camera's frame is next to the display.

        Returns:
            The frame's height over the display's: the display magnifies its inverse.
        """
        return self.zoomed_camera.frame.height / self.zoomed_display.height


class ThreeDScene(Scene):
    r"""A scene seen in three dimensions: from a camera that orbits it, with perspective
    and depth.

    The camera looks at the center of its frame from the angles `phi`, from the z axis
    (0 looks straight down on the xy plane), and `theta`, around it (−90° by default, so
    that x points right); `gamma` turns it about its line of sight, `zoom` magnifies,
    and `focal_distance` is how far it is from the point it looks at. Each is a
    [value tracker][manimgx.ValueTracker] of the [camera][manimgx.Camera], so it moves
    as any mobject does: [`move_camera`][manimgx.ThreeDScene.move_camera] animates it,
    and an ambient rotation keeps it turning. Nearer surfaces hide farther ones;
    mobjects fixed in the frame are drawn flat on the screen, over everything.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ThreeDSceneExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(
                    phi=65 * m.DEGREES, theta=-50 * m.DEGREES, zoom=0.6
                )
                axes = m.ThreeDAxes(x_range=(-3, 3), y_range=(-3, 3), z_range=(-2, 2))
                surface = m.Surface(
                    lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)),
                    u_range=(-3, 3),
                    v_range=(-3, 3),
                    resolution=(24, 24),
                ).set_fill_by_checkerboard(m.BLUE_D, m.TEAL, opacity=0.9)
                title = m.MathTex(r"z = \sin x \cos y", font_size=64).to_corner(m.UL)
                self.add_fixed_in_frame_mobjects(title)
                self.add(axes, surface)
        ```
    """

    three_d = True

    def set_camera_orientation(
        self,
        phi: float | None = None,
        theta: float | None = None,
        gamma: float | None = None,
        zoom: float | None = None,
        focal_distance: float | None = None,
        frame_center: Point3DLike | Mobject | None = None,
    ) -> None:
        """Set where the camera looks from, at once: each setting given; the others stay
        as they are.

        Args:
            phi: The angle between the camera's line of sight and the z axis, in
                radians: 0 looks straight down on the xy plane.
            theta: The camera's angle around the z axis, in radians, counterclockwise
                from the x axis: at −90° it looks from the side of negative y, so that x
                points right.
            gamma: How far the camera turns about its line of sight, in radians.
            zoom: How much the camera magnifies: 2 shows everything twice as large.
            focal_distance: The camera's distance from the point it looks at, in scene
                units: the nearer, the stronger the perspective.
            frame_center: The point the camera looks at, or a mobject whose center it
                is: the camera's frame moves there.
        """
        cam = self.camera
        for value, tracker in (
            (phi, cam.phi_tracker),
            (theta, cam.theta_tracker),
            (gamma, cam.gamma_tracker),
            (zoom, cam.zoom_tracker),
            (focal_distance, cam.focal_distance_tracker),
        ):
            if value is not None:
                tracker.set_value(value)
        if frame_center is not None:
            cam.frame.move_to(frame_center)

    def _tracker(self, about: str) -> ValueTracker:
        return {
            "theta": self.camera.theta_tracker,
            "phi": self.camera.phi_tracker,
            "gamma": self.camera.gamma_tracker,
        }[about.lower()]

    def begin_ambient_camera_rotation(
        self, rate: float = 0.02, about: str = "theta"
    ) -> None:
        """Start turning the camera steadily, through plays and waits alike, until
        `stop_ambient_camera_rotation`.

        One of the camera's angles grows at a steady rate: its tracker gets an updater
        (a [flow][manimgx.mobject.flow]) and joins the scene.

        Args:
            rate: How fast the angle grows, in radians per second; a negative rate turns
                the other way.
            about: The angle: "theta" (around the z axis), "phi" or "gamma", in any
                case.

        Examples:
            ```python
            import manimgx as m


            class ThreeDSceneAmbientRotationExample(m.ThreeDScene):
                def construct(self) -> None:
                    self.set_camera_orientation(
                        phi=70 * m.DEGREES, theta=-45 * m.DEGREES
                    )
                    torus = m.Torus(major_radius=2.5, minor_radius=0.8)
                    self.add(m.ThreeDAxes(), torus.set_color(m.TEAL))
                    self.begin_ambient_camera_rotation(rate=m.PI / 4)  # 45° a second
                    self.wait(4)
            ```
        """
        tracker = self._tracker(about)
        tracker.add_updater(flow(lambda m, dt: m.increment_value(rate * dt)))
        self.add(tracker)

    def stop_ambient_camera_rotation(self, about: str = "theta") -> None:
        """Stop turning the camera: every updater of the angle's tracker is removed, and
        the tracker leaves the scene. The camera stays where it turned to.

        Args:
            about: The angle: "theta", "phi" or "gamma", in any case.
        """
        tracker = self._tracker(about)
        tracker.clear_updaters()
        self.remove(tracker)

    def begin_3dillusion_camera_rotation(
        self,
        rate: float = 1,
        origin_phi: float | None = None,
        origin_theta: float | None = None,
    ) -> None:
        """Start swaying the camera around its orientation, for an illusion of depth,
        through plays and waits alike, until `stop_3dillusion_camera_rotation`.

        The camera circles a little: `theta` swings 0.2 radians either side of
        `origin_theta`, and `phi` between `origin_phi` and 0.2 radians less, a quarter
        of a cycle apart. The trackers of the two angles get updaters (flows) and join
        the scene.

        Args:
            rate: How fast it sways, in radians of its cycle per second: a cycle takes
                2π / `rate` seconds.
            origin_phi: The `phi` it sways from; None for the camera's present one.
            origin_theta: The `theta` it sways about; None for the camera's present one.
        """
        cam = self.camera
        origin_theta = cam.get_theta() if origin_theta is None else origin_theta
        origin_phi = cam.get_phi() if origin_phi is None else origin_phi
        clocks = [0.0, 0.0]

        def swing_theta(m: ValueTracker, dt: float) -> None:
            clocks[0] += dt * rate
            m.set_value(origin_theta + 0.2 * np.sin(clocks[0]))

        def swing_phi(m: ValueTracker, dt: float) -> None:
            clocks[1] += dt * rate
            m.set_value(origin_phi + 0.1 * np.cos(clocks[1]) - 0.1)

        cam.theta_tracker.add_updater(flow(swing_theta))
        cam.phi_tracker.add_updater(flow(swing_phi))
        self.add(cam.theta_tracker, cam.phi_tracker)

    def stop_3dillusion_camera_rotation(self) -> None:
        """Stop swaying the camera: every updater of the `theta` and `phi` trackers is
        removed, and they leave the scene. The camera stays where the sway left it."""
        for tracker in (self.camera.theta_tracker, self.camera.phi_tracker):
            tracker.clear_updaters()
            self.remove(tracker)

    def move_camera(
        self,
        phi: float | None = None,
        theta: float | None = None,
        gamma: float | None = None,
        zoom: float | None = None,
        focal_distance: float | None = None,
        frame_center: Point3DLike | Mobject | None = None,
        added_anims: Sequence[Animation] = (),
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        """Animate the camera to a new orientation, in one play: each setting given; the
        others stay as they are.

        Each setting moves steadily from its value to the new one, eased by the rate
        function, so a `theta` 2π greater takes the camera once around. The frame moves
        to `frame_center` if given, and `added_anims` play along.

        Args:
            phi: The angle between the camera's line of sight and the z axis, in
                radians: 0 looks straight down on the xy plane.
            theta: The camera's angle around the z axis, in radians, counterclockwise
                from the x axis.
            gamma: How far the camera turns about its line of sight, in radians.
            zoom: How much the camera magnifies: 2 shows everything twice as large.
            focal_distance: The camera's distance from the point it looks at, in scene
                units.
            frame_center: The point for the camera to look at, or a mobject whose center
                it is.
            added_anims: Animations to play along.
            **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] for
                every animation of the play, the added ones too.

        Examples:
            ```python
            import manimgx as m


            class ThreeDSceneMoveCameraExample(m.ThreeDScene):
                def construct(self) -> None:
                    cube = m.Cube(side_length=2.5, fill_opacity=0.8, fill_color=m.BLUE)
                    self.add(m.ThreeDAxes(), cube)
                    self.move_camera(
                        phi=70 * m.DEGREES, theta=-45 * m.DEGREES, run_time=2
                    )
                    self.move_camera(theta=45 * m.DEGREES, zoom=1.5, run_time=2)
            ```
        """
        cam = self.camera
        pairs = (
            (phi, cam.phi_tracker),
            (theta, cam.theta_tracker),
            (focal_distance, cam.focal_distance_tracker),
            (gamma, cam.gamma_tracker),
            (zoom, cam.zoom_tracker),
        )
        anims: list[Animation] = [
            tracker.animate.set_value(value)
            for value, tracker in pairs
            if value is not None
        ]
        if frame_center is not None:
            anims.append(cam.frame.animate.move_to(frame_center))
        self.play(*anims, *added_anims, **kwargs)
        if frame_center is not None:
            self.remove(cam.frame)

    def add_fixed_in_frame_mobjects(self, *mobjects: Mobject) -> None:
        """Add mobjects pinned to the screen: each is drawn where its points are, as in
        a two-dimensional view centered on the origin, over everything else.

        They are added to the scene, and stay where they are on the screen whatever the
        camera's angles, zoom and center: a title placed with `to_corner` stays in its
        corner. Everything in them is pinned, now and later: a member added later (a
        number's new digits, what an updater or a Transform makes) is pinned too.
        """
        self.add(*mobjects)
        self.camera.add_fixed_in_frame_mobjects(*mobjects)


def _tracks(
    anim: Animation,
    tweens: list[tuple[Transform, Path]],
    alpha: np.ndarray,
    introduced: set[int],
) -> list[tuple[Mobject, list[Mobject], Path, np.ndarray, np.ndarray]]:
    """A pure play at these alphas: per leaf, its keyframes, path, and per instant its interval
    and t (-1: not begun, as the play found it; -2: absent, before the part that brings it
    begins or after a remover's window closes)."""
    from manimgx.animation.timeline import keyframe_at, schedule

    alphas = {id(tween): (a, c) for tween, a, c in schedule(anim, alpha)}
    out = []
    for tween, path in tweens:
        family = list(tween.get_all_families_zipped())
        steps = len(family[0]) - 2 if family else 0  # keyframe intervals
        progress, closed = alphas[id(tween)]
        for i, (leaf, *keys) in enumerate(family):
            index = np.full(len(alpha), -2 if id(leaf) in introduced else -1)
            fraction = np.zeros(len(alpha))
            for f, a in enumerate(progress):
                if a == a:  # begun
                    index[f], fraction[f] = keyframe_at(
                        steps, tween.get_sub_alpha(float(a), i, len(family))
                    )
            if tween.is_remover():  # gone once its window closed
                index[closed] = -2
            out.append((leaf, keys, path, index, fraction))
    return out


def _voice_folder(scene: Scene) -> pathlib.Path:
    """Where a scene keeps what its voices said: `voice/` beside its file; for a scene
    with no file (a notebook's), the user's cache."""
    try:
        return pathlib.Path(inspect.getfile(type(scene))).parent / "voice"
    except (TypeError, OSError):
        return pathlib.Path.home() / ".cache" / "manimgx" / "voice"


def _leaves(anim: Animation) -> Iterable[Animation]:
    """The animations under `anim` that act themselves: its parts, and theirs."""
    from manimgx.animation.timeline import AnimationGroup

    if isinstance(anim, AnimationGroup):
        for part in anim.animations:
            yield from _leaves(part)
    else:
        yield anim


def _sounds(anim: Animation) -> bool:
    from manimgx.audio.sound import Sound

    return any(isinstance(p, Sound) for p in _leaves(anim))


def _acted_on(anim: Animation) -> list[Mobject]:
    """The mobjects an animation's parts act on, and the targets they run (their own
    objects)."""
    return [
        mob
        for part in _leaves(anim)
        for mob in [
            part.mobject,
            *(key for key in part.keys if isinstance(key, Mobject)),
        ]
    ]


def _forward(alpha: np.ndarray) -> bool:
    """Does a part's alpha only go forward — once begun, never not begun again, never back?"""
    begun = alpha == alpha
    first = int(np.argmax(begun)) if begun.any() else len(alpha)
    return bool(begun[first:].all() and np.all(np.diff(alpha[first:]) >= 0))


_PACKAGE = os.path.dirname(__file__) + os.sep


def _written() -> tuple[str, int] | None:
    """Where the scene's own code is running: the innermost caller outside ManimGX (a scene's
    `play`, or the `wait` that plays)."""
    here = inspect.currentframe()
    frame = None if here is None else here.f_back  # `play`'s
    frame = None if frame is None else frame.f_back
    while frame is not None and frame.f_code.co_filename.startswith(_PACKAGE):
        frame = frame.f_back
    return None if frame is None else (frame.f_code.co_filename, frame.f_lineno)


def _restructure(
    mobjects: Sequence[Mobject], to_remove: Iterable[Mobject], extract: bool = True
) -> list[Mobject]:
    """Drop members, replacing each containing group with its surviving children."""
    removing = {id(mob) for mob in (_family(to_remove) if extract else to_remove)}
    if not removing:
        return list(mobjects)
    broken: set[int] = set()
    # A family's last-occurrence order puts every parent before its children.
    # Fold in reverse: groups lose their place when a descendant is removed,
    # and vanish altogether when none of their children survive.
    for mob in reversed(_family(mobjects)):
        if id(mob) in removing or not mob.submobjects:
            continue
        if any(
            id(child) in removing or id(child) in broken for child in mob.submobjects
        ):
            if all(id(child) in removing for child in mob.submobjects):
                removing.add(id(mob))
            else:
                broken.add(id(mob))
    out: list[Mobject] = []
    pending = list(reversed(mobjects))
    while pending:
        mob = pending.pop()
        if id(mob) in removing:
            continue
        if id(mob) in broken:
            pending.extend(reversed(mob.submobjects))
        else:
            out.append(mob)
    return out


X_COLOR = GREEN_C
Y_COLOR = RED_C
Z_COLOR = BLUE_D


class _LabelPlacement(TypedDict, total=False):
    """LabelPlacement's keys, open, for the keywords that add to them."""

    at_tip: bool
    """Whether the label goes beyond the vector's tip, rather than beside its middle
    (default False)."""
    direction: Literal["left", "right"]
    """Which side of the vector the label goes on, looking along the vector (default
    "left")."""
    rotate: bool
    """Whether the label turns with the vector, rather than staying upright (default
    False)."""


class LabelPlacement(_LabelPlacement, total=False, closed=True):
    """Where a vector's label sits (for the methods that pass it on)."""


class VectorLabelOptions(_LabelPlacement, total=False, closed=True):
    """Where a vector's label sits, its color and its size (for the methods that pass
    them on)."""

    color: ParsableManimColor | None
    """The label's color, when it is made from a string (default None: the vector's)."""
    label_scale_factor: float
    """How much the label is scaled (default 0.8)."""


class UnitSquareOptions(TypedDict, total=False, closed=True):
    """The unit square's look (for the methods that pass it on)."""

    color: Colors
    """The color of its fill and its stroke (default yellow)."""
    opacity: float
    """Its fill's opacity, from 0 to 1 (default 0.3)."""
    stroke_width: float
    """Its stroke's width, in hundredths of a scene unit (default 3)."""


class VectorScene(Scene):
    """A scene for drawing vectors: arrows from the origin, their labels and their
    coordinates.

    Its methods add a plane and axes, draw vectors and label them, and animate the
    passage from a vector to its coordinates and back.
    [`add_vector`][manimgx.VectorScene.add_vector] draws a vector from the origin, in
    scene units; [`get_vector`][manimgx.VectorScene.get_vector] makes one in the
    coordinates of the scene's [`plane`][manimgx.VectorScene.plane].

    Args:
        basis_vector_stroke_width: The stroke width of the basis vectors (see
            [`get_basis_vectors`][manimgx.VectorScene.get_basis_vectors]), in hundredths
            of a scene unit.

    Examples:
        ```python
        import manimgx as m


        class VectorSceneExample(m.VectorScene):
            def construct(self) -> None:
                self.add_plane()
                vector = self.add_vector([3, 2], color=m.YELLOW)
                self.write_vector_coordinates(vector)
                self.wait()
        ```
    """

    plane: NumberPlane
    """The plane whose coordinates [`get_vector`][manimgx.VectorScene.get_vector] reads:
    a [`LinearTransformationScene`][manimgx.LinearTransformationScene] makes it; in a
    vector scene, assign it (`self.plane = self.add_plane()`)."""
    grows_vectors: ClassVar[bool] = (
        True  # `add_vector` animates unless told (CE's defaults)
    )
    """Whether [`add_vector`][manimgx.VectorScene.add_vector] shows a vector growing
    unless told otherwise: True in a vector scene, False in a transformation scene."""

    def __init__(self, basis_vector_stroke_width: float = 6.0) -> None:
        super().__init__()
        self.basis_vector_stroke_width = basis_vector_stroke_width

    def add_plane(
        self, animate: bool = False, **kwargs: Unpack[NumberPlaneOptions]
    ) -> NumberPlane:
        """Add a number plane to the scene.

        Args:
            animate: Whether to draw it in ([`Create`][manimgx.Create], its lines
                overlapping).
            **kwargs: [Number plane keywords][manimgx.NumberPlane].

        Returns:
            The plane. It is not the scene's [`plane`][manimgx.VectorScene.plane] unless
            assigned to it.
        """
        plane = NumberPlane(**kwargs)
        if animate:
            self.play(Create(plane, lag_ratio=0.5))
        self.add(plane)
        return plane

    def add_axes(self, animate: bool = False, color: Colors = WHITE) -> Axes:
        """Add axes to the scene, one scene unit to one unit.

        Args:
            animate: Whether to draw them in ([`Create`][manimgx.Create]).
            color: Their color.

        Returns:
            The axes.
        """
        axes = Axes(color=color, axis_config={"unit_size": 1})
        if animate:
            self.play(Create(axes))
        self.add(axes)
        return axes

    def get_vector(
        self, numerical_vector: Vector3DLike, **kwargs: Unpack[ArrowTips]
    ) -> Arrow:
        """Make an arrow from the origin of the scene's plane to a point given in its
        coordinates.

        Args:
            numerical_vector: The point's coordinates on
                [`plane`][manimgx.VectorScene.plane]: x and y (a z is ignored).
            **kwargs: [Arrow keywords][manimgx.Arrow].

        Returns:
            A new arrow, not added to the scene.
        """
        x, y = np.asarray(numerical_vector, dtype=float)[:2]
        return Arrow(
            self.plane.coords_to_point(0, 0),
            self.plane.coords_to_point(x, y),
            buff=0,
            **kwargs,
        )

    @overload
    def add_vector[A: Arrow](
        self,
        vector: A,
        color: Colors = ...,
        animate: bool = ...,
        **kwargs: Unpack[ArrowTipsBase],
    ) -> A: ...
    @overload
    def add_vector(
        self,
        vector: Vector3DLike,
        color: Colors = ...,
        animate: bool = ...,
        **kwargs: Unpack[ArrowTipsBase],
    ) -> Vector: ...
    def add_vector(
        self,
        vector: Arrow | Vector3DLike,
        color: Colors = PURE_YELLOW,
        animate: bool | None = None,
        **kwargs: Unpack[ArrowTipsBase],
    ) -> Arrow:
        """Add a vector to the scene: the arrow given, or a [Vector][manimgx.Vector] from
        the origin to the coordinates given.

        It is shown growing from the origin ([GrowArrow][manimgx.GrowArrow]) if `animate`
        says so, or else if the scene's `grows_vectors` does (a vector scene's does, a
        transformation scene's doesn't); then the scene takes it up: a
        [LinearTransformationScene][manimgx.LinearTransformationScene] moves it with the
        plane.

        Args:
            vector: An arrow, or the coordinates of a vector's tip, in scene units.
            color: The vector's color, when it is made from coordinates.
            animate: Whether it grows in a play; None for the scene's `grows_vectors`.
            **kwargs: [Arrow keywords][manimgx.mobjects.shapes.ArrowTipsBase] for
                a vector made from coordinates.

        Returns:
            The arrow.
        """
        if not isinstance(vector, Arrow):
            vector = Vector(np.asarray(vector, dtype=float), color=color, **kwargs)
        if self.grows_vectors if animate is None else animate:
            self.play(GrowArrow(vector))
        self.add(vector)
        self.added_vector(vector)
        return vector

    @deprecated("Manim CE's machinery: vector_to_coords calls it", category=None)
    def added_vector(self, vector: Arrow) -> None:
        """Take up a vector that [add_vector][manimgx.VectorScene.add_vector] added: a
        vector scene does nothing with it, and a
        [LinearTransformationScene][manimgx.LinearTransformationScene] moves it with its
        transformations.
        """

    def write_vector_coordinates(
        self, vector: Vector, **kwargs: Unpack[MatrixOptions]
    ) -> Matrix:
        """Write a vector's coordinates beside its tip, as a column (its
        `coordinate_label`), in a play of [`Write`][manimgx.Write].

        Args:
            **kwargs: [Matrix keywords][manimgx.mobjects.grid.MatrixOptions] for the
                column.

        Returns:
            The column.
        """
        coords = vector.coordinate_label(**kwargs)
        self.play(Write(coords))
        return coords

    def get_basis_vectors(
        self, i_hat_color: Colors = X_COLOR, j_hat_color: Colors = Y_COLOR
    ) -> VGroup:
        """Make the basis vectors î and ĵ: arrows from the origin to (1, 0) and (0, 1),
        in scene units.

        Args:
            i_hat_color: The color of î.
            j_hat_color: The color of ĵ.

        Returns:
            A new group of the two, î first.
        """
        return VGroup(
            *(
                Vector(
                    np.asarray(vect, dtype=float),
                    color=color,
                    stroke_width=self.basis_vector_stroke_width,
                )
                for vect, color in [([1, 0], i_hat_color), ([0, 1], j_hat_color)]
            )
        )

    def get_basis_vector_labels(self, **kwargs: Unpack[LabelPlacement]) -> VGroup:
        """Make labels for the basis vectors: î and ĵ, in the colors of the x and y axes
        (green and red).

        Args:
            **kwargs: [Label placement keywords][manimgx.scene.LabelPlacement].

        Returns:
            A new group of the two labels, î's first.
        """
        i_hat, j_hat = self.get_basis_vectors().submobjects
        return VGroup(
            *(
                self.get_vector_label(
                    vect, label, color=color, label_scale_factor=1, **kwargs
                )
                for vect, label, color in [
                    (i_hat, "\\hat{\\imath}", X_COLOR),
                    (j_hat, "\\hat{\\jmath}", Y_COLOR),
                ]
                if isinstance(vect, Vector)
            )
        )

    def get_vector_label(
        self,
        vector: Vector,
        label: ManimTextLabel | str,
        at_tip: bool = False,
        direction: Literal["left", "right"] = "left",
        rotate: bool = False,
        color: ParsableManimColor | None = None,
        label_scale_factor: float = LARGE_BUFF - 0.2,
    ) -> ManimTextLabel:
        r"""Make a label for a vector: beside its middle, on its left or its right, or
        beyond its tip.

        A string is typeset as LaTeX, a single letter as a bold vector
        (`\vec{\textbf{v}}`), in the vector's color. The label gets a background
        rectangle, to be read over the lines under it.

        Args:
            vector: The vector, from the origin.
            label: The label: a mobject, or LaTeX.
            at_tip: Whether it goes beyond the vector's tip, rather than beside its
                middle.
            direction: Which side of the vector it goes on, looking along the vector.
            rotate: Whether it turns with the vector, rather than staying upright.
            color: Its color, when it is made from a string; None for the vector's.
            label_scale_factor: How much it is scaled.

        Returns:
            The label, not added to the scene.
        """
        if isinstance(label, str):
            if len(label) == 1:
                label = f"\\vec{{\\textbf{{{label}}}}}"
            label = MathTex(label)
            label.set_color(vector.get_color() if color is None else color)
        label.scale(label_scale_factor)
        label.add_background_rectangle()
        if at_tip:
            vect = vector.get_vector()
            label.next_to(
                vector.get_end(), vect / np.linalg.norm(vect), buff=SMALL_BUFF
            )
        else:
            angle = vector.get_angle()
            if not rotate:
                label.rotate(-angle, about_point=ORIGIN)
            if direction == "left":
                label.shift(-np.asarray(label.get_bottom()) + 0.1 * UP)
            else:
                label.shift(-np.asarray(label.get_top()) + 0.1 * DOWN)
            label.rotate(angle, about_point=ORIGIN)
            label.shift((vector.get_end() - vector.get_start()) / 2)
        return label

    def label_vector(
        self,
        vector: Vector,
        label: ManimTextLabel | str,
        animate: bool = True,
        **kwargs: Unpack[VectorLabelOptions],
    ) -> ManimTextLabel:
        """Label a vector, and add the label to the scene (see
        [`get_vector_label`][manimgx.VectorScene.get_vector_label]).

        Args:
            vector: The vector, from the origin.
            label: The label: a mobject, or LaTeX.
            animate: Whether to write it in ([`Write`][manimgx.Write]).
            **kwargs: [Vector label keywords][manimgx.scene.VectorLabelOptions].

        Returns:
            The label.
        """
        mathtex_label = self.get_vector_label(vector, label, **kwargs)
        if animate:
            self.play(Write(mathtex_label, run_time=1))
        self.add(mathtex_label)
        return mathtex_label

    @deprecated("Manim CE's machinery: vector_to_coords calls it", category=None)
    def position_x_coordinate(
        self, x_coord: Mobject, x_line: Line, vector: Vector3DLike
    ) -> Mobject:
        """Place a vector's x coordinate by the line of its x component, in green: under
        it for a vector that points up, over it for one that points down.

        Args:
            x_coord: The coordinate.
            x_line: The line from the origin along x to the vector's x.
            vector: The vector's coordinates.

        Returns:
            The coordinate, placed.
        """
        x_coord.next_to(x_line, -np.sign(vector[1]) * UP)
        x_coord.set_color(X_COLOR)
        return x_coord

    @deprecated("Manim CE's machinery: vector_to_coords calls it", category=None)
    def position_y_coordinate(
        self, y_coord: Mobject, y_line: Line, vector: Vector3DLike
    ) -> Mobject:
        """Place a vector's y coordinate by the line of its y component, in red: right
        of it for a vector that points right, left of it for one that points left.

        Args:
            y_coord: The coordinate.
            y_line: The line along y up (or down) to the vector's tip.
            vector: The vector's coordinates.

        Returns:
            The coordinate, placed.
        """
        y_coord.next_to(y_line, np.sign(vector[0]) * RIGHT)
        y_coord.set_color(Y_COLOR)
        return y_coord

    def vector_to_coords(
        self,
        vector: Vector | Vector3DLike,
        integer_labels: bool = True,
        clean_up: bool = True,
    ) -> tuple[Matrix, Line, Line]:
        """Show how a vector gives its coordinates, in a series of plays.

        The vector (drawn first, when it is given by its coordinates) gets a line along
        x and a line up to its tip, each written with its coordinate; the coordinates
        then move into a column beside its tip.

        Args:
            vector: The vector, from the origin, or its coordinates.
            integer_labels: Whether the coordinates are rounded to integers.
            clean_up: Whether the scene is left holding what it held before, at the end.

        Returns:
            The column of coordinates, the line along x and the line up to the tip.
        """
        starting_mobjects = list(self.mobjects)
        show_creation = not isinstance(vector, Vector)
        arrow = vector if isinstance(vector, Vector) else Vector(vector)
        end = arrow.get_end()[:2]
        array = arrow.coordinate_label(integer_labels=integer_labels)
        x_line = Line(ORIGIN, end[0] * RIGHT)
        y_line = Line(x_line.get_end(), arrow.get_end())
        x_line.set_color(X_COLOR)
        y_line.set_color(Y_COLOR)
        x_coord, y_coord = array.get_entries().submobjects[:2]
        x_coord_start = self.position_x_coordinate(x_coord.copy(), x_line, end)
        y_coord_start = self.position_y_coordinate(y_coord.copy(), y_line, end)
        brackets = array.get_brackets()
        if show_creation:
            self.play(Create(arrow))
        self.play(Create(x_line), Write(x_coord_start), run_time=1)
        self.play(Create(y_line), Write(y_coord_start), run_time=1)
        self.wait()
        self.play(
            Transform(x_coord_start, x_coord, lag_ratio=0),
            Transform(y_coord_start, y_coord, lag_ratio=0),
            Write(brackets, run_time=1),
        )
        self.wait()
        self.remove(x_coord_start, y_coord_start, brackets)
        self.add(array)
        if clean_up:
            self.clear()
            self.add(*starting_mobjects)
        return array, x_line, y_line


@dataclass
class _TransformableLabel:
    """A vector's label that follows the transformations: rewritten as `target_text` (or kept)."""

    label: Mobject
    vector: Vector
    target_text: str | ManimTextLabel
    options: VectorLabelOptions


def _merged_plane(
    defaults: NumberPlaneOptions, given: NumberPlaneOptions | None
) -> NumberPlaneOptions:
    """A plane config over its defaults, key by key (and inside its axis and line styles)."""
    given = given or NumberPlaneOptions()
    merged = defaults | given
    merged["axis_config"] = merged_axis_config(
        defaults.get("axis_config"), given.get("axis_config")
    )
    merged["background_line_style"] = (defaults.get("background_line_style") or {}) | (
        given.get("background_line_style") or {}
    )
    return merged


class LinearTransformationScene(VectorScene):
    """A scene for linear transformations of the plane: a matrix applied to the plane
    and to everything on it, in one animation.

    Before `construct`, it lays a still plane in the background (`background_plane`), a
    plane over it that the transformations move ([`plane`][manimgx.VectorScene.plane]),
    and the basis vectors î and ĵ (`i_hat` and `j_hat`, together `basis_vectors`).
    [`apply_matrix`][manimgx.LinearTransformationScene.apply_matrix] then transforms
    what the scene holds, by kind: the points of the transformable mobjects, as the
    plane's; the vectors, redrawn to where their tips go; the labels that follow them;
    and the moving mobjects, moved whole to where their centers go. The background and
    foreground mobjects stay where they are.

    Args:
        include_background_plane: Whether a plane stays still in the background.
        include_foreground_plane: Whether a plane over it moves with the
            transformations: the scene's `plane`.
        background_plane_kwargs: [Number plane keywords][manimgx.NumberPlane]
            for the background plane, over its own (grey lines).
        foreground_plane_kwargs: [Number plane keywords][manimgx.NumberPlane]
            for the moving plane, over its own (it reaches past the frame, so that the
            frame stays covered as it moves).
        show_coordinates: Whether the background plane's axes are numbered.
        show_basis_vectors: Whether the basis vectors are drawn; they move with the
            transformations.
        basis_vector_stroke_width: The basis vectors' stroke width, in hundredths of a
            scene unit.
        i_hat_color: The color of î.
        j_hat_color: The color of ĵ.
        leave_ghost_vectors: Whether each transformation leaves faded copies of the
            vectors where they were.

    Examples:
        ```python
        import manimgx as m


        class LinearTransformationSceneExample(m.LinearTransformationScene):
            def __init__(self) -> None:
                super().__init__(show_coordinates=True, leave_ghost_vectors=True)

            def construct(self) -> None:
                self.add_unit_square()
                self.add_vector([-1, 2], color=m.YELLOW)
                self.apply_matrix([[1, 1], [0, 1]])  # a shear
                self.wait()
        ```
    """

    grows_vectors: ClassVar[bool] = False

    def __init__(
        self,
        include_background_plane: bool = True,
        include_foreground_plane: bool = True,
        background_plane_kwargs: NumberPlaneOptions | None = None,
        foreground_plane_kwargs: NumberPlaneOptions | None = None,
        show_coordinates: bool = False,
        show_basis_vectors: bool = True,
        basis_vector_stroke_width: float = 6,
        i_hat_color: ParsableManimColor = X_COLOR,
        j_hat_color: ParsableManimColor = Y_COLOR,
        leave_ghost_vectors: bool = False,
    ) -> None:
        super().__init__()
        self.include_background_plane = include_background_plane
        self.include_foreground_plane = include_foreground_plane
        self.show_coordinates = show_coordinates
        self.show_basis_vectors = show_basis_vectors
        self.basis_vector_stroke_width = basis_vector_stroke_width
        self.i_hat_color = ManimColor(i_hat_color)
        self.j_hat_color = ManimColor(j_hat_color)
        self.leave_ghost_vectors = leave_ghost_vectors
        self.ghost_vectors = VGroup()
        """The faded copies the transformations left of what they moved whole, where it
        was, with `leave_ghost_vectors`."""
        self.background_plane_kwargs = _merged_plane(
            {
                "color": GREY,
                "axis_config": {"color": GREY},
                "background_line_style": {"stroke_color": GREY, "stroke_width": 1},
            },
            background_plane_kwargs,
        )
        self.foreground_plane_kwargs = _merged_plane(
            {
                "x_range": (-config.frame_width, config.frame_width, 1.0),
                "y_range": (-config.frame_width, config.frame_width, 1.0),
                "faded_line_ratio": 1,
            },
            foreground_plane_kwargs,
        )

    def setup(self) -> None:
        """Lay out the planes and the basis vectors, and add them to the scene.

        [`render`][manimgx.Scene.render] calls it before `construct`; it acts once. A
        subclass that overrides it calls this one first.
        """
        if hasattr(self, "has_already_setup"):
            return
        self.has_already_setup = True
        self.background_mobjects: list[Mobject] = []
        self.foreground_mobjects: list[Mobject] = []
        self.transformable_mobjects: list[Mobject] = []
        self.moving_vectors: list[Mobject] = []
        self.transformable_labels: list[_TransformableLabel] = []
        self.moving_mobjects: list[Mobject] = []
        self.background_plane = NumberPlane(**self.background_plane_kwargs)
        if self.show_coordinates:
            self.background_plane.add_coordinates()
        if self.include_background_plane:
            self.add_background_mobject(self.background_plane)
        if self.include_foreground_plane:
            self.plane = NumberPlane(**self.foreground_plane_kwargs)
            self.add_transformable_mobject(self.plane)
        if self.show_basis_vectors:
            self.basis_vectors = self.get_basis_vectors(
                i_hat_color=self.i_hat_color, j_hat_color=self.j_hat_color
            )
            self.moving_vectors += list(self.basis_vectors)
            self.i_hat, self.j_hat = self.basis_vectors
            self.add(self.basis_vectors)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def add_special_mobjects(
        self, mob_list: list[Mobject], *mobs_to_add: Mobject
    ) -> None:
        """Add mobjects to the scene and to one of its lists of mobjects of a kind
        (background, foreground, transformable, moving), each once.

        Args:
            mob_list: The list.
            *mobs_to_add: The mobjects, in order; one the list holds already is skipped.
        """
        for mobject in mobs_to_add:
            if mobject not in mob_list:
                mob_list.append(mobject)
                self.add(mobject)

    def add_background_mobject(self, *mobjects: Mobject) -> None:
        """Add mobjects that the transformations leave where they are, as they leave the
        background plane.
        """
        self.add_special_mobjects(self.background_mobjects, *mobjects)

    def add_foreground_mobject(self, *mobjects: Mobject) -> Self:
        """Add mobjects that stay in front: drawn over everything else, and left where
        they are by the transformations.
        """
        self.add_special_mobjects(self.foreground_mobjects, *mobjects)
        return self

    def add_transformable_mobject(self, *mobjects: Mobject) -> None:
        """Add mobjects that the transformations move point by point, as they move the
        plane.
        """
        self.add_special_mobjects(self.transformable_mobjects, *mobjects)

    def add_moving_mobject(
        self, mobject: Mobject, target_mobject: Mobject | None = None
    ) -> None:
        """Add a mobject that the transformations move whole, its shape unchanged: to
        where they take its center.

        Args:
            target_mobject: What it becomes as it moves, placed where the transformation
                takes its center; None for itself.
        """
        mobject.target = target_mobject
        self.add_special_mobjects(self.moving_mobjects, mobject)

    def get_ghost_vectors(self) -> VGroup:
        """The faded copies the transformations left of what they moved whole, where it
        was, with `leave_ghost_vectors`.

        Returns:
            The group of them.
        """
        return self.ghost_vectors

    def get_unit_square(
        self, color: Colors = PURE_YELLOW, opacity: float = 0.3, stroke_width: float = 3
    ) -> Rectangle:
        """Make a rectangle over the plane's unit square: from its origin, one unit of x
        wide and one unit of y tall.

        Args:
            color: The color of its fill and its stroke.
            opacity: Its fill's opacity, from 0 to 1.
            stroke_width: Its stroke's width, in hundredths of a scene unit.

        Returns:
            A new rectangle, also kept as the scene's `square`.
        """
        square = self.square = Rectangle(
            color=color,
            width=self.plane.get_x_unit_size(),
            height=self.plane.get_y_unit_size(),
            stroke_color=color,
            stroke_width=stroke_width,
            fill_color=color,
            fill_opacity=opacity,
        )
        square.move_to(self.plane.coords_to_point(0, 0), DL)
        return square

    def add_unit_square(
        self, animate: bool = False, **kwargs: Unpack[UnitSquareOptions]
    ) -> Self:
        """Add the plane's unit square, which the transformations move with the plane:
        its area shows how they scale areas.

        The moving vectors are then brought to the front, over it.

        Args:
            animate: Whether to draw it in: its border, then its fill.
            **kwargs: [Unit square keywords][manimgx.scene.UnitSquareOptions].
        """
        square = self.get_unit_square(**kwargs)
        if animate:
            self.play(
                DrawBorderThenFill(square), Animation(Group(*self.moving_vectors))
            )
        self.add_transformable_mobject(square)
        self.bring_to_front(*self.moving_vectors)
        self.square = square
        return self

    def added_vector(self, vector: Arrow) -> None:
        self.moving_vectors.append(vector)

    def write_vector_coordinates(
        self, vector: Vector, **kwargs: Unpack[MatrixOptions]
    ) -> Matrix:
        """Write a vector's coordinates beside its tip, as a column that stays in front,
        where it is, through the transformations.

        Args:
            **kwargs: [Matrix keywords][manimgx.mobjects.grid.MatrixOptions] for the
                column.

        Returns:
            The column.
        """
        coords = super().write_vector_coordinates(vector, **kwargs)
        self.add_foreground_mobject(coords)
        return coords

    def add_transformable_label(
        self,
        vector: Vector,
        label: ManimTextLabel | str,
        transformation_name: str | ManimTextLabel = "L",
        new_label: str | ManimTextLabel | None = None,
        *,
        animate: bool = True,
        **kwargs: Unpack[VectorLabelOptions],
    ) -> ManimTextLabel:
        """Label a vector with a label that the transformations carry along and rewrite.

        After a transformation, the label sits by the vector where it went, and reads
        `new_label`, or else the label in the transformation's name: `L(v)` for a label
        `v`.

        Args:
            vector: The vector, from the origin.
            label: The label: a mobject, or LaTeX (see
                [`get_vector_label`][manimgx.VectorScene.get_vector_label]).
            transformation_name: The name of the transformation.
            new_label: What the label reads after a transformation; None for the
                transformation's name around it.
            animate: Whether to write it in.
            **kwargs: [Vector label keywords][manimgx.scene.VectorLabelOptions].

        Returns:
            The label.
        """
        label_mob = self.label_vector(vector, label, animate, **kwargs)
        if new_label:
            target_text: str | ManimTextLabel = new_label
        else:
            written = (
                label_mob.tex_string
                if isinstance(label_mob, (MathTex, SingleStringMathTex))
                else str(label)
            )
            target_text = f"{transformation_name}({written})"
        self.transformable_labels.append(
            _TransformableLabel(label_mob, vector, target_text, kwargs)
        )
        return label_mob

    def add_title(
        self, title: str | Mobject, scale_factor: float = 1.5, animate: bool = False
    ) -> Self:
        """Add a title at the top of the frame, in front and still, on a background
        rectangle.

        Args:
            title: The title: a mobject, or text, typeset as [`Tex`][manimgx.Tex].
            scale_factor: How much text is scaled.
            animate: Whether to write it in.
        """
        if not isinstance(title, Mobject):
            title = Tex(title).scale(scale_factor)
        title.to_edge(UP)
        title.add_background_rectangle()
        if animate:
            self.play(Write(title))
        self.add_foreground_mobject(title)
        self.title = title
        return self

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_matrix_transformation(
        self, matrix: npt.ArrayLike
    ) -> Callable[[Point3D], Point3D]:
        """The function that applies a matrix to a point.

        Args:
            matrix: A 2 × 2 matrix, which acts on x and y, or a 3 × 3 one; any other
                shape raises a ValueError.

        Returns:
            The function from a point to its image.
        """
        return self.get_transposed_matrix_transformation(np.array(matrix).T)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_transposed_matrix_transformation(
        self, transposed_matrix: npt.ArrayLike
    ) -> Callable[[Point3D], Point3D]:
        """The function that applies a matrix to a point, given its transpose.

        Args:
            transposed_matrix: The matrix's transpose, whose rows are where the matrix
                takes î and ĵ: 2 × 2, acting on x and y, or 3 × 3; any other shape
                raises a ValueError.

        Returns:
            The function from a point to its image.
        """
        matrix = np.array(transposed_matrix, dtype=float)
        if matrix.shape == (2, 2):
            full = np.identity(3)
            full[:2, :2] = matrix
            matrix = full
        elif matrix.shape != (3, 3):
            raise ValueError("Matrix has bad dimensions")
        return lambda point: np.dot(point, matrix)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_piece_movement(self, pieces: Iterable[Mobject]) -> Transform:
        """The animation that moves mobjects whole into their targets (their `target`
        each), all together.

        With `leave_ghost_vectors`, a faded copy of them is left in the scene where they
        are.

        Args:
            pieces: The mobjects; those that are not paths are left out.

        Returns:
            A [`Transform`][manimgx.Transform] of them into their targets.
        """
        v_pieces = [piece for piece in pieces if isinstance(piece, VMobject)]
        start = VGroup(*v_pieces)
        target = VGroup(*(mob.target for mob in v_pieces if mob.target is not None))
        if self.leave_ghost_vectors and start.submobjects:
            self.ghost_vectors.add(start.copy().fade(0.7))
            self.add(self.ghost_vectors[-1])
        return Transform(start, target, lag_ratio=0)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_moving_mobject_movement(self, func: MappingFunction) -> Transform:
        """The animation that moves the moving mobjects whole to where a function takes
        their centers.

        Args:
            func: The function, from a point to its image.

        Returns:
            A [`Transform`][manimgx.Transform] of them.
        """
        for m in self.moving_mobjects:
            if m.target is None:
                m.target = m.copy()
            m.target.move_to(func(m.get_center()))
        return self.get_piece_movement(self.moving_mobjects)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_vector_movement(self, func: MappingFunction) -> Transform:
        """The animation that redraws the moving vectors to where a function takes their
        tips; a vector that ends up shorter than 0.1 gets a tip as small.

        Args:
            func: The function, from a point to its image.

        Returns:
            A [`Transform`][manimgx.Transform] of them.
        """
        for v in self.moving_vectors:
            target = Vector(func(v.get_end()), color=v.get_color())
            norm = float(np.linalg.norm(target.get_end()))
            if norm < 0.1:
                target.get_tip().scale(norm)
            v.target = target
        return self.get_piece_movement(self.moving_vectors)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_transformable_label_movement(self) -> Transform:
        """The animation that moves each transformable label to where its vector goes,
        rewritten: it follows `get_vector_movement`, which moves the vectors.

        Returns:
            A [`Transform`][manimgx.Transform] of the labels.
        """
        for item in self.transformable_labels:
            moved = item.vector.target
            item.label.target = self.get_vector_label(
                moved if isinstance(moved, Vector) else item.vector,
                item.target_text,
                **item.options,
            )
        return self.get_piece_movement(item.label for item in self.transformable_labels)

    def apply_matrix(
        self, matrix: npt.ArrayLike, **kwargs: Unpack[TransformOptions]
    ) -> None:
        """Apply a matrix to the plane and to everything on it, in one play.

        Everything the transformations move goes where the matrix takes it (see
        [`apply_function`][manimgx.LinearTransformationScene.apply_function]). Unless a
        `path_arc` is given, the points travel along arcs that turn through the mean of
        the angles the matrix turns î and ĵ through.

        Args:
            matrix: A 2 × 2 matrix, which acts on x and y, or a 3 × 3 one: its columns
                are where it takes î and ĵ.
            **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] for
                every animation of the play (3 seconds long unless given a `run_time`).
        """
        self.apply_transposed_matrix(np.array(matrix).T, **kwargs)

    def apply_inverse(
        self, matrix: npt.ArrayLike, **kwargs: Unpack[TransformOptions]
    ) -> None:
        """Apply the inverse of a matrix to the plane and to everything on it: undo
        [`apply_matrix`][manimgx.LinearTransformationScene.apply_matrix] of the same
        matrix.

        Args:
            matrix: The matrix, 2 × 2 or 3 × 3, which must be invertible.
            **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] for
                every animation of the play.
        """
        self.apply_matrix(np.linalg.inv(np.asarray(matrix, dtype=float)), **kwargs)

    def apply_transposed_matrix(
        self, transposed_matrix: npt.ArrayLike, **kwargs: Unpack[TransformOptions]
    ) -> None:
        """Apply a matrix, given by its transpose, to the plane and to everything on it:
        as [`apply_matrix`][manimgx.LinearTransformationScene.apply_matrix] does.

        Args:
            transposed_matrix: The matrix's transpose, whose rows are where the matrix
                takes î and ĵ.
            **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] for
                every animation of the play.
        """
        func = self.get_transposed_matrix_transformation(transposed_matrix)
        if "path_arc" not in kwargs:
            kwargs["path_arc"] = float(
                np.mean(
                    [
                        angle_of_vector(func(RIGHT)),
                        angle_of_vector(func(UP)) - np.pi / 2,
                    ]
                )
            )
        self.apply_function(func, **kwargs)

    def apply_inverse_transpose(
        self, t_matrix: npt.ArrayLike, **kwargs: Unpack[TransformOptions]
    ) -> None:
        """Apply the inverse of a matrix's transpose to the plane and to everything on
        it.

        Args:
            t_matrix: The matrix, 2 × 2 or 3 × 3, which must be invertible.
            **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] for
                every animation of the play.
        """
        t_inv = np.linalg.inv(np.array(t_matrix, dtype=float).T).T
        self.apply_transposed_matrix(t_inv, **kwargs)

    def apply_nonlinear_transformation(
        self,
        function: Callable[[np.ndarray], np.ndarray],
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        """Apply a function that need not be linear to the plane and to everything on
        it.

        The plane's lines are first divided into many curves, so that they can bend (see
        [`apply_function`][manimgx.LinearTransformationScene.apply_function]).

        Args:
            function: The function, from a point to its image, in scene coordinates.
            **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] for
                every animation of the play.
        """
        self.plane.prepare_for_nonlinear_transform()
        self.apply_function(function, **kwargs)

    def apply_function(
        self,
        function: MappingFunction,
        added_anims: Sequence[Animation] | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        """Apply a function to the plane and to everything on it, in one play.

        Every point of the transformable mobjects goes where `function` takes it; each
        vector is redrawn to where its tip goes, and its transformable label follows it;
        each moving mobject moves whole to where its center goes; the foreground
        mobjects stay where they are. With `leave_ghost_vectors`, faded copies of what
        moves whole are left behind.

        Args:
            function: The function, from a point to its image, in scene coordinates.
            added_anims: Animations to play along.
            **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] for
                every animation of the play (3 seconds long unless given a `run_time`).
        """
        kwargs.setdefault("run_time", 3)
        anims: list[Animation] = [
            *(
                ApplyPointwiseFunction(function, t_mob)
                for t_mob in self.transformable_mobjects
            ),
            self.get_vector_movement(function),
            self.get_transformable_label_movement(),
            self.get_moving_mobject_movement(function),
            *(Animation(f_mob) for f_mob in self.foreground_mobjects),
            *(added_anims or ()),
        ]
        self.play(*anims, **kwargs)

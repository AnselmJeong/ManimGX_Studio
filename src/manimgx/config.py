# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Global scene configuration (a small, typed subset of CE's `config`)."""

from dataclasses import dataclass, field
from typing import Literal, overload
from warnings import deprecated

import numpy as np

from manimgx import constants
from manimgx.drawing.paint import BLACK, ManimColor, ParsableManimColor
from manimgx.typing import Point3D, Vector3D


@dataclass
class Config:
    """The configuration scenes are made and rendered with: the video's size, frame rate
    and background, and the frame's size in scene units.

    There is one, [`config`][manimgx.config.config]. Set its fields before making a
    scene: a scene's camera, and the mobjects that fill the frame, take their sizes and
    the background from it when they are made, and [`render`][manimgx.Scene.render]
    takes the video's size and frame rate when it starts. It can be read and set as a
    dictionary too, as Manim code does: `config["frame_width"]`,
    `config["pixel_height"] = 720`.

    The frame has the video's proportions, and its short side is 8 units: a wide video
    (16:9) shows about 14.2 × 8 units, a tall one (9:16) 8 × 14.2. So what fits in the
    8 × 8 square at the center fits both, at the same size.
    """

    pixel_width: int = 1920
    """The width of the video, in pixels (default 1920)."""
    pixel_height: int = 1080
    """The height of the video, in pixels (default 1080). For a tall video (9:16), make
    it the larger: `config.pixel_width, config.pixel_height = 1080, 1920`."""
    frame_rate: float = 60
    """How many frames a second the film has (default 60): frame k shows the scene at
    exactly k / `frame_rate` seconds. A video needs a whole number."""
    simulation_rate: int = 60  # the simulation clock of `manimgx.animation.clock`
    """How many times a second the simulation clock ticks (default 60).

    A time-based updater that is not a [flow][manimgx.mobject.flow] is simulated:
    it steps at each tick of this clock and at the end of each play and wait, never at
    frames, so it takes the same steps at any frame rate, and a frame shows it as its
    last step left it. While one is in the scene, the scene computes every tick. At 60
    frames a second each frame is a tick, so the ticks cost nothing more; at a frame
    rate that divides it (10, 12, 15, 20, 30), every frame falls on a tick too.
    """
    background_color: ParsableManimColor = BLACK
    """The color of the background (default black)."""
    background_opacity: float = 1.0
    """The opacity of the background, from 0 to 1 (default 1)."""
    _frame_height: float | None = field(default=None, repr=False)
    """The frame's height as set, if it was (`frame_height`)."""

    @property
    def frame_height(self) -> float:
        """The height of the frame, in scene units. Unless set, the frame's short side is
        8 units: a wide video's frame is 8 high, a tall one's as high as its proportions
        make it when it is 8 wide (about 14.2 at 9:16). Its width follows from the
        video's proportions."""
        if self._frame_height is not None:
            return self._frame_height
        return 8.0 * max(1.0, self.pixel_height / self.pixel_width)

    @frame_height.setter
    def frame_height(self, value: float) -> None:
        self._frame_height = value

    @property
    def frame_width(self) -> float:
        """The width of the frame, in scene units: `frame_height` times the video's
        aspect ratio (about 14.2 at 16:9, 8 at 9:16)."""
        return self.frame_height * self.pixel_width / self.pixel_height

    @property
    def frame_x_radius(self) -> float:
        """Half the frame's width, in scene units: the x of its right edge."""
        return self.frame_width / 2

    @property
    def frame_y_radius(self) -> float:
        """Half the frame's height, in scene units (4 for a wide video): the y of its top
        edge."""
        return self.frame_height / 2

    @property
    def top(self) -> "Point3D":
        """The middle of the frame's top edge: `frame_y_radius` up from the origin."""
        return self.frame_y_radius * np.array([0.0, 1.0, 0.0])

    @property
    def bottom(self) -> "Point3D":
        """The middle of the frame's bottom edge: `frame_y_radius` down from the
        origin."""
        return -self.top

    @property
    def right_side(self) -> "Point3D":
        """The middle of the frame's right edge: `frame_x_radius` right of the
        origin."""
        return self.frame_x_radius * np.array([1.0, 0.0, 0.0])

    @property
    def left_side(self) -> "Point3D":
        """The middle of the frame's left edge: `frame_x_radius` left of the origin."""
        return -self.right_side

    @property
    def aspect_ratio(self) -> float:
        """The video's width over its height: `pixel_width / pixel_height` (16:9 by
        default)."""
        return self.pixel_width / self.pixel_height

    @property
    def background(self) -> ManimColor:
        """The color of the background, as a [`ManimColor`][manimgx.ManimColor]."""
        return ManimColor(self.background_color)

    # CE's dict-style access (`config["frame_width"]`), typed by key
    @overload
    def __getitem__(
        self, key: Literal["pixel_width", "pixel_height", "simulation_rate"]
    ) -> int: ...
    @overload
    def __getitem__(
        self,
        key: Literal[
            "frame_rate",
            "frame_height",
            "frame_width",
            "frame_x_radius",
            "frame_y_radius",
            "aspect_ratio",
            "background_opacity",
        ],
    ) -> float: ...
    @overload
    def __getitem__(
        self, key: Literal["top", "bottom", "left_side", "right_side"]
    ) -> "Point3D": ...
    @overload
    def __getitem__(self, key: Literal["background_color"]) -> ParsableManimColor: ...
    @overload
    def __getitem__(self, key: Literal["background"]) -> ManimColor: ...
    def __getitem__(self, key: str) -> object:
        return getattr(self, key)

    @overload
    def __setitem__(
        self,
        key: Literal["pixel_width", "pixel_height", "simulation_rate"],
        value: int,
    ) -> None: ...
    @overload
    def __setitem__(
        self,
        key: Literal["frame_rate", "frame_height", "background_opacity"],
        value: float,
    ) -> None: ...
    @overload
    def __setitem__(
        self, key: Literal["background_color"], value: ParsableManimColor
    ) -> None: ...
    def __setitem__(self, key: str, value: object) -> None:
        setattr(self, key, value)


config = Config()
"""The configuration every scene is made and rendered with, as `m.config`: a
[`Config`][manimgx.config.Config]. Set its fields before making a scene:
`m.config.pixel_width, m.config.pixel_height = 1280, 720`."""


class _PixelUnits:
    def __mul__(self, val: float) -> float:
        return val * config.frame_width / config.pixel_width

    def __rmul__(self, val: float) -> float:
        return val * config.frame_width / config.pixel_width


@deprecated(
    "use a fraction of config.frame_width or config.frame_height", category=None
)
class Percent:
    """A length as a percentage of the frame's width or height: `25 * Percent(X_AXIS)`
    is a quarter of the frame's width, in scene units.

    The frame's size is read when the unit is made.

    Args:
        axis: [X_AXIS][manimgx.X_AXIS] for the frame's width, [Y_AXIS][manimgx.Y_AXIS]
            for its height; [Z_AXIS][manimgx.Z_AXIS], which has no length, raises an
            exception.
    """

    def __init__(self, axis: Vector3D) -> None:
        if np.array_equal(axis, constants.X_AXIS):
            self.length = config.frame_width
        if np.array_equal(axis, constants.Y_AXIS):
            self.length = config.frame_height
        if np.array_equal(axis, constants.Z_AXIS):
            raise NotImplementedError("length of Z axis is undefined")

    def __mul__(self, val: float) -> float:
        return val / 100 * self.length

    def __rmul__(self, val: float) -> float:
        return val / 100 * self.length


Pixels = _PixelUnits()
"""Pixels as a unit of length: `100 * Pixels` is the width of 100 of the rendered
frame's pixels, in scene units, as the configuration sets them when multiplied."""
Degrees = constants.PI / 180
"""One degree, in radians: `30 * Degrees` is 30°, as [DEGREES][manimgx.DEGREES] is."""
Munits = 1
"""One scene unit: `2 * Munits` is 2, a length written in scene units."""

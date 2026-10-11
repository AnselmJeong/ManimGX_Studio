"""Directions, buffers, math constants and style enums (values identical to Manim CE 0.21)."""

from enum import Enum
from typing import Literal

import numpy as np
import numpy.typing as npt

from manimgx.typing import Vector3D

__all__ = [
    "BOLD",
    "BOOK",
    "DEFAULT_ARROW_TIP_LENGTH",
    "DEFAULT_DASH_LENGTH",
    "DEFAULT_DOT_RADIUS",
    "DEFAULT_FONT_SIZE",
    "DEFAULT_MOBJECT_TO_EDGE_BUFFER",
    "DEFAULT_MOBJECT_TO_MOBJECT_BUFFER",
    "DEFAULT_POINTWISE_FUNCTION_RUN_TIME",
    "DEFAULT_POINT_DENSITY_1D",
    "DEFAULT_POINT_DENSITY_2D",
    "DEFAULT_SMALL_DOT_RADIUS",
    "DEFAULT_STROKE_WIDTH",
    "DEFAULT_WAIT_TIME",
    "DEGREES",
    "DL",
    "DOWN",
    "DR",
    "HEAVY",
    "IN",
    "ITALIC",
    "LARGE_BUFF",
    "LEFT",
    "LIGHT",
    "MEDIUM",
    "MED_LARGE_BUFF",
    "MED_SMALL_BUFF",
    "NORMAL",
    "OBLIQUE",
    "ORIGIN",
    "OUT",
    "PI",
    "RESAMPLING_ALGORITHMS",
    "RIGHT",
    "SCALE_FACTOR_PER_FONT_POINT",
    "SEMIBOLD",
    "SEMILIGHT",
    "SMALL_BUFF",
    "START_X",
    "START_Y",
    "TAU",
    "THIN",
    "UL",
    "ULTRABOLD",
    "ULTRAHEAVY",
    "ULTRALIGHT",
    "UP",
    "UR",
    "X_AXIS",
    "Y_AXIS",
    "Z_AXIS",
    "CapStyleType",
    "LineJointType",
]


def _constant(value: npt.ArrayLike) -> Vector3D:
    """A direction as a constant: read-only, so that a mobject that keeps it (an arc's
    center, a number's edge) can't change it for everything made after."""
    array = np.array(value, dtype=float)
    array.flags.writeable = False
    return array


ORIGIN: Vector3D = _constant((0.0, 0.0, 0.0))
"""The center of the scene: (0, 0, 0)."""
UP: Vector3D = _constant((0.0, 1.0, 0.0))
"""One unit up: (0, 1, 0)."""
DOWN: Vector3D = _constant((0.0, -1.0, 0.0))
"""One unit down: (0, −1, 0)."""
RIGHT: Vector3D = _constant((1.0, 0.0, 0.0))
"""One unit right: (1, 0, 0)."""
LEFT: Vector3D = _constant((-1.0, 0.0, 0.0))
"""One unit left: (−1, 0, 0)."""
IN: Vector3D = _constant((0.0, 0.0, -1.0))
"""One unit into the screen, away from the viewer: (0, 0, −1)."""
OUT: Vector3D = _constant((0.0, 0.0, 1.0))
"""One unit out of the screen, toward the viewer: (0, 0, 1)."""
X_AXIS: Vector3D = _constant((1.0, 0.0, 0.0))
"""The direction of the x axis: (1, 0, 0)."""
Y_AXIS: Vector3D = _constant((0.0, 1.0, 0.0))
"""The direction of the y axis: (0, 1, 0)."""
Z_AXIS: Vector3D = _constant((0.0, 0.0, 1.0))
"""The direction of the z axis, out of the screen: (0, 0, 1)."""
UL: Vector3D = _constant(UP + LEFT)
"""Up and left, toward the upper left corner: (−1, 1, 0)."""
UR: Vector3D = _constant(UP + RIGHT)
"""Up and right, toward the upper right corner: (1, 1, 0)."""
DL: Vector3D = _constant(DOWN + LEFT)
"""Down and left, toward the lower left corner: (−1, −1, 0)."""
DR: Vector3D = _constant(DOWN + RIGHT)
"""Down and right, toward the lower right corner: (1, −1, 0)."""

PI = np.pi
"""π: half a turn, in radians."""
TAU = 2 * PI
"""τ = 2π: a whole turn, in radians."""
DEGREES = TAU / 360
"""One degree, in radians: `30 * DEGREES` is a twelfth of a turn."""

SMALL_BUFF = 0.1
"""A small gap, in scene units: 0.1."""
MED_SMALL_BUFF = 0.25
"""A medium-small gap, in scene units: 0.25, the default between mobjects
placed next to each other."""
MED_LARGE_BUFF = 0.5
"""A medium-large gap, in scene units: 0.5, the default between a mobject and the
frame's edge."""
LARGE_BUFF = 1
"""A large gap, in scene units: 1."""
DEFAULT_MOBJECT_TO_EDGE_BUFFER = MED_LARGE_BUFF
"""The gap a mobject keeps from the frame's edge by default, in scene units: 0.5
(`to_edge`, `to_corner`)."""
DEFAULT_MOBJECT_TO_MOBJECT_BUFFER = MED_SMALL_BUFF
"""The gap between mobjects placed next to each other by default, in scene units:
0.25 (`next_to`, `arrange`)."""
DEFAULT_DOT_RADIUS = 0.08
"""A dot's radius by default, in scene units."""
DEFAULT_SMALL_DOT_RADIUS = 0.04
"""A small dot's radius, in scene units: half the default."""
DEFAULT_DASH_LENGTH = 0.05
"""A dashed line's dash length by default, in scene units."""
DEFAULT_ARROW_TIP_LENGTH = 0.35
"""An arrow tip's length by default, in scene units."""
DEFAULT_STROKE_WIDTH = 4
"""A stroke's width by default, in hundredths of a scene unit."""
DEFAULT_FONT_SIZE = 48
"""Text's font size by default."""
DEFAULT_WAIT_TIME = 1.0
"""How long a wait lasts by default, in seconds."""
DEFAULT_POINTWISE_FUNCTION_RUN_TIME = 3.0
"""How long [ApplyPointwiseFunction][manimgx.ApplyPointwiseFunction], which moves every
point through a function, and the animations built on it run by default, in seconds."""
SCALE_FACTOR_PER_FONT_POINT = 1 / 960
"""The scale of typeset text per unit of font size: Typst and LaTeX, typeset in 10-point
type, are scaled so a point is `font_size` / 960 scene units and an em `font_size` / 96
(0.5 at the default, 48). A [Text][manimgx.Text] is sized by its capitals instead."""


class LineJointType(Enum):
    """How a stroke is joined where its path turns (`joint_type`): round, beveled or
    mitered.

    The default, `AUTO`, is mitered. A two-dimensional scene draws the joints, of a
    stroke and of its background stroke alike; a three-dimensional scene miters every
    stroke.

    Examples:
        ```python
        import manimgx as m


        class LineJointTypeExample(m.Scene):
            def construct(self) -> None:
                corners = [[-1, -1.5, 0], [0, 1.5, 0], [1, -1.5, 0]]
                paths = m.VGroup()
                for joint in m.LineJointType:
                    path = m.VMobject(color=m.YELLOW, stroke_width=40, joint_type=joint)
                    path.set_points_as_corners(corners)
                    label = m.Text(joint.name, font_size=36).next_to(path, m.DOWN, 0.6)
                    paths.add(m.VGroup(path, label))
                self.add(paths.arrange(buff=1))
        ```
    """

    AUTO = 0
    """The default: mitered, as `MITER`."""
    ROUND = 1
    """Round corners."""
    BEVEL = 2
    """Corners cut straight across."""
    MITER = 3
    """Pointed corners, where the stroke's edges meet; cut straight across where the
    point would lie more than five stroke widths from the path's corner."""


class CapStyleType(Enum):
    """How a stroke ends (`cap_style`): round, butt or square.

    Every end a stroke shows is capped: the ends of an open path, the moving end of a
    reveal ([Create][manimgx.Create], [Write][manimgx.Write], …) and both ends of every
    dash. A closed path shown whole has no ends, and a stroke of no length (a path that
    stays at one point) shows as a dot with round caps, a square with square ones. The
    default, `AUTO`, is butt. A two-dimensional scene draws the caps, of a stroke and of
    its background stroke alike; a three-dimensional scene ends every stroke flat.

    Examples:
        ```python
        import manimgx as m


        class CapStyleTypeExample(m.Scene):
            def construct(self) -> None:
                arcs = m.VGroup()
                for cap in m.CapStyleType:
                    arc = m.Arc(radius=2, color=m.GREEN, stroke_width=40)
                    arc.set_cap_style(cap)
                    label = m.Text(cap.name, font_size=36).next_to(arc, m.DOWN, 0.6)
                    arcs.add(m.VGroup(arc, label))
                self.add(arcs.arrange(buff=1))
        ```
    """

    AUTO = 0
    """The default: flat at the end, as `BUTT`."""
    ROUND = 1
    """A half disk past the end."""
    BUTT = 2
    """Flat, at the end."""
    SQUARE = 3
    """Flat, half the stroke's width past the end."""


NORMAL = "NORMAL"
"""Text's normal slant, upright, and its normal weight (400)."""
ITALIC = "ITALIC"
"""An italic slant of text."""
OBLIQUE = "OBLIQUE"
"""An oblique slant of text: its upright letters, slanted."""
BOLD = "BOLD"
"""A weight of text: bold (700)."""
THIN = "THIN"
"""A weight of text: thin (100)."""
ULTRALIGHT = "ULTRALIGHT"
"""A weight of text: ultralight (200)."""
LIGHT = "LIGHT"
"""A weight of text: light (300)."""
SEMILIGHT = "SEMILIGHT"
"""A weight of text: semilight (350)."""
BOOK = "BOOK"
"""A weight of text: book (380)."""
MEDIUM = "MEDIUM"
"""A weight of text: medium (500)."""
SEMIBOLD = "SEMIBOLD"
"""A weight of text: semibold (600)."""
ULTRABOLD = "ULTRABOLD"
"""A weight of text: ultrabold (800)."""
HEAVY = "HEAVY"
"""A weight of text: heavy (900)."""
ULTRAHEAVY = "ULTRAHEAVY"
"""A weight of text: ultraheavy (950)."""
DEFAULT_POINT_DENSITY_1D = 10
"""How many points a point cloud's line gets per scene unit by default."""
DEFAULT_POINT_DENSITY_2D = 25
"""Kept for Manim compatibility; unused."""
START_X = 30
"""Kept for Manim compatibility; unused."""
START_Y = 20
"""Kept for Manim compatibility; unused."""

type Resampling = Literal[0, 2, 3]
"""How an image is reconstructed from its pixels where it is drawn larger than they are,
numbered as the Pillow library numbers its filters: 0, nearest (each pixel a square of
its color); 2, linear; 3, cubic (Keys' cubic convolution with a = −1/2, Pillow's
BICUBIC: smooth, and through every pixel)."""
RESAMPLING_ALGORITHMS: dict[str, Resampling] = {
    "nearest": 0,
    "none": 0,
    "bilinear": 2,
    "linear": 2,
    "bicubic": 3,
    "cubic": 3,
}
"""The filters an image can be reconstructed with, by name, each with its number (see
[Resampling][manimgx.constants.Resampling]): "nearest" or "none", "bilinear" or
"linear", "bicubic" or "cubic"."""

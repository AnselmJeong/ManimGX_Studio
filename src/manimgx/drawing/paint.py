# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Colors and immutable paint shared by paths, points and meshes.

Colors retain exact RGBA beside their string form. Paint owns the brushes and
appearance of a drawing; its geometry kind gives each brush row its meaning.
"""

import colorsys
import random
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePath
from typing import TYPE_CHECKING, Final, Self, TypeIs, cast, overload
from warnings import deprecated

import numpy as np
import numpy.typing as npt
from typing_extensions import TypedDict

from manimgx.caches import Memo, unchanged
from manimgx.constants import UL, CapStyleType, LineJointType
from manimgx.drawing.geometry import interpolate
from manimgx.typing import RGBA_Array, Vector3D, Vector3DLike

__all__ = [
    "BLACK",
    "BLUE",
    "BLUE_A",
    "BLUE_B",
    "BLUE_C",
    "BLUE_D",
    "BLUE_E",
    "DARKER_GRAY",
    "DARKER_GREY",
    "DARK_BLUE",
    "DARK_BROWN",
    "DARK_GRAY",
    "DARK_GREY",
    "GOLD",
    "GOLD_A",
    "GOLD_B",
    "GOLD_C",
    "GOLD_D",
    "GOLD_E",
    "GRAY",
    "GRAY_A",
    "GRAY_B",
    "GRAY_BROWN",
    "GRAY_C",
    "GRAY_D",
    "GRAY_E",
    "GREEN",
    "GREEN_A",
    "GREEN_B",
    "GREEN_C",
    "GREEN_D",
    "GREEN_E",
    "GREY",
    "GREY_A",
    "GREY_B",
    "GREY_BROWN",
    "GREY_C",
    "GREY_D",
    "GREY_E",
    "HSV",
    "LIGHTER_GRAY",
    "LIGHTER_GREY",
    "LIGHT_BROWN",
    "LIGHT_GRAY",
    "LIGHT_GREY",
    "LIGHT_PINK",
    "LOGO_BLACK",
    "LOGO_BLUE",
    "LOGO_GREEN",
    "LOGO_RED",
    "LOGO_WHITE",
    "MAROON",
    "MAROON_A",
    "MAROON_B",
    "MAROON_C",
    "MAROON_D",
    "MAROON_E",
    "ORANGE",
    "PALETTE",
    "PINK",
    "PURE_BLUE",
    "PURE_CYAN",
    "PURE_GREEN",
    "PURE_MAGENTA",
    "PURE_RED",
    "PURE_YELLOW",
    "PURPLE",
    "PURPLE_A",
    "PURPLE_B",
    "PURPLE_C",
    "PURPLE_D",
    "PURPLE_E",
    "RED",
    "RED_A",
    "RED_B",
    "RED_C",
    "RED_D",
    "RED_E",
    "TEAL",
    "TEAL_A",
    "TEAL_B",
    "TEAL_C",
    "TEAL_D",
    "TEAL_E",
    "WHITE",
    "YELLOW",
    "YELLOW_A",
    "YELLOW_B",
    "YELLOW_C",
    "YELLOW_D",
    "YELLOW_E",
    "Colorscale",
    "Floats",
    "ManimColor",
    "Material",
    "ParsableManimColor",
    "RandomColorGenerator",
    "average_color",
    "color_gradient",
    "color_to_rgb",
    "colors_by_value",
    "from_oklab",
    "interpolate_color",
    "invert_color",
    "mix_rgba",
    "parse_colors",
    "random_bright_color",
    "random_color",
    "rgb_to_color",
    "rgbas_by_value",
    "to_oklab",
]

type Floats = npt.NDArray[np.float64]
"""A NumPy array of floats."""

# ── mixing: one rule for every blend of colors ─────────────────────────────────
# Colors mix in OKLab, where lightness moves evenly (the midpoint of two colors sits exactly
# halfway in perceived lightness), premultiplied by opacity so an invisible color never tints
# the result; opacity itself mixes linearly. Compositing (drawing translucent layers) stays in
# sRGB, where 50% opacity looks half as bright.
_LMS: Floats = np.array(
    [
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005],
    ]
)
_LAB: Floats = np.array(
    [
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660],
    ]
)
_LMS_INV: Floats = np.linalg.inv(_LMS)
_LAB_INV: Floats = np.linalg.inv(_LAB)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def to_oklab(rgb: Floats) -> Floats:
    """Convert sRGB colors to OKLab, the color space colors are mixed in.

    Along a straight line in OKLab, colors pass through those the eye sees between its
    ends, and lightness changes evenly.

    Args:
        rgb: Red, green and blue, from 0 to 1, along the last axis: an array of shape
            (…, 3).

    Returns:
        Lightness L and the axes a and b, as an array of the same shape.
    """
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return np.cbrt(linear @ _LMS.T) @ _LAB.T


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def from_oklab(lab: Floats) -> Floats:
    """Convert OKLab colors to sRGB, clipped to the colors a screen shows.

    Args:
        lab: Lightness L and the axes a and b, along the last axis: an array of shape
            (…, 3).

    Returns:
        Red, green and blue, from 0 to 1, as an array of the same shape.
    """
    linear = np.clip(((lab @ _LAB_INV.T) ** 3) @ _LMS_INV.T, 0.0, 1.0)
    return np.where(
        linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055
    )


_LABS: Memo[int, tuple[Floats, Floats]] = Memo(1 << 12)


def _lab(rgba: Floats) -> Floats:
    """OKLab of an RGBA array's colors — once per array when the array cannot change (a
    paint's rows are read-only): a tween mixes the same two paints on every frame."""
    if rgba.flags.writeable:
        return to_oklab(rgba[..., :3])
    known = _LABS.recall(id(rgba), lambda: (rgba, to_oklab(rgba[..., :3])))
    if known[0] is not rgba:  # another array, since gone, had its id
        known = _LABS[id(rgba)] = (rgba, to_oklab(rgba[..., :3]))
    return known[1]


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def mix_rgba(a: Floats, b: Floats, t: float | Floats) -> Floats:
    """Mix colors given as rows of red, green, blue and opacity: `a` at 0, `b` at 1.

    Every blend of colors in ManimGX mixes this way. The colors mix in OKLab, weighted
    by their opacities, so a transparent color does not tint the mix; the opacity mixes
    evenly. Rows of one color only change their opacity.

    Args:
        a: The colors at 0: red, green, blue and opacity, from 0 to 1, along the last
            axis.
        b: The colors at 1, an array of the same shape.
        t: How far from `a` to `b`, from 0 to 1: one fraction for every row, or one per
            row (an array of `a`'s shape without its last axis).

    Returns:
        The mixed colors, an array of the same shape; exactly `a` at 0 and `b` at 1.
    """
    rows = isinstance(t, np.ndarray) and t.ndim > 0
    if rows:
        t = t.astype(float)[..., None]
    elif t <= 0.0:
        return np.array(a, dtype=float)
    elif t >= 1.0:
        return np.array(b, dtype=float)
    elif np.array_equal(a[..., :3], b[..., :3]):  # one color: only opacity moves
        out = np.array(a, dtype=float)
        out[..., 3] = a[..., 3] * (1.0 - t) + b[..., 3] * t
        return out
    wa, wb = a[..., 3:4] * (1.0 - t), b[..., 3:4] * t
    opacity = wa + wb
    la, lb = _lab(a), _lab(b)
    straight = la * (1.0 - t) + lb * t
    lab = np.where(
        opacity > 1e-9, (la * wa + lb * wb) / np.maximum(opacity, 1e-9), straight
    )
    mixed = np.concatenate([from_oklab(lab), opacity], axis=-1)
    # row by row too: a row of one color only changes its opacity
    same = np.all(a[..., :3] == b[..., :3], axis=-1, keepdims=True)
    if same.any():
        mixed[..., :3] = np.where(same, a[..., :3], mixed[..., :3])
    return mixed if not rows else np.where(t <= 0.0, a, np.where(t >= 1.0, b, mixed))


type ParsableManimColor = ManimColor | str | int | Sequence[float] | np.ndarray
"""Anything [ManimColor][manimgx.ManimColor] reads as a color: a color, a hex string
(`"#58C4DD"`) or a color's name (`"BLUE"`), an integer (`0x58C4DD`), or three or four
numbers (red, green, blue and opacity)."""

# a hex color: `#` or `0x`, then 3, 4, 6 or 8 digits (the opacity's last, when there are 4 or 8)
_HEX = re.compile(r"(?:#|0x)([0-9A-F]{3,4}|[0-9A-F]{6}|[0-9A-F]{8})", re.IGNORECASE)


class ManimColor(str):
    """A color: red, green, blue and opacity, from 0 to 1, which is also its hex string.

    As a string it is `"#RRGGBB"`, or `"#RRGGBBAA"` when translucent, so it goes
    wherever a string does; [to_rgba][manimgx.ManimColor.to_rgba] gives its values.
    `ManimColor(value, alpha=1.0)` reads `value` as a color, of opacity `alpha` (from 0
    to 1) where `value` gives none. `value` is:

    - a hex string, `"#FC6255"` or `"0xFC6255"`, of 3, 4, 6 or 8 digits (the fourth of
      four, and the last two of eight, are the opacity);
    - a color's name, in any case: `"BLUE"`, `"blue_c"`;
    - an integer, `0xFC6255`;
    - three or four numbers, red, green, blue and opacity: from 0 to 1 if all are
      floats, from 0 to 255 otherwise (`(1.0, 0.5, 0.0)` is orange, `(1, 0.5, 0)` nearly
      black);
    - another color, copied as it is;
    - None, for black.

    Examples:
        ```python
        import manimgx as m


        class ManimColorExample(m.Scene):
            def construct(self) -> None:
                colors = [
                    m.ManimColor("#58C4DD"),
                    m.ManimColor("orange"),
                    m.ManimColor((0.9, 0.3, 0.5)),
                    m.ManimColor.from_hsv((0.75, 0.6, 0.9)),
                    m.RED.lighter(0.4),
                    m.RED.darker(0.4),
                ]
                swatches = m.VGroup(
                    *(
                        m.VGroup(
                            m.Square(side_length=1.6, color=color, fill_opacity=1),
                            m.Text(color, font_size=24),
                        ).arrange(m.DOWN)
                        for color in colors
                    )
                )
                self.add(swatches.arrange(buff=0.4))
        ```
    """

    _rgba: np.ndarray

    def __new__(
        cls, value: ParsableManimColor | None = None, alpha: float = 1.0
    ) -> Self:
        return _made(cls, _parse(value, alpha))

    @overload
    @classmethod
    def parse(cls, value: "ParsableManimColor | None", alpha: float = 1.0) -> Self: ...
    @overload
    @classmethod
    def parse(
        cls,
        value: "list[ParsableManimColor] | tuple[ParsableManimColor, ...]",
        alpha: float = 1.0,
    ) -> list[Self]: ...
    @classmethod
    @deprecated("use ManimColor(...)", category=None)
    def parse(
        cls,
        value: "ParsableManimColor | Sequence[ParsableManimColor] | None",
        alpha: float = 1.0,
    ) -> Self | list[Self]:
        """Read one color, or a list of colors from a list or tuple of them.

        A color of this class is returned as it is.

        Args:
            value: A color in any form [ManimColor][manimgx.ManimColor] reads (three or
                four numbers are one color), or a list or tuple of them.
            alpha: The opacity, from 0 to 1, of those that give none.

        Returns:
            The color, or a list of the colors.
        """
        if (
            value is None
            or isinstance(value, (str, ManimColor, int))
            or _numbers(value)
        ):
            return value if isinstance(value, cls) else cls(value, alpha)
        return [cls.parse(v, alpha) for v in value]

    def to_rgb(self) -> np.ndarray:
        """The color's red, green and blue.

        Returns:
            An array of three floats, from 0 to 1.
        """
        return self._rgba[:3]

    def to_rgba(self) -> np.ndarray:
        """The color's red, green, blue and opacity.

        Returns:
            An array of four floats, from 0 to 1.
        """
        return self._rgba

    @deprecated("use to_rgba", category=None)
    def to_rgba_with_alpha(self, alpha: float) -> np.ndarray:
        """The color's red, green and blue, with another opacity.

        Args:
            alpha: The opacity, from 0 to 1.

        Returns:
            An array of red, green, blue and `alpha`.
        """
        return np.array((*self._rgba[:3], alpha))

    def to_hex(self, with_alpha: bool = False) -> str:
        """The color as a hex string, `"#RRGGBB"`, in capitals.

        Args:
            with_alpha: Whether to add the opacity's two digits: `"#RRGGBBAA"`.

        Returns:
            The string.
        """
        r, g, b, a = _bytes(self._rgba)
        return f"#{r:02X}{g:02X}{b:02X}" + (f"{a:02X}" if with_alpha else "")

    def interpolate(self, other: "ManimColor", alpha: float) -> "ManimColor":
        """The color a fraction of the way from this one to another, mixed as every
        blend of colors is: in OKLab, where the colors between two are those the eye sees
        between them.

        Args:
            other: The color at 1.
            alpha: How far toward it, from 0 (this color) to 1 (`other`).

        Returns:
            A new color.
        """
        return ManimColor(tuple(mix_rgba(self._rgba, other._rgba, alpha)))

    def opacity(self, opacity: float) -> "ManimColor":
        """This color with another opacity.

        Args:
            opacity: The opacity, from 0 (transparent) to 1 (opaque).

        Returns:
            A new color.
        """
        return ManimColor((*self._rgba[:3], float(opacity)))

    def lighter(self, blend: float = 0.2) -> "ManimColor":
        """This color mixed toward white, its opacity kept.

        Args:
            blend: How far toward white, from 0 (this color) to 1 (white).

        Returns:
            A new color.
        """
        return self.interpolate(WHITE, blend).opacity(self._rgba[3])

    def darker(self, blend: float = 0.2) -> "ManimColor":
        """This color mixed toward black, its opacity kept.

        Args:
            blend: How far toward black, from 0 (this color) to 1 (black).

        Returns:
            A new color.
        """
        return self.interpolate(BLACK, blend).opacity(self._rgba[3])

    @classmethod
    def from_hex(cls, hex_str: str, alpha: float = 1.0) -> "ManimColor":
        """The color of a hex string, read as the constructor reads it (`"#RRGGBB"`,
        `"#RGB"`, with or without opacity digits; a color's name too).

        Args:
            hex_str: The string.
            alpha: The opacity, from 0 to 1, if the string gives none.

        Returns:
            A new color.
        """
        return cls(hex_str, alpha)

    @classmethod
    def from_rgb(
        cls, rgb: Sequence[float] | Floats, alpha: float = 1.0
    ) -> "ManimColor":
        """The color of a red, green and blue.

        Args:
            rgb: Red, green and blue, from 0 to 1.
            alpha: The opacity, from 0 to 1.

        Returns:
            A new color.
        """
        return cls(tuple(float(x) for x in rgb), alpha)

    @classmethod
    def from_rgba(cls, rgba: Sequence[float] | Floats) -> "ManimColor":
        """The color of a red, green, blue and opacity.

        Args:
            rgba: Red, green, blue and opacity, from 0 to 1.

        Returns:
            A new color.
        """
        return cls(tuple(float(x) for x in rgba[:3]), float(rgba[3]))

    @classmethod
    def from_hsv(
        cls, hsv: Sequence[float] | Floats, alpha: float = 1.0
    ) -> "ManimColor":
        """The color of a hue, saturation and value.

        Args:
            hsv: Hue, saturation and value, each a float from 0 to 1: a hue of 0 (or 1)
                is red, 1/3 green, 2/3 blue.
            alpha: The opacity, from 0 to 1.

        Returns:
            A new color.
        """
        return cls(colorsys.hsv_to_rgb(*hsv[:3]), alpha)

    @classmethod
    def from_hsl(
        cls, hsl: Sequence[float] | Floats, alpha: float = 1.0
    ) -> "ManimColor":
        """The color of a hue, saturation and lightness.

        Args:
            hsl: Hue, saturation and lightness, each from 0 to 1: a hue of 0 (or 1) is
                red, 1/3 green, 2/3 blue; a lightness of 0.5 is the full color.
            alpha: The opacity, from 0 to 1.

        Returns:
            A new color.
        """
        hue, saturation, lightness = hsl[:3]
        return cls(colorsys.hls_to_rgb(hue, lightness, saturation), alpha)

    def to_hsv(self) -> np.ndarray:
        """The color's hue, saturation and value.

        Returns:
            An array of three floats, from 0 to 1.
        """
        return np.array(colorsys.rgb_to_hsv(*self.to_rgb()))

    @deprecated("use HSV(...)", category=None)
    def into[C: "ManimColor"](self, cls: type[C]) -> C:
        """This color as an instance of another color class, such as
        [HSV][manimgx.HSV].

        Args:
            cls: The class: ManimColor or a subclass of it.

        Returns:
            A new color of that class, of the same value.
        """
        return _made(cls, self._rgba.copy())

    def contrasting(
        self,
        threshold: float = 0.5,
        light: "ManimColor | None" = None,
        dark: "ManimColor | None" = None,
    ) -> "ManimColor":
        """A color that stands out against this one, as text on it would: dark on a
        light color, light on a dark one.

        Args:
            threshold: The luma (0.30 red + 0.59 green + 0.11 blue), from 0 to 1,
                above which this color counts as light.
            light: The color for a dark color; None for white.
            dark: The color for a light color; None for black.

        Returns:
            `dark` or `light`.
        """
        luminance = colorsys.rgb_to_yiq(*self.to_rgb())[0]
        return (dark or BLACK) if luminance > threshold else (light or WHITE)

    def invert(self) -> "ManimColor":
        """The color's complement: each of red, green and blue taken from 1, the opacity
        kept.

        Returns:
            A new color.
        """
        return ManimColor((*(1.0 - self._rgba[:3]), self._rgba[3]))

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{self}')"

    def __str__(self) -> str:
        """The hex of the color's value (a color changed since it was made, as an `HSV` can be,
        says what it is now)."""
        return _hex(self._rgba)

    def __reduce__(self) -> tuple[object, ...]:
        return _made, (type(self), self._rgba.copy())


def _bytes(rgba: np.ndarray) -> list[int]:
    return [round(float(c) * 255) for c in np.clip(rgba, 0.0, 1.0)]


def _hex(rgba: np.ndarray) -> str:
    r, g, b, a = _bytes(rgba)
    return f"#{r:02X}{g:02X}{b:02X}" + ("" if a == 255 else f"{a:02X}")


def _made[C: ManimColor](cls: type[C], rgba: np.ndarray) -> C:
    """A color of class `cls` with the value `rgba` (as it stands: no parsing)."""
    color = str.__new__(cls, _hex(rgba))
    color._rgba = rgba
    return color


def _parse(value: "ParsableManimColor | None", alpha: float) -> np.ndarray:
    if value is None:
        return np.array((0.0, 0.0, 0.0, alpha))
    if isinstance(value, ManimColor):
        return value._rgba.copy()
    if isinstance(value, int):
        return np.array(
            (
                (value >> 16 & 255) / 255,
                (value >> 8 & 255) / 255,
                (value & 255) / 255,
                alpha,
            )
        )
    if isinstance(value, str):
        m = _HEX.fullmatch(value.strip())
        if m is None:
            if value.strip()[:2].lower() in ("0x",) or value.strip().startswith("#"):
                raise ValueError(
                    f"{value!r} is not a hex color: `#` or `0x` and 3, 4, 6 or 8 digits"
                )
            named = PALETTE.get(value.upper())
            if named is None:
                raise ValueError(f"Color {value} not found")
            return np.array((*named.to_rgb(), alpha))
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            h += "FF"
        else:
            alpha = (int(h, 16) & 255) / 255
        tmp = int(h, 16)
        return np.array(
            (
                (tmp >> 24 & 255) / 255,
                (tmp >> 16 & 255) / 255,
                (tmp >> 8 & 255) / 255,
                alpha,
            )
        )
    arr = np.asarray(value)
    floats = all(isinstance(x, (float, np.floating)) for x in value)
    scale = 1.0 if floats else 255.0
    if len(arr) == 3:
        return np.array((*(arr / scale), alpha), dtype=float)
    if len(arr) == 4:
        return np.asarray(arr / scale, dtype=float)
    raise ValueError(f"ManimColor accepts length 3 or 4 sequences, not {len(arr)}")


@deprecated("color_to_rgb(color) is ManimColor(color).to_rgb(): use it", category=None)
def color_to_rgb(color: ParsableManimColor) -> np.ndarray:
    """The red, green and blue of a color.

    Args:
        color: The color, in any form [ManimColor][manimgx.ManimColor] reads.

    Returns:
        An array of three floats, from 0 to 1.
    """
    return ManimColor(color).to_rgb()


@deprecated("rgb_to_color(rgb) is ManimColor.from_rgb(rgb): use it", category=None)
def rgb_to_color(rgb: Sequence[float] | np.ndarray) -> ManimColor:
    """The color of a red, green and blue.

    Args:
        rgb: Red, green and blue, from 0 to 1.

    Returns:
        A new, opaque color.
    """
    return ManimColor(tuple(float(x) for x in rgb))


def invert_color(color: ParsableManimColor) -> ManimColor:
    """A color's complement: each of red, green and blue taken from 1, the opacity kept.

    Args:
        color: The color, in any form [ManimColor][manimgx.ManimColor] reads.

    Returns:
        A new color.
    """
    return ManimColor(color).invert()


def interpolate_color(a: ManimColor, b: ManimColor, alpha: float) -> ManimColor:
    """The color a fraction of the way from one color to another.

    The two mix as every blend of colors does: in OKLab, where the colors between two
    are those the eye sees between them.

    Args:
        a: The color at 0.
        b: The color at 1.
        alpha: How far from `a` to `b`, from 0 to 1.

    Returns:
        A new color.

    Examples:
        ```python
        import manimgx as m


        class InterpolateColorExample(m.Scene):
            def construct(self) -> None:
                swatches = m.VGroup()
                for alpha in (0, 0.25, 0.5, 0.75, 1):
                    color = m.interpolate_color(m.BLUE, m.RED, alpha)
                    square = m.Square(side_length=1.8, color=color, fill_opacity=1)
                    label = m.Text(str(alpha), font_size=32).next_to(square, m.DOWN)
                    swatches.add(m.VGroup(square, label))
                self.add(swatches.arrange(buff=0.5))
        ```
    """
    return ManimColor(a).interpolate(ManimColor(b), alpha)


def color_gradient(
    reference_colors: Sequence[ParsableManimColor], length_of_output: int
) -> list[ManimColor]:
    """Colors evenly spaced along a gradient through reference colors, from the first to
    the last.

    Each is mixed between the two reference colors on either side of it, as
    [interpolate_color][manimgx.interpolate_color] mixes them.

    Args:
        reference_colors: The colors the gradient runs through, evenly spaced along it.
        length_of_output: How many colors to return; one is the last reference color.

    Returns:
        The colors, in order along the gradient.

    Examples:
        ```python
        import manimgx as m


        class ColorGradientExample(m.Scene):
            def construct(self) -> None:
                colors = m.color_gradient([m.BLUE, m.GREEN, m.YELLOW, m.RED], 12)
                dots = m.VGroup(*(m.Dot(radius=0.4, color=color) for color in colors))
                self.add(dots.arrange(buff=0.3))
        ```
    """
    if length_of_output == 0:
        return []
    if len(reference_colors) == 1:
        return [ManimColor(reference_colors[0])] * length_of_output
    rgbas = [ManimColor(c).to_rgba() for c in reference_colors]
    alphas = np.linspace(0, len(rgbas) - 1, length_of_output)
    floors = alphas.astype(int)
    alphas_mod1 = alphas % 1
    alphas_mod1[-1] = 1
    floors[-1] = len(rgbas) - 2
    return [
        ManimColor(tuple(mix_rgba(rgbas[i], rgbas[i + 1], float(a))))
        for i, a in zip(floors, alphas_mod1, strict=True)
    ]


def average_color(*colors: ParsableManimColor) -> ManimColor:
    """The average of colors, taken in OKLab: the color the eye sees as their middle.

    Their opacities are left out: the average is opaque.

    Args:
        *colors: The colors, in any form [ManimColor][manimgx.ManimColor] reads.

    Returns:
        A new, opaque color.
    """
    lab = np.mean([to_oklab(ManimColor(c).to_rgb()) for c in colors], axis=0)
    return ManimColor(tuple(from_oklab(lab)))


type Colorscale = (
    Sequence[ParsableManimColor] | Sequence[tuple[ParsableManimColor, float]]
)
"""Colors for a range of values: colors spread evenly over the range, or (color, value)
pairs, each color at its value (see [colors_by_value][manimgx.colors_by_value])."""


def colors_by_value(
    colorscale: Colorscale, values: Iterable[float], low: float, high: float
) -> list[ManimColor]:
    """The color of each value on a colorscale: mixed between the colors on either side
    of it, and held beyond the colorscale's ends.

    The colors mix as every blend of colors does: in OKLab, where the colors between
    two are those the eye sees between them.

    Args:
        colorscale: Colors spread evenly from `low` to `high`, or (color, value) pairs,
            each color at its value, in increasing order of value.
        values: The values to color.
        low: The value of the first color, when the colors are spread evenly.
        high: The value of the last color, when the colors are spread evenly.

    Returns:
        One color per value, in order.
    """
    rows = rgbas_by_value(colorscale, list(values), low, high)
    return [ManimColor(tuple(row)) for row in rows]


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def rgbas_by_value(
    colorscale: Colorscale, values: npt.ArrayLike, low: float, high: float
) -> Floats:
    """The color of each value on a colorscale, as a row of red, green, blue and
    opacity: [colors_by_value][manimgx.colors_by_value], for many values at once.

    Each value's color is mixed between the colors on either side of it, as every blend
    of colors mixes (see [mix_rgba][manimgx.mix_rgba]), and held beyond the
    colorscale's ends.

    Args:
        colorscale: Colors spread evenly from `low` to `high`, or (color, value) pairs,
            each color at its value, in increasing order of value.
        values: The values to color: numbers, in an array of any shape (read in
            order, flattened).
        low: The value of the first color, when the colors are spread evenly.
        high: The value of the last color, when the colors are spread evenly.

    Returns:
        An (n, 4) array, a row per value, each from 0 to 1.
    """
    # the pivots are the colors' values, given or spread evenly over [low, high]
    if all(isinstance(c, (tuple, list)) and len(c) == 2 for c in colorscale):
        pairs = cast("Sequence[tuple[ParsableManimColor, float]]", colorscale)
        colors = np.array([ManimColor(c).to_rgba() for c, _ in pairs])
        pivots = np.array([p for _, p in pairs], dtype=float)
    else:
        scale = cast("Sequence[ParsableManimColor]", colorscale)
        colors = np.array([ManimColor(c).to_rgba() for c in scale])
        pivots = np.linspace(low, high, len(colors))
    v = np.asarray(values, dtype=float).reshape(-1)
    i = np.searchsorted(pivots, v, side="right")  # the first pivot above each value
    inside = (i > 0) & (i < len(pivots))
    ia, ib = np.clip(i - 1, 0, len(pivots) - 1), np.minimum(i, len(pivots) - 1)
    span = np.where(inside, pivots[ib] - pivots[ia], 1.0)
    t = np.where(inside, np.minimum(1.0, (v - pivots[ia]) / span), 0.0)
    mixed = mix_rgba(colors[ia], colors[ib], t)
    return np.where(
        inside[:, None], mixed, colors[np.where(i == 0, 0, len(pivots) - 1)]
    )


def random_color() -> ManimColor:
    """A named color, drawn at random.

    Python's `random` draws it, so `random.seed` makes it repeatable; see
    [RandomColorGenerator][manimgx.RandomColorGenerator] for a stream of its own.

    Returns:
        One of the named colors.
    """
    return random.choice(list(PALETTE.values()))


def random_bright_color() -> ManimColor:
    """A light color, drawn at random: its red, green and blue each from 0.5 to 1.

    NumPy's global generator draws it, so `np.random.seed` makes it repeatable.

    Returns:
        A new, opaque color.
    """
    return ManimColor(tuple(1.0 - 0.5 * np.random.random(3)))


def _numbers(value: object) -> TypeIs[Sequence[float] | np.ndarray]:
    """An rgb(a) tuple or array: one color, not several."""
    return isinstance(value, (Sequence, np.ndarray)) and all(
        isinstance(x, (int, float, np.integer, np.floating)) for x in value
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def parse_colors(
    value: ParsableManimColor | Iterable[ParsableManimColor] | None,
) -> list[ManimColor]:
    """Read one color or several, as a list.

    Args:
        value: A color in any form [ManimColor][manimgx.ManimColor] reads (three or four
            numbers are one color), several colors, or None for black.

    Returns:
        The colors, in a list.
    """
    if value is None:
        return [BLACK]
    if isinstance(value, (str, ManimColor, int)) or _numbers(value):
        return [ManimColor(value)]
    return [ManimColor(c) for c in value]


# ── the named palette (Manim CE 0.21 names and values), as real constants ──────
WHITE: Final = ManimColor("#FFFFFF")
GRAY_A: Final = ManimColor("#DDDDDD")
GREY_A: Final = ManimColor("#DDDDDD")
GRAY_B: Final = ManimColor("#BBBBBB")
GREY_B: Final = ManimColor("#BBBBBB")
GRAY_C: Final = ManimColor("#888888")
GREY_C: Final = ManimColor("#888888")
GRAY_D: Final = ManimColor("#444444")
GREY_D: Final = ManimColor("#444444")
GRAY_E: Final = ManimColor("#222222")
GREY_E: Final = ManimColor("#222222")
BLACK: Final = ManimColor(
    "#000000"
)  # here, as CE orders its palette (`random_color` draws from it)
LIGHTER_GRAY: Final = ManimColor("#DDDDDD")
LIGHTER_GREY: Final = ManimColor("#DDDDDD")
LIGHT_GRAY: Final = ManimColor("#BBBBBB")
LIGHT_GREY: Final = ManimColor("#BBBBBB")
GRAY: Final = ManimColor("#888888")
GREY: Final = ManimColor("#888888")
DARK_GRAY: Final = ManimColor("#444444")
DARK_GREY: Final = ManimColor("#444444")
DARKER_GRAY: Final = ManimColor("#222222")
DARKER_GREY: Final = ManimColor("#222222")
PURE_RED: Final = ManimColor("#FF0000")
PURE_GREEN: Final = ManimColor("#00FF00")
PURE_BLUE: Final = ManimColor("#0000FF")
PURE_CYAN: Final = ManimColor("#00FFFF")
PURE_MAGENTA: Final = ManimColor("#FF00FF")
PURE_YELLOW: Final = ManimColor("#FFFF00")
BLUE_A: Final = ManimColor("#C7E9F1")
BLUE_B: Final = ManimColor("#9CDCEB")
BLUE_C: Final = ManimColor("#58C4DD")
BLUE_D: Final = ManimColor("#29ABCA")
BLUE_E: Final = ManimColor("#236B8E")
BLUE: Final = ManimColor("#58C4DD")
DARK_BLUE: Final = ManimColor("#236B8E")
TEAL_A: Final = ManimColor("#ACEAD7")
TEAL_B: Final = ManimColor("#76DDC0")
TEAL_C: Final = ManimColor("#5CD0B3")
TEAL_D: Final = ManimColor("#55C1A7")
TEAL_E: Final = ManimColor("#49A88F")
TEAL: Final = ManimColor("#5CD0B3")
GREEN_A: Final = ManimColor("#C9E2AE")
GREEN_B: Final = ManimColor("#A6CF8C")
GREEN_C: Final = ManimColor("#83C167")
GREEN_D: Final = ManimColor("#77B05D")
GREEN_E: Final = ManimColor("#699C52")
GREEN: Final = ManimColor("#83C167")
YELLOW_A: Final = ManimColor("#FFF1B6")
YELLOW_B: Final = ManimColor("#FFEA94")
YELLOW_C: Final = ManimColor("#F7D96F")
YELLOW_D: Final = ManimColor("#F4D345")
YELLOW_E: Final = ManimColor("#E8C11C")
YELLOW: Final = ManimColor("#F7D96F")
GOLD_A: Final = ManimColor("#F7C797")
GOLD_B: Final = ManimColor("#F9B775")
GOLD_C: Final = ManimColor("#F0AC5F")
GOLD_D: Final = ManimColor("#E1A158")
GOLD_E: Final = ManimColor("#C78D46")
GOLD: Final = ManimColor("#F0AC5F")
RED_A: Final = ManimColor("#F7A1A3")
RED_B: Final = ManimColor("#FF8080")
RED_C: Final = ManimColor("#FC6255")
RED_D: Final = ManimColor("#E65A4C")
RED_E: Final = ManimColor("#CF5044")
RED: Final = ManimColor("#FC6255")
MAROON_A: Final = ManimColor("#ECABC1")
MAROON_B: Final = ManimColor("#EC92AB")
MAROON_C: Final = ManimColor("#C55F73")
MAROON_D: Final = ManimColor("#A24D61")
MAROON_E: Final = ManimColor("#94424F")
MAROON: Final = ManimColor("#C55F73")
PURPLE_A: Final = ManimColor("#CAA3E8")
PURPLE_B: Final = ManimColor("#B189C6")
PURPLE_C: Final = ManimColor("#9A72AC")
PURPLE_D: Final = ManimColor("#715582")
PURPLE_E: Final = ManimColor("#644172")
PURPLE: Final = ManimColor("#9A72AC")
PINK: Final = ManimColor("#D147BD")
LIGHT_PINK: Final = ManimColor("#DC75CD")
ORANGE: Final = ManimColor("#FF862F")
LIGHT_BROWN: Final = ManimColor("#CD853F")
DARK_BROWN: Final = ManimColor("#8B4513")
GRAY_BROWN: Final = ManimColor("#736357")
GREY_BROWN: Final = ManimColor("#736357")
LOGO_WHITE: Final = ManimColor("#ECE7E2")
LOGO_GREEN: Final = ManimColor("#87C2A5")
LOGO_BLUE: Final = ManimColor("#525893")
LOGO_RED: Final = ManimColor("#E07A5F")
LOGO_BLACK: Final = ManimColor("#343434")

PALETTE: Final[dict[str, ManimColor]] = {
    name: value
    for name, value in globals().items()
    if isinstance(value, ManimColor) and name.isupper()
}
"""The named colors, by name: `PALETTE["BLUE"]` is `BLUE`. A color's name, in any case,
is read as the color."""


class HSV(ManimColor):
    """A color made from a hue, saturation and value, which can be read and set.

    `HSV(hsv, alpha=1.0)` takes the hue, saturation and value, each from 0 to 1, and
    the opacity: a fourth number of `hsv`, if given, or else `alpha`, from 0 to 1.
    Setting [hue][manimgx.HSV.hue], [saturation][manimgx.HSV.saturation] or
    [value][manimgx.HSV.value] changes the color, as a value and as its `str`; it still
    compares equal to (and hashes as) the string it was made as.

    Examples:
        ```python
        import manimgx as m


        class HSVExample(m.Scene):
            def construct(self) -> None:
                color = m.HSV((0.0, 0.7, 0.9))
                swatches = m.VGroup()
                for step in range(8):
                    color.hue = step / 8
                    swatches.add(m.Square(side_length=1.2, color=color, fill_opacity=1))
                self.add(swatches.arrange(buff=0.3))
        ```
    """

    def __new__(cls, hsv: Sequence[float], alpha: float = 1.0) -> Self:
        rgb = colorsys.hsv_to_rgb(*(float(x) for x in hsv[:3]))
        return _made(
            cls, np.array((*rgb, hsv[3] if len(hsv) > 3 else alpha), dtype=float)
        )

    def _set(self, index: int, value: float) -> None:
        hsv = list(self.to_hsv())
        hsv[index] = value
        self._rgba[:3] = colorsys.hsv_to_rgb(*hsv)

    h = hue = property(
        lambda self: float(self.to_hsv()[0]), lambda self, v: self._set(0, v)
    )
    """The color's hue, from 0 to 1: 0 (or 1) red, 1/3 green, 2/3 blue. Set it to change
    the color."""
    s = saturation = property(
        lambda self: float(self.to_hsv()[1]), lambda self, v: self._set(1, v)
    )
    """The color's saturation, from 0 (grey) to 1 (the full color). Set it to change the
    color."""
    v = value = property(
        lambda self: float(self.to_hsv()[2]), lambda self, v: self._set(2, v)
    )
    """The color's value, from 0 (black) to 1 (the brightest). Set it to change the
    color."""


class RandomColorGenerator:
    """A stream of colors drawn at random, the same for the same seed.

    Args:
        seed: The seed; None for a different stream each run.
        sample_colors: The colors to draw from; None (or no colors) for the named
            colors.

    Examples:
        ```python
        import manimgx as m


        class RandomColorGeneratorExample(m.Scene):
            def construct(self) -> None:
                palette = [m.RED, m.GREEN, m.BLUE, m.YELLOW, m.PURPLE, m.TEAL]
                colors = m.RandomColorGenerator(seed=7, sample_colors=palette)
                squares = m.VGroup(
                    *(
                        m.Square(side_length=1, color=colors.next(), fill_opacity=1)
                        for _ in range(40)
                    )
                )
                self.add(squares.arrange_in_grid(rows=4, buff=0.2))
        ```
    """

    def __init__(
        self, seed: int | None = None, sample_colors: list[ManimColor] | None = None
    ) -> None:
        self.choice = random.Random(seed).choice
        self.colors = sample_colors or list(PALETTE.values())

    def next(self) -> ManimColor:
        """The stream's next color: one of its colors, drawn at random."""
        return self.choice(self.colors)


if TYPE_CHECKING:
    from manimgx.mobject import Mobject
    from manimgx.scene import Camera

type Colors = ParsableManimColor | Sequence[ParsableManimColor]


@dataclass(frozen=True)
class Material:
    """How a surface reflects light: a physically based model, its base color the mobject's fill.

    A mobject with a material is lit by the scene's lights
    ([`SunLight`][manimgx.SunLight], [`PointLight`][manimgx.PointLight],
    [`SpotLight`][manimgx.SpotLight], [`AmbientLight`][manimgx.AmbientLight],
    [`EnvironmentLight`][manimgx.EnvironmentLight]) in a three-dimensional scene, and a mobject without one keeps Manim's shading
    (`shade_in_3d`). Surfaces are lit, and so are flat filled shapes (their fill: a
    shape's strokes keep their color); the shadows of whatever the scene shows fall on
    them. What is fixed in the frame is not in the scene, and is not lit. A material
    tweens: its numbers are mixed like colors.

    Args:
        metallic: How metallic it is, from 0 (a dielectric: plastic, paint, stone, skin) to 1
            (a metal, whose reflections take its color).
        roughness: How rough it is, from 0 (a mirror finish: sharp highlights) to 1 (matte).
        reflectance: How much a dielectric reflects when seen head on, from 0 to 1 (0.5: 4%,
            most materials; 0.35: water's 2%; 1: 16%, gems).

    Examples:
        ```python
        import manimgx as m


        class MaterialExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-45 * m.DEGREES)
                self.add(
                    m.SunLight(5 * m.UP + 3 * m.OUT), m.AmbientLight(intensity=0.2)
                )
                for i, roughness in enumerate([0.2, 0.5, 0.9]):
                    sphere = m.Sphere(radius=0.8, resolution=(48, 48))
                    sphere.set_color(m.GOLD).shift(2 * (i - 1) * m.RIGHT)
                    self.add(
                        sphere.set_material(m.Material(metallic=1, roughness=roughness))
                    )
        ```
    """

    metallic: float = 0.0
    roughness: float = 0.5
    reflectance: float = 0.5

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def mixed(self, other: "Material", alpha: float) -> "Material":
        """This material's numbers moved `alpha` of the way to `other`'s."""
        return Material(
            *(
                a + (b - a) * alpha
                for a, b in (
                    (self.metallic, other.metallic),
                    (self.roughness, other.roughness),
                    (self.reflectance, other.reflectance),
                )
            )
        )


# Style is keyword-only, and a class never re-declares a style keyword to change its default
# (that is what made typed kwargs combinatorial): it lists what it changes in `defaults`, and
# the class hierarchy cascades. The one exception is `color`, which a few classes take by
# position (as `Circle(1, RED)`); they declare it with a None default ("not given") and use
# `StyleBase` for the rest.


class _Look(TypedDict, total=False):
    """Look's keys, open, for the keywords that add to them."""

    background_stroke_color: Colors | None
    """The color of an outline drawn behind the fill (default black)."""
    background_stroke_opacity: float | Sequence[float]
    """The outline's opacity, from 0 to 1 (default 1)."""
    background_stroke_width: float
    """The outline's width, in hundredths of a scene unit (default 0: none)."""
    sheen_factor: float
    """How much the colors lighten toward `sheen_direction`, from -1 to 1 (default 0);
    a negative factor darkens."""
    sheen_direction: Vector3DLike
    """The direction the colors lighten toward (default [`UL`][manimgx.UL])."""
    joint_type: LineJointType | None
    """How the stroke is joined where its path turns: round, beveled or mitered, as a
    two-dimensional scene draws it (see [LineJointType][manimgx.LineJointType]; default
    AUTO: mitered)."""
    cap_style: CapStyleType
    """How the stroke ends, at each end it shows (an open path's, a dash's): round, butt
    or square, as a two-dimensional scene draws it (see
    [CapStyleType][manimgx.CapStyleType]; default AUTO: butt)."""
    shade_in_3d: bool
    """Whether a three-dimensional scene's light shades the mobject."""
    material: Material | None
    """How its surface reflects the scene's lights in a three-dimensional scene (see
    [Material][manimgx.Material]); None: Manim's shading (default)."""
    name: str | None
    """A name for the mobject; its class's name if not given."""
    z_index: float
    """Its place in the drawing order: a higher index is drawn over a lower one
    (default 0)."""
    target: "Mobject | None"
    """The state [`MoveToTarget`][manimgx.MoveToTarget] moves the mobject to."""


class Look(_Look, total=False, closed=True):
    """The style keywords that are not paint.

    A mobject whose paint comes from its source (an SVG file, typeset text) takes these,
    with [`Repaint`][manimgx.drawing.paint.Repaint] to paint over its source's colors.
    """


class Repaint(TypedDict, total=False):
    """Paint over the paint a mobject's source gives its parts.

    An SVG file and typeset text color their own parts; each of these keywords, when given,
    paints over them, and when absent (or None) keeps the source's.
    """

    color: Colors | None
    """The color of both fill and stroke."""
    opacity: float | None
    """The opacity of both fill and stroke, from 0 to 1."""
    fill_color: Colors | None
    """The fill's color."""
    fill_opacity: float | Sequence[float] | None
    """The fill's opacity, from 0 to 1."""
    stroke_color: Colors | None
    """The stroke's color."""
    stroke_opacity: float | Sequence[float] | None
    """The stroke's opacity, from 0 to 1."""
    stroke_width: float | None
    """The stroke's width, in hundredths of a scene unit."""


class _StyleBase(_Look, total=False):
    """StyleBase's keys, open, for the keywords that add to them."""

    fill_color: Colors | None
    """The fill's color; `color` if not given. Several colors make a gradient along
    `sheen_direction`."""
    fill_opacity: float | Sequence[float]
    """The fill's opacity, from 0 to 1 (default 0: no fill)."""
    stroke_color: Colors | None
    """The stroke's color; `color` if not given. Several colors make a gradient."""
    stroke_opacity: float | Sequence[float]
    """The stroke's opacity, from 0 to 1 (default 1)."""
    stroke_width: float
    """The stroke's width, in hundredths of a scene unit (default 4; 0: no stroke)."""


class StyleBase(_StyleBase, total=False, closed=True):
    """Every style keyword but `color`.

    A class that takes `color` by position declares it itself, and the rest with this.
    """


class _Style(_StyleBase, total=False):
    """Style's keys, open, for the keywords that add to them."""

    color: Colors | None
    """The color of both fill and stroke (default white); None for the class's default."""


class Style(_Style, total=False, closed=True):
    """The style keywords: one vocabulary for every mobject and every group.

    Every mobject takes these keywords, and each class sets its own defaults for them
    (a [`Circle`][manimgx.Circle] is red, a [`Dot`][manimgx.Dot] is filled). A color is
    anything [`ManimColor`][manimgx.ManimColor] parses: a named color such as `BLUE`,
    a hex string, or RGB values.
    """


class Fill(TypedDict):
    """A fill's color and opacity: an image's style (`ImageMobject.get_style()`)."""

    fill_color: ManimColor
    fill_opacity: float


class SimpleStyle(Fill):
    """A style by its first brushes (`VMobject.get_style(simple=True)`)."""

    stroke_color: ManimColor
    stroke_opacity: float
    stroke_width: float


class StyleSnapshot(TypedDict):
    """A style, brush by brush (`VMobject.get_style()`): `set_style(**snapshot)` restores it."""

    fill_color: list[ManimColor]
    fill_opacity: list[float]
    stroke_color: list[ManimColor]
    stroke_opacity: list[float]
    stroke_width: float
    background_stroke_color: list[ManimColor]
    background_stroke_opacity: list[float]
    background_stroke_width: float
    sheen_factor: float
    sheen_direction: Vector3D


def key_of(value: object) -> object:
    """A plain value as a memo's key, by what it is: a color by its exact RGBA (not its
    hex), a small array by its dtype and bytes, a path by its text, a list or tuple
    item by item. Scalar types distinguish integer RGB from normalized floats.
    Anything else (a mobject, a function, a picture) raises TypeError: what is made
    from it is not remembered."""
    if isinstance(value, ManimColor):
        return (ManimColor, *value.to_rgba())
    if value is None:
        return None
    if isinstance(value, (str, int, float, Enum)):
        return (type(value), value)
    if isinstance(value, Material):
        return (Material, value.metallic, value.roughness, value.reflectance)
    if type(value) is dict:
        return (dict, tuple((key_of(k), key_of(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return (type(value), tuple(key_of(v) for v in value))
    if isinstance(value, np.ndarray) and value.size <= 64 and not value.dtype.hasobject:
        return (np.ndarray, value.dtype, value.shape, value.tobytes())
    if isinstance(value, PurePath):
        return (PurePath, str(value))
    raise TypeError(type(value))


_PARSED: Memo[tuple[object, object], RGBA_Array] = Memo(1 << 12)


def rgbas(
    color: ParsableManimColor | Iterable[ParsableManimColor] | None,
    opacity: float | Iterable[float] | None,
) -> RGBA_Array:
    """CE `generate_rgbas_array` without sheen (None color: black; None opacity: 0), parsed once
    per distinct (color, opacity)."""
    try:
        key = (key_of(color), key_of(opacity))
    except TypeError:
        return _rgbas(color, opacity)
    return _PARSED.recall(key, lambda: frozen(_rgbas(color, opacity)))


def _rgbas(
    color: ParsableManimColor | Iterable[ParsableManimColor] | None,
    opacity: float | Iterable[float] | None,
) -> RGBA_Array:
    colors = parse_colors(color)
    opacities = list(opacity) if isinstance(opacity, Iterable) else [opacity]
    opacities = [o if o is not None else 0.0 for o in opacities]
    n = max(len(colors), len(opacities))
    colors = stretch(colors, n)
    opacities = stretch(opacities, n)
    return np.array(
        [c.to_rgba_with_alpha(o) for c, o in zip(colors, opacities, strict=True)]
    )


def stretch[T](values: list[T], n: int) -> list[T]:
    """CE `make_even` for one list: repeat entries so the list has length n."""
    if len(values) == n:
        return values
    return [values[i * len(values) // n] for i in range(n)]


def stretch_array(array: np.ndarray, n: int) -> np.ndarray:
    """Stretch an array to `n` items, repeating its items evenly, in order.

    Item `i` of the result is item `i * len(array) // n` of the array.

    Args:
        array: The items, along its first axis.
        n: How many items the result has: at least as many as the array has (fewer
            raise ValueError).

    Returns:
        The array itself if it has `n` items; else a new one.
    """
    cur = len(array)
    if cur == n:
        return array
    if cur > n:
        raise ValueError("Can't stretch array to a shorter length")
    return array[(np.arange(n) * cur // n).astype(int)]


@deprecated("stretch_array_to_length is stretch_array: use it", category=None)
def stretch_array_to_length(array: np.ndarray, n: int) -> np.ndarray:
    """Manim CE's name for [stretch_array][manimgx.stretch_array]."""
    return stretch_array(array, n)


def frozen(values: npt.ArrayLike, held: object = None) -> np.ndarray:
    """Adopt an internal float array as read-only; keep `held` when they are equal.

    Inputs are fresh buffers or values already owned by paint. Public style
    setters copy borrowed arrays before transferring them here.
    """
    array = np.asarray(values, dtype=float)
    if isinstance(held, np.ndarray) and unchanged(array, held):
        return held
    if array.flags.writeable:
        if not array.flags.owndata:
            array = array.copy()
        array.flags.writeable = False
    return array


class Paint:
    """How a mobject is painted, as a value: a change makes a new paint, so copies share one and
    what is derived from it (a record) holds while a mobject keeps it. It stores only what differs
    from the default (the class attributes). A tween's paint leaves brushes (None) to its `mix`
    (brushes_a, brushes_b, t), which the player mixes. Capturing brush inputs
    materializes any prior mixes; no source paint or its other resources is kept."""

    _fill: RGBA_Array | None = frozen([[1.0, 1.0, 1.0, 0.0]])
    _stroke: RGBA_Array | None = frozen([[1.0, 1.0, 1.0, 1.0]])
    _background: RGBA_Array | None = frozen([[0.0, 0.0, 0.0, 1.0]])
    stroke_width: float = 4.0
    background_width: float = 0.0
    sheen_factor: float = 0.0
    sheen_direction: np.ndarray = frozen(UL)
    joint: LineJointType = LineJointType.AUTO
    cap: CapStyleType = CapStyleType.AUTO
    shade_in_3d: bool = False
    material: "Material | None" = None
    texture: "np.ndarray | Camera | None" = None  # pixels (h, w, 4) uint8, or a camera
    # the texture is the fill's colors by value (a colormap): a fill color replaces it
    colormap: bool = False
    trim: np.ndarray = frozen([0.0, 1.0])  # the reveal window, fractions of the length
    pace: tuple[np.ndarray, np.ndarray] | None = (
        None  # (length fraction, u) at reveal start
    )
    # dashes: (period, duty, phase) over the path's parameter, drawn where
    # frac((u − phase) / period) < duty — a second, periodic window beside `trim`
    dash: tuple[float, float, float] | None = None
    mix: tuple[tuple[RGBA_Array, ...], tuple[RGBA_Array, ...], float] | None = None
    # what was derived from this paint: changes asked of it, and their results (its own, made with it)
    _derived: dict[tuple[object, ...], object]

    def __init__(self) -> None:
        self.__dict__["_derived"] = {}

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("a paint never changes: derive one with `but`")

    @property
    def fill(self) -> RGBA_Array:
        return self._fill if self._fill is not None else self._mixed("fill")

    @property
    def stroke(self) -> RGBA_Array:
        return self._stroke if self._stroke is not None else self._mixed("stroke")

    @property
    def background(self) -> RGBA_Array:
        b = self._background
        return b if b is not None else self._mixed("background")

    def _mixed(self, name: str) -> RGBA_Array:
        """A brush left to the tween, read here: mixed as the player mixes it, once."""
        known = self._derived.get(("brush", name))
        if known is None:
            assert self.mix is not None
            a, b, t = self.mix
            index = _BRUSHES.index(name)
            known = self._derived[("brush", name)] = frozen(
                mix_rgba(a[index], b[index], t)
            )
        return cast("RGBA_Array", known)

    def ends(self, name: str) -> tuple[RGBA_Array, RGBA_Array]:
        """A brush's two arrays as the player draws them, mixed by `mix`."""
        own = getattr(self, _SLOTS[name])
        if own is not None:
            return own, own
        assert self.mix is not None
        a, b, _ = self.mix
        index = _BRUSHES.index(name)
        return a[index], b[index]

    def but(self, **changes: object) -> "Paint":
        """This paint with some fields changed (`fill`, `stroke`, `background`: brushes) —
        itself when they change nothing (arrays equal to those it holds), and the same paint
        for the same plain changes, so what was derived from it holds too. Textures are
        borrowed resources: equal only by identity, and their changes are not remembered.

        Internal brush and direction arrays transfer ownership: callers must not
        change them or their aliases afterward. Public mobject style setters
        snapshot borrowed values before deriving a paint.
        """
        try:
            key: tuple[object, ...] | None = (
                "but",
                *((name, _kept(name, value)) for name, value in changes.items()),
            )
        except TypeError:
            key = None
        derived = self._derived
        if key is not None and (known := derived.get(key)) is not None:
            return cast("Paint", known)
        new = self._but(changes)
        if key is not None and all(
            not isinstance(value, np.ndarray)
            or value is getattr(new, _SLOTS.get(name, name), None)
            for name, value in changes.items()
        ):
            if len(derived) > 32:
                derived.clear()
            derived[key] = new
        return new

    def _but(self, changes: dict[str, object]) -> "Paint":
        fields = self.__dict__.copy()
        changed = False
        numbers: list[tuple[object, object]] = []  # given anew: equal to those held?
        for name, value in changes.items():
            slot = _SLOTS.get(name, name)
            held = getattr(self, slot, None)
            if value is not None and (name in _ARRAYS or name in _SLOTS):
                value = frozen(cast("npt.ArrayLike", value), held)
            elif (
                name != "texture"
                and isinstance(value, np.ndarray)
                and unchanged(value, held)
            ):
                value = held
            elif name in _NUMERIC and value is not held:
                numbers.append((value, held))  # (compared only if nothing else changes)
                fields[slot] = value
                continue
            changed = changed or value is not held
            fields[slot] = value
        if not changed and all(_same_number(*pair) for pair in numbers):
            return self
        fields["_derived"] = {}
        if fields.get("mix") is not None and all(
            fields.get(slot, True) is not None for slot in _SLOTS.values()
        ):
            fields["mix"] = None  # no brush is left to the tween
        new = object.__new__(Paint)
        object.__setattr__(new, "__dict__", fields)
        return new

    def window(self, steps: int) -> tuple[float, float]:
        """The reveal window over u ∈ [0, steps] — what the player draws. u counts a shape's
        steps: a path's curves (its parameter, paced by `pace`), a cloud's points, a mesh's
        triangles, a surface's faces; a step the window reaches into shows, with all it draws."""
        if self.pace is None:
            return float(self.trim[0]) * steps, float(self.trim[1]) * steps
        s, u = self.pace
        lo, hi = np.interp(self.trim, s, u)
        return float(lo), float(hi)

    def updated(
        self,
        name: str,
        color: ParsableManimColor | Iterable[ParsableManimColor] | None,
        opacity: float | Iterable[float] | None,
    ) -> "Paint":
        """CE `update_rgbas_array`: colors and/or opacities written into one brush — remembered,
        and the paint itself when nothing changes."""
        try:
            key: tuple[object, ...] | None = (
                "updated",
                name,
                key_of(color),
                key_of(opacity),
            )
        except TypeError:
            key = None
        derived = self._derived
        if key is not None and (known := derived.get(key)) is not None:
            return cast("Paint", known)
        result = self._updated(name, color, opacity)
        if key is not None:
            if len(derived) > 32:
                derived.clear()
            derived[key] = result
        return result

    def _updated(
        self,
        name: str,
        color: ParsableManimColor | Iterable[ParsableManimColor] | None,
        opacity: float | Iterable[float] | None,
    ) -> "Paint":
        new = rgbas(color, opacity)
        if self.sheen_factor != 0 and len(new) == 1:
            light = new.copy()
            light[:, :3] = np.clip(light[:, :3] + self.sheen_factor, 0, 1)
            new = np.append(new, light, axis=0)
        cur = getattr(self, name)
        if len(cur) == 0:  # a brush of no rows (a cloud of no points): nothing to color
            return self
        if len(cur) < len(new):
            cur = stretch_array(cur, len(new))
        elif len(new) < len(cur):
            new = stretch_array(new, len(cur))
        out = np.array(cur, dtype=float)
        if color is not None:
            out[:, :3] = new[:, :3]
        if opacity is not None:
            out[:, 3] = new[:, 3]
        if color is not None and name == "fill" and self.colormap:
            return self.but(fill=out, texture=None, colormap=False)
        if unchanged(out, cur):  # what is written changes nothing (the brush stretched)
            return self
        return self.but(**{name: out})

    @staticmethod
    def aligned(a: "Paint", b: "Paint") -> tuple["Paint", "Paint"]:
        """Both paints with the same number of brush rows (CE `align_rgbas`)."""
        changes_a: dict[str, np.ndarray] = {}
        changes_b: dict[str, np.ndarray] = {}
        for name in _BRUSHES:
            x, y = getattr(a, name), getattr(b, name)
            if len(x) > len(y):
                changes_b[name] = stretch_array(y, len(x))
            elif len(y) > len(x):
                changes_a[name] = stretch_array(x, len(y))
        return (a.but(**changes_a) if changes_a else a), (
            b.but(**changes_b) if changes_b else b
        )

    def mixed(self, a: "Paint", b: "Paint", alpha: float) -> "Paint":
        """This paint with a's numeric fields blended into b's (joint, cap… stay this paint's):
        brushes left to the tween (`mix`, OKLab, by the player), the rest linearly."""
        changes: dict[str, object] = {
            "pace": b.pace if alpha == 1.0 or a.pace is None else a.pace,
            "dash": (
                (b.dash if alpha >= 0.5 else a.dash)  # dashed ↔ solid: at the middle
                if a.dash is None or b.dash is None
                else tuple(
                    x + (y - x) * alpha for x, y in zip(a.dash, b.dash, strict=True)
                )
            ),
            "mix": None,
            "material": (
                (
                    b.material if alpha >= 0.5 else a.material
                )  # lit ↔ Manim's shading: at the middle
                if a.material is None or b.material is None
                else a.material.mixed(b.material, alpha)
            ),
        }
        for name in _LERPED:
            x, y = getattr(a, name), getattr(b, name)
            changes[name] = y if alpha == 1.0 or x is y else interpolate(x, y, alpha)
        for (
            name
        ) in _WIDTHS:  # past its ends an overshooting rate function: no width < 0
            if cast("float", changes[name]) < 0:  # (a field kept is kept by identity)
                changes[name] = 0.0
        for name, slot in _SLOTS.items():
            x, y = getattr(a, slot), getattr(b, slot)  # None: a tween's
            if alpha >= 1.0 or alpha <= 0.0:
                changes[name] = getattr(b if alpha >= 1.0 else a, name)
            elif x is not None and x is y:
                changes[name] = x
            else:
                changes[name] = None
                if changes["mix"] is None:
                    changes["mix"] = (
                        (a.fill, a.stroke, a.background),
                        (b.fill, b.stroke, b.background),
                        alpha,
                    )
        return self._but(changes)  # a frame's paint: nothing to remember it by


_WIDTHS = ("stroke_width", "background_width")
_LERPED = (
    "stroke_width",
    "background_width",
    "sheen_direction",
    "sheen_factor",
    "trim",
)


def _kept(name: str, value: object) -> object:
    """A change as a key: plain values by value; a read-only array a paint keeps by identity (the
    derived paint holds it, so no other array can take its id while remembered)."""
    if name == "texture" and isinstance(value, np.ndarray):
        raise TypeError(type(value))
    if (
        isinstance(value, np.ndarray)
        and not value.flags.writeable
        and value.dtype == np.float64
        and (name in _SLOTS or name in _ARRAYS)
    ):
        return ("kept", id(value))
    return key_of(value)


_BRUSHES = ("fill", "stroke", "background")


# numbers as concrete classes: `isinstance` on an ABC (`numbers.Real`) is slow
_NUMBERS = (int, float, np.number)


def _same_number(value: object, held: object) -> bool:
    """Whether `value` is a number, or a tuple of numbers (a dash), equal to the one held: a
    change to it is none (an equal width of another type, or another object, keeps the
    paint)."""
    if isinstance(value, _NUMBERS):  # (as floats: a numpy scalar's == is a ufunc's)
        return isinstance(held, _NUMBERS) and float(value) == float(held)
    return (
        isinstance(value, tuple)
        and isinstance(held, tuple)
        and len(value) == len(held) > 0
        and isinstance(value[0], _NUMBERS)
        and all(map(_same_number, value, held))
    )


_SLOTS = {"fill": "_fill", "stroke": "_stroke", "background": "_background"}
_ARRAYS = ("_fill", "_stroke", "_background", "sheen_direction", "trim")
_NUMERIC = frozenset({"stroke_width", "background_width", "sheen_factor", "dash"})


class PaintAttribute[G, S = G]:
    """A CE style attribute of a mobject (`mob.joint_type`), kept in its paint's `field` (G: what
    is read, S: what may be set; the paint keeps arrays as float values)."""

    def __init__(self, field: str) -> None:
        self.field = field

    @overload
    def __get__(self, mob: None, owner: type) -> Self: ...
    @overload
    def __get__(self, mob: "Mobject", owner: type) -> G: ...
    def __get__(self, mob: "Mobject | None", owner: type) -> "G | Self":
        return self if mob is None else getattr(mob.paint, self.field)

    def __set__(self, mob: "Mobject", value: S) -> None:
        own = (
            frozen(np.array(cast("npt.ArrayLike", value), dtype=float, copy=True))
            if value is not None and (self.field in _SLOTS or self.field in _ARRAYS)
            else value
        )
        mob.paint = mob.paint.but(**{self.field: own})

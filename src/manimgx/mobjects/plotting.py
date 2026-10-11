# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"Coordinates, sampled functions, axes, planes and data drawn in those coordinates."

from __future__ import annotations

from warnings import deprecated

__all__ = [
    "Axes",
    "BarChart",
    "ComplexPlane",
    "FunctionGraph",
    "ImplicitFunction",
    "LinearBase",
    "LogBase",
    "NumberLine",
    "NumberPlane",
    "ParametricFunction",
    "PolarPlane",
    "SampleSpace",
    "ThreeDAxes",
    "UnitInterval",
]

import fractions as fr
import math
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Literal,
    Self,
    Unpack,
    cast,
    overload,
)

import numpy as np
import numpy.typing as npt
from isosurfaces import plot_isoline
from typing_extensions import TypedDict

from manimgx.config import config
from manimgx.constants import (
    DEFAULT_ARROW_TIP_LENGTH,
    DEFAULT_DOT_RADIUS,
    DEGREES,
    DL,
    DOWN,
    DR,
    LEFT,
    MED_SMALL_BUFF,
    ORIGIN,
    OUT,
    PI,
    RIGHT,
    SMALL_BUFF,
    TAU,
    UP,
    UR,
)
from manimgx.drawing.geometry import angle_of_vector, interpolate, normalize, sample
from manimgx.drawing.paint import (
    BLACK,
    BLUE,
    BLUE_D,
    DARK_GREY,
    GREEN,
    LIGHT_GREY,
    MAROON_B,
    PURE_YELLOW,
    WHITE,
    YELLOW,
    Colorscale,
    ManimColor,
    ParsableManimColor,
    Style,
    StyleBase,
    _Style,
    color_gradient,
    colors_by_value,
    invert_color,
    parse_colors,
)
from manimgx.mobject import Group, Mobject, VDict, VGroup, VMobject
from manimgx.mobjects.numbers import DecimalNumber, DecimalNumberOptions, Integer
from manimgx.mobjects.shapes import (
    ArrowTip,
    Circle,
    DashedLine,
    DashedLineOptions,
    Dot,
    Line,
    LineOptions,
    Polygon,
    Rectangle,
    RegularPolygon,
    Tipped,
    _Tipped,
)
from manimgx.mobjects.text import MathTex, MathTexOptions, Tex, Typst
from manimgx.typing import ManimTextLabel, Vector3D

if TYPE_CHECKING:
    from manimgx.typing import (
        ManimTextLabel,
        Point3D,
        Point3DLike,
        Point3DLike_Array,
        Vector3D,
        Vector3DLike,
    )


class _ScaleBase:
    """How numbers are laid along an axis: `function` maps a value to its position."""

    def __init__(self, custom_labels: bool = False):
        self.custom_labels = custom_labels

    @overload
    def function(self, value: float) -> float: ...
    @overload
    def function(self, value: np.ndarray) -> np.ndarray: ...
    def function(self, value: float | np.ndarray) -> float | np.ndarray:
        """The number of the axis at a value of its range: 10² for 2, on a logarithmic
        axis.

        Args:
            value: The value of the range; or an array of values.

        Returns:
            The number; or the numbers, an array of the same shape.
        """
        return self._function(value)

    @overload
    def inverse_function(self, value: float) -> float: ...
    @overload
    def inverse_function(self, value: np.ndarray) -> np.ndarray: ...
    def inverse_function(self, value: float | np.ndarray) -> float | np.ndarray:
        """The value of the axis's range at one of its numbers: 2 for 100, on a
        logarithmic axis; the inverse of `function`.

        Args:
            value: The number; or an array of numbers.

        Returns:
            The value of the range; or the values, an array of the same shape.
        """
        return self._inverse_function(value)

    # a scale's own map, of a float to a float and of an array to an array
    def _function(self, value: float | np.ndarray) -> float | np.ndarray:
        raise NotImplementedError

    def _inverse_function(self, value: float | np.ndarray) -> float | np.ndarray:
        raise NotImplementedError

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_custom_labels(
        self, val_range: Iterable[float], unit_decimal_places: int = 0
    ) -> list[Mobject]:
        """Make the labels of numbers, as the scale writes them (a scale with
        `custom_labels`).

        Args:
            val_range: The numbers.
            unit_decimal_places: The decimal places the labels are written with.

        Returns:
            A new label for each number, in order.
        """
        raise NotImplementedError  # a scale with `custom_labels` makes its own


class LinearBase(_ScaleBase):
    """An even scale for a number line: its numbers evenly spaced along it, the numbers
    of its range times `scale_factor`.

    It is a number line's default scale, and with a factor of 1 its numbers are those of
    its range. With another factor, the line keeps its length and its ticks, and its
    numbers are multiplied: with 2, a range `[-2, 2, 1]` is numbered from -4 to 4 in
    steps of 2, and [n2p][manimgx.NumberLine.n2p] places 4 at its end. Give it as a
    number line's `scaling`, or an axis's in an axis config.

    Args:
        scale_factor: The factor from the numbers of the range to the numbers of the
            line.

    Examples:
        ```python
        import manimgx as m


        class LinearBaseExample(m.Scene):
            def construct(self) -> None:
                plain = m.NumberLine(
                    x_range=[-3, 3, 1], length=10, include_numbers=True
                )
                doubled = m.NumberLine(
                    x_range=[-3, 3, 1],
                    length=10,
                    include_numbers=True,
                    scaling=m.LinearBase(scale_factor=2),
                    color=m.BLUE,
                )
                self.add(m.VGroup(plain, doubled).arrange(m.DOWN, buff=1.5))
        ```
    """

    def __init__(self, scale_factor: float = 1.0):
        super().__init__()
        self.scale_factor = scale_factor
        """The factor from the numbers of the range to the numbers of the line."""

    def _function(self, value: float | np.ndarray) -> float | np.ndarray:
        return self.scale_factor * value

    def _inverse_function(self, value: float | np.ndarray) -> float | np.ndarray:
        return value / self.scale_factor


class LogBase(_ScaleBase):
    """A logarithmic scale for a number line: its range is of exponents, and its
    numbers are powers of `base`, spaced by their logarithms.

    With base 10, a range `[0, 3, 1]` runs from 1 to 1000, a tick at each power of 10,
    and [n2p][manimgx.NumberLine.n2p] places 100 two thirds of the way along. Its
    numbers are all positive: 0 and negative numbers have no place on it. Give it as a
    number line's `scaling`, or an axis's in an axis config; then
    [plot][manimgx.Axes.plot] samples a function over the powers, and
    [add_coordinates][manimgx.Axes.add_coordinates] writes the axis's
    numbers as powers.

    Args:
        base: The base of the powers.
        custom_labels: Whether the line's numbers are written as powers (10², 10³, …),
            rather than as decimals.

    Examples:
        ```python
        import manimgx as m


        class LogBaseExample(m.Scene):
            def construct(self) -> None:
                ax = m.Axes(
                    x_range=[0, 10, 1],
                    y_range=[-2, 6, 1],
                    x_length=11,
                    y_length=6.5,
                    tips=False,
                    axis_config={"include_numbers": True, "font_size": 28},
                    y_axis_config={"scaling": m.LogBase()},
                )
                exponential = ax.plot(lambda x: 0.01 * 10 ** (0.8 * x), color=m.BLUE)
                square = ax.plot(lambda x: x**2, x_range=[0.1, 10], color=m.YELLOW)
                self.add(ax, exponential, square)
        ```
    """

    def __init__(self, base: float = 10, custom_labels: bool = True):
        super().__init__()
        self.base = base
        """The base of the powers."""
        self.custom_labels = custom_labels
        """Whether the line's numbers are written as powers of the base."""

    def _function(self, value: float | np.ndarray) -> float | np.ndarray:
        if isinstance(value, np.ndarray):
            return np.power(self.base, value)
        return float(self.base**value)

    def _inverse_function(self, value: float | np.ndarray) -> float | np.ndarray:
        if np.any(np.asarray(value) <= 0):
            raise ValueError(
                "log(0) is undefined. Make sure the value is in the domain of the"
                " function"
            )
        if isinstance(value, np.ndarray):
            return np.log(value) / np.log(self.base)
        return math.log(value, self.base)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_custom_labels(
        self,
        val_range: Iterable[float],
        unit_decimal_places: int = 0,
        **base_config: Unpack[DecimalNumberOptions],
    ) -> list[Mobject]:
        """Make the labels of numbers, written as powers of the base: 100 as 10².

        A number line with `custom_labels` numbers its ticks with these.

        Args:
            val_range: The numbers, all positive.
            unit_decimal_places: The decimal places the exponents are written with.
            **base_config: [Number keywords][manimgx.DecimalNumber]
                for the labels: each is an [Integer][manimgx.Integer], the base, with
                its exponent as its `unit`.

        Returns:
            A new label for each number, in order, not placed.
        """
        return [
            Integer(
                self.base,
                **(
                    base_config
                    | {
                        "unit": (
                            f"^{{{self.inverse_function(i):.{unit_decimal_places}f}}}"
                        )
                    }
                ),
            )
            for i in val_range
        ]


_CURVE_LINEAR = LinearBase()  # a default (never changed)


class _CurveOptions(_Style, total=False):
    """CurveOptions's keys, open, for the keywords that add to them."""

    dt: float
    """How far short of each discontinuity the curve's pieces stop, in units of its
    parameter (default 1e-8)."""
    discontinuities: Iterable[float] | None
    """The values of the parameter where the curve breaks: it is drawn in pieces
    between them (default None: none)."""
    use_smoothing: bool
    """Whether the samples are joined by a smooth curve through them, rather than by
    straight segments (default True)."""


class CurveOptions(_CurveOptions, total=False, closed=True):
    """How a curve is sampled and smoothed, with the style keywords: the keywords of
    [plot][manimgx.Axes.plot] and the other curves, for the methods that
    pass them on."""


class ParametricOptions(_CurveOptions, total=False):
    """A [ParametricFunction][manimgx.ParametricFunction]'s keywords but its function:
    its parameter's range and spacing, with the curve keywords."""

    t_range: Sequence[float]
    """The parameter's range, `[t_min, t_max]` or `[t_min, t_max, t_step]`: the
    function is sampled every `t_step`, 0.01 if not given (default [0, 1])."""
    scaling: _ScaleBase
    """How the parameter is spaced over its range: evenly, with
    [LinearBase][manimgx.LinearBase]; with [LogBase][manimgx.LogBase], the range is of
    exponents, and the parameter runs over powers (default `LinearBase()`)."""
    use_vectorized: bool
    """Whether the function takes all the values of the parameter at once, as an
    array, and returns the arrays of x, y and z (default False)."""


class ParametricFunction(VMobject):
    """A parametric curve: the points `function(t)` for t from `t_min` to `t_max`,
    joined smoothly; white unless styled.

    The function is sampled every `t_step`, and at `t_max`, and the samples are joined
    by a smooth curve through them (or by straight segments, without
    `use_smoothing`). Where the function jumps, give its `discontinuities`: the curve
    is drawn in pieces between them, each stopping `dt` short. Unless
    `use_vectorized`, the function is first tried on all the values of t at once, as
    an array, and checked against single calls; a function that does not take arrays
    is called once per value.

    The discontinuities are kept as the list they were when the curve was made, before
    range filtering, so copies and regenerated curves keep all its breaks.

    To graph a function on axes, in their coordinates, see [plot][manimgx.Axes.plot].

    Args:
        function: The function, from t to a point in scene coordinates: its x, y and z.
        t_range: The range of t, `[t_min, t_max]` or `[t_min, t_max, t_step]`; the
            step is 0.01 if not given.
        scaling: How t is spaced over its range: evenly, with
            [LinearBase][manimgx.LinearBase]; with [LogBase][manimgx.LogBase], the
            range is of exponents, and t runs over powers.
        dt: How far short of each discontinuity the pieces stop, in units of t.
        discontinuities: The values of t where the curve breaks; None for none.
        use_smoothing: Whether the samples are joined by a smooth curve through them,
            rather than by straight segments.
        use_vectorized: Whether `function` takes all the values of t at once, as an
            array, and returns the arrays of x, y and z (a z that is not an array is
            taken as 0).

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ParametricFunctionExample(m.Scene):
            def construct(self) -> None:
                lissajous = m.ParametricFunction(
                    lambda t: np.array([2.5 * np.sin(2 * t), 2.5 * np.sin(3 * t), 0]),
                    t_range=[0, m.TAU],
                    color=m.BLUE,
                )
                spiral = m.ParametricFunction(
                    lambda t: np.array([0.15 * t * np.cos(t), 0.15 * t * np.sin(t), 0]),
                    t_range=[0, 3 * m.TAU],
                    color=m.YELLOW,
                )
                curves = m.VGroup(lissajous, spiral).arrange(buff=1.5)
                self.play(m.Create(curves), run_time=3)
        ```
    """

    underlying_function: Callable[[float], float] | None = None
    """The function y = f(x) the curve is the graph of, if it is one:
    [plot][manimgx.Axes.plot] and [FunctionGraph][manimgx.FunctionGraph]
    set it. None for other curves."""

    def __init__(
        self,
        function: Callable[[float], Point3DLike],
        t_range: Sequence[float] | np.ndarray = (0, 1),
        scaling: _ScaleBase = _CURVE_LINEAR,
        dt: float = 1e-08,
        discontinuities: Iterable[float] | None = None,
        use_smoothing: bool = True,
        use_vectorized: bool = False,
        **kwargs: Unpack[Style],
    ):

        def internal_parametric_function(t: float) -> Point3D:
            return np.asarray(function(t))

        self.function = internal_parametric_function
        """The curve's function: from t to its point, as an array."""
        if len(t_range) == 2:
            t_range = (*t_range, 0.01)
        self.scaling = scaling
        self.dt = dt
        self.discontinuities = (
            None if discontinuities is None else list(discontinuities)
        )
        self.use_smoothing = use_smoothing
        self.use_vectorized = use_vectorized
        self.t_min, self.t_max, self.t_step = t_range
        super().__init__(**kwargs)

    def get_function(self) -> Callable[[float], Point3D]:
        """The curve's function: from t to its point.

        Returns:
            The function, which returns an array.
        """
        return self.function

    def get_point_from_function(self, t: float, /) -> Point3D:
        """The curve's point at a value of t, from its function: past `t_range` too.

        Args:
            t: The value of t.

        Returns:
            The point, in scene coordinates.
        """
        return self.function(t)

    def generate_points(self) -> Self:
        if self.discontinuities is not None:
            values = self.discontinuities
            discontinuities = filter(lambda t: self.t_min <= t <= self.t_max, values)
            discontinuities_array = np.array(list(discontinuities))
            boundary_times = np.array(
                [
                    self.t_min,
                    self.t_max,
                    *discontinuities_array - self.dt,
                    *discontinuities_array + self.dt,
                ]
            )
            boundary_times.sort()
        else:
            boundary_times = [self.t_min, self.t_max]
        for t1, t2 in zip(boundary_times[0::2], boundary_times[1::2], strict=True):
            t_range = np.array(
                [
                    *self.scaling.function(np.arange(t1, t2, self.t_step)),
                    self.scaling.function(t2),
                ]
            )
            if self.use_vectorized:  # the function takes all the parameters at once
                x, y, z = cast(
                    "Callable[[np.ndarray], Sequence[np.ndarray]]", self.function
                )(t_range)
                if not isinstance(z, np.ndarray):
                    z = np.zeros_like(x)
                points = np.stack([x, y, z], axis=1)
            else:
                points = sample(self.function, t_range)
            self.start_new_path(points[0])
            self.add_points_as_corners(points[1:])
        if self.use_smoothing:
            self.make_smooth()
        return self


class FunctionGraph(ParametricFunction):
    """The graph of a function y = f(x), in scene coordinates: the points (x, f(x), 0),
    joined smoothly; bright yellow (`PURE_YELLOW`) unless styled.

    The sampler may call the function with arrays and individual values, falling
    back to scalar evaluation when needed. The number of callback calls is not
    guaranteed.

    To graph a function on axes, in their coordinates, see
    [plot][manimgx.Axes.plot].

    Args:
        function: The function, from x to y.
        x_range: The range of x, `[x_min, x_max]` or `[x_min, x_max, x_step]`; the
            step is 0.01 if not given. None for the frame's width.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class FunctionGraphExample(m.Scene):
            def construct(self) -> None:
                wave = m.FunctionGraph(
                    lambda x: np.sin(x) + 0.5 * np.sin(7 * x) + np.sin(14 * x) / 7,
                    color=m.BLUE,
                )
                bell = m.FunctionGraph(
                    lambda x: 3 * np.exp(-(x**2)), x_range=[-4, 4], color=m.YELLOW
                )
                self.play(m.Create(wave), m.Create(bell), run_time=2)
        ```
    """

    defaults: ClassVar[Style] = {"color": PURE_YELLOW}

    def __init__(
        self,
        function: Callable[[float], float],
        x_range: Sequence[float] | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        if x_range is None:
            x_range = (-config.frame_x_radius, config.frame_x_radius)
        self.x_range = x_range
        """The range of x the graph spans, `[x_min, x_max]` or `[x_min, x_max,
        x_step]`."""
        self.parametric_function: Callable[[float], Point3D] = lambda t: np.array(
            np.broadcast_arrays(t, function(t), 0)
            if isinstance(t, np.ndarray)
            else [t, function(t), 0]
        )
        """The graph's point function: from x to the point (x, f(x), 0)."""
        super().__init__(self.parametric_function, self.x_range, **kwargs)
        self.underlying_function = function

    def get_point_from_function(self, x: float, /) -> Point3D:
        return self.parametric_function(x)


class ImplicitOptions(_Style, total=False, closed=True):
    """An [ImplicitFunction][manimgx.ImplicitFunction]'s smoothing, with the style
    keywords, for the methods that pass them on
    ([plot_implicit_curve][manimgx.Axes.plot_implicit_curve])."""

    use_smoothing: bool
    """Whether the curve is smoothed through its points, rather than drawn in straight
    segments (default True)."""


class ImplicitFunction(VMobject):
    """The curve where a function of x and y is zero, `func(x, y) = 0`, in scene
    coordinates, found within a rectangle; white unless styled.

    The rectangle is divided in four, and each part in four again, finer where the
    curve passes, and the curve is traced through the cells: one path for each of its
    pieces. To plot on axes, in their coordinates, see
    [plot_implicit_curve][manimgx.Axes.plot_implicit_curve].

    Args:
        func: The function of x and y, in scene coordinates.
        x_range: The range of x to look in, `[x_min, x_max]`; None for the frame's
            width.
        y_range: The range of y to look in, `[y_min, y_max]`; None for the frame's
            height.
        min_depth: How many times the rectangle is at least divided in four: more
            finds smaller pieces of the curve.
        max_quads: The most cells the rectangle may be divided into: more follow the
            curve more closely, and take longer.
        use_smoothing: Whether the curve is smoothed through its points, rather than
            drawn in straight segments.

    Examples:
        ```python
        import manimgx as m


        class ImplicitFunctionExample(m.Scene):
            def construct(self) -> None:
                cubic = m.ImplicitFunction(
                    lambda x, y: x * y**2 - x**2 * y - 2, color=m.YELLOW
                )
                heart = m.ImplicitFunction(
                    lambda x, y: (x**2 + y**2 - 1) ** 3 - x**2 * y**3,
                    x_range=[-1.5, 1.5],
                    y_range=[-1.5, 1.5],
                    color=m.RED,
                ).scale(1.5)
                self.add(m.NumberPlane(), cubic, heart)
        ```
    """

    def __init__(
        self,
        func: Callable[[float, float], float],
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        min_depth: int = 5,
        max_quads: int = 1500,
        use_smoothing: bool = True,
        **kwargs: Unpack[Style],
    ):
        self.function = func
        """The function whose zeros the curve is."""
        self.min_depth = min_depth
        self.max_quads = max_quads
        self.use_smoothing = use_smoothing
        self.x_range = x_range or [-config.frame_width / 2, config.frame_width / 2]
        self.y_range = y_range or [-config.frame_height / 2, config.frame_height / 2]
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        p_min, p_max = (
            np.array([self.x_range[0], self.y_range[0]]),
            np.array([self.x_range[1], self.y_range[1]]),
        )
        curves = plot_isoline(
            fn=lambda u: self.function(u[0], u[1]),
            pmin=p_min,
            pmax=p_max,
            min_depth=self.min_depth,
            max_quads=self.max_quads,
        )
        curves = [np.pad(curve, [(0, 0), (0, 1)]) for curve in curves if curve != []]
        for curve in curves:
            self.start_new_path(curve[0])
            self.add_points_as_corners(curve[1:])
        if self.use_smoothing:
            self.make_smooth()
        return self


type Label = float | str | Mobject


"""A label: a mobject, used as it is, or a number or a string, typeset (as math, by
default)."""


_AXIS_LINEAR = LinearBase()  # a default (never changed)


class NumberLineOptions(_Tipped, total=False, closed=True):
    """A [NumberLine][manimgx.NumberLine]'s keywords but its range, for the configs that
    pass them on (a coordinate system's axes): its size, ticks, tip and numbers, with
    the style and tip keywords."""

    length: float | None
    """The line's length, in scene units (default None: `unit_size` per unit)."""
    unit_size: float
    """The length of one unit, in scene units, when `length` is not given (default
    1)."""
    include_ticks: bool
    """Whether to draw the ticks (default True)."""
    tick_size: float
    """How far each tick reaches on either side of the line, in scene units: half its
    length (default 0.1)."""
    numbers_with_elongated_ticks: Iterable[float] | None
    """The numbers whose ticks are longer (default None: none)."""
    longer_tick_multiple: int
    """How many times longer those ticks are (default 2)."""
    exclude_origin_tick: bool
    """Whether to leave out the tick at 0 (default False; an axis of
    [Axes][manimgx.Axes] leaves it out, when linear, for the other axis crosses
    there)."""
    rotation: float
    """The angle the line is turned through about its center, in radians,
    counterclockwise (default 0; a y-axis's is a quarter turn)."""
    include_tip: bool
    """Whether the line ends in an arrow tip, at its end (default False; an axis's
    does, unless `tips=False`)."""
    tip_width: float
    """The tip's width, in scene units (default 0.35)."""
    tip_height: float
    """The tip's length, along the line, in scene units (default 0.35)."""
    tip_shape: type[ArrowTip] | None
    """The class of the tip (default None:
    [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip])."""
    include_numbers: bool
    """Whether to number the ticks (default False)."""
    font_size: float
    """The numbers' font size (default 36)."""
    label_direction: Vector3DLike
    """The side of the line the numbers go on, as a direction (default DOWN: below; a
    y-axis's are on its left)."""
    label_constructor: type[ManimTextLabel]
    """The class the numbers and labels are typeset with (default
    [MathTex][manimgx.MathTex])."""
    scaling: _ScaleBase
    """How numbers are spaced along the line: evenly, with
    [LinearBase][manimgx.LinearBase], or by their logarithms, with
    [LogBase][manimgx.LogBase] (default `LinearBase()`)."""
    line_to_number_buff: float
    """The gap between the line and its numbers, in scene units (default 0.25)."""
    decimal_number_config: DecimalNumberOptions | None
    """[Number keywords][manimgx.DecimalNumber] for the
    numbers (default None: as many decimal places as the range's step has)."""
    numbers_to_exclude: Iterable[float] | None
    """Numbers not to write, when the ticks are numbered (default None: none; an
    axis's leave out 0)."""
    numbers_to_include: Iterable[float] | None
    """The numbers to write, instead of the ticks': given, they are written even
    without `include_numbers` (default None: the ticks')."""


class NumberLine(Line):
    """A number line: a line with ticks at every step of its range, numbers if asked
    for, and a map between numbers and points; white, with a stroke 2 wide, unless
    styled.

    Its range, `[x_min, x_max, x_step]`, runs from its left end to its right end: the
    line is `length` long, in scene units, or `unit_size` per unit, and it is centered
    on the scene's origin (then turned through `rotation`). Its ticks are `x_step`
    apart, counted from 0 when the range contains it (from `x_min` otherwise); a tip at
    its end takes the place of the last tick.
    [number_to_point][manimgx.NumberLine.number_to_point] and
    [point_to_number][manimgx.NumberLine.point_to_number] convert between numbers and
    points; [add_numbers][manimgx.NumberLine.add_numbers] and
    [add_labels][manimgx.NumberLine.add_labels] write on it. A `scaling` spaces the
    numbers otherwise: with [LogBase][manimgx.LogBase], the range is of exponents, and
    the line's numbers are powers.

    Initial length, rotation, tip dimensions and which ticks/numbers to draw are
    construction inputs, not retained attributes. The line keeps its drawing and
    the defaults used by later tick and label methods; the numbers to exclude and
    those with elongated ticks are kept as the lists they were when it was made.

    Args:
        x_range: The range, `[x_min, x_max, x_step]`, or `[x_min, x_max]` for a step of
            1; None for [-7, 7, 1].
        length: The line's length, in scene units; None for `unit_size` per unit.
        unit_size: The length of one unit, in scene units, when `length` is None.
        include_ticks: Whether to draw the ticks.
        tick_size: How far each tick reaches on either side of the line, in scene
            units: half its length.
        numbers_with_elongated_ticks: The numbers whose ticks are longer; None for
            none.
        longer_tick_multiple: How many times longer those ticks are.
        exclude_origin_tick: Whether to leave out the tick at 0.
        rotation: The angle the line is turned through about its center, in radians,
            counterclockwise.
        include_tip: Whether the line ends in an arrow tip, at its end.
        tip_width: The tip's width, in scene units.
        tip_height: The tip's length, along the line, in scene units.
        tip_shape: The class of the tip; None for
            [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip].
        include_numbers: Whether to number the ticks (see
            [add_numbers][manimgx.NumberLine.add_numbers]).
        font_size: The numbers' font size.
        label_direction: The side of the line the numbers go on, as a direction: DOWN
            for below.
        label_constructor: The class the numbers and labels are typeset with:
            [MathTex][manimgx.MathTex], [MathTypst][manimgx.MathTypst], ….
        scaling: How numbers are spaced along the line: evenly, with
            [LinearBase][manimgx.LinearBase], or by their logarithms, with
            [LogBase][manimgx.LogBase] (its numbers are then written as powers).
        line_to_number_buff: The gap between the line and its numbers, in scene units.
        decimal_number_config: The numbers'
            [number keywords][manimgx.DecimalNumber]; None
            for as many decimal places as `x_step` has.
        numbers_to_exclude: Numbers not to write, when the ticks are numbered; None
            for none.
        numbers_to_include: The numbers to write, instead of the ticks': given, they
            are written even without `include_numbers`. None for the ticks'.

    Examples:
        ```python
        import manimgx as m


        class NumberLineExample(m.Scene):
            def construct(self) -> None:
                lines = m.VGroup(
                    m.NumberLine(x_range=[-5, 5, 1], length=12, include_numbers=True),
                    m.NumberLine(
                        x_range=[0, 2, 0.25],
                        length=12,
                        include_numbers=True,
                        font_size=28,
                        color=m.BLUE,
                    ),
                    m.NumberLine(
                        x_range=[-10, 10, 2],
                        length=12,
                        numbers_with_elongated_ticks=[-10, 0, 10],
                        include_tip=True,
                        include_numbers=True,
                        label_direction=m.UP,
                        color=m.YELLOW,
                    ),
                ).arrange(m.DOWN, buff=1)
                self.add(lines)
        ```
    """

    defaults: ClassVar[Style] = {"stroke_width": 2.0}

    def __init__(
        self,
        x_range: Sequence[float] | None = None,
        length: float | None = None,
        unit_size: float = 1,
        include_ticks: bool = True,
        tick_size: float = 0.1,
        numbers_with_elongated_ticks: Iterable[float] | None = None,
        longer_tick_multiple: int = 2,
        exclude_origin_tick: bool = False,
        rotation: float = 0,
        include_tip: bool = False,
        tip_width: float = DEFAULT_ARROW_TIP_LENGTH,
        tip_height: float = DEFAULT_ARROW_TIP_LENGTH,
        tip_shape: type[ArrowTip] | None = None,
        include_numbers: bool = False,
        font_size: float = 36,
        label_direction: Vector3DLike = DOWN,
        label_constructor: type[ManimTextLabel] = MathTex,
        scaling: _ScaleBase = _AXIS_LINEAR,
        line_to_number_buff: float = MED_SMALL_BUFF,
        decimal_number_config: DecimalNumberOptions | None = None,
        numbers_to_exclude: Iterable[float] | None = None,
        numbers_to_include: Iterable[float] | None = None,
        **kwargs: Unpack[Tipped],
    ):
        # values, as they are given: what the line keeps is its own
        numbers_to_exclude = (
            [] if numbers_to_exclude is None else list(numbers_to_exclude)
        )
        numbers_with_elongated_ticks = (
            []
            if numbers_with_elongated_ticks is None
            else list(numbers_with_elongated_ticks)
        )
        if x_range is None:
            x_range = [
                round(-config.frame_x_radius),
                round(config.frame_x_radius),
                1,
            ]
        elif len(x_range) == 2:
            x_range = [*x_range, 1]
        if decimal_number_config is None:
            decimal_number_config = {
                "num_decimal_places": self._decimal_places_from_step(x_range[2])
            }
        self.x_range = np.array(x_range, dtype=float)
        """The line's range, `[x_min, x_max, x_step]`, as given: of exponents, on a
        logarithmic line."""
        self.x_min: float
        """The line's number at its start: the first of its range, scaled (10⁰ = 1 for
        a range from 0, on a logarithmic line)."""
        self.x_max: float
        """The line's number at its end: the second of its range, scaled."""
        self.x_step: float
        """The step of its range, scaled."""
        self.x_min, self.x_max, self.x_step = scaling.function(self.x_range)
        self.unit_size = unit_size
        """The length of one unit, in scene units, as the line was made; see
        [get_unit_size][manimgx.NumberLine.get_unit_size] for its length now."""
        self.tick_size = tick_size
        self.numbers_with_elongated_ticks = numbers_with_elongated_ticks
        self.longer_tick_multiple = longer_tick_multiple
        self.exclude_origin_tick = exclude_origin_tick
        self.include_tip = include_tip
        self.font_size = font_size
        self.label_direction = label_direction
        self.label_constructor = label_constructor
        self.line_to_number_buff = line_to_number_buff
        self.decimal_number_config = decimal_number_config
        self.numbers_to_exclude = numbers_to_exclude
        self.scaling = scaling
        """How the line's numbers are spaced along it."""
        super().__init__(self.x_range[0] * RIGHT, self.x_range[1] * RIGHT, **kwargs)
        if length:
            self.set_length(length)
            self.unit_size = self.get_unit_size()
        else:
            self.scale(self.unit_size)
        self.center()
        if self.include_tip:
            self.add_tip(
                tip_length=tip_height,
                tip_width=tip_width,
                tip_shape=tip_shape,
            )
            self.tip.set_stroke(self.stroke_color, self.stroke_width)
        if include_ticks:
            self.add_ticks()
        self.rotate(rotation)
        if include_numbers or numbers_to_include is not None:
            if self.scaling.custom_labels:
                tick_range = self.get_tick_range()
                custom_labels = self.scaling.get_custom_labels(
                    tick_range,
                    unit_decimal_places=decimal_number_config.get(
                        "num_decimal_places", 0
                    ),
                )
                self.add_labels(dict(zip(tick_range, custom_labels, strict=True)))
            else:
                self.add_numbers(
                    x_values=numbers_to_include, excluding=self.numbers_to_exclude
                )

    def rotate_about_zero(self, angle: float, axis: Vector3DLike = OUT) -> Self:
        """Turn the line about the point of its number 0.

        Args:
            angle: The angle, in radians, counterclockwise about `axis`.
            axis: The axis of the turn: OUT turns it in the plane of the screen.
        """
        return self.rotate_about_number(0, angle, axis)

    def rotate_about_number(
        self, number: float, angle: float, axis: Vector3DLike = OUT
    ) -> Self:
        """Turn the line about the point of one of its numbers.

        Args:
            number: The number whose point stays fixed.
            angle: The angle, in radians, counterclockwise about `axis`.
            axis: The axis of the turn: OUT turns it in the plane of the screen.
        """
        return self.rotate(angle, axis, about_point=self.n2p(number))

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def add_ticks(self) -> Self:
        """Add the line's ticks: one at each number of its
        [tick range][manimgx.NumberLine.get_tick_range], across the line, those of
        `numbers_with_elongated_ticks` longer.

        The constructor calls it, unless `include_ticks` is False. The ticks are a group
        added to the line, and kept as its `ticks`.
        """
        ticks = VGroup()
        elongated_tick_size = self.tick_size * self.longer_tick_multiple
        elongated_tick_offsets = (
            np.array(self.numbers_with_elongated_ticks) - self.x_min
        )
        for x in self.get_tick_range():
            size = self.tick_size
            if np.any(np.isclose(x - self.x_min, elongated_tick_offsets)):
                size = elongated_tick_size
            ticks.add(self.get_tick(x, size))
        self.add(ticks)
        self.ticks = ticks
        return self

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def get_tick(self, x: float, size: float | None = None) -> Line:
        """Make a tick for a number: a short line across the number line at the
        number's point, in the line's style.

        Args:
            x: The number.
            size: How far the tick reaches on either side of the line, in scene units;
                None for the line's `tick_size`.

        Returns:
            A new line, not added to the number line.
        """
        if size is None:
            size = self.tick_size
        result = Line(size * DOWN, size * UP)
        result.rotate(self.get_angle())
        result.move_to(self.number_to_point(x))
        result.match_style(self)
        return result

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def get_tick_range(self) -> np.ndarray:
        """The numbers the line's ticks are at.

        They are `x_step` apart, counted from 0 outward when the range contains it
        (from `x_min` otherwise), up to `x_max` included — excluded if the line has a
        tip — and without 0 if `exclude_origin_tick`. On a scaled line they are the
        numbers themselves: powers, on a logarithmic one.

        Returns:
            An array of the numbers, in increasing order.
        """
        x_min, x_max, x_step = self.x_range
        if not self.include_tip:
            x_max += 1e-06
        if x_min < x_max < 0 or x_max > x_min > 0:
            tick_range = np.arange(x_min, x_max, x_step)
        else:
            start_point = 0
            if self.exclude_origin_tick:
                start_point += x_step
            x_min_segment = np.arange(start_point, np.abs(x_min) + 1e-06, x_step) * -1
            x_max_segment = np.arange(start_point, x_max, x_step)
            tick_range = np.unique(np.concatenate((x_min_segment, x_max_segment)))
        return self.scaling.function(tick_range)

    def number_to_point(self, number: float | np.ndarray) -> np.ndarray:
        """Convert a number to its point on the line, or numbers to their points.

        A number outside the range is on the line extended past its ends.

        Args:
            number: The number; or an array of numbers, of any shape.

        Returns:
            The point, in scene coordinates; for an array, the points, with the
            coordinates last (the array's shape, then 3).

        Examples:
            ```python
            import manimgx as m


            class NumberLineNumberToPointExample(m.Scene):
                def construct(self) -> None:
                    line = m.NumberLine(
                        x_range=[-4, 4, 1], length=12, include_numbers=True
                    )
                    dot = m.Dot(line.n2p(-3), radius=0.15, color=m.YELLOW)
                    self.add(line, dot)
                    self.play(dot.animate.move_to(line.n2p(2.5)))
            ```
        """
        number = self.scaling.inverse_function(np.asarray(number, dtype=float))
        alphas = (number - self.x_range[0]) / (self.x_range[1] - self.x_range[0])
        start, end = self.get_start(), self.get_end()
        a = np.asarray(alphas)[..., None]
        return (1 - a) * start + a * end

    def point_to_number(self, point: Point3DLike) -> float:
        """Convert a point to the number at its projection on the line: the inverse of
        [number_to_point][manimgx.NumberLine.number_to_point] for points on the line.

        Args:
            point: The point, in scene coordinates.
        """
        point = np.asarray(point, dtype=float)
        start, end = self.get_start(), self.get_end()
        unit_vect = normalize(end - start)
        proportion: float = np.dot(point - start, unit_vect) / np.dot(
            end - start, unit_vect
        )
        # along the range, then through the scale, as number_to_point goes back
        return self.scaling.function(
            interpolate(self.x_range[0], self.x_range[1], proportion)
        )

    def n2p(self, number: float | np.ndarray) -> Point3D:
        """Convert a number to its point on the line:
        [number_to_point][manimgx.NumberLine.number_to_point], by a shorter name.

        Args:
            number: The number; or an array of numbers, of any shape.

        Returns:
            The point, in scene coordinates; or the points.
        """
        return self.number_to_point(number)

    def get_unit_size(self) -> float:
        """The length of one unit of the line: its length over its range.

        Returns:
            The length, in scene units (of one unit of exponent, on a logarithmic
            line).
        """
        val: float = self.get_length() / (self.x_range[1] - self.x_range[0])
        return val

    def get_unit_vector(self) -> Vector3D:
        """The line's direction, one unit long: the vector from its start toward its
        end, as long as the unit the line was made with (its `unit_size`).

        Returns:
            The vector, in scene units.
        """
        return super().get_unit_vector() * self.unit_size

    def get_number_mobject(
        self,
        x: float,
        direction: Vector3DLike | None = None,
        buff: float | None = None,
        label_constructor: type[ManimTextLabel] | None = None,
        **number_config: Unpack[DecimalNumberOptions],
    ) -> VMobject:
        """Make a number, written beside its point on the line.

        It is a [DecimalNumber][manimgx.DecimalNumber] in the line's number style (its
        `decimal_number_config` and `font_size`), with `number_config` over it. A
        negative number written straight below or above the line is shifted so its
        digits, not its minus sign, are centered on the point.

        Args:
            x: The number.
            direction: The side of the line it goes on; None for the line's
                `label_direction`.
            buff: The gap between the line and the number, in scene units; None for the
                line's `line_to_number_buff`.
            label_constructor: The class it is typeset with; None for the line's.
            **number_config: [Number keywords][manimgx.DecimalNumber],
                over the line's.

        Returns:
            A new number, not added to the line.
        """
        options = self.decimal_number_config | number_config
        options.setdefault("font_size", self.font_size)
        options["mob_class"] = label_constructor or self.label_constructor
        num_mob = DecimalNumber(x, **options)
        num_mob.next_to(
            self.number_to_point(x),
            direction=self.label_direction if direction is None else direction,
            buff=self.line_to_number_buff if buff is None else buff,
        )
        if x < 0 and self.label_direction[0] == 0:
            num_mob.shift(num_mob[0].width * LEFT / 2)
        return num_mob

    def add_numbers(
        self,
        x_values: Iterable[float] | None = None,
        excluding: Iterable[float] | None = None,
        label_constructor: type[ManimTextLabel] | None = None,
        **kwargs: Unpack[DecimalNumberOptions],
    ) -> Self:
        """Number the line: write numbers beside the points of the given values, or of
        its ticks.

        Each number is written as
        [get_number_mobject][manimgx.NumberLine.get_number_mobject] writes it. The
        numbers are a group added to the line, and kept as its `numbers`.

        Args:
            x_values: The numbers to write; None for the ticks' numbers.
            excluding: Numbers not to write; None for the line's `numbers_to_exclude`.
            label_constructor: The class they are typeset with; None for the line's.
            **kwargs: [Number keywords][manimgx.DecimalNumber],
                over the line's: `font_size`, `num_decimal_places`, `color`, ….

        Examples:
            ```python
            import manimgx as m


            class NumberLineAddNumbersExample(m.Scene):
                def construct(self) -> None:
                    ticks = m.NumberLine(x_range=[0, 10, 1], length=12).add_numbers()
                    chosen = m.NumberLine(x_range=[0, 10, 1], length=12, color=m.BLUE)
                    chosen.add_numbers(
                        [0, 2.5, 5, 7.5, 10], num_decimal_places=1, color=m.BLUE
                    )
                    self.add(m.VGroup(ticks, chosen).arrange(m.DOWN, buff=1.5))
            ```
        """
        if x_values is None:
            x_values = self.get_tick_range()
        excluded = list(self.numbers_to_exclude if excluding is None else excluding)
        numbers = VGroup()
        for x in x_values:
            if x in excluded:
                continue
            numbers.add(
                self.get_number_mobject(
                    x, label_constructor=label_constructor, **kwargs
                )
            )
        self.add(numbers)
        self.numbers = numbers
        return self

    def add_labels(
        self,
        dict_values: Mapping[float, Label],
        direction: Point3DLike | None = None,
        buff: float | None = None,
        font_size: float | None = None,
        label_constructor: type[ManimTextLabel] | None = None,
    ) -> Self:
        r"""Label the line: put each label beside the point of its number.

        A string is typeset as text with [Tex][manimgx.Tex] when the constructor is
        [MathTex][manimgx.MathTex] (as by default), and with the constructor otherwise;
        a number is written with the constructor. A mobject is used as it is, and must
        be typeset (a [Typst][manimgx.Typst] mobject: [Text][manimgx.Text],
        [Tex][manimgx.Tex], [MathTex][manimgx.MathTex], …) or a
        [DecimalNumber][manimgx.DecimalNumber]: another raises an exception. Every label
        is set to `font_size`. The labels are a group added to the line, and kept as its
        `labels`.

        Args:
            dict_values: The labels, by number.
            direction: The side of the line they go on, as a direction; None for the
                line's `label_direction`.
            buff: The gap between the line and the labels, in scene units; None for the
                line's `line_to_number_buff`.
            font_size: The labels' font size; None for the line's.
            label_constructor: The class strings and numbers are typeset with; None for
                the line's.

        Examples:
            ```python
            import manimgx as m


            class NumberLineAddLabelsExample(m.Scene):
                def construct(self) -> None:
                    line = m.NumberLine(x_range=[0, m.TAU, m.PI / 2], length=12)
                    line.add_labels(
                        {
                            0: "0",
                            m.PI / 2: m.MathTex(r"\frac{\pi}{2}"),
                            m.PI: m.MathTex(r"\pi"),
                            3 * m.PI / 2: m.MathTex(r"\frac{3\pi}{2}"),
                            m.TAU: m.MathTex(r"2\pi"),
                        },
                        font_size=44,
                    )
                    self.add(line)
            ```
        """
        direction = self.label_direction if direction is None else direction
        buff = self.line_to_number_buff if buff is None else buff
        font_size = self.font_size if font_size is None else font_size
        if label_constructor is None:
            label_constructor = self.label_constructor
        labels = VGroup()
        for x, label in dict_values.items():
            if isinstance(label, str):
                if label_constructor is MathTex:
                    label = Tex(label)
                else:
                    label = self._create_label_tex(label, label_constructor)
            else:
                label = self._create_label_tex(label, label_constructor)
            if not isinstance(
                label, (Typst, DecimalNumber)
            ):  # its type size can be set
                raise AttributeError(f"{label} is not compatible with add_labels.")
            label.font_size = font_size
            label.next_to(self.number_to_point(x), direction=direction, buff=buff)
            labels.add(label)
        self.labels = labels
        self.add(labels)
        return self

    def _create_label_tex(
        self,
        label_tex: Label,
        label_constructor: type[ManimTextLabel] | None = None,
        **kwargs: Unpack[Style],
    ) -> Mobject:
        if isinstance(label_tex, Mobject):
            return label_tex
        if label_constructor is None:
            label_constructor = self.label_constructor
        if isinstance(label_tex, str):
            return label_constructor(label_tex, **kwargs)
        return label_constructor(str(label_tex), **kwargs)

    @staticmethod
    def _decimal_places_from_step(step: float) -> int:
        step_str = str(step)
        if "." not in step_str:
            return 0
        return len(step_str.split(".")[-1])


class UnitInterval(NumberLine):
    """The unit interval: a number line from 0 to 1, with a tick every tenth; 10 units
    long, its ticks at 0 and 1 longer, unless told otherwise.

    Its numbers, when it has them, have one decimal place.

    Args:
        **kwargs: [Number line keywords][manimgx.NumberLine]:
            its range is always `[0, 1, 0.1]`, and its `unit_size`,
            `numbers_with_elongated_ticks` and `decimal_number_config` default to 10,
            [0, 1] and one decimal place.

    Examples:
        ```python
        import manimgx as m


        class UnitIntervalExample(m.Scene):
            def construct(self) -> None:
                interval = m.UnitInterval(include_numbers=True, font_size=28)
                dot = m.Dot(interval.n2p(0.25), radius=0.12, color=m.YELLOW)
                self.add(interval, dot)
                self.play(dot.animate.move_to(interval.n2p(0.8)))
        ```
    """

    def __init__(self, **kwargs: Unpack[NumberLineOptions]):
        kwargs.setdefault("unit_size", 10)
        kwargs.setdefault("numbers_with_elongated_ticks", [0, 1])
        kwargs.setdefault("decimal_number_config", {"num_decimal_places": 1})
        super().__init__(x_range=(0, 1, 0.1), **kwargs)


type Coordinates = (
    float | Sequence[float] | np.ndarray
)  # a number per axis, or arrays of them


"""A coordinate on one axis: a number, or an array of numbers (of any shape) for many
points at once."""


def _halved(opacity: float | Sequence[float]) -> float | list[float]:
    """An opacity, or one for each part, at half strength."""
    if isinstance(opacity, int | float):
        return opacity * 0.5
    return [o * 0.5 for o in opacity]


def merged_axis_config(*configs: NumberLineOptions | None) -> NumberLineOptions:
    """Merge axis configs: later ones win, key by key, and inside their
    `decimal_number_config` too. An iterator among the values is read into a list: the
    config is shared by every axis, and an iterator would give its numbers to the first.

    Args:
        *configs: [Number line keywords][manimgx.NumberLine],
            in order; None for none.

    Returns:
        A new config.
    """
    merged: NumberLineOptions = {}
    for config_ in configs:
        if config_:
            numbers = (
                merged.get("decimal_number_config") or DecimalNumberOptions()
            ) | (config_.get("decimal_number_config") or DecimalNumberOptions())
            merged = merged | config_
            if numbers:
                merged["decimal_number_config"] = numbers
    for key in (
        "numbers_to_include",
        "numbers_to_exclude",
        "numbers_with_elongated_ticks",
    ):
        values = merged.get(key)
        if isinstance(values, Iterator):
            merged[key] = list(values)
    return merged


class AxisLine(TypedDict, total=False, closed=True):
    """The keywords of a line from an axis to a point
    ([get_vertical_line][manimgx.Axes.get_vertical_line] and the like): its class, its
    keywords, its color and its width."""

    line_func: type[Line]
    """The class of the line (default [DashedLine][manimgx.DashedLine]; a
    [Line][manimgx.Line] is solid)."""
    line_config: DashedLineOptions | None
    """[Dashed line keywords][manimgx.DashedLine] for the
    line, but its color and width, which `color` and `stroke_width` set (default None:
    none)."""
    color: ParsableManimColor | None
    """The line's color (default None: white)."""
    stroke_width: float
    """The line's width, in hundredths of a scene unit (default 2)."""


class PlotOptions(_CurveOptions, total=False, closed=True):
    """[plot][manimgx.Axes.plot]'s keywords but its function, for the methods that pass
    them on ([plot_derivative_graph][manimgx.Axes.plot_derivative_graph],
    [plot_antiderivative_graph][manimgx.Axes.plot_antiderivative_graph]): the range of
    x and the colorscale, with the curve keywords."""

    x_range: Sequence[float] | None
    """The range of x the graph spans, `[x_min, x_max]` or `[x_min, x_max, x_step]`,
    the function sampled every `x_step` (default None: the x-axis's range; without a
    step, a tenth of the x-axis's)."""
    use_vectorized: bool
    """Whether the function takes all the values of x at once, as an array (default
    False: it is tried on an array anyway, and called once per value if it does not
    take one)."""
    colorscale: Colorscale | None
    """Colors to paint the graph with by its value: colors spread evenly over the
    axis's range, or `(color, value)` pairs, blended between (default None: the
    graph's own color)."""
    colorscale_axis: int
    """The value the colorscale goes by: 1 for y, 0 for x (default 1)."""


class SecantSlopeGroup(VGroup):
    """A secant's construction, as
    [get_secant_slope_group][manimgx.Axes.get_secant_slope_group] makes it: its dx and
    df legs, their labels and the secant line, each by name."""

    dx_line: Line
    """The horizontal leg: from the first point of the graph across to below (or
    above) the second."""
    df_line: Line
    """The vertical leg: from the end of `dx_line` to the second point."""
    dx_label: Mobject
    """The horizontal leg's label, if it has one."""
    df_label: Mobject
    """The vertical leg's label, if it has one."""
    secant_line: Line
    """The secant: the line through both points, if it has one."""


class Axes(VGroup):
    """Axes: number lines through one origin, with coordinates of their own, and the
    tools to plot on them; white, with tips, unless configured.

    Axis option maps are construction inputs. The finished number lines
    retain their own defaults for later ticks, labels and coordinates.

    The x-axis runs over `x_range` and the y-axis over `y_range`, each a
    [NumberLine][manimgx.NumberLine] with ticks at every step of its range. The axes
    cross at their 0 (or, for a range without 0, at its end nearest 0), and the point
    of the middle of both ranges is put at the scene's origin. On a linear axis the
    tick at 0 is left out, where the other axis crosses; numbers are written at the
    ticks but 0 (see [add_coordinates][manimgx.Axes.add_coordinates]).

    [coords_to_point][manimgx.Axes.coords_to_point] (`c2p`, or `axes @ (x, y)`) and
    [point_to_coords][manimgx.Axes.point_to_coords] (`p2c`) convert between the axes'
    coordinates and the scene's points. The `plot` methods draw on the axes, in their
    coordinates: graphs of functions, curves given implicitly or in polar coordinates,
    line graphs. The `get_` methods make what explains a graph: its label, the area
    under it, Riemann rectangles, a secant, lines to a point. All of them return new
    mobjects, not added to the axes.

    Args:
        x_range: The x-axis's range, `[x_min, x_max, x_step]`, or `[x_min, x_max]` for
            a step of 1; None for the frame's width, [-7, 7, 1].
        y_range: The y-axis's range, likewise; None for the frame's height, [-4, 4, 1].
        x_length: The x-axis's length, in scene units; None for the frame's width
            less 2, rounded, as the frame is when the axes are made (12 in a wide video,
            6 in a tall one), or `unit_size` per unit if the axis's config gives one.
        y_length: The y-axis's length, in scene units; None for the frame's height
            less 2, rounded (6 in a wide video, 12 in a tall one), or `unit_size` per unit
            if the axis's config gives one.
        axis_config: [Number line keywords][manimgx.NumberLine]
            for both axes: `include_numbers`, `font_size`, `color`, …; None for none.
        x_axis_config: Number line keywords for the x-axis, over `axis_config`'s; None
            for none.
        y_axis_config: Number line keywords for the y-axis, over `axis_config`'s; None
            for none.
        tips: Whether each axis ends in an arrow tip.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] of the axes' group itself:
            as it has no points, they do not restyle the axes (`axis_config` does).

    Examples:
        ```python
        import manimgx as m


        class AxesExample(m.Scene):
            def construct(self) -> None:
                axes = m.Axes(
                    x_range=[0, 10, 1],
                    y_range=[-2, 6, 2],
                    x_length=10,
                    y_length=6,
                    axis_config={"include_numbers": True, "font_size": 28},
                )
                labels = axes.get_axis_labels("t", "v")
                graph = axes.plot(lambda t: 5 - 0.2 * (t - 4) ** 2, color=m.BLUE)
                self.add(axes, labels)
                self.play(m.Create(graph))
        ```
    """

    def __init__(
        self,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        axis_config: NumberLineOptions | None = None,
        x_axis_config: NumberLineOptions | None = None,
        y_axis_config: NumberLineOptions | None = None,
        tips: bool = True,
        **kwargs: Unpack[Style],
    ):
        super().__init__(**kwargs)
        self.dimension = 2
        self.x_range = _full_range(x_range, config.frame_x_radius)
        """The x-axis's range, `[x_min, x_max, x_step]`."""
        self.y_range = _full_range(y_range, config.frame_y_radius)
        """The y-axis's range, `[y_min, y_max, y_step]`."""
        self.num_sampled_graph_points_per_tick = 10
        """How many times per step of the x-axis [plot][manimgx.Axes.plot] samples a
        function, when not given a step (default 10)."""
        axis_config = merged_axis_config(
            {"include_tip": tips, "numbers_to_exclude": [0]}, axis_config
        )
        x_axis_config = _origin_tick(merged_axis_config(axis_config, x_axis_config))
        y_axis_config = _origin_tick(
            merged_axis_config(
                axis_config,
                {"rotation": 90 * DEGREES, "label_direction": LEFT},
                y_axis_config,
            )
        )
        self.x_axis = self._create_axis(self.x_range, x_axis_config, x_length, 0)
        """The x-axis, a [NumberLine][manimgx.NumberLine]."""
        self.y_axis = self._create_axis(self.y_range, y_axis_config, y_length, 1)
        """The y-axis, a [NumberLine][manimgx.NumberLine]."""
        self.x_length, self.y_length = (
            self.x_axis.get_length(),
            self.y_axis.get_length(),
        )
        self.axes = Group[NumberLine](self.x_axis, self.y_axis)
        """The axes, in a group: the x-axis, the y-axis (and the z-axis, in 3D)."""
        self.add(*self.axes)
        lines_center_point = [
            axis.scaling.function((axis.x_range[1] + axis.x_range[0]) / 2)
            for axis in self.axes
        ]
        self.shift(-self.coords_to_point(*lines_center_point))

    def _create_axis(
        self,
        range_terms: Sequence[float] | None,
        axis_config: NumberLineOptions,
        length: float | None,
        index: int,
    ) -> NumberLine:
        if length is None and "unit_size" not in axis_config:
            length = self._fitting_length(index)
        axis = NumberLine(range_terms, **(axis_config | {"length": length}))
        axis.shift(-axis.number_to_point(_origin_shift([axis.x_min, axis.x_max])))
        return axis

    def _fitting_length(self, index: int) -> float:
        """The length of an axis given none (0: x, 1: y): the frame's width or height
        less 2, rounded, as the frame is now (a scene's file may make it tall after
        ManimGX is imported)."""
        return round((config.frame_width, config.frame_height)[index]) - 2

    def coords_to_point(self, *coords: Coordinates) -> npt.NDArray[np.float64]:
        """Convert coordinates on the axes to a point of the scene, or arrays of them to
        points.

        `c2p` is its short name, and `axes @ (x, y)` its shortest. Coordinates past the
        ends of the axes are on the axes extended; a missing one is where the axes
        cross (`c2p(x)` is on the x-axis). Given an array per axis, of any shape (a
        grid too), it converts them all at once.

        Args:
            *coords: The coordinates, one per axis, in order: numbers, or arrays of one
                shape.

        Returns:
            The point, in scene coordinates; for arrays, the points, with the
            coordinates first (3, then the arrays' shape).

        Examples:
            ```python
            import manimgx as m


            class AxesCoordsToPointExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(
                        x_range=[0, 6], y_range=[0, 4], x_length=10, y_length=6
                    )
                    dot = m.Dot(axes.c2p(1, 1), radius=0.15, color=m.YELLOW)
                    self.add(axes.add_coordinates(), dot)
                    self.play(dot.animate.move_to(axes.c2p(5, 3)))
                    self.play(dot.animate.move_to(axes @ (3, 0.5)))
            ```
        """
        origin = self.x_axis.number_to_point(
            _origin_shift([self.x_axis.x_min, self.x_axis.x_max])
        )
        points = self.x_axis.number_to_point(np.asarray(coords[0], dtype=float))
        for axis, nums in zip(self.axes.submobjects[1:], coords[1:], strict=False):
            points = (
                points + axis.number_to_point(np.asarray(nums, dtype=float)) - origin
            )
        return points if points.ndim == 1 else np.moveaxis(points, -1, 0)

    def point_to_coords(
        self, point: Point3DLike | Point3DLike_Array
    ) -> npt.NDArray[np.float64]:
        """Convert a point of the scene to its coordinates on the axes, or points to
        theirs.

        `p2c` is its short name. Each coordinate is the axis's number at the point's
        projection onto it: for perpendicular axes, the inverse of
        [coords_to_point][manimgx.Axes.coords_to_point].

        Args:
            point: The point, in scene coordinates; or an (n, 3) array of points.

        Returns:
            The coordinates, one per axis; for n points, an array of n rows of them.
        """
        array = np.asarray(point, dtype=float)
        result = np.asarray([axis.point_to_number(array) for axis in self.axes])
        return result.T if array.ndim == 2 else result

    def polar_to_point(self, radius: float, azimuth: float) -> npt.NDArray[np.float64]:
        """Convert polar coordinates on the axes to a point of the scene.

        `pr2pt` is its short name. The point is at the coordinates
        (`radius` cos `azimuth`, `radius` sin `azimuth`).

        Args:
            radius: The distance from the origin, in the axes' units.
            azimuth: The angle from the positive x-axis, in radians, counterclockwise.

        Returns:
            The point, in scene coordinates.
        """
        return self.coords_to_point(radius * np.cos(azimuth), radius * np.sin(azimuth))

    c2p, p2c, pr2pt = coords_to_point, point_to_coords, polar_to_point

    def get_axes(self) -> Group[NumberLine]:
        """The axes: the x-axis, the y-axis (and the z-axis, in 3D).

        Returns:
            The group of the axes, each a [NumberLine][manimgx.NumberLine].
        """
        return self.axes

    def get_axis(self, index: int) -> NumberLine:
        """One of the axes.

        Args:
            index: The axis's index: 0 for x, 1 for y, 2 for z.

        Returns:
            The axis, a [NumberLine][manimgx.NumberLine].
        """
        return self.get_axes()[index]

    def get_origin(self) -> Point3D:
        """The point of the coordinates (0, 0): where the axes cross, if their ranges
        contain 0.

        Returns:
            The point, in scene coordinates.
        """
        return self.coords_to_point(0, 0)

    def get_x_axis(self) -> NumberLine:
        """The x-axis.

        Returns:
            The axis, a [NumberLine][manimgx.NumberLine].
        """
        return self.get_axis(0)

    def get_y_axis(self) -> NumberLine:
        """The y-axis.

        Returns:
            The axis, a [NumberLine][manimgx.NumberLine].
        """
        return self.get_axis(1)

    def get_z_axis(self) -> NumberLine:
        """The z-axis, of three-dimensional axes.

        Returns:
            The axis, a [NumberLine][manimgx.NumberLine].
        """
        return self.get_axis(2)

    def get_x_unit_size(self) -> float:
        """The length of one unit of the x-axis.

        Returns:
            The length, in scene units.
        """
        return self.get_x_axis().get_unit_size()

    def get_y_unit_size(self) -> float:
        """The length of one unit of the y-axis.

        Returns:
            The length, in scene units.
        """
        return self.get_y_axis().get_unit_size()

    def get_x_axis_label(
        self,
        label: Label,
        edge: Vector3DLike = UR,
        direction: Vector3DLike = UR,
        buff: float = SMALL_BUFF,
    ) -> Mobject:
        """Make a label for the x-axis, by its end.

        A string or a number is typeset with the axes' `label_constructor` (as math,
        with [MathTex][manimgx.MathTex], by default); a mobject is used as it is. The
        label is put next to a corner of the axis, toward `direction`, then moved onto
        the screen if it is off it.

        Args:
            label: The label: a string, a number or a mobject.
            edge: The corner of the axis the label is put by, as a direction: UR, the
                upper right one, by its end.
            direction: The direction the label is put toward, from that corner.
            buff: The gap between the corner and the label, in scene units.

        Returns:
            The label, not added to the axes.
        """
        return self._get_axis_label(
            label, self.get_x_axis(), edge, direction, buff=buff
        )

    def get_y_axis_label(
        self,
        label: Label,
        edge: Vector3DLike = UR,
        direction: Vector3DLike = UP * 0.5 + RIGHT,
        buff: float = SMALL_BUFF,
    ) -> Mobject:
        """Make a label for the y-axis, by its end.

        A string or a number is typeset with the axes' `label_constructor` (as math,
        with [MathTex][manimgx.MathTex], by default); a mobject is used as it is. The
        label is put next to a corner of the axis, toward `direction`, then moved onto
        the screen if it is off it.

        Args:
            label: The label: a string, a number or a mobject.
            edge: The corner of the axis the label is put by, as a direction: UR, the
                upper right one, by its end.
            direction: The direction the label is put toward, from that corner: by
                default up and to the right.
            buff: The gap between the corner and the label, in scene units.

        Returns:
            The label, not added to the axes.
        """
        return self._get_axis_label(
            label, self.get_y_axis(), edge, direction, buff=buff
        )

    def _get_axis_label(
        self,
        label: Label,
        axis: Mobject,
        edge: Vector3DLike,
        direction: Vector3DLike,
        buff: float = SMALL_BUFF,
    ) -> Mobject:
        label_mobject: Mobject = self.x_axis._create_label_tex(label)
        label_mobject.next_to(
            axis.get_critical_point(edge), direction=direction, buff=buff
        )
        label_mobject.shift_onto_screen(buff=MED_SMALL_BUFF)
        return label_mobject

    def get_axis_labels(self, x_label: Label = "x", y_label: Label = "y") -> VGroup:
        """Make a label for each axis, by its end, as
        [get_x_axis_label][manimgx.Axes.get_x_axis_label] and
        [get_y_axis_label][manimgx.Axes.get_y_axis_label] place them.

        Args:
            x_label: The x-axis's label: a string or a number, typeset as math, or a
                mobject.
            y_label: The y-axis's label, likewise.

        Returns:
            A new group of the labels, kept as the axes' `axis_labels`; not added to
            the axes.

        Examples:
            ```python
            import manimgx as m


            class AxesGetAxisLabelsExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 10], y_range=[0, 5], x_length=10)
                    labels = axes.get_axis_labels(m.Tex("time"), m.Tex("height"))
                    self.add(axes, labels)
            ```
        """
        self.axis_labels = VGroup(
            self.get_x_axis_label(x_label), self.get_y_axis_label(y_label)
        )
        return self.axis_labels

    def add_coordinates(
        self,
        *axes_numbers: Iterable[float] | Mapping[float, Label] | None,
        **kwargs: Unpack[DecimalNumberOptions],
    ) -> Self:
        """Number the axes: at their ticks, at the values given, or with labels by
        value.

        Give one argument per axis, in order: None numbers the axis at its ticks, but
        0 (on a logarithmic axis, as powers: 10², 10³, …); values number it at those
        values; a dictionary from values to labels (strings, numbers or typeset
        mobjects) puts each label by its value (see
        [add_labels][manimgx.NumberLine.add_labels]). Without arguments, every axis is
        numbered at its ticks. The numbers are added to the axes, and kept, one group
        per axis, as the axes' `coordinate_labels`.

        Args:
            *axes_numbers: What to write on each axis, in order: None, values, or
                labels by value; the axes past the last argument get nothing.
            **kwargs: [Number keywords][manimgx.DecimalNumber]
                for the numbers: `font_size`, `num_decimal_places`, `color`, … (only
                `font_size`, for labels by value).

        Examples:
            ```python
            import manimgx as m


            class AxesAddCoordinatesExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(
                        x_range=[0, 5], y_range=[0, 1, 0.25], x_length=10, y_length=6
                    )
                    axes.add_coordinates(
                        {1: "one", 2: "two", 3: "three", 4: "four"}, None, font_size=30
                    )
                    self.add(axes)
            ```
        """
        self.coordinate_labels = VGroup()
        for axis, values in zip(
            self.axes, axes_numbers or (None,) * self.dimension, strict=False
        ):
            if isinstance(values, Mapping):
                axis.add_labels(values, font_size=kwargs.get("font_size"))
                labels = axis.labels
            elif values is None and axis.scaling.custom_labels:
                tick_range = axis.get_tick_range()
                axis.add_labels(
                    dict(
                        zip(
                            tick_range,
                            axis.scaling.get_custom_labels(tick_range),
                            strict=True,
                        )
                    )
                )
                labels = axis.labels
            else:
                axis.add_numbers(values, **kwargs)
                labels = axis.numbers
            self.coordinate_labels.add(labels)
        return self

    @deprecated("use get_vertical_line or get_horizontal_line", category=None)
    def get_line_from_axis_to_point(
        self,
        index: int,
        point: Point3DLike,
        line_func: type[Line] = DashedLine,
        line_config: DashedLineOptions | None = None,
        color: ParsableManimColor | None = None,
        stroke_width: float = 2,
    ) -> Line:
        """Make a line from an axis to a point: from the point's projection onto the
        axis, dashed, white and thin unless styled.

        Args:
            index: The axis's index: 0 for x, 1 for y.
            point: The point, in scene coordinates.
            line_func: The class of the line: [DashedLine][manimgx.DashedLine], or
                [Line][manimgx.Line] for a solid one, ….
            line_config: [Dashed line keywords][manimgx.DashedLine]
                for the line, but its color and width; None for none.
            color: The line's color; None for white.
            stroke_width: The line's width, in hundredths of a scene unit.

        Returns:
            A new line, not added to the axes.
        """
        start = self.get_axis(index).get_projection(point)
        style = (line_config or DashedLineOptions()).copy()
        style["color"], style["stroke_width"] = (
            ManimColor(WHITE if color is None else color),
            stroke_width,
        )
        if issubclass(line_func, DashedLine):
            return line_func(start, point, **style)
        # a solid line has no dashes: it takes the line keywords without them
        style.pop("dash_length", None)
        style.pop("dashed_ratio", None)
        return line_func(start, point, **cast("LineOptions", style))

    def get_vertical_line(self, point: Point3DLike, **kwargs: Unpack[AxisLine]) -> Line:
        """Make a line from the x-axis up (or down) to a point: dashed, white and thin
        unless styled.

        Args:
            point: The point, in scene coordinates.
            **kwargs: [Axis line keywords][manimgx.mobjects.plotting.AxisLine]:
                the line's class, keywords, `color` and `stroke_width`.

        Returns:
            A new line, not added to the axes.
        """
        return self.get_line_from_axis_to_point(0, point, **kwargs)

    def get_horizontal_line(
        self, point: Point3DLike, **kwargs: Unpack[AxisLine]
    ) -> Line:
        """Make a line from the y-axis across to a point: dashed, white and thin unless
        styled.

        Args:
            point: The point, in scene coordinates.
            **kwargs: [Axis line keywords][manimgx.mobjects.plotting.AxisLine]:
                the line's class, keywords, `color` and `stroke_width`.

        Returns:
            A new line, not added to the axes.
        """
        return self.get_line_from_axis_to_point(1, point, **kwargs)

    def get_lines_to_point(
        self, point: Point3DLike, **kwargs: Unpack[AxisLine]
    ) -> VGroup:
        """Make the lines from both axes to a point: the
        [horizontal][manimgx.Axes.get_horizontal_line] one from the y-axis, then the
        [vertical][manimgx.Axes.get_vertical_line] one from the x-axis.

        Args:
            point: The point, in scene coordinates.
            **kwargs: [Axis line keywords][manimgx.mobjects.plotting.AxisLine]
                for both lines.

        Returns:
            A new group of the two lines, not added to the axes.

        Examples:
            ```python
            import manimgx as m


            class AxesGetLinesToPointExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 6], y_range=[0, 4], x_length=10)
                    dot = m.Dot(axes.c2p(4, 3), radius=0.15, color=m.YELLOW)
                    lines = axes.get_lines_to_point(dot.get_center(), color=m.BLUE)
                    self.add(axes.add_coordinates(), dot)
                    self.play(m.Create(lines))
            ```
        """
        return VGroup(
            self.get_horizontal_line(point, **kwargs),
            self.get_vertical_line(point, **kwargs),
        )

    def plot(
        self,
        function: Callable[[float], float],
        x_range: Sequence[float] | None = None,
        use_vectorized: bool = False,
        colorscale: Colorscale | None = None,
        colorscale_axis: int = 1,
        **kwargs: Unpack[CurveOptions],
    ) -> ParametricFunction:
        """Plot the graph of a function y = f(x) on the axes, in their coordinates.

        The function is sampled over `x_range` and the samples are joined smoothly (see
        [ParametricFunction][manimgx.ParametricFunction]); on a logarithmic x-axis, x
        runs over powers. The graph keeps the function as its `underlying_function`,
        for the methods that work on graphs. With a `colorscale`, the graph's stroke is
        a gradient, from left to right, of the colors of its values (y, or x), taken at
        every step of `x_range` (every 0.01 without one).

        Args:
            function: The function, from x to y, in the axes' coordinates.
            x_range: The range of x the graph spans, `[x_min, x_max]` or
                `[x_min, x_max, x_step]`, the function sampled every `x_step`; None
                for the x-axis's range. Without a step, it is a tenth of the x-axis's.
            use_vectorized: Whether `function` takes all the values of x at once, as an
                array; it is tried on an array anyway, and called once per value if it
                does not take one.
            colorscale: Colors to paint the graph with by its value: colors spread
                evenly over the axis's range, or `(color, value)` pairs, blended
                between; None for the graph's own color.
            colorscale_axis: The value the colorscale goes by: 1 for y, 0 for x.
            **kwargs: [Curve keywords][manimgx.mobjects.plotting.CurveOptions]:
                `discontinuities`, `use_smoothing`, and the style keywords.

        Returns:
            A new [ParametricFunction][manimgx.ParametricFunction], not added to the
            axes.

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesPlotExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-4, 4], y_range=[-2, 2], y_length=6)
                    sine = axes.plot(np.sin, color=m.BLUE)
                    parabola = axes.plot(
                        lambda x: x**2 - 1.5,
                        x_range=[-1.8, 1.8],
                        colorscale=[m.GREEN, m.YELLOW, m.RED],
                    )
                    self.add(axes)
                    self.play(m.Create(sine), m.Create(parabola))
            ```
        """
        t_range = np.array(self.x_range, dtype=float)
        if x_range is not None:
            t_range[: len(x_range)] = x_range
        if x_range is None or len(x_range) < 3:
            t_range[2] /= self.num_sampled_graph_points_per_tick

        def point(t: float | np.ndarray) -> np.ndarray:
            """The graph's point at t — or at every t of an array, mapped in one call."""
            if isinstance(t, np.ndarray):
                return self.coords_to_point(t, sample(function, t))
            return self.coords_to_point(t, function(t))

        graph = ParametricFunction(
            point,
            t_range=t_range,
            scaling=self.x_axis.scaling,
            use_vectorized=use_vectorized,
            **kwargs,
        )
        graph.underlying_function = function
        if colorscale:
            resolution = (
                x_range[2] if x_range is not None and len(x_range) == 3 else 0.01
            )
            graph.set_stroke(
                self._colorscale(
                    function, colorscale, colorscale_axis, t_range, resolution
                )
            )
            graph.set_sheen_direction(RIGHT)
        return graph

    def _colorscale(
        self,
        function: Callable[[float], float],
        colorscale: Colorscale,
        axis: int,
        t_range: np.ndarray,
        resolution: float,
    ) -> list[ManimColor]:
        """Colors along a graph by its x or y value (`axis`), over that axis' range by default."""
        low, high = (self.x_range, self.y_range)[axis][:2]
        xs = np.arange(t_range[0], t_range[1] + resolution, resolution)
        return colors_by_value(
            colorscale, ((x, function(x))[axis] for x in xs), low, high
        )

    def plot_implicit_curve(
        self,
        func: Callable[[float, float], float],
        min_depth: int = 5,
        max_quads: int = 1500,
        **kwargs: Unpack[ImplicitOptions],
    ) -> ImplicitFunction:
        """Plot the curve where a function of x and y is zero, `func(x, y) = 0`, on the
        axes, in their coordinates: found within their ranges.

        The rectangle of the ranges is divided in four, and each part in four again,
        finer where the curve passes (see [ImplicitFunction][manimgx.ImplicitFunction]).
        On a logarithmic axis, the function is given powers.

        Args:
            func: The function of x and y, in the axes' coordinates.
            min_depth: How many times the rectangle is at least divided in four: more
                finds smaller pieces of the curve.
            max_quads: The most cells the rectangle may be divided into: more follow
                the curve more closely, and take longer.
            **kwargs: [Implicit curve keywords][manimgx.mobjects.plotting.ImplicitOptions]:
                `use_smoothing`, and the style keywords.

        Returns:
            A new [ImplicitFunction][manimgx.ImplicitFunction], not added to the axes.

        Examples:
            ```python
            import manimgx as m


            class AxesPlotImplicitCurveExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-3, 3], y_range=[-3, 3], y_length=7)
                    curve = axes.plot_implicit_curve(
                        lambda x, y: y**2 - x**3 + 2 * x - 1, color=m.YELLOW
                    )
                    self.add(axes)
                    self.play(m.Create(curve))
            ```
        """
        x_scale = self.get_x_axis().scaling
        y_scale = self.get_y_axis().scaling
        graph = ImplicitFunction(
            func=lambda x, y: func(x_scale.function(x), y_scale.function(y)),
            x_range=self.x_range[:2],
            y_range=self.y_range[:2],
            min_depth=min_depth,
            max_quads=max_quads,
            **kwargs,
        )
        graph.stretch(self.get_x_unit_size(), 0, about_point=ORIGIN).stretch(
            self.get_y_unit_size(), 1, about_point=ORIGIN
        ).shift(self.get_origin())
        return graph

    def plot_polar_graph(
        self,
        r_func: Callable[[float], float],
        theta_range: Sequence[float] | None = None,
        **kwargs: Unpack[CurveOptions],
    ) -> ParametricFunction:
        """Plot a curve in polar coordinates, r = r_func(θ), on the axes: for each
        angle θ of its range, the point in the direction θ from the origin, at the
        distance `r_func(θ)`.

        Args:
            r_func: The function, from the angle θ, in radians, to the distance r, in
                the axes' units.
            theta_range: The range of θ, `[θ_min, θ_max]` or `[θ_min, θ_max, θ_step]`,
                in radians, sampled every 0.01 without a step; None for a full turn,
                [0, 2π].
            **kwargs: [Curve keywords][manimgx.mobjects.plotting.CurveOptions]:
                `use_smoothing`, and the style keywords.

        Returns:
            A new [ParametricFunction][manimgx.ParametricFunction], not added to the
            axes.

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesPlotPolarGraphExample(m.Scene):
                def construct(self) -> None:
                    plane = m.PolarPlane(radius_max=3, size=7.5)
                    rose = plane.plot_polar_graph(
                        lambda theta: 3 * np.sin(5 * theta), color=m.ORANGE
                    )
                    self.add(plane)
                    self.play(m.Create(rose), run_time=3)
            ```
        """
        theta_range = theta_range if theta_range is not None else [0, 2 * PI]
        return ParametricFunction(
            function=lambda th: self.pr2pt(r_func(th), th),
            t_range=theta_range,
            **kwargs,
        )

    def input_to_graph_point(self, x: float, graph: ParametricFunction) -> Point3D:
        """Find the point of a graph at an input: at x, for a graph of
        [plot][manimgx.Axes.plot]; at a value of its parameter, for another curve.

        `i2gp` is its short name. The input may be past the graph's ends: the point is
        then its function's, beyond what is drawn.

        Args:
            x: The input: x, in the axes' coordinates, for a graph.
            graph: The graph, or curve.

        Returns:
            The point, in scene coordinates.

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesInputToGraphPointExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 7], y_range=[-1.5, 1.5, 0.5])
                    curve = axes.plot(np.cos, color=m.BLUE)
                    dots = m.VGroup(
                        *(m.Dot(axes.i2gp(x, curve), radius=0.12) for x in range(7))
                    )
                    self.add(axes, curve, dots.set_color(m.YELLOW))
            ```
        """
        return graph.function(x)

    def input_to_graph_coords(
        self, x: float, graph: ParametricFunction
    ) -> tuple[float, float]:
        """Find the coordinates of a graph's point at an input: (x, f(x)), for a graph
        of [plot][manimgx.Axes.plot]; for another curve, those of its point at a value
        of its parameter.

        Args:
            x: The input: x, for a graph.
            graph: The graph, or curve.

        Returns:
            The point's coordinates, (x, y).
        """
        if (
            graph.underlying_function is None
        ):  # a curve, not a graph of y(x): its point's coordinates
            coords = self.point_to_coords(graph.function(x))
            return float(coords[0]), float(coords[1])
        return (x, graph.underlying_function(x))

    i2gp = input_to_graph_point
    """[input_to_graph_point][manimgx.Axes.input_to_graph_point], by a shorter name."""

    def get_graph_label(
        self,
        graph: ParametricFunction,
        label: Label = "f(x)",
        x_val: float | None = None,
        direction: Vector3DLike = RIGHT,
        buff: float = MED_SMALL_BUFF,
        color: ParsableManimColor | None = None,
        dot: bool = False,
        dot_config: Style | None = None,
    ) -> Mobject:
        r"""Make a label for a graph, by one of its points: in the graph's color, unless
        given another.

        A string or a number is typeset with the axes' `label_constructor` (as math,
        with [MathTex][manimgx.MathTex], by default); a mobject is used as it is, and
        recolored too. The label is put next to the graph's point at `x_val`, toward
        `direction`, then moved onto the screen if it is off it. Without `x_val`, the
        point is the rightmost, of a hundred over the x-axis's range, that is below the
        top of the frame.

        Args:
            label: The label: a string or a number, typeset as math, or a mobject.
            x_val: The x of the point the label is put by; None for the rightmost on
                screen.
            direction: The direction the label is put toward, from the point.
            buff: The gap between the point and the label, in scene units.
            color: The label's color; None for the graph's.
            dot: Whether a dot marks the point, as part of the label.
            dot_config: [Style keywords][manimgx.drawing.paint.Style] for the dot; None
                for none.

        Returns:
            The label, not added to the axes.

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesGetGraphLabelExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-4, 4], y_range=[-2, 4], x_length=11)
                    parabola = axes.plot(lambda x: x**2 / 4, color=m.BLUE)
                    sine = axes.plot(np.sin, color=m.YELLOW)
                    parabola_label = axes.get_graph_label(parabola, "x^2 / 4")
                    sine_label = axes.get_graph_label(
                        sine, r"\sin x", x_val=m.PI / 2, direction=m.UP, dot=True
                    )
                    self.add(axes, parabola, sine, parabola_label, sine_label)
            ```
        """
        label_object: Mobject = self.x_axis._create_label_tex(label).set_color(
            graph.get_color() if color is None else color
        )
        if x_val is None:  # the rightmost point of the graph that is on screen
            xs = np.linspace(self.x_range[1], self.x_range[0], 100)
            points = (self.input_to_graph_point(x, graph) for x in xs)
            point = next(
                (p for p in points if p[1] < config["frame_y_radius"]),
                self.input_to_graph_point(xs[-1], graph),
            )
        else:
            point = self.input_to_graph_point(x_val, graph)
        label_object.next_to(point, direction, buff=buff)
        label_object.shift_onto_screen()
        if dot:
            label_object.add(Dot(point=point, **(dot_config or Style())))
        return label_object

    def get_riemann_rectangles(
        self,
        graph: ParametricFunction,
        x_range: Sequence[float] | None = None,
        dx: float = 0.1,
        input_sample_type: str = "left",
        stroke_width: float = 1,
        stroke_color: ParsableManimColor = BLACK,
        fill_opacity: float = 1,
        color: Iterable[ParsableManimColor] | ParsableManimColor = (BLUE, GREEN),
        show_signed_area: bool = True,
        bounded_graph: ParametricFunction | None = None,
        blend: bool = False,
        width_scale_factor: float = 1.001,
    ) -> VGroup:
        """Make Riemann rectangles for a graph: from the x-axis (or a second graph) up
        to the graph, `dx` wide, their colors a gradient; outlined thinly in black
        unless styled.

        A rectangle begins at every `dx` from the start of `x_range`, the last before
        its end. Each rises from the x-axis — or from `bounded_graph`, at its left
        edge — to the graph at its left edge, its right edge or its center
        (`input_sample_type`). With `show_signed_area`, a rectangle where the graph is
        below its base takes the inverse of its color.

        Args:
            graph: The graph, of [plot][manimgx.Axes.plot].
            x_range: The range of x the rectangles cover, `[x_min, x_max]`; None for
                the graph's (and `bounded_graph`'s, where both are).
            dx: The rectangles' width, in the axes' units.
            input_sample_type: Where each rectangle meets the graph: `"left"`,
                `"right"` or `"center"`.
            stroke_width: The width of the rectangles' outlines, in hundredths of a
                scene unit.
            stroke_color: The outlines' color (unless `blend`).
            fill_opacity: The rectangles' opacity, from 0 to 1.
            color: The rectangles' color, or colors for a gradient from the first
                rectangle to the last.
            show_signed_area: Whether a rectangle where the graph is below its base
                takes the inverse of its color.
            bounded_graph: A second graph, of [plot][manimgx.Axes.plot], the
                rectangles rise from; None for the x-axis.
            blend: Whether each outline takes its rectangle's color, rather than
                `stroke_color`.
            width_scale_factor: How much wider than `dx` each rectangle is made, so
                that neighbours meet without a seam.

        Returns:
            A new group of the rectangles, from left to right; not added to the axes.

        Examples:
            ```python
            import manimgx as m


            class AxesGetRiemannRectanglesExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-3, 3], y_range=[-2, 4], y_length=6.5)
                    graph = axes.plot(lambda x: x**2 / 2 - 1, color=m.YELLOW)
                    coarse, fine = (
                        axes.get_riemann_rectangles(graph, x_range=[-2.5, 2.5], dx=dx)
                        for dx in (0.5, 0.1)
                    )
                    self.add(axes, coarse, graph)
                    self.play(m.Transform(coarse, fine), run_time=2)
            ```
        """
        if x_range is None:
            if bounded_graph is None:
                x_range = [graph.t_min, graph.t_max]
            else:
                x_min = max(graph.t_min, bounded_graph.t_min)
                x_max = min(graph.t_max, bounded_graph.t_max)
                x_range = [x_min, x_max]
        rectangles = VGroup()
        x_range_array = np.arange(x_range[0], x_range[1], dx)
        colors = color_gradient(parse_colors(color), len(x_range_array))
        for x, color_x in zip(x_range_array, colors, strict=True):
            if input_sample_type == "left":
                sample_input = x
            elif input_sample_type == "right":
                sample_input = x + dx
            elif input_sample_type == "center":
                sample_input = x + 0.5 * dx
            else:
                raise ValueError("Invalid input sample type")
            graph_point = self.input_to_graph_point(sample_input, graph)
            if bounded_graph is None or bounded_graph.underlying_function is None:
                y_point = _origin_shift(self.y_range)
            else:
                y_point = bounded_graph.underlying_function(x)
            points = np.array(
                [
                    self.coords_to_point(x, y_point),
                    self.coords_to_point(x + width_scale_factor * dx, y_point),
                    graph_point,
                ]
            )
            low, high = points.min(axis=0), points.max(axis=0)
            rect = Rectangle()
            rect.stretch_to_fit_width(high[0] - low[0])
            rect.stretch_to_fit_height(high[1] - low[1])
            rect.shift((low + high) / 2 - rect.get_center())
            rectangles.add(rect)
            if self.p2c(graph_point)[1] < y_point and show_signed_area:
                color_x = invert_color(color_x)
            if blend:
                stroke_color = color_x
            rect.set_style(
                fill_color=color_x,
                fill_opacity=fill_opacity,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
            )
        return rectangles

    def get_area(
        self,
        graph: ParametricFunction,
        x_range: Sequence[float] | None = None,
        color: ParsableManimColor | Iterable[ParsableManimColor] = (BLUE, GREEN),
        opacity: float = 0.3,
        bounded_graph: ParametricFunction | None = None,
        **kwargs: Unpack[StyleBase],
    ) -> Polygon:
        """Make the area between a graph and the x-axis, or between two graphs, over a
        range of x: a polygon, blue to green and translucent unless styled.

        The area's edge follows the graph's own points, and closes along the x-axis, or
        back along `bounded_graph`; its fill and outline both take `color` and
        `opacity`. Two graphs whose ranges do not meet raise a ValueError.

        Args:
            x_range: The range of x, `(x_min, x_max)`; None for the graph's.
            color: The area's color, or colors for a gradient.
            opacity: The area's opacity, from 0 to 1.
            bounded_graph: A second graph the area reaches to, rather than the x-axis;
                None for the x-axis. Only the range both graphs span is covered.
            **kwargs: [Style keywords][manimgx.drawing.paint.Style] for the polygon, but
                its colors and opacities: `stroke_width`, ….

        Returns:
            A new [Polygon][manimgx.Polygon], not added to the axes.

        Examples:
            ```python
            import manimgx as m


            class AxesGetAreaExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 5], y_range=[0, 6], y_length=6.5)
                    curve = axes.plot(lambda x: 5 - (x - 2.5) ** 2 / 2, color=m.BLUE)
                    line = axes.plot(lambda x: x / 2, color=m.YELLOW)
                    under = axes.get_area(curve, x_range=(0.5, 2))
                    between = axes.get_area(
                        curve, x_range=(3, 4.5), bounded_graph=line, color=m.RED
                    )
                    self.add(axes, under, between, curve, line)
            ```
        """
        if x_range is None:
            a = graph.t_min
            b = graph.t_max
        else:
            a, b = x_range
        if bounded_graph is not None:
            if bounded_graph.t_min > b:
                raise ValueError(f"Ranges not matching: {bounded_graph.t_min} < {b}")
            if bounded_graph.t_max < a:
                raise ValueError(f"Ranges not matching: {bounded_graph.t_max} > {a}")
            a = max(a, bounded_graph.t_min)
            b = min(b, bounded_graph.t_max)
        if bounded_graph is None:
            points = (
                [self.c2p(a), graph.function(a)]
                + [p for p in graph.points if a <= self.p2c(p)[0] <= b]
                + [graph.function(b), self.c2p(b)]
            )
        else:
            graph_points, bounded_graph_points = (
                [g.function(a)]
                + [p for p in g.points if a <= self.p2c(p)[0] <= b]
                + [g.function(b)]
                for g in (graph, bounded_graph)
            )
            points = graph_points + bounded_graph_points[::-1]
        return Polygon(*points, **kwargs).set_opacity(opacity).set_color(color)

    def angle_of_tangent(
        self, x: float, graph: ParametricFunction, dx: float = 1e-08
    ) -> float:
        """Find the angle of a graph's tangent at an input, in the axes' coordinates.

        The tangent is taken from the graph's point at `x` to its point at `x + dx`.

        Args:
            x: The input: x, for a graph of [plot][manimgx.Axes.plot].
            dx: The step the tangent is taken over, in the axes' units.

        Returns:
            The angle, in radians, counterclockwise from the direction of the x-axis,
            measured in the axes' coordinates: not as drawn, where their units differ.
        """
        p0 = np.array([*self.input_to_graph_coords(x, graph)])
        p1 = np.array([*self.input_to_graph_coords(x + dx, graph)])
        return angle_of_vector(p1 - p0)

    def slope_of_tangent(
        self, x: float, graph: ParametricFunction, dx: float = 1e-08
    ) -> float:
        """Find the slope of a graph's tangent at an input: its derivative, dy/dx, in
        the axes' coordinates.

        It is the tangent of [angle_of_tangent][manimgx.Axes.angle_of_tangent]'s angle.

        Args:
            x: The input: x, for a graph of [plot][manimgx.Axes.plot].
            dx: The step the tangent is taken over, in the axes' units.
        """
        return float(np.tan(self.angle_of_tangent(x, graph, dx)))

    def plot_derivative_graph(
        self, graph: ParametricFunction, **kwargs: Unpack[PlotOptions]
    ) -> ParametricFunction:
        """Plot the derivative of a graph: at each x, its
        [slope][manimgx.Axes.slope_of_tangent]; green unless styled.

        Args:
            **kwargs: [Plot keywords][manimgx.mobjects.plotting.PlotOptions]:
                `x_range`, `color`, ….

        Returns:
            A new [ParametricFunction][manimgx.ParametricFunction], not added to the
            axes.

        Examples:
            ```python
            import manimgx as m


            class AxesPlotDerivativeGraphExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-3, 3], y_range=[-3, 4], y_length=6.5)
                    cubic = axes.plot(lambda x: x**3 / 6 - x, color=m.BLUE)
                    derivative = axes.plot_derivative_graph(cubic)
                    labels = m.VGroup(
                        axes.get_graph_label(cubic, "f(x)", x_val=-1.4, direction=m.UP),
                        axes.get_graph_label(derivative, "f'(x)", x_val=2.5),
                    )
                    self.add(axes, cubic, labels[0])
                    self.play(m.Create(derivative), m.FadeIn(labels[1]))
            ```
        """
        if kwargs.get("color") is None:  # not given, None too
            kwargs["color"] = GREEN
        return self.plot(lambda x: self.slope_of_tangent(x, graph), **kwargs)

    def plot_antiderivative_graph(
        self,
        graph: ParametricFunction,
        y_intercept: float = 0,
        samples: int = 50,
        **kwargs: Unpack[PlotOptions],
    ) -> ParametricFunction:
        """Plot an antiderivative of a graph: at each x, the integral of the graph from
        0 to x, plus `y_intercept`.

        Each value is a trapezoidal sum of the graph's values at `samples` points from
        0 to x.

        Args:
            y_intercept: The antiderivative's value at 0.
            samples: How many of the graph's values each integral sums.
            **kwargs: [Plot keywords][manimgx.mobjects.plotting.PlotOptions]:
                `x_range`, `color`, ….

        Returns:
            A new [ParametricFunction][manimgx.ParametricFunction], not added to the
            axes.

        Examples:
            ```python
            import manimgx as m


            class AxesPlotAntiderivativeGraphExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-3, 3], y_range=[-3, 3], y_length=6.5)
                    graph = axes.plot(lambda x: (x**2 - 2) / 3, color=m.RED)
                    antiderivative = axes.plot_antiderivative_graph(
                        graph, y_intercept=1, color=m.BLUE
                    )
                    self.add(axes, graph)
                    self.play(m.Create(antiderivative))
            ```
        """
        axis = 1 if kwargs.get("use_vectorized", False) else 0
        f_vec = np.vectorize(
            graph.underlying_function
            or (lambda x: self.input_to_graph_coords(x, graph)[1])
        )

        def antideriv(x: float) -> float:
            x_vals = np.linspace(0, x, samples, axis=axis)
            return float(np.trapezoid(f_vec(x_vals), x_vals) + y_intercept)

        return self.plot(antideriv, **kwargs)

    def get_secant_slope_group(
        self,
        x: float,
        graph: ParametricFunction,
        dx: float | None = None,
        dx_line_color: ParsableManimColor = PURE_YELLOW,
        dy_line_color: ParsableManimColor | None = None,
        dx_label: Label | None = None,
        dy_label: Label | None = None,
        include_secant_line: bool = True,
        secant_line_color: ParsableManimColor = GREEN,
        secant_line_length: float = 10,
    ) -> SecantSlopeGroup:
        """Make a secant's construction on a graph, between its points at `x` and
        `x + dx`: the legs dx and df, their labels, and the secant through both points.

        The dx leg runs across from the first point, and the df leg up (or down) to the
        second, in the graph's color unless given another. The labels, typeset as math
        unless mobjects, are scaled down together to fit their legs (to 80% of the dx
        leg's width and of the df leg's height), and put below the dx leg and right of
        the df leg (above and left, for a negative `dx`), each in its leg's color. The
        secant is `secant_line_length` long, centered between the points.

        Args:
            x: The input of the first point: its x.
            dx: The step to the second point, in the axes' units; None for a tenth of
                the x-axis's range.
            dx_line_color: The dx leg's color.
            dy_line_color: The df leg's color; None for the graph's.
            dx_label: The dx leg's label: a string, a number or a mobject; None for
                none.
            dy_label: The df leg's label, likewise; None for none.
            include_secant_line: Whether the construction includes the secant.
            secant_line_color: The secant's color.
            secant_line_length: The secant's length, in scene units.

        Returns:
            A new [SecantSlopeGroup][manimgx.mobjects.plotting.SecantSlopeGroup],
            not added to the axes: its parts are its `dx_line`, `df_line`, `dx_label`,
            `df_label` and `secant_line`.

        Examples:
            ```python
            import manimgx as m


            class AxesGetSecantSlopeGroupExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 5], y_range=[0, 7], y_length=6.5)
                    graph = axes.plot(lambda x: x**2 / 4, color=m.BLUE)
                    secant = axes.get_secant_slope_group(
                        2,
                        graph,
                        dx=2,
                        dx_label="dx",
                        dy_label="dy",
                        secant_line_length=7,
                        secant_line_color=m.RED,
                    )
                    self.add(axes, graph)
                    self.play(m.Create(secant))
            ```
        """
        group = SecantSlopeGroup()
        dx = dx or float(self.x_range[1] - self.x_range[0]) / 10
        dy_line_color = dy_line_color or graph.get_color()
        p1 = self.input_to_graph_point(x, graph)
        p2 = self.input_to_graph_point(x + dx, graph)
        interim_point = p2[0] * RIGHT + p1[1] * UP
        group.dx_line = Line(p1, interim_point, color=dx_line_color)
        group.df_line = Line(interim_point, p2, color=dy_line_color)
        group.add(group.dx_line, group.df_line)
        labels = VGroup()
        if dx_label is not None:
            group.dx_label = self.x_axis._create_label_tex(dx_label)
            labels.add(group.dx_label)
            group.add(group.dx_label)
        if dy_label is not None:
            group.df_label = self.x_axis._create_label_tex(dy_label)
            labels.add(group.df_label)
            group.add(group.df_label)
        if len(labels) > 0:
            max_width = 0.8 * group.dx_line.width
            max_height = 0.8 * group.df_line.height
            if labels.width > max_width:
                labels.width = max_width
            if labels.height > max_height:
                labels.height = max_height
        if dx_label is not None:
            group.dx_label.next_to(
                group.dx_line, np.sign(dx) * DOWN, buff=group.dx_label.height / 2
            )
            group.dx_label.set_color(group.dx_line.get_color())
        if dy_label is not None:
            group.df_label.next_to(
                group.df_line, np.sign(dx) * RIGHT, buff=group.df_label.height / 2
            )
            group.df_label.set_color(group.df_line.get_color())
        if include_secant_line:
            group.secant_line = Line(p1, p2, color=secant_line_color)
            group.secant_line.scale(secant_line_length / group.secant_line.get_length())
            group.add(group.secant_line)
        return group

    def get_vertical_lines_to_graph(
        self,
        graph: ParametricFunction,
        x_range: Sequence[float] | None = None,
        num_lines: int = 20,
        **kwargs: Unpack[AxisLine],
    ) -> VGroup:
        """Make lines from the x-axis to a graph, evenly spaced over a range of x:
        dashed, white and thin unless styled.

        Args:
            x_range: The range of x, `[x_min, x_max]`: the first line at x_min, the
                last at x_max; None for the x-axis's range.
            num_lines: How many lines.
            **kwargs: [Axis line keywords][manimgx.mobjects.plotting.AxisLine]:
                the lines' class, keywords, `color` and `stroke_width`.

        Returns:
            A new group of the lines, from left to right; not added to the axes.

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesGetVerticalLinesToGraphExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 8], y_range=[-1, 1, 0.5], y_length=5)
                    curve = axes.plot(
                        lambda x: np.sin(2 * x) * np.exp(-x / 4), color=m.YELLOW
                    )
                    lines = axes.get_vertical_lines_to_graph(
                        curve, x_range=[0.5, 7.5], num_lines=15, color=m.BLUE
                    )
                    self.add(axes, curve)
                    self.play(m.Create(lines))
            ```
        """
        x_range = x_range if x_range is not None else self.x_range
        return VGroup(
            *(
                self.get_vertical_line(self.i2gp(x, graph), **kwargs)
                for x in np.linspace(x_range[0], x_range[1], num_lines)
            )
        )

    def get_T_label(
        self,
        x_val: float,
        graph: ParametricFunction,
        label: float | str | Mobject | None = None,
        label_color: ParsableManimColor | None = None,
        triangle_size: float = MED_SMALL_BUFF,
        triangle_color: ParsableManimColor | None = WHITE,
        line_func: type[Line] = Line,
        line_color: ParsableManimColor = PURE_YELLOW,
    ) -> VGroup:
        """Make a T-label for a value of x: a small triangle under the x-axis pointing
        up at the value, a label below the triangle, and a line from the x-axis up to
        the graph.

        Args:
            x_val: The value of x it marks.
            graph: The graph the line reaches.
            label: The label below the triangle: a string or a number, typeset as math,
                or a mobject; None for none.
            label_color: The label's color; None to leave it as it is.
            triangle_size: The triangle's height, in scene units.
            triangle_color: The triangle's color.
            line_func: The class of the line: [Line][manimgx.Line] (solid),
                [DashedLine][manimgx.DashedLine], ….
            line_color: The line's color.

        Returns:
            A new group of the label (if any), the triangle and the line; not added to
            the axes.

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesGetTLabelExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 10], y_range=[0, 10], y_length=6)
                    graph = axes.plot(lambda x: 3 * np.sqrt(x), color=m.BLUE)
                    t_label = axes.get_T_label(4, graph, label=m.MathTex("x = 4"))
                    self.add(axes, graph)
                    self.play(m.FadeIn(t_label))
            ```
        """
        T_label_group = VGroup()
        triangle = RegularPolygon(n=3, start_angle=np.pi / 2, stroke_width=0).set_fill(
            color=triangle_color, opacity=1
        )
        triangle.height = triangle_size
        triangle.move_to(self.coords_to_point(x_val, 0), UP)
        if label is not None:
            t_label = self.x_axis._create_label_tex(label)
            if label_color is not None:
                t_label.set_color(label_color)
            t_label.next_to(triangle, DOWN)
            T_label_group.add(t_label)
        v_line = self.get_vertical_line(
            self.i2gp(x_val, graph), color=line_color, line_func=line_func
        )
        T_label_group.add(triangle, v_line)
        return T_label_group

    def plot_line_graph(
        self,
        x_values: Iterable[float],
        y_values: Iterable[float],
        z_values: Iterable[float] | None = None,
        line_color: ParsableManimColor = PURE_YELLOW,
        add_vertex_dots: bool = True,
        vertex_dot_radius: float = DEFAULT_DOT_RADIUS,
        vertex_dot_style: Style | None = None,
        **kwargs: Unpack[Style],
    ) -> VDict:
        """Plot a line graph: straight segments through points given by their
        coordinates, with a dot at each point; bright yellow (`PURE_YELLOW`), with white
        dots, unless styled. Empty inputs produce an empty graph.

        Args:
            x_values: The points' x coordinates.
            y_values: Their y coordinates, as many.
            z_values: Their z coordinates, on three-dimensional axes; None for 0.
            line_color: The line's color, unless the keywords give a `color`.
            add_vertex_dots: Whether a dot marks each point.
            vertex_dot_radius: The dots' radius, in scene units.
            vertex_dot_style: [Style keywords][manimgx.drawing.paint.Style] for the dots;
                None for none.
            **kwargs: [Style keywords][manimgx.drawing.paint.Style] for the line.

        Returns:
            A new [VDict][manimgx.VDict], not added to the axes, with the line
            under `"line_graph"` and the dots, in a group, under `"vertex_dots"`.

        Examples:
            ```python
            import manimgx as m


            class AxesPlotLineGraphExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 7], y_range=[0, 5], y_length=6)
                    graph = axes.plot_line_graph(
                        x_values=[0, 1.5, 2, 2.8, 4, 6.25],
                        y_values=[1, 3, 2.25, 4, 2.5, 1.75],
                        line_color=m.ORANGE,
                        vertex_dot_radius=0.12,
                        vertex_dot_style={"color": m.PURPLE},
                        stroke_width=6,
                    )
                    self.add(axes.add_coordinates())
                    self.play(m.Create(graph))
            ```
        """
        xs, ys = (
            np.array(list(x_values), dtype=float),
            np.array(list(y_values), dtype=float),
        )
        zs = (
            np.zeros(xs.shape)
            if z_values is None
            else np.array(list(z_values), dtype=float)
        )
        line_graph = VDict()
        if kwargs.get("color") is None:  # not given, None too
            kwargs["color"] = line_color
        graph = VMobject(**kwargs)
        vertices = self.coords_to_point(*np.array((xs, ys, zs))).T
        graph.set_points_as_corners(vertices)
        line_graph["line_graph"] = graph
        if add_vertex_dots:
            line_graph["vertex_dots"] = VGroup(
                *(
                    Dot(
                        point=vertex.copy(),  # the dot retains its center
                        radius=vertex_dot_radius,
                        **(vertex_dot_style or Style()),
                    )
                    for vertex in vertices
                )
            )
        return line_graph

    def __matmul__(self, coord: Point3DLike | Mobject) -> np.ndarray:
        if isinstance(coord, Mobject):
            coord = coord.get_center()
        return self.coords_to_point(*coord)


def _full_range(given: Sequence[float] | None, radius: float) -> Sequence[float]:
    """An axis' (min, max, step): the frame's width or height, by 1, unless given."""
    if given is None:
        return [round(-radius), round(radius), 1]
    return [*given, 1] if len(given) == 2 else given


def _origin_shift(axis_range: Sequence[float]) -> float:
    """Where an axis crosses the others: 0, or the end of its range nearest 0."""
    if axis_range[0] > 0:
        return axis_range[0]
    if axis_range[1] < 0:
        return axis_range[1]
    return 0


class _AxesOptions(_Style, total=False):
    """AxesOptions's keys, open, for the keywords that add to them."""

    axis_config: NumberLineOptions | None
    """[Number line keywords][manimgx.NumberLine]
    for every axis: `include_numbers`, `font_size`, `color`, … (default None: none)."""
    x_axis_config: NumberLineOptions | None
    """Number line keywords for the x-axis, over `axis_config`'s (default None:
    none)."""
    y_axis_config: NumberLineOptions | None
    """Number line keywords for the y-axis, over `axis_config`'s (default None:
    none)."""
    tips: bool
    """Whether each axis ends in an arrow tip (default True; a plane's axes have none,
    unless `axis_config` includes `include_tip`)."""


class AxesOptions(_AxesOptions, total=False, closed=True):
    """[Axes][manimgx.Axes]' keywords but their ranges and lengths, for the classes that
    pass them on ([ThreeDAxes][manimgx.ThreeDAxes], the planes,
    [BarChart][manimgx.BarChart]): their axes' configs and tips, with the style
    keywords."""


def _origin_tick(config_: NumberLineOptions) -> NumberLineOptions:
    """A linear axis leaves its origin unticked (the other axis crosses there)."""
    return config_ | {
        "exclude_origin_tick": isinstance(
            config_.get("scaling", LinearBase()), LinearBase
        )
    }


class ThreeDAxes(Axes):
    """Three-dimensional axes: a z-axis out of the screen, through the origin of x- and
    y-axes; white, with tips, and shaded by a three-dimensional scene's light, unless
    configured.

    The z-axis is made as the others, over `z_range`, and points OUT, crossing them at
    its 0 (or at the end of its range nearest 0). Each axis is drawn as short pieces,
    shaded as three-dimensional objects are, with a slight sheen toward the light.
    Coordinates are converted with three numbers, `axes.c2p(x, y, z)`, and everything
    [Axes][manimgx.Axes] do, these axes do. Seen
    from straight above, they look like two-dimensional axes: turn the camera
    ([set_camera_orientation][manimgx.ThreeDScene.set_camera_orientation]) to see
    their depth.

    Common axis options are captured when construction starts; each
    finished number line retains its own runtime defaults.

    Args:
        x_range: The x-axis's range, `[x_min, x_max, x_step]`, or `[x_min, x_max]` for
            a step of 1; None for [-7, 7, 1].
        y_range: The y-axis's range, likewise; None for [-4, 4, 1].
        z_range: The z-axis's range, likewise; None for [-7, 7, 1].
        x_length: The x-axis's length, in scene units; None for the frame's short side
            plus 2.5 (10.5, in a wide video and a tall one), or `unit_size` per unit if
            the axis's config gives one.
        y_length: The y-axis's length, in scene units; None for 10.5 too, or `unit_size`
            per unit if the axis's config gives one.
        z_length: The z-axis's length, in scene units; None for the frame's short side
            less 1.5 (6.5), or `unit_size` per unit if the axis's config gives one.
        z_axis_config: [Number line keywords][manimgx.NumberLine]
            for the z-axis, over `axis_config`'s; None for none.
        **kwargs: [Axes keywords][manimgx.mobjects.plotting.AxesOptions]:
            `axis_config`, `x_axis_config`, `y_axis_config`, `tips`.

    Examples:
        ```python
        import manimgx as m


        class ThreeDAxesExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=60 * m.DEGREES, theta=-50 * m.DEGREES)
                axes = m.ThreeDAxes(
                    x_range=(-4, 4),
                    y_range=(-4, 4),
                    z_range=(-3, 3),
                    x_length=8,
                    y_length=8,
                    z_length=6,
                )
                dot = m.Dot3D(axes.c2p(2, 3, 2), radius=0.15, color=m.YELLOW)
                self.add(axes, axes.get_axis_labels(), dot)
        ```
    """

    def __init__(
        self,
        x_range: Sequence[float] | None = (-6, 6, 1),
        y_range: Sequence[float] | None = (-5, 5, 1),
        z_range: Sequence[float] | None = (-4, 4, 1),
        x_length: float | None = None,
        y_length: float | None = None,
        z_length: float | None = None,
        z_axis_config: NumberLineOptions | None = None,
        **kwargs: Unpack[AxesOptions],
    ):
        axis_config = merged_axis_config(
            {"include_tip": kwargs.get("tips", True), "numbers_to_exclude": [0]},
            kwargs.get("axis_config"),
        )
        kwargs["axis_config"] = axis_config
        super().__init__(
            x_range=x_range,
            x_length=x_length,
            y_range=y_range,
            y_length=y_length,
            **kwargs,
        )
        self.z_range = z_range
        """The z-axis's range, as given."""
        z_axis_config = _origin_tick(merged_axis_config(axis_config, z_axis_config))
        self.dimension = 3
        z_axis = self._create_axis(self.z_range, z_axis_config, z_length, 2)
        z_origin = _origin_shift([z_axis.x_min, z_axis.x_max])
        z_axis.rotate_about_number(z_origin, -PI / 2, UP)
        z_axis.rotate_about_number(z_origin, angle_of_vector(DOWN))
        z_axis.shift(-z_axis.number_to_point(z_origin))
        z_axis.shift(
            self.x_axis.number_to_point(
                _origin_shift([self.x_axis.x_min, self.x_axis.x_max])
            )
        )
        self.axes.add(z_axis)
        self.add(z_axis)
        self.z_axis = z_axis
        """The z-axis, a [NumberLine][manimgx.NumberLine]."""
        self.z_length = z_axis.get_length()
        self._add_3d_pieces()
        self._set_axis_shading()

    def _fitting_length(self, index: int) -> float:
        """The length of an axis given none (0: x, 1: y, 2: z), from the frame's short
        side, which a wide video and a tall one share."""
        short = min(config.frame_width, config.frame_height)
        return short - 1.5 if index == 2 else short + 2.5

    def _add_3d_pieces(self) -> None:
        for axis in self.axes:
            drawing = VMobject(z_index=axis.z_index)
            drawing._geometry, drawing.paint = axis._geometry, axis.paint
            axis.add(drawing.get_pieces(20))
            axis.set_stroke(width=0, family=False)
            axis.set_shade_in_3d(True)

    def _set_axis_shading(self) -> None:
        """A sheen toward the light, across each whole axis (not piece by piece)."""
        toward_light = np.sign(9 * DOWN + 7 * LEFT + 10 * OUT)
        for axis in self.axes:
            for piece in axis.family_members_with_points():
                if isinstance(piece, VMobject):
                    piece.gradient_frame = axis
                piece.set_sheen(0.2, toward_light)

    def get_y_axis_label(
        self,
        label: Label,
        edge: Vector3DLike = UR,
        direction: Vector3DLike = UR,
        buff: float = SMALL_BUFF,
        rotation: float = PI / 2,
        rotation_axis: Vector3DLike = OUT,
    ) -> Mobject:
        """Make a label for the y-axis, by its end, turned to lie along it.

        A string or a number is typeset with the axes' `label_constructor` (as math,
        with [MathTex][manimgx.MathTex], by default); a mobject is used as it is. The
        label is put next to a corner of the axis, toward `direction`, moved onto the
        screen if it is off it, then turned about its center.

        Args:
            label: The label: a string, a number or a mobject.
            edge: The corner of the axis the label is put by, as a direction: UR, the
                upper right one, by its end.
            direction: The direction the label is put toward, from that corner.
            buff: The gap between the corner and the label, in scene units.
            rotation: The angle the label is turned through, in radians: a quarter
                turn, counterclockwise.
            rotation_axis: The axis it is turned about: OUT turns it in the xy-plane.

        Returns:
            The label, not added to the axes.
        """
        placed = super().get_y_axis_label(label, edge, direction, buff)
        return placed.rotate(rotation, axis=rotation_axis)

    def get_z_axis_label(
        self,
        label: Label,
        edge: Vector3DLike = OUT,
        direction: Vector3DLike = RIGHT,
        buff: float = SMALL_BUFF,
        rotation: float = PI / 2,
        rotation_axis: Vector3DLike = RIGHT,
    ) -> Mobject:
        """Make a label for the z-axis, by its end, stood upright.

        A string or a number is typeset with the axes' `label_constructor` (as math,
        with [MathTex][manimgx.MathTex], by default); a mobject is used as it is. The
        label is put next to the axis's end, toward `direction`, moved onto the screen
        if it is off it, then turned about its center: by default a quarter turn about
        RIGHT, which stands it up out of the xy-plane.

        Args:
            label: The label: a string, a number or a mobject.
            edge: The point of the axis the label is put by, as a direction: OUT, its
                end.
            direction: The direction the label is put toward, from that point.
            buff: The gap between the point and the label, in scene units.
            rotation: The angle the label is turned through, in radians.
            rotation_axis: The axis it is turned about.

        Returns:
            The label, not added to the axes.
        """
        placed = self._get_axis_label(label, self.z_axis, edge, direction, buff)
        return placed.rotate(rotation, axis=rotation_axis)

    def get_axis_labels(
        self, x_label: Label = "x", y_label: Label = "y", z_label: Label = "z"
    ) -> VGroup:
        """Make a label for each axis, by its end, as
        [get_x_axis_label][manimgx.Axes.get_x_axis_label],
        [get_y_axis_label][manimgx.ThreeDAxes.get_y_axis_label] and
        [get_z_axis_label][manimgx.ThreeDAxes.get_z_axis_label] place them.

        Args:
            x_label: The x-axis's label: a string or a number, typeset as math, or a
                mobject.
            y_label: The y-axis's label, likewise.
            z_label: The z-axis's label, likewise.

        Returns:
            A new group of the labels, kept as the axes' `axis_labels`; not added to
            the axes.
        """
        self.axis_labels = VGroup(
            self.get_x_axis_label(x_label),
            self.get_y_axis_label(y_label),
            self.get_z_axis_label(z_label),
        )
        return self.axis_labels


class _Plane(Axes):
    """Grid planes build styled backgrounds once and prepare their paths for transforms."""

    def __init__(
        self,
        *,
        background_line_style: Style | None = None,
        faded_line_style: Style | None = None,
        faded_line_ratio: int = 1,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        **kwargs: Unpack[AxesOptions],
    ) -> None:
        background_line_style = Style(
            stroke_color=BLUE_D, stroke_width=2, stroke_opacity=1
        ) | (background_line_style or Style())
        # a plane's unit is a scene unit, unless a length or a unit_size is given
        kwargs["axis_config"] = merged_axis_config(
            {"unit_size": 1}, kwargs.get("axis_config")
        )
        super().__init__(
            x_range=x_range,
            y_range=y_range,
            x_length=x_length,
            y_length=y_length,
            **kwargs,
        )
        if faded_line_style is None:  # the background lines at half strength
            faded = background_line_style.copy()
            if (width := faded.get("stroke_width")) is not None:
                faded["stroke_width"] = width * 0.5
            if (opacity := faded.get("stroke_opacity")) is not None:
                faded["stroke_opacity"] = _halved(opacity)
            if (opacity := faded.get("fill_opacity")) is not None:
                faded["fill_opacity"] = _halved(opacity)
            faded_line_style = faded
        self.background_lines, self.faded_lines = self._get_lines(faded_line_ratio)
        for lines, style in (
            (self.background_lines, background_line_style),
            (self.faded_lines, faded_line_style),
        ):
            lines.set_style(
                fill_color=style.get("fill_color"),
                fill_opacity=style.get("fill_opacity"),
                stroke_color=style.get("stroke_color"),
                stroke_width=style.get("stroke_width"),
                stroke_opacity=style.get("stroke_opacity"),
            )
        self.add_to_back(self.faded_lines, self.background_lines)

    def _get_lines(self, faded_line_ratio: int) -> tuple[VGroup, VGroup]:
        raise NotImplementedError

    def prepare_for_nonlinear_transform(self, num_inserted_curves: int = 50) -> Self:
        """Split the plane's lines into many curves, so that a nonlinear function bends
        them smoothly.

        A function applied to the plane (with
        [apply_function][manimgx.Mobject.apply_function] or
        [apply_complex_function][manimgx.Mobject.apply_complex_function]) moves the
        points of its lines, and a straight line is a single curve: moving its few
        points would barely bend it. Each part of the plane with fewer curves than
        `num_inserted_curves` is divided into that many.

        Args:
            num_inserted_curves: How many curves each line has at least.

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class PlanePrepareForNonlinearTransformExample(m.Scene):
                def construct(self) -> None:
                    plane = m.ComplexPlane(x_range=[-3, 3, 0.5], y_range=[-2, 2, 0.5])
                    plane.prepare_for_nonlinear_transform()
                    self.add(plane)
                    self.play(plane.animate.apply_complex_function(np.sin), run_time=3)
            ```
        """
        for mob in self.family_members_with_points():
            if isinstance(mob, VMobject):
                num_curves = mob.get_num_curves()
                if num_inserted_curves > num_curves:
                    mob.insert_n_curves(num_inserted_curves - num_curves)
        return self


class NumberPlaneOptions(_AxesOptions, total=False, closed=True):
    """A [NumberPlane][manimgx.NumberPlane]'s keywords, for the scenes that pass them on
    ([LinearTransformationScene][manimgx.LinearTransformationScene], …): its ranges,
    sizes and grid, with the axes' keywords."""

    x_range: Sequence[float] | None
    """The x-axis's range, `[x_min, x_max, x_step]`: a vertical line of the grid at
    every step (default: the frame's width, by 1)."""
    y_range: Sequence[float] | None
    """The y-axis's range, `[y_min, y_max, y_step]`: a horizontal line of the grid at
    every step (default: the frame's height, by 1)."""
    x_length: float | None
    """The x-axis's length, in scene units (default None: one scene unit per unit)."""
    y_length: float | None
    """The y-axis's length, in scene units (default None: one scene unit per unit)."""
    background_line_style: Style | None
    """[Style keywords][manimgx.drawing.paint.Style] for the grid's lines, over their
    defaults: blue (`BLUE_D`), 2 wide, opaque (default None: none)."""
    faded_line_style: Style | None
    """[Style keywords][manimgx.drawing.paint.Style] for the fainter lines between them
    (default None: the grid lines' style, at half their width and opacity)."""
    faded_line_ratio: int
    """How many parts the fainter lines divide each step of the grid into: 1 for no
    fainter lines, 2 for one between each two grid lines (default 1)."""


class NumberPlane(_Plane):
    """A number plane: axes over a grid, a line at every step of each axis's range;
    filling the frame, with the scene's own coordinates, unless sized.

    The grid's lines are blue (`BLUE_D`) and 2 wide; with a `faded_line_ratio` above
    1, fainter lines divide each step further, half as wide and half as opaque unless
    styled. The lines are drawn behind the axes, which are white, 2 wide, without
    ticks or tips; their numbers, when written, are small (font size 24), below and to
    the right of their points. By default the ranges span the frame, one scene unit
    per unit, so the plane's coordinates are the scene's. Everything
    [Axes][manimgx.Axes] do, the plane does: converting coordinates, plotting,
    labeling.

    Background styles and the faded-line ratio are construction inputs; the plane
    retains its drawn grid rather than those setup attributes.

    Args:
        x_range: The x-axis's range, `[x_min, x_max, x_step]`: a vertical line of the
            grid at every step. None for the frame's width when the plane is made, by
            1.
        y_range: The y-axis's range, `[y_min, y_max, y_step]`: a horizontal line of
            the grid at every step. None for the frame's height when the plane is made,
            by 1.
        x_length: The x-axis's length, in scene units; None for one scene unit per
            unit.
        y_length: The y-axis's length, in scene units; None for one scene unit per
            unit.
        background_line_style: [Style keywords][manimgx.drawing.paint.Style] for the
            grid's lines, over their defaults; None for none.
        faded_line_style: [Style keywords][manimgx.drawing.paint.Style] for the fainter
            lines; None for the grid lines' style, at half their width and opacity.
        faded_line_ratio: How many parts the fainter lines divide each step of the
            grid into: 1 for no fainter lines, 2 for one between each two grid lines.
        **kwargs: [Axes keywords][manimgx.mobjects.plotting.AxesOptions]:
            `axis_config` over the plane's own (no ticks, no tips, font size 24), …;
            `tips` is overridden by it, so tips need `include_tip` in `axis_config`.

    Examples:
        ```python
        import manimgx as m


        class NumberPlaneExample(m.Scene):
            def construct(self) -> None:
                plane = m.NumberPlane(
                    x_range=[-6.5, 6.5, 1],
                    y_range=[-4, 4, 1],
                    faded_line_ratio=2,
                    background_line_style={"stroke_color": m.TEAL},
                )
                arrow = m.Arrow(plane.c2p(0, 0), plane.c2p(3, 2), buff=0)
                self.add(plane.add_coordinates(), arrow.set_color(m.YELLOW))
        ```
    """

    def __init__(
        self,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        background_line_style: Style | None = None,
        faded_line_style: Style | None = None,
        faded_line_ratio: int = 1,
        **kwargs: Unpack[AxesOptions],
    ):
        kwargs["axis_config"] = merged_axis_config(
            {
                "stroke_width": 2,
                "include_ticks": False,
                "include_tip": False,
                "line_to_number_buff": SMALL_BUFF,
                "label_direction": DR,
                "font_size": 24,
            },
            kwargs.get("axis_config"),
        )
        kwargs["y_axis_config"] = merged_axis_config(
            {"label_direction": DR}, kwargs.get("y_axis_config")
        )
        # the frame as it is now: a tall video's (9:16) is taller than a wide one's
        if x_range is None:
            x_range = (-config.frame_x_radius, config.frame_x_radius, 1)
        if y_range is None:
            y_range = (-config.frame_y_radius, config.frame_y_radius, 1)
        super().__init__(
            background_line_style=background_line_style,
            faded_line_style=faded_line_style,
            faded_line_ratio=faded_line_ratio,
            x_range=x_range,
            y_range=y_range,
            x_length=x_length,
            y_length=y_length,
            **kwargs,
        )

    def _get_lines(self, faded_line_ratio: int) -> tuple[VGroup, VGroup]:
        x_axis, y_axis = self.get_x_axis(), self.get_y_axis()
        x_lines1, x_lines2 = self._get_lines_parallel_to_axis(
            x_axis, y_axis, self.y_axis.x_range[2], faded_line_ratio
        )
        y_lines1, y_lines2 = self._get_lines_parallel_to_axis(
            y_axis, x_axis, self.x_axis.x_range[2], faded_line_ratio
        )
        self.x_lines, self.y_lines = x_lines1, y_lines1
        return VGroup(*x_lines1, *y_lines1), VGroup(*x_lines2, *y_lines2)

    def _get_lines_parallel_to_axis(
        self,
        axis_parallel_to: NumberLine,
        axis_perpendicular_to: NumberLine,
        freq: float,
        ratio_faded_lines: int,
    ) -> tuple[VGroup, VGroup]:
        line = Line(axis_parallel_to.get_start(), axis_parallel_to.get_end())
        ratio_faded_lines = ratio_faded_lines or 1
        step = 1 / ratio_faded_lines * freq
        lines1, lines2 = VGroup(), VGroup()
        parts1: list[Line] = []
        parts2: list[Line] = []
        unit_vector_axis_perp_to = axis_perpendicular_to.get_unit_vector()
        x_min, x_max, _ = axis_perpendicular_to.x_range
        if axis_perpendicular_to.x_min > 0 and x_min < 0:
            x_min, x_max = (0, np.abs(x_min) + np.abs(x_max))
        ranges = (  # (short of the edges, which no rounding of the steps puts a line on)
            [0],
            np.arange(step, min(x_max - x_min, x_max) - step * 1e-06, step),
            np.arange(-step, max(x_min - x_max, x_min) + step * 1e-06, -step),
        )
        for inputs in ranges:
            for k, x in enumerate(inputs):
                new_line = line.copy()
                new_line.shift(unit_vector_axis_perp_to * x)
                (parts1 if (k + 1) % ratio_faded_lines == 0 else parts2).append(
                    new_line
                )
        lines1.add(*parts1)
        lines2.add(*parts2)
        return lines1, lines2


type AzimuthUnits = Literal["PI radians", "TAU radians", "degrees", "gradians"] | None


"""How a [PolarPlane][manimgx.PolarPlane] labels its angles: as fractions of π or of τ,
in degrees, in gradians, or (None) as fractions of a turn."""


class PolarPlane(_Plane):
    """A polar plane: circles around its origin, one at every step of the radius, and
    lines out from it, a fraction of a turn apart; blue over white axes without ticks
    or tips, unless styled.

    The plane is a disc of radius `radius_max`, centered on the scene's origin, its x-
    and y-axes its radii. [add_coordinates][manimgx.PolarPlane.add_coordinates] numbers
    the radii and labels the lines' angles, in `azimuth_units`: fractions of π (3π/4),
    of τ, degrees, gradians, or fractions of a turn.
    [polar_to_point][manimgx.Axes.polar_to_point] (`pr2pt`) converts polar coordinates
    to points, and [plot_polar_graph][manimgx.Axes.plot_polar_graph] plots curves
    r = f(θ); everything [Axes][manimgx.Axes] do, the plane does.

    Background styles and the faded-line ratio are construction inputs; the plane
    retains its drawn grid rather than those setup attributes.

    Args:
        radius_max: The radius of the outer circle, in the plane's units; None for half
            the frame's short side when the plane is made (4).
        size: The plane's width, its diameter, in scene units; None for one scene unit
            per unit.
        radius_step: The distance between two circles, in the plane's units.
        azimuth_step: How many lines divide the full turn: a line every turn divided
            by it; None for the units' own: 20 for radians, 36 for degrees, 40 for
            gradians, 1 for fractions of a turn.
        azimuth_units: How the angles are labeled: `"PI radians"` (fractions of π),
            `"TAU radians"` (fractions of τ), `"degrees"`, `"gradians"`, or None
            (fractions of a turn, as decimals).
        azimuth_compact_fraction: Whether a fraction of π or τ is written with the
            constant in its numerator (3π/4), rather than after it (3/4 π).
        azimuth_offset: The angle of the line labeled 0, in radians, counterclockwise
            from the right: the lines and their labels turn with it.
        azimuth_direction: The direction the angles increase in: `"CCW"`,
            counterclockwise, or `"CW"`, clockwise.
        azimuth_label_buff: The gap between the outer circle and the angles' labels, in
            scene units.
        azimuth_label_font_size: The font size of the angles' labels.
        radius_config: [Number line keywords][manimgx.NumberLine]
            for the radii's axes, over the plane's own (no ticks, no tips, 2 wide,
            font size 24, numbers below and to the left); None for none.
        background_line_style: [Style keywords][manimgx.drawing.paint.Style] for the
            circles and lines, over their defaults: blue (`BLUE_D`), 2 wide, opaque;
            None for none.
        faded_line_style: [Style keywords][manimgx.drawing.paint.Style] for the fainter
            circles and lines; None for the others' style, at half their width and
            opacity.
        faded_line_ratio: How many parts fainter circles and lines divide each step
            into: 1 for none.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] of the plane's group
            itself: as it has no points, they do not restyle its lines.

    Examples:
        ```python
        import manimgx as m


        class PolarPlaneExample(m.Scene):
            def construct(self) -> None:
                planes = m.VGroup(
                    m.PolarPlane(radius_max=2, size=5.5, radius_step=0.5),
                    m.PolarPlane(
                        radius_max=2,
                        size=5.5,
                        azimuth_units="degrees",
                        azimuth_step=12,
                        faded_line_ratio=2,
                    ),
                )
                for plane in planes:
                    plane.add_coordinates()
                self.add(planes.arrange(buff=1.5))
        ```
    """

    def __init__(
        self,
        radius_max: float | None = None,
        size: float | None = None,
        radius_step: float = 1,
        azimuth_step: float | None = None,
        azimuth_units: AzimuthUnits = "PI radians",
        azimuth_compact_fraction: bool = True,
        azimuth_offset: float = 0,
        azimuth_direction: Literal["CW", "CCW"] = "CCW",
        azimuth_label_buff: float = SMALL_BUFF,
        azimuth_label_font_size: float = 24,
        radius_config: NumberLineOptions | None = None,
        background_line_style: Style | None = None,
        faded_line_style: Style | None = None,
        faded_line_ratio: int = 1,
        **kwargs: Unpack[Style],
    ):
        self.azimuth_units, self.azimuth_direction = azimuth_units, azimuth_direction
        radius = (
            min(config.frame_x_radius, config.frame_y_radius)
            if radius_max is None
            else radius_max
        )
        radius_config = merged_axis_config(
            {
                "stroke_width": 2,
                "include_ticks": False,
                "include_tip": False,
                "line_to_number_buff": SMALL_BUFF,
                "label_direction": DL,
                "font_size": 24,
            },
            radius_config,
        )
        # Snapshot before assigning azimuth properties, which subclasses may override.
        background_line_style = (background_line_style or Style()).copy()
        default_steps = {
            "PI radians": 20,
            "TAU radians": 20,
            "degrees": 36,
            "gradians": 40,
            None: 1,
        }
        self.azimuth_step = (
            default_steps[azimuth_units] if azimuth_step is None else azimuth_step
        )
        self.azimuth_offset = azimuth_offset
        self.azimuth_label_buff = azimuth_label_buff
        self.azimuth_label_font_size = azimuth_label_font_size
        self.azimuth_compact_fraction = azimuth_compact_fraction
        super().__init__(
            background_line_style=background_line_style,
            faded_line_style=faded_line_style,
            faded_line_ratio=faded_line_ratio,
            x_range=(-radius, radius, radius_step),
            y_range=(-radius, radius, radius_step),
            x_length=size,
            y_length=size,
            axis_config=radius_config,
            **kwargs,
        )

    def _get_lines(self, faded_line_ratio: int) -> tuple[VGroup, VGroup]:
        center = self.get_origin()
        ratio_faded_lines = faded_line_ratio or 1
        rstep = 1 / ratio_faded_lines * self.x_axis.x_range[2]
        astep = 1 / ratio_faded_lines * (TAU * (1 / self.azimuth_step))
        rlines1, rlines2, alines1, alines2 = VGroup(), VGroup(), VGroup(), VGroup()
        parts1: list[VMobject] = []
        parts2: list[VMobject] = []
        unit_vector = self.x_axis.get_unit_vector()[0]
        # (the circles to the radius, the lines short of a whole turn: no rounding of the
        # steps adds one beyond them)
        for k, x in enumerate(
            np.arange(0, self.x_axis.x_range[1] + rstep * 1e-06, rstep)
        ):
            (parts1 if k % ratio_faded_lines == 0 else parts2).append(
                Circle(radius=x * unit_vector)
            )
        alines1.add(*parts1)
        alines2.add(*parts2)
        parts1, parts2 = [], []
        line = Line(center, self.get_x_axis().get_end())
        for k, x in enumerate(np.arange(0, TAU - astep * 1e-06, astep)):
            new_line = line.copy()
            new_line.rotate(x + self.azimuth_offset, about_point=center)
            (parts1 if k % ratio_faded_lines == 0 else parts2).append(new_line)
        rlines1.add(*parts1)
        rlines2.add(*parts2)
        return VGroup(*rlines1, *alines1), VGroup(*rlines2, *alines2)

    def get_coordinate_labels(
        self,
        r_values: Iterable[float] | None = None,
        a_values: Iterable[float] | None = None,
    ) -> VGroup:
        """Number the plane's radii, and make labels for its angles.

        The radii are numbered along the x-axis, right of the center; the numbers are
        added to the axis. The angles' labels, in the plane's `azimuth_units`, go around
        the outer circle, `azimuth_label_buff` beyond it: placed for a plane centered on
        the scene's origin, as it is made.

        Args:
            r_values: The radii to number, in the plane's units; None for every
                circle's but 0.
            a_values: The angles to label, as fractions of a turn (0.25 is a quarter
                turn); None for every line's.

        Returns:
            A new group of the x-axis, now numbered, and a group of the angles' labels
            (not added to the plane); kept as the plane's `coordinate_labels`.
        """
        if r_values is None:
            r_values = [r for r in self.get_x_axis().get_tick_range() if r >= 0]
        if a_values is None:
            a_values = np.arange(0, 1, 1 / self.azimuth_step)
        r_mobs = self.get_x_axis().add_numbers(r_values)
        d = 1 if self.azimuth_direction == "CCW" else -1
        radius = self.get_right()[0]
        labels = VGroup()
        for i in a_values:
            angle = d * (i * TAU) + self.azimuth_offset
            point = np.array([radius * np.cos(angle), radius * np.sin(angle), 0])
            label = self._azimuth_label(i)
            labels.add(
                label.next_to(
                    point,
                    direction=point,
                    aligned_edge=point,
                    buff=self.azimuth_label_buff,
                )
            )
        self.coordinate_labels = VGroup(r_mobs, labels)
        return self.coordinate_labels

    def _azimuth_label(self, turns: float) -> MathTex:
        """The label of the direction `turns` of a full turn, in the plane's units."""
        size = self.azimuth_label_font_size
        match self.azimuth_units:
            case "PI radians" | "TAU radians":
                return self.get_radian_label(turns, font_size=size)
            case "degrees":
                return MathTex(f"{360 * turns:g}" + "^{\\circ}", font_size=size)
            case "gradians":
                return MathTex(f"{400 * turns:g}" + "^{g}", font_size=size)
            case _:
                return MathTex(f"{turns:g}", font_size=size)

    def add_coordinates(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: a polar plane numbers radii and angles
        self,
        r_values: Iterable[float] | None = None,
        a_values: Iterable[float] | None = None,
    ) -> Self:
        """Number the plane's radii along its x-axis, and label its angles around it,
        as [get_coordinate_labels][manimgx.PolarPlane.get_coordinate_labels] makes them.

        Args:
            r_values: The radii to number, in the plane's units; None for every
                circle's but 0.
            a_values: The angles to label, as fractions of a turn (0.25 is a quarter
                turn); None for every line's.
        """
        self.add(self.get_coordinate_labels(r_values, a_values))
        return self

    def get_radian_label(
        self, number: float, **kwargs: Unpack[MathTexOptions]
    ) -> MathTex:
        """Make the label of an angle in radians: a fraction of π, or of τ if the
        plane's units are `"TAU radians"`.

        The fraction is the nearest with a denominator up to 100, written as the plane's
        `azimuth_compact_fraction` says: 3π/4, or 3/4 π.

        Args:
            number: The angle, as a fraction of a turn (0.375 for 3π/4).
            **kwargs: [Math keywords][manimgx.MathTex]
                for the label; its font size is 24 unless given.

        Returns:
            A new [MathTex][manimgx.MathTex].
        """
        kwargs.setdefault("font_size", 24)
        units = (
            self.azimuth_units
            if self.azimuth_units in ("PI radians", "TAU radians")
            else "PI radians"
        )
        constant = {"PI radians": "\\pi", "TAU radians": "\\tau"}[units]
        frac = fr.Fraction(number * {"PI radians": 2, "TAU radians": 1}[units])
        p, q = (frac := frac.limit_denominator(100)).numerator, frac.denominator
        if p == 0:
            string = "0"
        elif q == 1:
            string = constant if p == 1 else f"{p}{constant}"
        elif self.azimuth_compact_fraction:
            string = f"\\tfrac{{{'' if p == 1 else p}{constant}}}{{{q}}}"
        else:
            string = f"\\tfrac{{{p}}}{{{q}}}{constant}"
        return MathTex(string, **kwargs)


class ComplexPlane(NumberPlane):
    """A complex plane: a [NumberPlane][manimgx.NumberPlane] whose points are complex
    numbers, x + yi at the point of coordinates (x, y).

    [number_to_point][manimgx.ComplexPlane.number_to_point] (`n2p`) and
    [point_to_number][manimgx.ComplexPlane.point_to_number] (`p2n`) convert between
    numbers and points, and [add_coordinates][manimgx.ComplexPlane.add_coordinates]
    writes the real numbers along the x-axis and the imaginary ones (with `i`) along
    the y-axis. A function of complex numbers maps the plane with
    [apply_complex_function][manimgx.Mobject.apply_complex_function]. It takes the
    arguments of a [NumberPlane][manimgx.NumberPlane], and does everything it does.

    Examples:
        ```python
        import manimgx as m


        class ComplexPlaneExample(m.Scene):
            def construct(self) -> None:
                plane = m.ComplexPlane(x_range=[-6.5, 6.5, 1]).add_coordinates()
                self.add(plane)
                for z, name in ((2 + 1j, "2+i"), (-3 - 2j, "-3-2i")):
                    dot = m.Dot(plane.n2p(z), radius=0.12, color=m.YELLOW)
                    self.add(dot, m.MathTex(name).next_to(dot, m.UR, buff=0.1))
        ```
    """

    def number_to_point(self, number: float | complex) -> Point3D:
        """Convert a complex number to its point on the plane: x + yi to the point of
        coordinates (x, y).

        `n2p` is its short name.

        Args:
            number: The number; a real number is on the x-axis.

        Returns:
            The point, in scene coordinates.
        """
        number = complex(number)
        return self.coords_to_point(number.real, number.imag)

    def point_to_number(self, point: Point3DLike) -> complex:
        """Convert a point to the complex number at it: x + yi, for the point's
        coordinates (x, y).

        `p2n` is its short name.

        Args:
            point: The point, in scene coordinates.
        """
        x, y = self.point_to_coords(point)[:2]
        return complex(x, y)

    n2p, p2n = number_to_point, point_to_number

    def _get_default_coordinate_values(self) -> list[float | complex]:
        x_numbers = [float(x) for x in self.get_x_axis().get_tick_range()]
        y_numbers = [
            complex(0, y) for y in self.get_y_axis().get_tick_range() if y != 0
        ]
        return [*x_numbers, *y_numbers]

    def get_coordinate_labels(
        self, *numbers: float | complex, **kwargs: Unpack[DecimalNumberOptions]
    ) -> VGroup:
        """Make labels for numbers of the plane: a real number by its point on the
        x-axis, an imaginary one, with `i`, by its point on the y-axis.

        A number is written as its larger part: its imaginary part, by the y-axis, if
        that is larger in size than its real part; its real part, by the x-axis,
        otherwise. Each is written as the axis numbers its ticks (see
        [get_number_mobject][manimgx.NumberLine.get_number_mobject]).

        Args:
            *numbers: The numbers to label; none for the ticks of both axes, but 0.
            **kwargs: [Number keywords][manimgx.DecimalNumber]
                for the labels: `font_size`, `num_decimal_places`, `color`, ….

        Returns:
            A new group of the labels, kept as the plane's `coordinate_labels`; not
            added to the plane.
        """
        self.coordinate_labels = VGroup()
        for number in numbers or self._get_default_coordinate_values():
            z = complex(number)
            if abs(z.imag) > abs(z.real):
                self.coordinate_labels.add(
                    self.get_y_axis().get_number_mobject(
                        z.imag, **(kwargs | {"unit": "i"})
                    )
                )
            else:
                self.coordinate_labels.add(
                    self.get_x_axis().get_number_mobject(z.real, **kwargs)
                )
        return self.coordinate_labels

    def add_coordinates(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: numbers, not per-axis values
        self, *numbers: float | complex, **kwargs: Unpack[DecimalNumberOptions]
    ) -> Self:
        """Label numbers of the plane, as
        [get_coordinate_labels][manimgx.ComplexPlane.get_coordinate_labels] makes the
        labels, and add them to the plane.

        Args:
            *numbers: The numbers to label; none for the ticks of both axes, but 0.
            **kwargs: [Number keywords][manimgx.DecimalNumber]
                for the labels: `font_size`, `num_decimal_places`, `color`, ….
        """
        self.add(self.get_coordinate_labels(*numbers, **kwargs))
        return self


EPSILON = 0.0001


"""How far from 1 probabilities may sum before a sample space adds the rest as a
part."""


class SampleSpace(Rectangle):
    """A sample space: a rectangle standing for all the outcomes, to divide into parts
    whose areas are probabilities; dark grey, filled, with a thin light grey outline,
    unless styled.

    [divide_vertically][manimgx.SampleSpace.divide_vertically] splits it into vertical
    strips, one per probability, from left to right, and keeps them as its
    `vertical_parts`;
    [get_division_along_dimension][manimgx.SampleSpace.get_division_along_dimension]
    makes the parts of a division along either side, in either direction. Each part is
    a sample space itself, which can be divided in turn.

    Args:
        height: Its height, in scene units.
        width: Its width, in scene units.
        default_label_scale_val: Accepted for Manim compatibility; ignored.

    Examples:
        ```python
        import manimgx as m


        class SampleSpaceExample(m.Scene):
            def construct(self) -> None:
                space = m.SampleSpace(width=6, height=5)
                space.divide_vertically(0.4, colors=[m.BLUE_E, m.GREY_BROWN])
                rain, dry = space.vertical_parts
                colors = [m.RED_E, m.TEAL_E]
                rain.add(rain.get_division_along_dimension(0.7, 1, colors, m.DOWN))
                dry.add(dry.get_division_along_dimension(0.2, 1, colors, m.DOWN))
                rain_label = m.Text("rain").next_to(rain, m.DOWN)
                dry_label = m.Text("dry").next_to(dry, m.DOWN)
                self.add(space, rain_label, dry_label)
        ```
    """

    defaults: ClassVar[Style] = {
        "fill_color": DARK_GREY,
        "fill_opacity": 1.0,
        "stroke_width": 0.5,
        "stroke_color": LIGHT_GREY,
    }

    def __init__(
        self,
        height: float = 3,
        width: float = 3,
        default_label_scale_val: float = 1,
        **kwargs: Unpack[Style],
    ):
        super().__init__(height=height, width=width, **kwargs)
        self.default_label_scale_val = default_label_scale_val

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def complete_p_list(self, p_list: float | Iterable[float]) -> list[float]:
        """The probabilities of a division, completed to sum to 1: the rest, 1 minus
        their sum, is added as one more, unless it is within 0.0001 of 0.

        Args:
            p_list: A probability, or probabilities.

        Returns:
            A new list of the probabilities.
        """
        new_p_list: list[float] = (
            list(p_list) if isinstance(p_list, Iterable) else [p_list]
        )
        remainder = 1.0 - sum(new_p_list)
        if abs(remainder) > EPSILON:
            new_p_list.append(remainder)
        return new_p_list

    def get_division_along_dimension(
        self,
        p_list: float | Iterable[float],
        dim: int,
        colors: Sequence[ParsableManimColor],
        vect: Vector3D,
    ) -> VGroup:
        """Make the parts that divide the sample space along a dimension, one per
        probability, each that fraction of it.

        The parts follow one another in the direction `vect`, from the space's edge
        opposite it; they are colored along a gradient of `colors`, and each is a sample
        space itself.

        Args:
            p_list: The probabilities: a part is added for the rest, if they sum to less
                than 1.
            dim: The dimension divided: 0 for the width, 1 for the height.
            colors: The colors, a gradient over the parts.
            vect: The direction the parts follow one another in.

        Returns:
            A new group of the parts, not added to the space.
        """
        p_list_complete = self.complete_p_list(p_list)
        last_point = self.get_critical_point(-vect)
        parts = VGroup()
        for factor, color in zip(
            p_list_complete, color_gradient(colors, len(p_list_complete)), strict=True
        ):
            part = SampleSpace()
            part.set_fill(color, 1)
            part.replace(self, stretch=True)
            part.stretch(factor, dim)
            part.move_to(last_point, -vect)
            last_point = part.get_critical_point(vect)
            parts.add(part)
        return parts

    def get_vertical_division(
        self,
        p_list: float | Iterable[float],
        colors: Sequence[ParsableManimColor] = (MAROON_B, YELLOW),
        vect: Vector3D = RIGHT,
    ) -> VGroup:
        """Make vertical strips that divide the sample space, one per probability, from
        left to right (see
        [get_division_along_dimension][manimgx.SampleSpace.get_division_along_dimension]).

        Args:
            p_list: The probabilities, completed to sum to 1.
            colors: The colors, a gradient over the strips.
            vect: The direction the strips follow one another in: RIGHT, from the left.

        Returns:
            A new group of the strips, not added to the space.
        """
        return self.get_division_along_dimension(p_list, 0, colors, vect)

    def divide_vertically(
        self,
        p_list: float | Iterable[float],
        colors: Sequence[ParsableManimColor] = (MAROON_B, YELLOW),
        vect: Vector3D = RIGHT,
    ) -> Self:
        """Divide the sample space into vertical strips, one per probability, from left
        to right: each is that fraction of its width.

        The probabilities are completed to sum to 1. The strips are added to the space,
        as one group, and kept as its `vertical_parts`.

        Args:
            p_list: A probability, or probabilities.
            colors: The strips' colors: a gradient over them.
            vect: The direction the strips follow one another in: RIGHT, from the left.

        Examples:
            ```python
            import manimgx as m


            class SampleSpaceDivideVerticallyExample(m.Scene):
                def construct(self) -> None:
                    space = m.SampleSpace(width=9, height=4)
                    space.divide_vertically([0.25, 0.25], colors=[m.RED_E, m.GOLD_E])
                    parts = space.vertical_parts
                    labels = [m.Text(n).move_to(p) for n, p in zip("ABC", parts)]
                    self.add(space, *labels)
            ```
        """
        self.vertical_parts = self.get_vertical_division(p_list, colors, vect)
        self.add(self.vertical_parts)
        return self


class BarChart(Axes):
    """A bar chart: a bar for each value, rising from the x-axis (or hanging below it,
    for a negative value), on axes with a numbered y-axis; the bars colored along a
    gradient.

    Each bar stands in its own unit of the x-axis, centered in it and `bar_width` of it
    wide, and it is as tall as its value, in the y-axis's units. The bars' names go
    below the x-axis (above it, under a negative bar).
    [change_bar_values][manimgx.BarChart.change_bar_values] changes the bars, and
    [get_bar_labels][manimgx.BarChart.get_bar_labels] writes their values beside them.
    The chart is [Axes][manimgx.Axes]: its x-axis runs from 0 to the number of bars.

    Args:
        values: The values, one bar each, from left to right.
        bar_names: The bars' names, written by the x-axis, typeset as text; None for
            none.
        y_range: The y-axis's range, `[y_min, y_max, y_step]`; None to fit the values,
            from 0 (or the lowest value, if negative) to the highest (or 0), with a step
            of about one scene unit. Given two numbers, the step is that one.
        x_length: The x-axis's length, in scene units; None for one scene unit per bar,
            at most the frame's width less 2.
        y_length: The y-axis's length, in scene units; None for 4, the frame's height
            less 4.
        bar_colors: The bars' colors: a gradient over them, from left to right.
        bar_width: Each bar's width, as a fraction of its unit of the x-axis.
        bar_fill_opacity: The bars' fill opacity, from 0 to 1.
        bar_stroke_width: The width of the bars' outlines, in hundredths of a scene
            unit.
        **kwargs: [Axes keywords][manimgx.mobjects.plotting.AxesOptions]:
            `x_axis_config` (over the chart's: numbers of size 24, typeset with
            [Tex][manimgx.Tex]), `tips` (default False), ….

    Examples:
        ```python
        import manimgx as m


        class BarChartExample(m.Scene):
            def construct(self) -> None:
                chart = m.BarChart(
                    values=[-5, 40, -10, 20, -3],
                    bar_names=["one", "two", "three", "four", "five"],
                    y_range=[-20, 50, 10],
                    x_length=10,
                    y_length=6,
                    x_axis_config={"font_size": 36},
                )
                self.add(chart)
        ```
    """

    def __init__(
        self,
        values: Sequence[float],
        bar_names: Sequence[str] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        bar_colors: Iterable[ParsableManimColor] = (
            "#003f5c",
            "#58508d",
            "#bc5090",
            "#ff6361",
            "#ffa600",
        ),
        bar_width: float = 0.6,
        bar_fill_opacity: float = 0.7,
        bar_stroke_width: float = 3,
        **kwargs: Unpack[AxesOptions],
    ):
        y_length = y_length if y_length is not None else config.frame_height - 4
        self.values = list(values)
        """The chart's values, one per bar, as they are now."""
        self.bar_names = bar_names
        self.bar_colors = list(bar_colors)
        self.bar_width = bar_width
        self.bar_fill_opacity = bar_fill_opacity
        self.bar_stroke_width = bar_stroke_width
        x_range = [0, len(self.values), 1]
        if y_range is None:
            y_range = [
                min(0, min(self.values)),
                max(0, max(self.values)),
                round(max(self.values) / y_length, 2),
            ]
        elif len(y_range) == 2:
            y_range = [*y_range, round(max(self.values) / y_length, 2)]
        if x_length is None:
            x_length = min(len(self.values), config.frame_width - 2)
        kwargs["x_axis_config"] = merged_axis_config(
            {"font_size": 24, "label_constructor": Tex}, kwargs.get("x_axis_config")
        )
        kwargs.setdefault("tips", False)
        self.bars: VGroup = VGroup()
        """The bars, rectangles, from left to right."""
        self.x_labels: VGroup | None = None
        self.bar_labels: VGroup | None = None
        super().__init__(
            x_range=x_range,
            y_range=y_range,
            x_length=x_length,
            y_length=y_length,
            **kwargs,
        )
        self._add_bars()
        if self.bar_names is not None:
            self._add_x_axis_labels()
        self.y_axis.add_numbers()

    def _update_colors(self) -> None:
        self.bars.set_color_by_gradient(*self.bar_colors)

    def _add_x_axis_labels(self) -> None:
        if self.bar_names is None:
            return
        val_range = np.arange(0.5, len(self.bar_names), 1)
        labels = VGroup()
        for i, (value, bar_name) in enumerate(
            zip(val_range, self.bar_names, strict=True)
        ):
            direction = UP if self.values[i] < 0 else DOWN
            bar_name_label = self.x_axis.label_constructor(bar_name)
            bar_name_label.font_size = self.x_axis.font_size
            bar_name_label.next_to(
                self.x_axis.number_to_point(value),
                direction=direction,
                buff=self.x_axis.line_to_number_buff,
            )
            labels.add(bar_name_label)
        self.x_axis.labels = labels
        self.x_axis.add(labels)

    def _create_bar(self, bar_number: int, value: float) -> Rectangle:
        bar_h = abs(self.c2p(0, value)[1] - self.c2p(0, 0)[1])
        bar_w = self.c2p(self.bar_width, 0)[0] - self.c2p(0, 0)[0]
        bar = Rectangle(
            height=bar_h,
            width=bar_w,
            stroke_width=self.bar_stroke_width,
            fill_opacity=self.bar_fill_opacity,
        )
        pos = UP if value >= 0 else DOWN
        bar.next_to(self.c2p(bar_number + 0.5, 0), pos, buff=0)
        return bar

    def _add_bars(self) -> None:
        for i, value in enumerate(self.values):
            tmp_bar = self._create_bar(bar_number=i, value=value)
            self.bars.add(tmp_bar)
        self._update_colors()
        self.add_to_back(self.bars)

    def get_bar_labels(
        self,
        color: ParsableManimColor | None = None,
        font_size: float = 24,
        buff: float = MED_SMALL_BUFF,
        label_constructor: type[ManimTextLabel] = Tex,
    ) -> VGroup:
        """Make labels of the bars' values: each above its bar (below it, for a
        negative value), in the bar's color unless given another.

        Args:
            color: The labels' color; None for each bar's fill color.
            font_size: Their font size.
            buff: The gap between each bar and its label, in scene units.
            label_constructor: The class they are typeset with: [Tex][manimgx.Tex],
                [MathTex][manimgx.MathTex], ….

        Returns:
            A new group of the labels, from left to right, not added to the chart.

        Examples:
            ```python
            import manimgx as m


            class BarChartGetBarLabelsExample(m.Scene):
                def construct(self) -> None:
                    chart = m.BarChart(
                        values=[9, 7, 4, 3, 1],
                        y_range=[0, 10, 2],
                        x_length=10,
                        y_length=5,
                        bar_colors=[m.BLUE, m.GREEN, m.YELLOW],
                    )
                    self.add(chart, chart.get_bar_labels(font_size=40))
            ```
        """
        bar_labels = VGroup()
        for bar, value in zip(self.bars, self.values, strict=False):
            bar_lbl = label_constructor(str(value))
            if color is None:
                bar_lbl.set_color(bar.get_fill_color())
            else:
                bar_lbl.set_color(color)
            bar_lbl.font_size = font_size
            pos = UP if value >= 0 else DOWN
            bar_lbl.next_to(bar, pos, buff=buff)
            bar_labels.add(bar_lbl)
        return bar_labels

    def change_bar_values(
        self, values: Iterable[float], update_colors: bool = True
    ) -> Self:
        """Change the bars' values: each bar is stretched to its new height from the
        x-axis, crossing to its other side if the value changes sign.

        The y-axis stays as it is, and labels made before do not follow; to animate the
        change, use `.animate`.

        Args:
            values: The new values, from left to right; fewer than the bars change the
                first ones only.
            update_colors: Whether to color the bars along the chart's gradient again (a
                bar remade from a value of 0 needs it).

        Examples:
            ```python
            import manimgx as m


            class BarChartChangeBarValuesExample(m.Scene):
                def construct(self) -> None:
                    chart = m.BarChart(
                        values=[4, 8, 2, 6], y_range=[-4, 8, 2], x_length=9, y_length=6
                    )
                    self.add(chart)
                    self.play(chart.animate.change_bar_values([7, -3, 5, 1]))
            ```
        """
        values = list(values)
        # the bars as they are: a bar remade below takes its place in `self.bars`
        for i, (bar, value) in enumerate(zip(list(self.bars), values, strict=False)):
            chart_val = self.values[i]
            if chart_val == 0:  # a bar of no height has no side to grow from: remade
                self.bars.remove(bar)
                self.bars.insert(i, self._create_bar(i, value))
                continue
            bar_lim, aligned_edge = (
                (bar.get_bottom(), DOWN) if chart_val > 0 else (bar.get_top(), UP)
            )
            quotient = value / chart_val
            if quotient < 0:
                aligned_edge = UP if chart_val > 0 else DOWN
            bar.stretch_to_fit_height(abs(quotient) * bar.height)
            bar.move_to(bar_lim, aligned_edge)
        if update_colors:
            self._update_colors()
        self.values[: len(values)] = values
        return self

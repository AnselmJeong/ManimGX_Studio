# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Ported from Manim CE 0.21 (MIT)."""

from __future__ import annotations

__all__ = ["DecimalNumber", "Integer", "Variable", "index_labels"]
from typing import ClassVar, Self, Unpack

import numpy as np

from manimgx.caches import Memo
from manimgx.constants import DEFAULT_FONT_SIZE, DOWN, LEFT, ORIGIN, RIGHT, UP
from manimgx.drawing.geometry import Blend
from manimgx.drawing.paint import BLACK, Paint, Style, _Style
from manimgx.mobject import Mobject, ValueTracker, VGroup, VMobject, copied, prototype
from manimgx.mobjects.text import MathTex, SingleStringMathTex, Text
from manimgx.typing import ManimTextLabel, Vector3DLike

# a string's glyphs laid out (CE's procedure, run once per string and layout): what laying out
# sets on the number, copied in by every later layout of the same string
_ROWS: Memo[tuple[object, ...], dict[str, object]] = Memo(1 << 12)
_ROW = ("submobjects", "initial_height", "background_rectangle")


class _NumberStyle(_Style, total=False):
    """NumberStyle's keys, open, for the keywords that add to them."""

    mob_class: type[ManimTextLabel]
    """The class each character is typeset with (default [MathTex][manimgx.MathTex])."""
    include_sign: bool
    """Whether a number that is not negative is written with a plus sign (default
    False)."""
    group_with_commas: bool
    """Whether the digits before the decimal point are grouped in threes by commas,
    12,345 (default True)."""
    digit_buff_per_font_unit: float
    """The gap between characters, per unit of font size: 0.001, the default, is 0.048
    scene units at font size 48."""
    show_ellipsis: bool
    """Whether "…" follows the number, for a value that goes on (default False)."""
    unit: str | None
    r"""A unit after the number, in LaTeX math: `"^\circ"` for degrees, `r"\text{ m}"`;
    one that starts with "^" is raised to the number's top (default None)."""
    unit_buff_per_font_unit: float
    """The gap before the unit, beyond the gap between characters, per unit of font
    size (default 0)."""
    include_background_rectangle: bool
    """Whether a background rectangle is behind the number (default False)."""
    edge_to_fix: Vector3DLike
    """The edge, as a direction, that stays where it is when a new value changes the
    number's width (default LEFT: it grows to the right)."""
    font_size: float
    """The characters' font size, as `mob_class` measures it (default 48)."""


class NumberStyle(_NumberStyle, total=False, closed=True):
    """How a number is written: [DecimalNumber][manimgx.DecimalNumber]'s keywords but
    its number of decimal places, for the classes that pass them on.

    Beyond these, they take the [style keywords][manimgx.drawing.paint.Style].
    """


class DecimalNumberOptions(_NumberStyle, total=False, closed=True):
    """[DecimalNumber][manimgx.DecimalNumber]'s keywords, for the classes that pass them
    on: a number line's labels.

    Beyond these, they take the
    [number keywords][manimgx.mobjects.numbers.NumberStyle].
    """

    num_decimal_places: int
    """How many digits follow the decimal point (default 2)."""


class DecimalNumber[V: (float, complex) = float](VMobject):
    r"""A number, written with a fixed number of decimal places: white and filled
    unless styled.

    Its parts are its characters, in order, each typeset by `mob_class`: the sign, the
    digits, the commas and the decimal point; then "…" and the unit, if any (and a
    background rectangle before them all, if asked for). The number shown is rounded (a
    negative one that rounds to zero loses its sign, in either component of a complex
    number), and a complex one is written `a+bi`.
    [set_value][manimgx.DecimalNumber.set_value] shows another
    number, keeping the font size, the color and the edge `edge_to_fix` where they are:
    driven by a [value tracker][manimgx.ValueTracker], or by
    [ChangeDecimalToValue][manimgx.ChangeDecimalToValue], the number counts on screen.

    A type checker follows the initial value's kind: real by default, complex for a
    complex initial value. Use `DecimalNumber[complex](0)` to start real and later
    accept complex values.

    Args:
        number: The number to show; a complex one too.
        num_decimal_places: How many digits follow the decimal point.
        mob_class: The class each character is typeset with.
        include_sign: Whether a number that is not negative is written with a plus
            sign.
        group_with_commas: Whether the digits before the decimal point are grouped in
            threes by commas.
        digit_buff_per_font_unit: The gap between characters, per unit of font size
            (0.001: 0.048 scene units at 48).
        show_ellipsis: Whether "…" follows the number.
        unit: A unit after the number, in LaTeX math (`"^\circ"`, `r"\text{ m}"`); one
            that starts with "^" is raised to the number's top.
        unit_buff_per_font_unit: The gap before the unit, beyond the gap between
            characters, per unit of font size.
        include_background_rectangle: Whether a background rectangle is behind the
            number.
        edge_to_fix: The edge, as a direction, that stays where it is when a new value
            changes the number's width.
        font_size: The characters' font size, as `mob_class` measures it.

    Examples:
        ```python
        import manimgx as m


        class DecimalNumberExample(m.Scene):
            def construct(self) -> None:
                numbers = m.VGroup(
                    m.DecimalNumber(3.14159),
                    m.DecimalNumber(1234567.891, num_decimal_places=1),
                    m.DecimalNumber(42, include_sign=True, color=m.YELLOW),
                    m.DecimalNumber(90, num_decimal_places=0, unit=r"^\circ"),
                    m.DecimalNumber(3.14159, num_decimal_places=4, show_ellipsis=True),
                )
                self.add(numbers.arrange(m.DOWN, buff=0.4).scale(1.5))
        ```
    """

    defaults: ClassVar[Style] = {"stroke_width": 0, "fill_opacity": 1.0}

    @prototype
    def __init__(
        self,
        number: V = 0,
        num_decimal_places: int = 2,
        mob_class: type[ManimTextLabel] = MathTex,
        include_sign: bool = False,
        group_with_commas: bool = True,
        digit_buff_per_font_unit: float = 0.001,
        show_ellipsis: bool = False,
        unit: str | None = None,
        unit_buff_per_font_unit: float = 0,
        include_background_rectangle: bool = False,
        edge_to_fix: Vector3DLike = LEFT,
        font_size: float = DEFAULT_FONT_SIZE,
        **kwargs: Unpack[Style],
    ):
        if font_size <= 0:
            raise ValueError("font_size must be greater than 0.")
        super().__init__(**kwargs)
        self.number = number
        self.num_decimal_places = num_decimal_places
        self.include_sign = include_sign
        self.mob_class = mob_class
        self.group_with_commas = group_with_commas
        self.digit_buff_per_font_unit = digit_buff_per_font_unit
        self.show_ellipsis = show_ellipsis
        self.unit = unit
        self.unit_buff_per_font_unit = unit_buff_per_font_unit
        self.include_background_rectangle = include_background_rectangle
        self.edge_to_fix = edge_to_fix
        self._font_size = font_size
        self._set_submobjects_from_number(number)
        self.init_colors()

    @property
    def font_size(self) -> float:
        """The number's font size: the one it was made with, times how much it has been
        scaled since. Set it, to a positive size, to scale the number to it."""
        return_value: float = self.height / self.initial_height * self._font_size
        return return_value

    @font_size.setter
    def font_size(self, font_val: float) -> None:
        if font_val <= 0:
            raise ValueError("font_size must be greater than 0.")
        elif self.height > 0:
            self.scale(font_val / self.font_size)

    def _row_key(self, shown: str) -> tuple[object, ...]:
        """The displayed row, before placement and final repaint."""
        return (
            type(self),
            shown,
            self.mob_class,
            self._font_size,
            self.digit_buff_per_font_unit,
            self.unit,
            self.unit_buff_per_font_unit,
            self.include_background_rectangle,
            self.show_ellipsis,
        )

    def _set_submobjects_from_number(self, number: V) -> tuple[object, ...]:
        """The glyphs of `number` about the origin at the constructed font size: laid out once per
        string and layout, then copied."""
        self.number = number
        shown = self._get_num_string(number)
        key = self._row_key(shown)
        # The layout is independent of paint; the cached ellipsis starts in its ink.
        cache_key = (*key, str(self.get_color()) if self.show_ellipsis else None)
        if not self.include_background_rectangle:
            self.__dict__.pop("background_rectangle", None)
        row = _ROWS.get(cache_key)
        if row is None:
            self._lay_out(shown)
            _ROWS.keep(
                cache_key,
                copied(
                    {
                        name: self.__dict__[name]
                        for name in _ROW
                        if name in self.__dict__
                    }
                ),
            )
        else:
            self.__dict__.update(copied(row))
        return key

    def _lay_out(self, num_string: str) -> None:
        self.submobjects = []
        # Size the constructed labels: constructing at that size rounds their points
        # differently, enough to move a number line's coordinates in rendered frames.
        self.add(
            *(
                self.mob_class(char).set(font_size=self._font_size)
                for char in num_string
            )
        )
        if self.show_ellipsis:
            self.add(
                SingleStringMathTex("\\dots", color=self.get_color()).set(
                    font_size=self._font_size
                )
            )
        self.arrange(
            buff=self.digit_buff_per_font_unit * self._font_size, aligned_edge=DOWN
        )
        unit_sign = None
        if self.unit is not None:
            unit_sign = SingleStringMathTex(self.unit).set(font_size=self._font_size)
            self.add(
                unit_sign.next_to(
                    self,
                    direction=RIGHT,
                    buff=(self.unit_buff_per_font_unit + self.digit_buff_per_font_unit)
                    * self._font_size,
                    aligned_edge=DOWN,
                )
            )
        self.move_to(ORIGIN)
        for i, c in enumerate(num_string):
            if c == "-" and len(num_string) > i + 1:
                self[i].align_to(self[i + 1], UP)
                self[i].shift(self[i + 1].height * DOWN / 2)
            elif c == ",":
                self[i].shift(self[i].height * DOWN / 2)
        if unit_sign is not None and self.unit and self.unit.startswith("^"):
            unit_sign.align_to(self, UP)
        self.initial_height: float = self.height
        if self.include_background_rectangle:
            self.add_background_rectangle()

    def _get_num_string(self, number: float | complex) -> str:
        if isinstance(number, complex | np.complexfloating):  # a+bi, not Python's a+bj
            return (
                self._get_formatter("0.real")
                + self._get_formatter("0.imag", include_sign=True)
                + "i"
            ).format(number)
        return self._get_formatter().format(number)

    def _get_formatter(
        self, field_name: str = "", include_sign: bool | None = None
    ) -> str:
        sign = self.include_sign if include_sign is None else include_sign
        commas = "," if self.group_with_commas else ""
        return f"{{{field_name}:{'+' if sign else ''}z{commas}.{self.num_decimal_places}f}}"

    _shown: (
        tuple[tuple[object, ...], tuple[tuple[Mobject, Blend, Paint], ...]] | None
    ) = None

    def get_value(self) -> V:
        """The number shown, as it was given: not rounded."""
        return self.number

    def increment_value(self, delta_t: V = 1) -> Self:
        """Show the number plus `delta_t`.

        Args:
            delta_t: What to add.
        """
        return self.set_value(self.get_value() + delta_t)

    def set_value(self, number: V) -> Self:
        """Show another number, keeping the look: the font size, the edge `edge_to_fix`
        where it is, and the color — every character takes the number's own, so a color
        given to single characters is not kept.

        Args:
            number: The number to show.

        Examples:
            ```python
            import manimgx as m


            class DecimalNumberSetValueExample(m.Scene):
                def construct(self) -> None:
                    tracker = m.ValueTracker(0)
                    number = m.DecimalNumber(0, font_size=144).shift(2 * m.LEFT)
                    number.add_updater(lambda n: n.set_value(tracker.get_value()))
                    self.add(number)
                    self.play(tracker.animate.set_value(100), run_time=3)
            ```
        """
        # every glyph takes the number's own color, as CE's `init_colors` repaints them.
        # A number still as it was left showing the same string is left alone: its
        # members' geometry and paint are values, so "as it was left" is the same objects
        shown = self._get_num_string(number)
        key = self._row_key(shown)
        last = self._shown
        if last is not None and last[0] == key:
            family = self.get_family()
            if len(family) == len(last[1]) and all(
                m is was and m._geometry is g and m.paint is p
                for m, (was, g, p) in zip(family, last[1], strict=True)
            ):
                self.number = number
                return self
        old_font_size = self.font_size
        move_to_point = self.get_critical_point(self.edge_to_fix)
        key = self._set_submobjects_from_number(number)
        self.font_size = old_font_size
        self.move_to(move_to_point, self.edge_to_fix)
        self.init_colors()
        self._shown = (
            key,
            tuple((m, m._geometry, m.paint) for m in self.get_family()),
        )
        return self


class Integer(DecimalNumber):
    """An integer: a [DecimalNumber][manimgx.DecimalNumber] with no decimal places,
    white and filled unless styled.

    A number with a fractional part is shown rounded, and
    [get_value][manimgx.Integer.get_value] rounds it too.

    Args:
        number: The number to show.
        num_decimal_places: How many digits follow the decimal point: none unless
            given.

    Examples:
        ```python
        import manimgx as m


        class IntegerExample(m.Scene):
            def construct(self) -> None:
                count = m.Integer(0, font_size=144).shift(1.5 * m.LEFT)
                self.add(count)
                self.play(m.ChangeDecimalToValue(count, 1000), run_time=3)
        ```
    """

    def __init__(
        self,
        number: float = 0,
        num_decimal_places: int = 0,
        **kwargs: Unpack[NumberStyle],
    ) -> None:
        super().__init__(number=number, num_decimal_places=num_decimal_places, **kwargs)

    def get_value(self) -> int:
        """The number shown: the number given, rounded to an integer."""
        return int(np.round(super().get_value()))


class Variable(VMobject):
    """A named value: a label, "=", and a number that shows a value tracker's value.

    Its parts are its [label][manimgx.Variable.label], followed by "=", and its
    [value][manimgx.Variable.value], a [DecimalNumber][manimgx.DecimalNumber] or an
    [Integer][manimgx.Integer] that shows its [tracker][manimgx.Variable.tracker]'s
    value at every frame: animate the tracker, and the number counts.

    Args:
        var: The value it starts with.
        label: The label: a string, typeset as math ([MathTex][manimgx.MathTex]), or a
            text or math mobject.
        var_type: The number's class: DecimalNumber or a subclass, such as Integer.
        num_decimal_places: How many digits follow the decimal point. Integer classes
            use their own precision defaults instead.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] of the group itself; its
            parts keep their own (color them through `label` and `value`).

    Examples:
        ```python
        import manimgx as m


        class VariableExample(m.Scene):
            def construct(self) -> None:
                x = m.Variable(2.0, "x", num_decimal_places=3)
                y = m.Variable(4.0, "x^2", num_decimal_places=3)
                self.add(m.VGroup(x, y).arrange(m.DOWN, buff=0.5).scale(2))
                t = x.tracker
                y.add_updater(lambda v: v.tracker.set_value(t.get_value() ** 2))
                self.play(t.animate.set_value(5), run_time=3, rate_func=m.linear)
        ```
    """

    def __init__(
        self,
        var: float,
        label: str | MathTex | Text | SingleStringMathTex,
        var_type: type[DecimalNumber] = DecimalNumber,
        num_decimal_places: int = 2,
        **kwargs: Unpack[Style],
    ):
        self.label = MathTex(label) if isinstance(label, str) else label
        """The label, followed by "=", one of its submobjects."""
        equals = MathTex("=").next_to(self.label, RIGHT)
        self.label.add(equals)
        self.tracker = ValueTracker(var)
        """The value tracker the number shows: set or animate it to change the
        number."""
        self.value = (
            var_type(self.tracker.get_value())
            if issubclass(var_type, Integer)
            else var_type(
                self.tracker.get_value(), num_decimal_places=num_decimal_places
            )
        )
        """The number, which shows the tracker's value at every frame."""
        self.value.add_updater(self._update_value).next_to(self.label, RIGHT)
        super().__init__(**kwargs)
        self.add(self.label, self.value)

    def _update_value(self, value: DecimalNumber) -> None:
        value.set_value(self.tracker.get_value())


def index_labels(
    mobject: Mobject, label_height: float = 0.15, **kwargs: Unpack[NumberStyle]
) -> VGroup:
    r"""Number the submobjects of a mobject: an [Integer][manimgx.Integer] at the center
    of each, on a dark outline, to find a part's index.

    A debugging help: add the labels to the scene to see them; they don't follow the
    mobject.

    Args:
        mobject: The mobject whose submobjects are numbered, from 0.
        label_height: Each label's height, in scene units.
        **kwargs: [Number keywords][manimgx.mobjects.numbers.NumberStyle] (a black
            background stroke 5 wide unless given).

    Returns:
        A new group of the labels, in order.

    Examples:
        ```python
        import manimgx as m


        class IndexLabelsExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex(r"\binom{2n}{n+2}", font_size=144)
                formula[0][1:3].set_color(m.YELLOW)
                formula[0][3:6].set_color(m.RED)
                self.add(formula, m.index_labels(formula[0], label_height=0.3))
        ```
    """
    kwargs.setdefault("background_stroke_width", 5)
    kwargs.setdefault("background_stroke_color", BLACK)
    labels = VGroup()
    for n, submob in enumerate(mobject):
        label = Integer(n, **kwargs)
        label.height = label_height
        labels.add(label.move_to(submob))
    return labels

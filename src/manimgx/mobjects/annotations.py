# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"Frames, braces and labels placed relative to existing geometric objects."

from __future__ import annotations

__all__ = [
    "ArcBrace",
    "BackgroundRectangle",
    "Brace",
    "BraceBetweenPoints",
    "BraceLabel",
    "BraceText",
    "Cross",
    "Label",
    "LabeledArrow",
    "LabeledDot",
    "LabeledLine",
    "LabeledPolygram",
    "SurroundingRectangle",
    "Underline",
]

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, ClassVar, Self, Unpack

import numpy as np

from manimgx.config import config
from manimgx.constants import (
    DEFAULT_FONT_SIZE,
    DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
    DOWN,
    LEFT,
    ORIGIN,
    RIGHT,
    SMALL_BUFF,
    UP,
)
from manimgx.drawing.geometry import polylabel
from manimgx.drawing.paint import (
    BLACK,
    PURE_YELLOW,
    RED,
    WHITE,
    Look,
    ParsableManimColor,
    Style,
    _Style,
)
from manimgx.mobject import Mobject, Placement, VGroup, VMobject, _family, _family_box
from manimgx.mobjects.shapes import (
    Arc,
    Arced,
    Arrow,
    Dot,
    Line,
    LineOptions,
    Polygram,
    RoundedRectangle,
    Tipped,
)
from manimgx.mobjects.svg import VMobjectFromSVGPath
from manimgx.mobjects.text import (
    MathTex,
    MathTexOptions,
    Tex,
    Text,
    Typst,
    TypstOptions,
)
from manimgx.typing import ManimTextLabel

if TYPE_CHECKING:
    from manimgx.mobject import Mobject
    from manimgx.typing import (
        ManimTextLabel,
        Point3D,
        Point3DLike,
        Point3DLike_Array,
        Vector3D,
        Vector3DLike,
    )


class FrameOptions(_Style, total=False, closed=True):
    """The keywords of a rectangle made around a mobject, as a
    [SurroundingRectangle][manimgx.SurroundingRectangle] or a
    [BackgroundRectangle][manimgx.BackgroundRectangle] is: its margin and its corners,
    with the style keywords (for the classes that pass them on)."""

    buff: float | tuple[float, float]
    """The margin around the mobject, in scene units: one for all sides, or
    (horizontal, vertical) (default 0.1 around a surrounding rectangle, 0 behind a
    background rectangle)."""
    corner_radius: float
    """The radius of the rectangle's corners, in scene units (default 0: square
    corners)."""


class SurroundingRectangle(RoundedRectangle):
    r"""A rectangle around mobjects: around their bounding box, all of them together,
    with a margin; bright yellow (`PURE_YELLOW`) unless styled.

    It is sized and placed when it is made, and does not follow the mobjects
    afterwards.

    Args:
        *mobjects: The mobjects to surround.
        buff: The margin around them, in scene units: one for all sides, or
            (horizontal, vertical).
        corner_radius: The radius of its corners, in scene units: 0 for square
            corners.

    Examples:
        ```python
        import manimgx as m


        class SurroundingRectangleExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex(r"e^{i\pi} + 1 = 0", font_size=96)
                words = m.Text("Euler's identity").next_to(formula, m.DOWN, buff=1)
                self.add(formula, words)
                self.play(
                    m.Create(m.SurroundingRectangle(formula, buff=0.3)),
                    m.Create(
                        m.SurroundingRectangle(words, corner_radius=0.2, color=m.BLUE)
                    ),
                )
        ```
    """

    defaults: ClassVar[Style] = {"color": PURE_YELLOW}

    def __init__(
        self,
        *mobjects: Mobject,
        buff: float | tuple[float, float] = SMALL_BUFF,
        corner_radius: float = 0.0,
        **kwargs: Unpack[Style],
    ) -> None:
        if not all(isinstance(mob, Mobject) for mob in mobjects):
            raise TypeError(
                "Expected all inputs for parameter mobjects to be a Mobjects"
            )
        if isinstance(buff, tuple):
            buff_x = buff[0]
            buff_y = buff[1]
        else:
            buff_x = buff_y = buff
        box = _family_box(_family(mobjects))
        if box is None:
            box = np.zeros((2, 3))
        super().__init__(
            width=float(box[1, 0] - box[0, 0]) + 2 * buff_x,
            height=float(box[1, 1] - box[0, 1]) + 2 * buff_y,
            corner_radius=corner_radius,
            **kwargs,
        )
        self.buff = buff
        self.move_to((box[0] + box[1]) / 2)


class BackgroundRectangle(SurroundingRectangle):
    """A rectangle behind mobjects, in the background's color and three quarters
    opaque, so they stand out from what lies behind them; without an outline.

    Its color is the scene's background color when it is made, unless given. It goes
    behind the mobjects: add it to the scene before them.

    Args:
        *mobjects: The mobjects to go behind.
        buff: The margin around them, in scene units: one for all sides, or
            (horizontal, vertical).
        corner_radius: The radius of its corners, in scene units: 0 for square
            corners.

    Examples:
        ```python
        import manimgx as m


        class BackgroundRectangleExample(m.Scene):
            def construct(self) -> None:
                bare = m.Text("on the grid", font_size=60).shift(3.5 * m.LEFT)
                backed = m.Text("on a background", font_size=60).shift(3.2 * m.RIGHT)
                background = m.BackgroundRectangle(backed, buff=0.2)
                self.add(m.NumberPlane(), bare, background, backed)
        ```
    """

    defaults: ClassVar[Style] = {
        "stroke_width": 0,
        "stroke_opacity": 0.0,
        "fill_opacity": 0.75,
    }

    def __init__(
        self,
        *mobjects: Mobject,
        buff: float | tuple[float, float] = 0,
        corner_radius: float = 0.0,
        **kwargs: Unpack[Style],
    ) -> None:
        if kwargs.get("color") is None:  # not given (None too): the scene's, when made
            kwargs["color"] = config.background_color
        super().__init__(*mobjects, buff=buff, corner_radius=corner_radius, **kwargs)
        self.original_fill_opacity: float = self.fill_opacity


class Cross(VGroup):
    """A cross, an X: two lines from corner to corner of a mobject's bounding box, or of
    a square 2 on a side at the origin; red, 6 wide, unless styled.

    Args:
        mobject: The mobject to cross out: the cross is stretched over its bounding
            box; None for none.
        stroke_color: The color of its lines.
        stroke_width: The width of its lines, in hundredths of a scene unit.
        scale_factor: How much larger than the bounding box (or the square) it is,
            about its center.
        color: The color of its lines, in place of `stroke_color`; None to use that.

    Examples:
        ```python
        import manimgx as m


        class CrossExample(m.Scene):
            def construct(self) -> None:
                wrong = m.MathTex("2 + 2 = 5", font_size=96).shift(2 * m.RIGHT)
                self.add(m.Cross().shift(4 * m.LEFT), wrong)
                self.play(m.Create(m.Cross(wrong, scale_factor=1.2, color=m.YELLOW)))
        ```
    """

    def __init__(
        self,
        mobject: Mobject | None = None,
        stroke_color: ParsableManimColor = RED,
        stroke_width: float = 6.0,
        scale_factor: float = 1.0,
        color: ParsableManimColor | None = None,
        **kwargs: Unpack[Look],
    ) -> None:
        super().__init__(
            Line(UP + LEFT, DOWN + RIGHT), Line(UP + RIGHT, DOWN + LEFT), **kwargs
        )
        if mobject is not None:
            self.replace(mobject, stretch=True)
        self.scale(scale_factor)
        self.set_stroke(
            color=stroke_color if color is None else color, width=stroke_width
        )


class Underline(Line):
    """A line under a mobject: as wide as it, `buff` below it; white unless styled.

    It is sized and placed when it is made, and does not follow the mobject afterwards.

    Args:
        mobject: The mobject to underline.
        buff: The gap between the mobject and the line, in scene units.

    Examples:
        ```python
        import manimgx as m


        class UnderlineExample(m.Scene):
            def construct(self) -> None:
                word = m.Text("important", font_size=120)
                self.add(word)
                self.play(m.Create(m.Underline(word, buff=0.2, color=m.YELLOW)))
        ```
    """

    def __init__(
        self, mobject: Mobject, buff: float = SMALL_BUFF, **kwargs: Unpack[Arced]
    ) -> None:
        super().__init__(LEFT, RIGHT, buff=buff, **kwargs)
        self.match_width(mobject)
        self.next_to(mobject, DOWN, buff=self.buff)


class Label(VGroup):
    """A label on a background, in a frame: text or math, over an opaque rectangle in
    the background's color, inside a thin white outline.

    A string is typeset as math, white, at font size 48 (see
    [MathTex][manimgx.MathTex]); a mobject of text or math is used as it is. Its parts
    are its submobjects, in drawing order: its
    [background_rect][manimgx.Label.background_rect], its
    [rendered_label][manimgx.Label.rendered_label] and its
    [frame][manimgx.Label.frame].

    Args:
        label: The label: a string, typeset as math, or a text or math mobject.
        label_config: [MathTex
            keywords][manimgx.MathTex] for a string
            label, over white at font size 48.
        box_config: [Surrounding rectangle
            keywords][manimgx.mobjects.annotations.FrameOptions] for the
            background, over a margin of 0.05 and an opaque fill (see
            [BackgroundRectangle][manimgx.BackgroundRectangle]).
        frame_config: [Surrounding rectangle
            keywords][manimgx.mobjects.annotations.FrameOptions] for the
            frame, over white, a margin of 0.05 and an outline 0.5 wide.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] of the group itself; its
            parts keep the styles the configs give them.

    Examples:
        ```python
        import manimgx as m


        class LabelExample(m.Scene):
            def construct(self) -> None:
                plain = m.Label("x^2 + y^2 = r^2")
                styled = m.Label(
                    m.Text("a label", color=m.YELLOW),
                    box_config={"color": m.BLUE, "buff": 0.2},
                    frame_config={"color": m.YELLOW, "stroke_width": 4, "buff": 0.2},
                )
                self.add(m.VGroup(plain, styled).arrange(m.DOWN, buff=1).scale(2))
        ```
    """

    def __init__(
        self,
        label: str | ManimTextLabel,
        label_config: MathTexOptions | None = None,
        box_config: FrameOptions | None = None,
        frame_config: FrameOptions | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(**kwargs)
        label_style = MathTexOptions(color=WHITE, font_size=DEFAULT_FONT_SIZE) | (
            label_config or MathTexOptions()
        )
        box_style = FrameOptions(buff=0.05, fill_opacity=1, stroke_width=0.5) | (
            box_config or FrameOptions()
        )
        frame_style = FrameOptions(color=WHITE, buff=0.05, stroke_width=0.5) | (
            frame_config or FrameOptions()
        )
        if isinstance(label, str):
            self.rendered_label: ManimTextLabel = MathTex(label, **label_style)
            """The label's text or math, a submobject."""
        elif isinstance(label, Typst):
            self.rendered_label = label
        else:
            raise TypeError(
                "Unsupported label type. Must be MathTex, Tex, Text or Typst."
            )
        self.background_rect = BackgroundRectangle(self.rendered_label, **box_style)
        """The rectangle behind the label, a submobject."""
        self.frame = SurroundingRectangle(self.rendered_label, **frame_style)
        """The outline around the label, a submobject."""
        self.add(self.background_rect, self.rendered_label, self.frame)


class LabeledLine(Line):
    """A line with a label on it: a [Label][manimgx.Label] centered at a point
    `label_position` of the way from the line's start to its end; white unless styled.

    The label is a submobject, the line's [label][manimgx.LabeledLine.label]. It is
    placed on the straight way between the ends, even when the line is bent.

    Args:
        label: The label: a string, typeset as math, or a text or math mobject.
        label_position: Where the label goes, as a proportion of the way from the
            line's start (0) to its end (1).
        label_config: [MathTex
            keywords][manimgx.MathTex] for a string
            label (see [Label][manimgx.Label]).
        box_config: [Surrounding rectangle
            keywords][manimgx.mobjects.annotations.FrameOptions] for the
            label's background.
        frame_config: [Surrounding rectangle
            keywords][manimgx.mobjects.annotations.FrameOptions] for the
            label's frame.
        start: Where the line starts: a point, or a mobject (see [Line][manimgx.Line]).
        end: Where it ends: a point, or a mobject.

    Examples:
        ```python
        import manimgx as m


        class LabeledLineExample(m.Scene):
            def construct(self) -> None:
                a, b, c = [-4, -2, 0], [4, -2, 0], [4, 2.5, 0]
                sides = m.VGroup(
                    m.LabeledLine("8", start=a, end=b, color=m.BLUE),
                    m.LabeledLine("4.5", start=b, end=c, color=m.GREEN),
                    m.LabeledLine("c", start=c, end=a, label_position=0.4),
                )
                self.add(sides)
        ```
    """

    def __init__(
        self,
        label: str | ManimTextLabel,
        label_position: float = 0.5,
        label_config: MathTexOptions | None = None,
        box_config: FrameOptions | None = None,
        frame_config: FrameOptions | None = None,
        *,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        **kwargs: Unpack[LineOptions],
    ) -> None:
        super().__init__(start, end, **kwargs)
        self.label = Label(
            label=label,
            label_config=label_config,
            box_config=box_config,
            frame_config=frame_config,
        )
        """The label, a submobject."""
        line_start, line_end = self.get_start_and_end()
        self.label.move_to(line_start + (line_end - line_start) * label_position)
        self.add(self.label)


class LabeledArrow(LabeledLine, Arrow):
    """An arrow with a label on it: a [LabeledLine][manimgx.LabeledLine] that is an
    [Arrow][manimgx.Arrow], stopping 0.25 short of its ends unless given another
    `buff`; white unless styled.

    Args:
        label: The label: a string, typeset as math, or a text or math mobject.
        label_position: Where the label goes, as a proportion of the way from the
            arrow's start (0) to its tip's point (1).
        label_config: [MathTex
            keywords][manimgx.MathTex] for a string
            label (see [Label][manimgx.Label]).
        box_config: [Surrounding rectangle
            keywords][manimgx.mobjects.annotations.FrameOptions] for the
            label's background.
        frame_config: [Surrounding rectangle
            keywords][manimgx.mobjects.annotations.FrameOptions] for the
            label's frame.
        start: Where the arrow starts: a point, or a mobject (see [Line][manimgx.Line]).
        end: Where it points to: a point, or a mobject.
        **kwargs: [Line keywords][manimgx.Line].

    Examples:
        ```python
        import manimgx as m


        class LabeledArrowExample(m.Scene):
            def construct(self) -> None:
                arrows = m.VGroup(
                    m.LabeledArrow("F", start=4 * m.LEFT, end=4 * m.RIGHT),
                    m.LabeledArrow(
                        "0.5",
                        label_position=0.3,
                        start=3 * m.LEFT + m.DOWN,
                        end=3 * m.RIGHT + 2 * m.UP,
                        color=m.YELLOW,
                    ),
                ).arrange(m.DOWN, buff=1)
                self.add(arrows)
        ```
    """


class LabeledPolygram(Polygram):
    """A polygram with a label inside it, at its pole of inaccessibility: the point
    inside it farthest from its edges, found to within `precision`; blue unless styled.

    The first group of vertices is its outline, and the others are holes the label is
    kept out of. The label is a submobject, [label][manimgx.LabeledPolygram.label];
    `pole` is where it is, and `radius` how far that is from the nearest edge.

    Args:
        *vertex_groups: The groups of vertices, each a closed path (see
            [Polygram][manimgx.Polygram]): the outline first, then its holes.
        label: The label: a string, typeset as math, or a text or math mobject.
        precision: Allowed error in the largest distance from the polygon's edges,
            in scene units. Several label positions can meet this radius tolerance.
        label_config: [MathTex
            keywords][manimgx.MathTex] for a string
            label (see [Label][manimgx.Label]).
        box_config: [Surrounding rectangle
            keywords][manimgx.mobjects.annotations.FrameOptions] for the
            label's background.
        frame_config: [Surrounding rectangle
            keywords][manimgx.mobjects.annotations.FrameOptions] for the
            label's frame.

    Examples:
        ```python
        import manimgx as m


        class LabeledPolygramExample(m.Scene):
            def construct(self) -> None:
                outline = [[-6, -3, 0], [5, -3, 0], [6, 3, 0], [0, 0.5, 0], [-5, 3, 0]]
                hole = [[0, -2, 0], [0, -0.5, 0], [4, -0.5, 0], [4, -2, 0]]
                shape = m.LabeledPolygram(outline, hole, label="P", fill_opacity=0.3)
                reach = m.Circle(shape.radius, color=m.YELLOW).move_to(shape.pole)
                self.add(shape, reach)
        ```
    """

    def __init__(
        self,
        *vertex_groups: Point3DLike_Array,
        label: str | ManimTextLabel,
        precision: float = 0.01,
        label_config: MathTexOptions | None = None,
        box_config: FrameOptions | None = None,
        frame_config: FrameOptions | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(*vertex_groups, **kwargs)
        self.label = Label(
            label=label,
            label_config=label_config,
            box_config=box_config,
            frame_config=frame_config,
        )
        """The label, a submobject."""
        rings = []
        for group in vertex_groups:
            ring = np.asarray(group, dtype=float)
            rings.append(
                ring
                if np.array_equal(ring[0], ring[-1])
                else np.vstack([ring, ring[:1]])
            )
        cell = polylabel(rings, precision=precision)
        self.pole, self.radius = (np.pad(cell.c, (0, 1), "constant"), cell.d)
        self.label.move_to(self.pole)
        self.add(self.label)


class BraceOptions(_Style, total=False, closed=True):
    """A [brace][manimgx.Brace]'s keywords but its direction, for the classes that pass
    them on.

    Beyond these, they take the [style keywords][manimgx.drawing.paint.Style].
    """

    buff: float
    """The gap between the mobject and the brace, in scene units (default 0.2)."""
    sharpness: float
    """How sharp the brace's tip and ends are: the higher, the narrower its curls
    (default 2)."""


class Brace(VMobjectFromSVGPath):
    """A curly brace along a side of a mobject, as long as the mobject is wide there:
    filled white, without an outline, unless styled.

    The brace lies `buff` beyond the mobject's bounding box, on the side `direction`
    points to, spanning the mobject across that direction, its tip pointing away; the
    mobject is left as it is. [get_text][manimgx.Brace.get_text] and
    [get_tex][manimgx.Brace.get_tex] label its tip.

    Args:
        mobject: The mobject to brace.
        direction: The side the brace is on, as a direction (DOWN: below).
        buff: The gap between the mobject and the brace, in scene units.
        sharpness: How sharp the brace's tip and ends are: the higher, the narrower its
            curls.

    Examples:
        ```python
        import manimgx as m


        class BraceExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                self.add(square)
                self.play(
                    m.GrowFromCenter(m.Brace(square)),
                    m.GrowFromCenter(m.Brace(square, m.RIGHT, color=m.YELLOW)),
                    m.GrowFromCenter(m.Brace(square, m.UP, buff=0.5, color=m.GREEN)),
                )
        ```
    """

    defaults: ClassVar[Style] = {
        "stroke_width": 0,
        "fill_opacity": 1.0,
        "background_stroke_width": 0,
        "background_stroke_color": BLACK,
    }

    def __init__(
        self,
        mobject: Mobject,
        direction: Vector3DLike = DOWN,
        buff: float = 0.2,
        sharpness: float = 2,
        **kwargs: Unpack[Style],
    ):
        path_string_template = (
            "m0.01216 0c-0.01152 0-0.01216 6.103e-4 -0.01216 0.01311v0.007762c0.06776"
            " 0.122 0.1799 0.1455 0.2307 0.1455h{0}c0.03046 3.899e-4 0.07964 0.00449"
            " 0.1246 0.02636 0.0537 0.02695 0.07418 0.05816 0.08648 0.07769 0.001562"
            " 0.002538 0.004539 0.002563 0.01098 0.002563 0.006444-2e-8"
            " 0.009421-2.47e-5 0.01098-0.002563 0.0123-0.01953 0.03278-0.05074"
            " 0.08648-0.07769 0.04491-0.02187 0.09409-0.02597"
            " 0.1246-0.02636h{0}c0.05077 0 0.1629-0.02346"
            " 0.2307-0.1455v-0.007762c-1.78e-6 -0.0125-6.365e-4"
            " -0.01311-0.01216-0.01311-0.006444-3.919e-8 -0.009348 2.448e-5 -0.01091"
            " 0.002563-0.0123 0.01953-0.03278 0.05074-0.08648 0.07769-0.04491"
            " 0.02187-0.09416 0.02597-0.1246 0.02636h{1}c-0.04786 0-0.1502"
            " 0.02094-0.2185"
            " 0.1256-0.06833-0.1046-0.1706-0.1256-0.2185-0.1256h{1}c-0.03046-3.899e-4"
            " -0.07972-0.004491-0.1246-0.02636-0.0537-0.02695-0.07418-0.05816-0.08648-0.07769-0.001562-0.002538-0.004467-0.002563-0.01091-0.002563z"
        )
        default_min_width = 0.90552
        self.buff = buff
        dx, dy = np.asarray(direction, dtype=float)[:2]
        angle = -np.arctan2(dx, dy) + np.pi
        mobject.rotate(-angle, about_point=ORIGIN)
        left = mobject.get_corner(DOWN + LEFT)
        right = mobject.get_corner(DOWN + RIGHT)
        target_width = right[0] - left[0]
        linear_section_length = max(
            0, (target_width * sharpness - default_min_width) / 2
        )
        import svgelements as se

        path = se.Path(
            path_string_template.format(linear_section_length, -linear_section_length)
        )
        super().__init__(path_obj=path, **kwargs)
        self.flip(RIGHT)
        self.stretch_to_fit_width(target_width)
        self.shift(left - self.get_corner(UP + LEFT) + self.buff * DOWN)
        for mob in (mobject, self):
            mob.rotate(angle, about_point=ORIGIN)

    def put_at_tip(
        self, mob: Mobject, use_next_to: bool = True, **kwargs: Unpack[Placement]
    ) -> Self:
        """Put a mobject at the brace's tip, beyond it.

        Args:
            mob: The mobject to put there.
            use_next_to: Whether it goes next to the tip, on the side the brace points
                to (its direction rounded to one of the eight compass directions); if
                not, its center goes from the tip along the brace's direction, by half
                its width and `buff`.
            **kwargs: [Placement keywords][manimgx.mobject.Placement]: `buff`, the
                gap, is 0.25 unless given.
        """
        if use_next_to:
            mob.next_to(self.get_tip(), np.round(self.get_direction()), **kwargs)
        else:
            mob.move_to(self.get_tip())
            buff = kwargs.get("buff", DEFAULT_MOBJECT_TO_MOBJECT_BUFFER)
            shift_distance = mob.width / 2.0 + buff
            mob.shift(self.get_direction() * shift_distance)
        return self

    def get_text(self, *text: str, **kwargs: Unpack[Placement]) -> Tex:
        """Make a label of LaTeX text at the brace's tip, as
        [put_at_tip][manimgx.Brace.put_at_tip] puts it.

        Args:
            *text: The label, in LaTeX: a string per part (see [Tex][manimgx.Tex]).
            **kwargs: [Placement keywords][manimgx.mobject.Placement].

        Returns:
            A new [Tex][manimgx.Tex], at the tip; add it to the scene.

        Examples:
            ```python
            import manimgx as m


            class BraceGetTextExample(m.Scene):
                def construct(self) -> None:
                    line = m.Line([-3, -1.5, 0], [3, 1.5, 0], color=m.ORANGE)
                    normal = line.copy().rotate(m.PI / 2).get_unit_vector()
                    below, side = m.Brace(line), m.Brace(line, normal)
                    self.add(line, below, side)
                    self.play(
                        m.Write(below.get_text("Horizontal distance")),
                        m.Write(side.get_tex("x - x_1")),
                    )
            ```
        """
        text_mob = Tex(*text)
        self.put_at_tip(text_mob, **kwargs)
        return text_mob

    def get_tex(self, *tex: str, **kwargs: Unpack[Placement]) -> MathTex:
        """Make a label of LaTeX math at the brace's tip, as
        [put_at_tip][manimgx.Brace.put_at_tip] puts it.

        Args:
            *tex: The label, in LaTeX: a string per part (see
                [MathTex][manimgx.MathTex]).
            **kwargs: [Placement keywords][manimgx.mobject.Placement].

        Returns:
            A new [MathTex][manimgx.MathTex], at the tip; add it to the scene.
        """
        tex_mob = MathTex(*tex)
        self.put_at_tip(tex_mob, **kwargs)
        return tex_mob

    def get_tip(self) -> Point3D:
        """The brace's tip: the point of its middle cusp.

        Returns:
            The point, in scene coordinates.
        """
        return self.points[28]

    def get_direction(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: a brace's direction is a vector, a path's a winding
        self,
    ) -> Vector3D:
        """The direction the brace points to: from its center to its tip.

        Returns:
            A unit vector.
        """
        vect = self.get_tip() - self.get_center()
        return vect / np.linalg.norm(vect)


type LabelMaker = Callable[
    ..., ManimTextLabel
]  # strings (MathTex takes several) to a label


class BraceLabelOptions(_Style, total=False, closed=True):
    """A [brace label][manimgx.BraceLabel]'s keywords but its label's class, for the
    classes that choose it.

    Beyond these, they take the [style keywords][manimgx.drawing.paint.Style].
    """

    brace_direction: Vector3DLike
    """The side the brace is on, as a direction (default DOWN: below)."""
    font_size: float
    """The label's font size (default 48)."""
    buff: float
    """The gap between the mobject and the brace, in scene units (default 0.2)."""
    brace_config: BraceOptions | None
    """[Brace keywords][manimgx.Brace], over `buff` (default
    None)."""


class BraceLabel(VMobject):
    r"""A brace along a side of a mobject, and a label at its tip: math unless another
    label class is given.

    Its parts are its [brace][manimgx.BraceLabel.brace] and its
    [label][manimgx.BraceLabel.label].

    Args:
        obj: The mobject to brace.
        text: The label: a string, or several (as a [MathTex][manimgx.MathTex]'s
            parts).
        brace_direction: The side the brace is on, as a direction.
        label_constructor: The label's class: MathTex, or another text class.
        font_size: The label's font size.
        buff: The gap between the mobject and the brace, in scene units.
        brace_config: [Brace keywords][manimgx.Brace], over
            `buff`.
        **kwargs: [Style keywords][manimgx.drawing.paint.Style] of the group itself, and
            of the label when `text` is several strings.

    Examples:
        ```python
        import manimgx as m


        class BraceLabelExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                side = m.BraceLabel(square, "a", font_size=72)
                diagonal = m.BraceLabel(square, r"a\sqrt{2}", m.UR, font_size=72)
                self.add(square)
                self.play(m.Write(side), m.Write(diagonal))
        ```
    """

    def __init__(
        self,
        obj: Mobject,
        text: str | Sequence[str],
        brace_direction: Vector3DLike = DOWN,
        label_constructor: LabelMaker = MathTex,
        font_size: float = DEFAULT_FONT_SIZE,
        buff: float = 0.2,
        brace_config: BraceOptions | None = None,
        **kwargs: Unpack[Style],
    ):
        self.label_constructor = label_constructor
        super().__init__(**kwargs)
        self.brace_direction = brace_direction
        self.brace = Brace(
            obj,
            brace_direction,
            **(BraceOptions(buff=buff) | (brace_config or BraceOptions())),
        )
        """The brace, a part."""
        if isinstance(text, str):
            self.label: ManimTextLabel = self.label_constructor(
                text, font_size=font_size
            )
            """The label, at the brace's tip: a part."""
        else:
            self.label = self.label_constructor(*text, font_size=font_size, **kwargs)
        self.brace.put_at_tip(self.label)
        self.add(self.brace, self.label)

    def change_label(self, *text: str, **kwargs: Unpack[TypstOptions]) -> Self:
        """Replace the label with a new one, made of `text` by the label class, at the
        brace's tip.

        Args:
            *text: The new label's strings.
            **kwargs: [Typst keywords][manimgx.mobjects.text.TypstOptions]
                for it (at font size 48 unless given).
        """
        self.remove(self.label)
        self.label = self.label_constructor(*text, **kwargs)
        self.brace.put_at_tip(self.label)
        self.add(self.label)
        return self


class BraceText(BraceLabel):
    """A brace along a side of a mobject, and a label of text at its tip: a
    [BraceLabel][manimgx.BraceLabel] whose label is a [Text][manimgx.Text].

    Args:
        obj: The mobject to brace.
        text: The label's text.
        label_constructor: The label's class.

    Examples:
        ```python
        import manimgx as m


        class BraceTextExample(m.Scene):
            def construct(self) -> None:
                rectangle = m.Rectangle(width=6, height=3, color=m.BLUE)
                width = m.BraceText(rectangle, "width")
                height = m.BraceText(rectangle, "height", brace_direction=m.RIGHT)
                self.add(rectangle, width, height)
        ```
    """

    def __init__(
        self,
        obj: Mobject,
        text: str | Sequence[str],
        label_constructor: LabelMaker = Text,
        **kwargs: Unpack[BraceLabelOptions],
    ):
        super().__init__(obj, text, label_constructor=label_constructor, **kwargs)


class BraceBetweenPoints(Brace):
    """A brace spanning the segment between two points.

    Args:
        point_1: One end.
        point_2: The other end.
        direction: The side the brace is on, as a direction; ORIGIN (the default) for
            the right-hand side going from `point_1` to `point_2` (below, for points
            from left to right).

    Examples:
        ```python
        import manimgx as m


        class BraceBetweenPointsExample(m.Scene):
            def construct(self) -> None:
                a, b = [-3, -1, 0], [3, 2, 0]
                self.add(m.Line(a, b), m.Dot(a), m.Dot(b))
                brace = m.BraceBetweenPoints(a, b, color=m.YELLOW)
                self.play(m.GrowFromCenter(brace))
        ```
    """

    def __init__(
        self,
        point_1: Point3DLike,
        point_2: Point3DLike,
        direction: Vector3DLike = ORIGIN,
        **kwargs: Unpack[BraceOptions],
    ):
        if not np.any(np.asarray(direction, dtype=float)):  # a side of the line
            line_vector = np.array(point_2, dtype=float) - np.array(
                point_1, dtype=float
            )
            direction = np.array([line_vector[1], -line_vector[0], 0])
        super().__init__(Line(point_1, point_2), direction=direction, **kwargs)


class ArcBrace(Brace):
    """A brace bent along an arc, outside it or inside.

    Args:
        arc: The arc to brace; None for one of radius 1, from -1 to 1 radian.
        direction: RIGHT for the brace outside the arc, LEFT for inside.

    Examples:
        ```python
        import manimgx as m


        class ArcBraceExample(m.Scene):
            def construct(self) -> None:
                arc = m.Arc(radius=2.5, angle=2 * m.PI / 3, color=m.BLUE)
                arc.shift(1.5 * m.DOWN)
                self.add(arc)
                self.play(
                    m.GrowFromCenter(m.ArcBrace(arc)),
                    m.GrowFromCenter(m.ArcBrace(arc, m.LEFT, color=m.YELLOW)),
                )
        ```
    """

    def __init__(
        self,
        arc: Arc | None = None,
        direction: Vector3DLike = RIGHT,
        **kwargs: Unpack[BraceOptions],
    ):
        if arc is None:
            arc = Arc(start_angle=-1, angle=2, radius=1)
        arc_end_angle = arc.start_angle + arc.angle
        line = Line(UP * arc.start_angle, UP * arc_end_angle)
        scale_shift = RIGHT * np.log(arc.radius)
        if arc.radius >= 1:
            line.scale(arc.radius, about_point=ORIGIN)
            super().__init__(line, direction=direction, **kwargs)
            self.scale(1 / arc.radius, about_point=ORIGIN)
        else:
            super().__init__(line, direction=direction, **kwargs)
        if arc.radius >= 0.3:
            self.shift(scale_shift)
        else:
            self.shift(RIGHT * np.log(0.3))
        self.apply_complex_function(np.exp)
        self.shift(arc.get_arc_center())


class LabeledDot(Dot):
    r"""A dot with a label in its middle: a disc just large enough for the label unless
    given a radius; white, without an outline, unless styled.

    It is made at the origin, and the label, centered on it, is its submobject.

    Args:
        label: The label: a string, typeset as math in black (see
            [MathTex][manimgx.MathTex]), or a mobject, as it is.
        radius: Its radius, in scene units; None for half the diagonal of the label's
            bounding box, plus `buff`.
        buff: The margin between the label's corners and the dot's edge, in scene
            units, when the radius fits the label.

    Examples:
        ```python
        import manimgx as m


        class LabeledDotExample(m.Scene):
            def construct(self) -> None:
                dots = m.VGroup(
                    m.LabeledDot("A"),
                    m.LabeledDot("42", color=m.BLUE),
                    m.LabeledDot(m.MathTex(r"\alpha"), color=m.PURPLE, radius=0.5),
                    m.LabeledDot(m.Text("hi", color=m.BLACK), color=m.YELLOW),
                ).arrange(buff=1)
                self.add(dots.scale(2))
        ```
    """

    def __init__(
        self,
        label: str | Mobject,
        radius: float | None = None,
        buff: float = SMALL_BUFF,
        **kwargs: Unpack[Tipped],
    ) -> None:
        if isinstance(label, str):
            from manimgx.mobjects.text import MathTex

            rendered_label: Mobject = MathTex(label, color=BLACK)
        else:
            rendered_label = label
        if radius is None:
            radius = buff + float(
                np.linalg.norm([rendered_label.width, rendered_label.height]) / 2
            )
        super().__init__(radius=radius, **kwargs)
        rendered_label.move_to(self.get_center())
        self.add(rendered_label)

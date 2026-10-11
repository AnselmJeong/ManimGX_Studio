# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Animation presets built from the shared lifecycle and transform primitives.

A reveal is paint, so drawing, passing flashes and border reveals use the same
Transform as movement and morphing; whole-object procedures use Animation. Showing a
group's parts in turn is visibility, not paint: the scene leaves the parts not shown yet
out of the picture (`Animation.hidden`)."""

from __future__ import annotations

import inspect
import itertools as it
import math
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, ClassVar, Unpack, cast
from warnings import deprecated

import numpy as np
import numpy.typing as npt

from manimgx.animation.easing import (
    double_smooth,
    linear,
    smooth,
    there_and_back,
    wiggle,
)
from manimgx.animation.timeline import (
    Animation,
    AnimationGroup,
    AnimationOptions,
    Key,
    LaggedStart,
    Succession,
    _gathered,
)
from manimgx.config import config
from manimgx.constants import (
    DEFAULT_POINTWISE_FUNCTION_RUN_TIME,
    DEFAULT_STROKE_WIDTH,
    DEGREES,
    ORIGIN,
    OUT,
    PI,
    RIGHT,
    SMALL_BUFF,
    TAU,
    UP,
)
from manimgx.drawing.geometry import (
    Path,
    interpolate,
    inverse_interpolate,
    normalize,
    path_along_circles,
    spiral_path,
)
from manimgx.drawing.paint import GREY, PURE_YELLOW, ParsableManimColor
from manimgx.mobject import Group, Mobject, Pivot, VGroup, VMobject
from manimgx.typing import Point3D, Point3DLike, Vector3DLike

if TYPE_CHECKING:
    from manimgx.drawing.paint import Paint
    from manimgx.mobjects.numbers import DecimalNumber
    from manimgx.scene import Scene
from manimgx.animation.transform import Transform, TransformOptions, _Call

__all__ = [
    "AddTextLetterByLetter",
    "AddTextWordByWord",
    "ApplyComplexFunction",
    "ApplyFunction",
    "ApplyMatrix",
    "ApplyMethod",
    "ApplyPointwiseFunction",
    "ApplyWave",
    "Blink",
    "Broadcast",
    "ChangeDecimalToValue",
    "ChangingDecimal",
    "Circumscribe",
    "ClockwiseTransform",
    "ComplexHomotopy",
    "CounterclockwiseTransform",
    "Create",
    "CyclicReplace",
    "DrawBorderThenFill",
    "FadeIn",
    "FadeOut",
    "FadeToColor",
    "FadeTransform",
    "FadeTransformPieces",
    "Flash",
    "FocusOn",
    "GrowArrow",
    "GrowFromCenter",
    "GrowFromEdge",
    "GrowFromPoint",
    "Homotopy",
    "Indicate",
    "MaintainPositionRelativeTo",
    "MoveAlongPath",
    "MoveToTarget",
    "PhaseFlow",
    "RemoveTextLetterByLetter",
    "ReplacementTransform",
    "Restore",
    "Rotate",
    "Rotating",
    "ScaleInPlace",
    "ShowIncreasingSubsets",
    "ShowPassingFlash",
    "ShowPassingFlashWithThinningStrokeWidth",
    "ShowSubmobjectsOneByOne",
    "ShrinkToCenter",
    "SpinInFromNothing",
    "SpiralIn",
    "Swap",
    "Transform",
    "TransformFromCopy",
    "TypeWithCursor",
    "Uncreate",
    "UntypeWithCursor",
    "Unwrite",
    "UpdateFromAlphaFunc",
    "UpdateFromFunc",
    "Wiggle",
    "Write",
]


def trimmed(mob: Mobject, a: float, b: float) -> Mobject:
    """Set which stretch of each path of a mobject is drawn.

    The stretch is paint state, which each frame applies when it draws: the points are
    not changed.

    Args:
        mob: The mobject whose parts with points are trimmed.
        a: Where the drawn stretch begins, as a fraction of each path's length.
        b: Where it ends; (0, 0) draws nothing, (0, 1) the whole path.

    Returns:
        The mobject, for chaining.
    """
    for leaf in mob.family_members_with_points():
        leaf.paint = leaf.paint.but(trim=np.array([a, b]), pace=leaf.reveal_pace())
    return mob


class Create(Transform):
    """Draw a mobject into view along its paths, one part after another.

    The mobject joins the scene when the animation begins. Each part is revealed from its
    start to its end; with the default `lag_ratio` of 1, a part begins when the one before
    it is drawn.

    Args:
        mobject: The mobject to draw.

    Examples:
        ```python
        import manimgx as m


        class CreateExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=4, color=m.BLUE, fill_opacity=0.5)
                self.play(m.Create(square, run_time=2))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"lag_ratio": 1.0, "introducer": True}

    def __init__(self, mobject: Mobject, **kwargs: Unpack[AnimationOptions]) -> None:
        super().__init__(mobject, keys=(lambda m: trimmed(m, 0, 0), None), **kwargs)


class Uncreate(Create):
    """Undraw a mobject along its paths, and take it out of the scene.

    Each part is erased from its end back to its start, one part after another in the
    order [`Create`][manimgx.Create] draws them. The mobject leaves the scene when the
    animation finishes.

    Args:
        mobject: The mobject to undraw.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions].

    Examples:
        ```python
        import manimgx as m


        class UncreateExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex("a^2 + b^2 = c^2", font_size=120)
                box = m.SurroundingRectangle(formula, buff=0.4, color=m.YELLOW)
                self.add(formula, box)
                self.play(m.Uncreate(box, run_time=2))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {
        "reverse_rate_function": True,
        "remover": True,
        "introducer": False,
    }


class ShowPassingFlash(Transform):
    """Flash a stretch of a mobject's path along it, from its start to past its end.

    A window, `time_width` of the path's length, travels along the mobject, which shows
    only what lies inside it. The mobject joins the scene for the flash and leaves
    it at the end, even if it was there before (flash a copy to keep the original); its
    paths are whole again afterward.

    Args:
        mobject: The mobject whose paths the window travels along.
        time_width: The window's length, as a fraction of the path's length.

    Examples:
        ```python
        import manimgx as m


        class ShowPassingFlashExample(m.Scene):
            def construct(self) -> None:
                pentagon = m.RegularPolygon(5, color=m.GREY, stroke_width=8).scale(3)
                flash = pentagon.copy().set_color(m.YELLOW)
                self.add(pentagon)
                self.play(m.ShowPassingFlash(flash, time_width=0.5, run_time=2))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"remover": True, "introducer": True}

    def __init__(
        self,
        mobject: Mobject,
        time_width: float = 0.1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.time_width = time_width
        super().__init__(
            mobject,
            keys=(
                lambda m: trimmed(m, -time_width, 0),
                lambda m: trimmed(m, 1, 1 + time_width),
            ),
            **kwargs,
        )

    def clean_up_from_scene(self, scene: Scene) -> None:
        super().clean_up_from_scene(scene)
        trimmed(self.mobject, 0, 1)


class DrawBorderThenFill(Transform):
    """Draw a mobject's outline, then fill it in.

    In the first half, each part's border is drawn along its path, `stroke_width` wide,
    in the paint the part is seen in: its own stroke, if it draws one, or else its fill
    (a gradient stays one), unless `stroke_color` is given. In the second, the fill
    comes in while the border turns into the part's own stroke; where the part draws no
    stroke, the border thins away in the same paint. The parts end as they were. The
    mobject joins the scene when the animation begins. It runs 2 seconds, eased by
    [`double_smooth`][manimgx.double_smooth]: smoothly in each half.

    Args:
        vmobject: The mobject to draw.
        stroke_width: The border's width, in hundredths of a scene unit.
        stroke_color: The border's color; None for the paint each part is seen in.

    Examples:
        ```python
        import manimgx as m


        class DrawBorderThenFillExample(m.Scene):
            def construct(self) -> None:
                shapes = m.VGroup(
                    m.Square(side_length=3, color=m.ORANGE, fill_opacity=1),
                    m.Star(outer_radius=2, color=m.BLUE, fill_opacity=1),
                ).arrange(buff=1.5)
                self.play(m.DrawBorderThenFill(shapes, stroke_color=m.YELLOW))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {
        "run_time": 2.0,
        "rate_func": double_smooth,
        "introducer": True,
    }
    # the last keyframe's parts and their own paints, to end on
    _own: list[tuple[Mobject, Paint]]

    def __init__(
        self,
        vmobject: Mobject,
        stroke_width: float = 2,
        stroke_color: ParsableManimColor | None = None,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        super().__init__(
            vmobject,
            keys=(self._undrawn, self._outline, self._filled),
            **kwargs,
        )
        self.stroke_width, self.stroke_color = stroke_width, stroke_color

    def _undrawn(self, mobject: Mobject) -> Mobject:
        """Its outline, none of it drawn yet: where it starts."""
        return trimmed(self._outline(mobject), 0, 0)

    def _border(self, part: Mobject) -> None:
        """A part's stroke as its border: its own stroke if it draws one, else its fill (every
        row, so a gradient stays one; at its opacity); in `stroke_color`, if given."""
        p = part.paint
        if not _draws_stroke(p):
            part.paint = p.but(stroke=p.fill)
        if self.stroke_color is not None:
            part.set_stroke(self.stroke_color, family=False)

    def _outline(self, m: Mobject) -> Mobject:
        for part in m.family_members_with_points():
            self._border(part)
            part.paint = part.paint.but(stroke_width=self.stroke_width)
        return m.set_fill(opacity=0)

    def _filled(self, m: Mobject) -> Mobject:
        """The object, but a part that draws no stroke has its unseen stroke in its border's
        paint: its border thins away in it, not in a color it never shows."""
        self._own = [(part, part.paint) for part in m.family_members_with_points()]
        for part, paint in self._own:
            if not _draws_stroke(paint):
                self._border(part)
        return m

    def finish(self) -> None:
        for part, paint in self._own:  # it ends as itself: its unseen strokes its own
            part.paint = paint
        super().finish()


def _draws_stroke(paint: Paint) -> bool:
    return paint.stroke_width > 0 and bool(paint.stroke[:, 3].any())


class Write(DrawBorderThenFill):
    r"""Write a mobject as if by hand: each part's outline drawn, then filled in.

    The drawing of [`DrawBorderThenFill`][manimgx.DrawBorderThenFill], at an even pace
    (`linear`), its parts staggered: `lag_ratio` is 4 divided by the number of parts, at
    most 0.2, and it runs 1 second for fewer than 15 parts, 2 seconds otherwise. The
    mobject joins the scene when the animation begins. [`Unwrite`][manimgx.Unwrite]
    erases it.

    Args:
        vmobject: The mobject to write, as a text or a formula.
        reverse: Whether to write the parts from the last to the first (they keep their
            order, so the later ones stay drawn over the earlier ones); the mobject then
            leaves the scene when the animation finishes (unless given `remover=False`).

    Examples:
        ```python
        import manimgx as m


        class WriteExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex(r"e^{i\pi} + 1 = 0", font_size=144)
                self.play(m.Write(formula))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": linear}

    def __init__(
        self,
        vmobject: Mobject,
        reverse: bool = False,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        n = len(vmobject.family_members_with_points())
        kwargs.setdefault("run_time", 1 if n < 15 else 2)
        kwargs.setdefault("lag_ratio", min(4.0 / max(1.0, n), 0.2))
        kwargs.setdefault("remover", reverse)
        kwargs.setdefault("introducer", not reverse)
        self.reverse = reverse
        super().__init__(vmobject, **kwargs)

    def get_sub_alpha(self, alpha: float, index: int, num_submobjects: int) -> float:
        # reversed, the last part goes first; the parts keep their order, so their
        # stacking
        if self.reverse:
            index = num_submobjects - 1 - index
        return super().get_sub_alpha(alpha, index, num_submobjects)


class Unwrite(Write):
    """Erase a mobject as if writing it backward, and take it out of the scene.

    The reverse of [`Write`][manimgx.Write]: each part's fill fades into its outline,
    and the outline is undrawn, one part shortly after another, by default the last
    part first. The parts keep their order while it plays, so the later ones stay drawn
    over the earlier ones. The mobject leaves the scene when the animation finishes.

    Args:
        vmobject: The mobject to erase.
        reverse: Whether to erase the parts from the last to the first; False erases
            from the first.

    Examples:
        ```python
        import manimgx as m


        class UnwriteExample(m.Scene):
            def construct(self) -> None:
                alice = m.Text("Alice", font_size=96)
                rest = m.Text("and Bob", font_size=96)
                m.VGroup(alice, rest).arrange(buff=0.4)
                self.add(alice, rest)
                self.play(m.Unwrite(rest))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"reverse_rate_function": True}

    def __init__(
        self,
        vmobject: Mobject,
        reverse: bool = True,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        super().__init__(vmobject, reverse=reverse, **kwargs)


class _Fade(Transform):
    fading_in: ClassVar[bool] = False

    def __init__(
        self,
        *mobjects: Mobject,
        shift: Vector3DLike | None = None,
        target_position: Point3DLike | Mobject | None = None,
        scale: float = 1,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        if not mobjects:
            raise ValueError("At least one mobject must be passed.")
        mobject = mobjects[0] if len(mobjects) == 1 else _gathered(*mobjects)
        self.point_target = shift is None and target_position is not None
        if self.point_target:
            center = (
                target_position.get_center()
                if isinstance(target_position, Mobject)
                else np.asarray(target_position, dtype=float)
            )
            shift = center - mobject.get_center()
        self.shift_vector = ORIGIN if shift is None else np.asarray(shift, dtype=float)
        self.scale_factor = scale
        super().__init__(
            mobject,
            keys=(self._faded, None) if self.fading_in else (None, self._faded),
            **kwargs,
        )

    def _faded(self, m: Mobject) -> Mobject:
        m.fade(1)
        m.shift(
            self.shift_vector * (-1 if self.fading_in and not self.point_target else 1)
        )
        return m.scale(self.scale_factor)


class FadeIn(_Fade):
    """Fade mobjects into view.

    They start transparent (moved back by `shift`, or at `target_position`, and `scale`
    times their size) and arrive as they are. They join the scene when the animation
    begins.

    Args:
        *mobjects: The mobjects to fade in, together; at least one.
        shift: The direction and distance they move while fading in: they start this far
            behind their places.
        target_position: Where they start from, when no `shift` is given: a point, or a
            mobject's center.
        scale: Their size at the start, relative to their own.
        **kwargs: [Transform options][manimgx.animation.transform.TransformOptions].

    Examples:
        ```python
        import manimgx as m


        class FadeInExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(2 * m.UP + 4 * m.LEFT, radius=0.2, color=m.YELLOW)
                names = ("plain", "shift", "target", "scale")
                words = m.VGroup(*(m.Text(name, font_size=60) for name in names))
                words.arrange(buff=0.8)
                self.add(dot)
                self.play(
                    m.LaggedStart(
                        m.FadeIn(words[0]),
                        m.FadeIn(words[1], shift=m.DOWN),
                        m.FadeIn(words[2], target_position=dot),
                        m.FadeIn(words[3], scale=1.5),
                        lag_ratio=0.5,
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"introducer": True}
    fading_in = True


class FadeOut(_Fade):
    """Fade mobjects out of view, and take them out of the scene.

    They end transparent (moved along `shift`, or to `target_position`, and `scale`
    times their size). They leave the scene when the animation finishes, and are then as
    they were before it: adding them again shows them.

    Args:
        *mobjects: The mobjects to fade out, together; at least one.
        shift: The direction and distance they move while fading out.
        target_position: Where they go, when no `shift` is given: a point, or a
            mobject's center.
        scale: Their size at the end, relative to their own.
        **kwargs: [Transform options][manimgx.animation.transform.TransformOptions].

    Examples:
        ```python
        import manimgx as m


        class FadeOutExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(2 * m.UP + 4 * m.LEFT, radius=0.2, color=m.YELLOW)
                names = ("plain", "shift", "target", "scale")
                words = m.VGroup(*(m.Text(name, font_size=60) for name in names))
                words.arrange(buff=0.8)
                self.add(dot, words)
                self.play(
                    m.LaggedStart(
                        m.FadeOut(words[0]),
                        m.FadeOut(words[1], shift=m.DOWN),
                        m.FadeOut(words[2], target_position=dot),
                        m.FadeOut(words[3], scale=0.5),
                        lag_ratio=0.5,
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"remover": True}

    def clean_up_from_scene(self, scene: Scene) -> None:
        super().clean_up_from_scene(scene)
        self.interpolate(0)


class GrowFromPoint(Transform):
    """Grow a mobject from a point.

    It starts shrunk to nothing at `point`, in `point_color` if given, and grows to its
    size and place. The mobject joins the scene when the animation begins.

    Args:
        mobject: The mobject to grow.
        point: The point it grows from, or a mobject whose center it grows from (taken
            when the animation is made).
        point_color: The color it starts in; None for its own.

    Examples:
        ```python
        import manimgx as m


        class GrowFromPointExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(3 * m.UP + 5 * m.LEFT, radius=0.2, color=m.YELLOW)
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                self.add(dot)
                self.play(m.GrowFromPoint(square, dot, point_color=m.YELLOW))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"introducer": True}

    def __init__(
        self,
        mobject: Mobject,
        point: Point3DLike | Mobject,
        point_color: ParsableManimColor | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.point = (
            point.get_center()
            if isinstance(point, Mobject)
            else np.asarray(point, dtype=float)
        )
        self.point_color = point_color
        super().__init__(mobject, keys=(self._shrunk, None), **kwargs)

    def _shrunk(self, m: Mobject) -> Mobject:
        m.scale(0).move_to(self.point)
        return m.set_color(self.point_color) if self.point_color else m


class GrowFromCenter(GrowFromPoint):
    """Grow a mobject from its center.

    It starts shrunk to nothing at its center, in `point_color` if given. The mobject
    joins the scene when the animation begins.

    Args:
        mobject: The mobject to grow.
        point_color: The color it starts in; None for its own.

    Examples:
        ```python
        import manimgx as m


        class GrowFromCenterExample(m.Scene):
            def construct(self) -> None:
                left = m.Circle(radius=1.5, color=m.BLUE, fill_opacity=0.5)
                right = m.Circle(radius=1.5, color=m.GREEN, fill_opacity=0.5)
                m.VGroup(left, right).arrange(buff=2)
                self.play(
                    m.GrowFromCenter(left), m.GrowFromCenter(right, point_color=m.RED)
                )
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        point_color: ParsableManimColor | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(
            mobject, mobject.get_center(), point_color=point_color, **kwargs
        )


class GrowFromEdge(GrowFromPoint):
    """Grow a mobject from an edge or a corner of its bounding box.

    It starts shrunk to nothing there, in `point_color` if given. The mobject joins the
    scene when the animation begins.

    Args:
        mobject: The mobject to grow.
        edge: The direction of the edge (as [`DOWN`][manimgx.DOWN], its bottom) or the
            corner (as [`UR`][manimgx.UR], its top right) it grows from.
        point_color: The color it starts in; None for its own.

    Examples:
        ```python
        import manimgx as m


        class GrowFromEdgeExample(m.Scene):
            def construct(self) -> None:
                squares = m.VGroup(
                    *(m.Square(side_length=2.5, fill_opacity=0.5) for _ in range(3))
                ).arrange(buff=1.5)
                squares.set_color_by_gradient(m.BLUE, m.GREEN)
                self.play(
                    m.GrowFromEdge(squares[0], m.DOWN),
                    m.GrowFromEdge(squares[1], m.RIGHT),
                    m.GrowFromEdge(squares[2], m.UR),
                )
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        edge: Vector3DLike,
        point_color: ParsableManimColor | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(
            mobject, mobject.get_critical_point(edge), point_color=point_color, **kwargs
        )


class GrowArrow(GrowFromPoint):
    """Grow an arrow from its start; its tip grows with it.

    The arrow joins the scene when the animation begins.

    Args:
        arrow: The arrow to grow.
        point_color: The color it starts in; None for its own.

    Examples:
        ```python
        import manimgx as m


        class GrowArrowExample(m.Scene):
            def construct(self) -> None:
                right = m.Arrow(3 * m.LEFT, 3 * m.RIGHT, color=m.BLUE).shift(1.5 * m.UP)
                up = m.Arrow(3 * m.LEFT, 3 * m.RIGHT + 1.5 * m.UP, color=m.YELLOW)
                up.shift(1.5 * m.DOWN)
                self.play(m.GrowArrow(right), m.GrowArrow(up, point_color=m.RED))
        ```
    """

    def __init__(
        self,
        arrow: Mobject,
        point_color: ParsableManimColor | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(arrow, arrow.get_start(), point_color=point_color, **kwargs)

    def _shrunk(self, m: Mobject) -> Mobject:
        from manimgx.mobjects.shapes import Arrow

        if isinstance(m, Arrow):
            m.scale(0, scale_tips=True, about_point=self.point)
        else:
            m.scale(0, about_point=self.point)
        return m.set_color(self.point_color) if self.point_color else m


class SpinInFromNothing(GrowFromCenter):
    """Grow a mobject from its center while spinning it into place.

    It turns through `angle` as it grows (counterclockwise, for a positive angle). The
    mobject joins the scene when the animation begins.

    Args:
        mobject: The mobject to spin in.
        angle: How far it turns on its way, in radians.
        point_color: The color it starts in; None for its own.

    Examples:
        ```python
        import manimgx as m


        class SpinInFromNothingExample(m.Scene):
            def construct(self) -> None:
                left = m.Square(side_length=2.5, color=m.BLUE, fill_opacity=0.5)
                right = m.Star(outer_radius=1.5, color=m.YELLOW, fill_opacity=0.5)
                m.VGroup(left, right).arrange(buff=3)
                self.play(
                    m.SpinInFromNothing(left),
                    m.SpinInFromNothing(right, angle=m.TAU, point_color=m.RED),
                    run_time=2,
                )
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        angle: float = PI / 2,
        point_color: ParsableManimColor | None = None,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.angle = angle
        super().__init__(
            mobject, path_func=spiral_path(angle), point_color=point_color, **kwargs
        )


class Indicate(Transform):
    """Draw attention to a mobject: enlarge and color it for a moment.

    It grows to `scale_factor` times its size in `color`, and comes back as it was
    (eased by [`there_and_back`][manimgx.there_and_back]).

    Args:
        mobject: The mobject to indicate.
        scale_factor: How many times its size it grows to.
        color: The color it turns.

    Examples:
        ```python
        import manimgx as m


        class IndicateExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=144)
                self.add(formula)
                self.play(m.Indicate(formula[4]))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": there_and_back}

    def __init__(
        self,
        mobject: Mobject,
        scale_factor: float = 1.2,
        color: ParsableManimColor = PURE_YELLOW,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.color, self.scale_factor = color, scale_factor
        super().__init__(
            mobject,
            keys=(None, lambda m: m.scale(scale_factor).set_color(color)),
            **kwargs,
        )


class Rotate(Transform):
    """Rotate a mobject rigidly about a point.

    It turns by `angle` about `axis` around one pivot: `about_point`, or the point of
    its bounding box at `about_edge`, or its center, taken from the mobject as it is
    when the rotation begins. Every point travels along a circle about the pivot, so the
    mobject keeps its shape on the way, and an angle of [`TAU`][manimgx.TAU] is a full
    turn.

    Args:
        mobject: The mobject to rotate.
        angle: The angle, in radians, counterclockwise about `axis`.
        axis: The axis it turns about; the default, [`OUT`][manimgx.OUT], turns it in
            the plane of the screen.
        about_point: The pivot; None to take it from `about_edge`, or the center.
        about_edge: The direction of the point of its bounding box it turns about, when
            no `about_point` is given.
        **kwargs: [Transform options][manimgx.animation.transform.TransformOptions]; a
            `path_func` or `path_arc_centers` of its own replaces the turn on the way.

    Examples:
        ```python
        import manimgx as m


        class RotateExample(m.Scene):
            def construct(self) -> None:
                pivot = m.Dot(radius=0.1)
                left = m.Rectangle(m.BLUE, width=2.5, height=1.2, fill_opacity=0.5)
                right = left.copy().set_color(m.YELLOW)
                left.shift(4 * m.LEFT)
                right.shift(2 * m.RIGHT)
                self.add(pivot, left, right)
                self.play(
                    m.Rotate(left, m.PI / 2),
                    m.Rotate(right, m.PI / 2, about_point=pivot.get_center()),
                    run_time=2,
                )
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        angle: float = PI,
        axis: Vector3DLike = OUT,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.angle, self.axis, self.about_edge = angle, axis, about_edge
        self._point = None if about_point is None else np.asarray(about_point, float)
        self.about_point = self._pivot(mobject)
        self._own_path = "path_func" in kwargs or "path_arc_centers" in kwargs
        kwargs.setdefault("path_arc", angle)
        kwargs.setdefault("path_arc_axis", axis)
        kwargs.setdefault("path_arc_centers", self.about_point)
        super().__init__(
            mobject,
            keys=(None, self._turned),
            **kwargs,
        )

    def _turned(self, mob: Mobject) -> Mobject:
        """Where it ends: turned through the whole angle about its pivot (a method, so
        that a copy of the animation turns about its own)."""
        return mob.rotate(self.angle, self.axis, about_point=self.about_point)

    def _pivot(self, mob: Mobject) -> Point3D:
        if self._point is not None:
            return self._point
        if self.about_edge is not None:
            return mob.get_critical_point(self.about_edge)
        return mob.get_center()

    def derive(self, source: Mobject) -> None:
        self._about(source)
        super().derive(source)

    def rederive(self) -> None:
        if self.model is not None:
            self._about(self.model)
        super().rederive()

    def _about(self, source: Mobject) -> None:
        # the pivot, unless given, is a point of the object: read from it as it is now (as
        # its updaters have it, while they run beneath), and the path turns about it
        self.about_point = self._pivot(source)
        if not self._own_path:
            self._path_func = path_along_circles(
                self.path_arc, self.about_point, self.path_arc_axis
            )


class ReplacementTransform(Transform):
    """Transform a mobject into another, which then takes its place in the scene.

    It plays as [`Transform`][manimgx.Transform] does; when it finishes,
    `target_mobject` is in the scene where the mobject was, and the mobject is not: go
    on animating the target.

    Args:
        mobject: The mobject to transform; it leaves the scene.
        target_mobject: The mobject it turns into, which takes its place.

    Examples:
        ```python
        import manimgx as m


        class ReplacementTransformExample(m.Scene):
            def construct(self) -> None:
                numbers = m.VGroup(*(m.MathTex(n, font_size=144) for n in "123"))
                numbers.arrange(buff=3)
                self.add(numbers[0])
                self.play(m.ReplacementTransform(numbers[0], numbers[1]))
                self.play(m.ReplacementTransform(numbers[1], numbers[2]))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        kwargs.setdefault("replace_mobject_with_target_in_scene", True)
        super().__init__(mobject, target_mobject, **kwargs)


class TransformFromCopy(Transform):
    """Transform a copy of a mobject into another, leaving the mobject where it is.

    `target_mobject` joins the scene, starting as a copy of the mobject and turning into
    itself; the mobject stays as it is.

    Args:
        mobject: The mobject the copy is made from.
        target_mobject: The mobject the copy turns into; it joins the scene.

    Examples:
        ```python
        import manimgx as m


        class TransformFromCopyExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2.5, color=m.BLUE, fill_opacity=0.5)
                circle = m.Circle(radius=1.25, color=m.YELLOW, fill_opacity=0.5)
                square.shift(3 * m.LEFT)
                circle.shift(3 * m.RIGHT)
                self.add(square)
                self.play(m.TransformFromCopy(square, circle, run_time=2))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(target_mobject, mobject, **kwargs)

    def interpolate(self, alpha: float) -> None:
        super().interpolate(1 - alpha)


class ClockwiseTransform(Transform):
    """Transform a mobject into another along clockwise half circles.

    Each point travels from its start to its end clockwise along a half circle: a
    [`Transform`][manimgx.Transform] whose `path_arc` is −π, unless given another.

    Args:
        mobject: The mobject to transform.
        target_mobject: The mobject whose shape and style it takes.

    Examples:
        ```python
        import manimgx as m


        class ClockwiseTransformExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(2.5 * m.LEFT, radius=0.3, color=m.YELLOW)
                square = m.Square(side_length=1.5, color=m.BLUE, fill_opacity=0.5)
                square.shift(2.5 * m.RIGHT)
                self.add(dot)
                self.play(m.ClockwiseTransform(dot, square, run_time=2))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        kwargs.setdefault("path_arc", -PI)
        super().__init__(mobject, target_mobject, **kwargs)


class CounterclockwiseTransform(Transform):
    """Transform a mobject into another along counterclockwise half circles.

    Each point travels from its start to its end counterclockwise along a half circle: a
    [`Transform`][manimgx.Transform] whose `path_arc` is π, unless given another.

    Args:
        mobject: The mobject to transform.
        target_mobject: The mobject whose shape and style it takes.

    Examples:
        ```python
        import manimgx as m


        class CounterclockwiseTransformExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=1.5, color=m.BLUE, fill_opacity=0.5)
                circle = m.Circle(radius=0.75, color=m.YELLOW, fill_opacity=0.5)
                square.shift(2.5 * m.RIGHT)
                circle.shift(2.5 * m.LEFT)
                self.add(square)
                self.play(m.CounterclockwiseTransform(square, circle, run_time=2))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        kwargs.setdefault("path_arc", PI)
        super().__init__(mobject, target_mobject, **kwargs)


class MoveToTarget[M: Mobject = Mobject](Transform[M]):
    """Transform a mobject into its `target`.

    Make the target first with [`generate_target`][manimgx.Mobject.generate_target], a
    copy of the mobject, and change it as you like; the animation transforms the mobject
    into it. A mobject without a target raises a ValueError.

    Args:
        mobject: The mobject to transform; its `target` is what it becomes.

    Examples:
        ```python
        import manimgx as m


        class MoveToTargetExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=2, color=m.BLUE).shift(3 * m.LEFT)
                target = circle.generate_target()
                target.set_fill(m.GREEN, opacity=0.5).scale(0.5).shift(6 * m.RIGHT)
                self.add(circle)
                self.play(m.MoveToTarget(circle))
        ```
    """

    def __init__(self, mobject: M, **kwargs: Unpack[TransformOptions]) -> None:
        if mobject.target is None:
            raise ValueError(
                "MoveToTarget called on a mobject without a target (see"
                " generate_target)"
            )
        super().__init__(mobject, mobject.target, **kwargs)


class _ApplyMethod(Transform):
    """Transform a mobject into what a call of one of its methods makes of it: what
    `ApplyMethod` and the animations that apply one method (`Restore`, …) are made of.

    The call is carried out when the animation begins, on the mobject as it is then. Its
    arguments are taken as written, when the animation is made: a mobject among them
    that is not part of this one is a copy of it as it was then. The method's keywords
    go in a dict after its positional arguments (the animation's own keywords are its
    options): `_ApplyMethod(square.scale, 2, {"about_edge": DL})`.

    Args:
        method: A method of a mobject, not called: `square.scale`.
        *args: The method's arguments; a dict at the end holds its keywords.
    """

    def __init__(
        self,
        method: Callable[..., object],
        *args: object,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        if not inspect.ismethod(method) or not isinstance(method.__self__, Mobject):
            raise ValueError(
                "Whoops, looks like you accidentally invoked the method you want to"
                " animate"
            )
        keywords: dict[str, object] = {}
        if args and isinstance(args[-1], dict):
            args, keywords = args[:-1], cast("dict[str, object]", args[-1])
        call = _Call(
            method.__func__,
            args,
            keywords,
            {id(m) for m in method.__self__.get_family()},
        )
        super().__init__(method.__self__, keys=(None, call), **kwargs)


@deprecated(
    "ApplyMethod(mobject.method, *args) is mobject.animate.method(*args): use .animate",
    category=None,
)
class ApplyMethod(_ApplyMethod):
    """Transform a mobject into what a call of one of its methods makes of it: Manim
    CE's older way to write [`.animate`][manimgx.Mobject.animate].
    `ApplyMethod(square.scale, 2)` is `square.animate.scale(2)`.

    Args:
        method: A method of a mobject, not called: `square.scale`.
        *args: The method's arguments; a dict at the end holds its keywords.
    """


class ApplyPointwiseFunction(_ApplyMethod):
    """Transform a mobject into its image under a function of a point.

    Each point p travels in a straight line to `function(p)`, and a path's curves are
    mapped as [apply_function][manimgx.Mobject.apply_function] maps them, cut into more
    curves where the function bends them. It runs 3 seconds.

    Args:
        function: A function from a point to where it goes, in scene coordinates.
        mobject: The mobject to move.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ApplyPointwiseFunctionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)
                self.add(square)
                self.play(
                    m.ApplyPointwiseFunction(
                        lambda p: m.complex_to_R3(np.exp(m.R3_to_complex(p))), square
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {
        "run_time": DEFAULT_POINTWISE_FUNCTION_RUN_TIME
    }

    def __init__(
        self,
        function: Callable[[Point3D], Point3D],
        mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(mobject.apply_function, function, **kwargs)


@deprecated(
    "FadeToColor(mobject, color) is mobject.animate.set_color(color): use .animate",
    category=None,
)
class FadeToColor(_ApplyMethod):
    """Change a mobject's color, gradually: `mobject.animate.set_color(color)`.

    Args:
        mobject: The mobject to recolor.
        color: The color it turns.
    """

    def __init__(
        self,
        mobject: Mobject,
        color: ParsableManimColor,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(mobject.set_color, color, **kwargs)


@deprecated(
    "ScaleInPlace(mobject, k) is mobject.animate.scale(k): use .animate",
    category=None,
)
class ScaleInPlace(_ApplyMethod):
    """Scale a mobject about its center: `mobject.animate.scale(scale_factor)`.

    Args:
        mobject: The mobject to scale.
        scale_factor: The factor it is scaled by: 2 doubles its size.
    """

    def __init__(
        self, mobject: Mobject, scale_factor: float, **kwargs: Unpack[TransformOptions]
    ) -> None:
        super().__init__(mobject.scale, scale_factor, **kwargs)


class ShrinkToCenter(_ApplyMethod):
    """Shrink a mobject to nothing at its center.

    It stays in the scene, shrunk to a point: pass `remover=True` to take it out when
    the animation finishes.

    Args:
        mobject: The mobject to shrink.

    Examples:
        ```python
        import manimgx as m


        class ShrinkToCenterExample(m.Scene):
            def construct(self) -> None:
                circles = m.VGroup(
                    *(
                        m.Circle(radius=1.2, color=color, fill_opacity=0.5)
                        for color in (m.BLUE, m.YELLOW, m.GREEN)
                    )
                ).arrange(buff=1)
                self.add(circles)
                self.play(m.ShrinkToCenter(circles[1]))
        ```
    """

    def __init__(self, mobject: Mobject, **kwargs: Unpack[TransformOptions]) -> None:
        super().__init__(mobject.scale, 0, **kwargs)


class Restore(_ApplyMethod):
    """Transform a mobject back into the state it saved.

    Save the state first with [`save_state`][manimgx.Mobject.save_state]; the animation
    transforms the mobject into it.

    Args:
        mobject: The mobject to restore.

    Examples:
        ```python
        import manimgx as m


        class RestoreExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                square.save_state()
                square.scale(0.5).rotate(m.PI / 4).shift(4 * m.LEFT)
                square.set_color(m.YELLOW)
                self.add(square)
                self.play(m.Restore(square, run_time=2))
        ```
    """

    def __init__(self, mobject: Mobject, **kwargs: Unpack[TransformOptions]) -> None:
        super().__init__(mobject.restore, **kwargs)


class ApplyFunction(Transform):
    """Transform a mobject into what a function makes of it.

    The function gets a copy of the mobject when the animation begins, and returns the
    state to transform into: the copy, changed, or a new mobject (anything else raises a
    TypeError).

    Args:
        function: A function from a copy of the mobject to its end state.
        mobject: The mobject to transform.

    Examples:
        ```python
        import manimgx as m


        class ApplyFunctionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                self.add(square)

                def to_red_circle(mob: m.Mobject) -> m.Mobject:
                    circle = m.Circle(radius=2, color=m.RED, fill_opacity=0.5)
                    return circle.move_to(mob)

                self.play(m.ApplyFunction(to_red_circle, square))
        ```
    """

    def __init__(
        self,
        function: Callable[[Mobject], Mobject],
        mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.function = function
        super().__init__(mobject, keys=(None, self._apply), **kwargs)

    def _apply(self, copy: Mobject) -> Mobject:
        target = self.function(copy)
        if not isinstance(target, Mobject):
            raise TypeError(
                "Functions passed to ApplyFunction must return object of type Mobject"
            )
        return target


class ApplyMatrix(ApplyPointwiseFunction):
    """Transform a mobject by a matrix: each point p goes to M·p.

    A 2 × 2 matrix acts on x and y, keeping z; a 3 × 3 one on all three (any other shape
    raises a ValueError). The points travel in straight lines. It runs 3 seconds.

    Args:
        matrix: The matrix, 2 × 2 or 3 × 3, as nested lists or an array.
        mobject: The mobject to transform.
        about_point: The point that stays where it is.

    Examples:
        ```python
        import manimgx as m


        class ApplyMatrixExample(m.Scene):
            def construct(self) -> None:
                matrix = [[1, 1], [0, 2 / 3]]
                plane = m.NumberPlane()
                text = m.Text("Hello World!", font_size=72)
                self.add(plane, text)
                self.play(m.ApplyMatrix(matrix, plane), m.ApplyMatrix(matrix, text))
        ```
    """

    def __init__(
        self,
        matrix: npt.ArrayLike,
        mobject: Mobject,
        about_point: Point3DLike = ORIGIN,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        matrix = np.array(matrix)
        if matrix.shape == (2, 2):
            matrix = np.block(
                [[matrix, np.zeros((2, 1))], [np.zeros((1, 2)), np.ones((1, 1))]]
            )
        elif matrix.shape != (3, 3):
            raise ValueError("Matrix has bad dimensions")
        center = np.asarray(about_point, dtype=float)
        super().__init__(
            lambda p: np.dot(p - center, matrix.T) + center, mobject, **kwargs
        )


class ApplyComplexFunction(_ApplyMethod):
    """Transform a mobject into its image under a function of a complex number.

    Each point (x, y, z) is taken as x + iy and travels in a straight line to its image
    under the function, keeping z, and a path's curves are mapped as
    [apply_function][manimgx.Mobject.apply_function] maps them.

    Args:
        function: A function from a complex number to a complex number.
        mobject: The mobject to move.

    Examples:
        ```python
        import manimgx as m


        class ApplyComplexFunctionExample(m.Scene):
            def construct(self) -> None:
                plane = m.NumberPlane(x_range=(-3, 3, 0.5), y_range=(-3, 3, 0.5))
                plane.prepare_for_nonlinear_transform()
                self.add(plane)
                self.play(m.ApplyComplexFunction(lambda z: z**2 / 4, plane), run_time=2)
        ```
    """

    def __init__(
        self,
        function: Callable[[complex], complex],
        mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.function = function
        super().__init__(mobject.apply_complex_function, function, **kwargs)


class CyclicReplace(Transform):
    """Move each mobject to the place of the next one, and the last to the first's.

    Each travels along an arc, of 90° by default (`path_arc`). A group given alone is
    taken as the mobjects.

    Args:
        *mobjects: The mobjects, in the order of the cycle.

    Examples:
        ```python
        import manimgx as m


        class CyclicReplaceExample(m.Scene):
            def construct(self) -> None:
                shapes = m.VGroup(
                    m.Square(color=m.BLUE),
                    m.Circle(color=m.YELLOW),
                    m.Triangle(color=m.GREEN),
                    m.Star(color=m.RED),
                ).arrange(buff=1)
                self.add(shapes)
                self.play(m.CyclicReplace(*shapes))
                self.play(m.CyclicReplace(*shapes))
        ```
    """

    def __init__(self, *mobjects: Mobject, **kwargs: Unpack[TransformOptions]) -> None:
        self.group = (
            mobjects[0]
            if len(mobjects) == 1 and isinstance(mobjects[0], Group)
            else _gathered(*mobjects)
        )
        kwargs.setdefault("path_arc", 90 * DEGREES)
        super().__init__(self.group, keys=(None, self._cycled), **kwargs)

    def _cycled(self, target: Mobject) -> Mobject:
        for m1, m2 in zip([target[-1], *target[:-1]], self.group, strict=True):
            m1.move_to(m2)
        return target


class Swap(CyclicReplace):
    """Swap the places of two mobjects, each along an arc.

    The same as [`CyclicReplace`][manimgx.CyclicReplace], which with two mobjects moves
    each to the other's place.

    Args:
        *mobjects: The two mobjects.
        **kwargs: [Transform options][manimgx.animation.transform.TransformOptions].

    Examples:
        ```python
        import manimgx as m


        class SwapExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=1)
                circle = m.Circle(color=m.RED, fill_opacity=1)
                square.shift(2 * m.LEFT)
                circle.shift(2 * m.RIGHT)
                self.add(square, circle)
                self.play(m.Swap(square, circle))
        ```
    """


class FadeTransform(Transform):
    """Cross-fade a mobject into another, each moving onto the other's place and size.

    The mobject fades out as it moves and stretches onto `target_mobject`, and the
    target fades in from the mobject's place and size. When it finishes, the target is
    in the scene and the mobject is not (it is back as it was when the animation was
    made).

    Args:
        mobject: The mobject to fade out.
        target_mobject: The mobject to fade in; it joins the scene.
        stretch: Whether each is stretched to the other's width and height; if not, it
            is scaled evenly to match the dimension `dim_to_match`.
        dim_to_match: The dimension matched when not stretching: 0 the width, 1 the
            height.

    Examples:
        ```python
        import manimgx as m


        class FadeTransformExample(m.Scene):
            def construct(self) -> None:
                rectangle = m.Rectangle(
                    width=4, height=1.5, color=m.BLUE, fill_opacity=0.5
                ).shift(3 * m.LEFT)
                circle = m.Circle(radius=1.5, color=m.YELLOW, fill_opacity=0.5)
                circle.shift(3 * m.RIGHT)
                self.add(rectangle)
                self.play(m.FadeTransform(rectangle, circle, run_time=2))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        stretch: bool = True,
        dim_to_match: int = 1,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.to_add_on_completion, self.stretch, self.dim_to_match = (
            target_mobject,
            stretch,
            dim_to_match,
        )
        self._start = mobject.copy()  # what the mobject is put back to when it is done
        super().__init__(
            Group(mobject, target_mobject.copy()),
            keys=(self._fading_in, self._faded_out),
            **kwargs,
        )

    def _fading_in(self, group: Mobject) -> Mobject:
        """Where it starts: the target ghosted onto the mobject."""
        return self._ghosted(group, 1, 0)

    def _faded_out(self, group: Mobject) -> Mobject:
        """Where it ends: the mobject ghosted onto the target."""
        return self._ghosted(group, 0, 1)

    def _ghosted(self, group: Mobject, i: int, j: int) -> Mobject:
        """The group with its part i ghosted onto its part j."""
        self.ghost_to(group[i], group[j])
        return group

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def ghost_to(self, source: Mobject, target: Mobject) -> None:
        """Fit a mobject onto another and make it transparent.

        It is stretched, or scaled to match (`stretch`, `dim_to_match`): the state one
        side of the cross-fade fades from or to. `begin` calls it for both sides.

        Args:
            source: The mobject to fit and make transparent.
            target: The mobject it is fitted onto; if it is empty, `source` stays in
                place.
        """
        if target.get_num_points() or target.submobjects:
            source.replace(target, stretch=self.stretch, dim_to_match=self.dim_to_match)
        source.set_opacity(0)

    def clean_up_from_scene(self, scene: Scene) -> None:
        Animation.clean_up_from_scene(self, scene)
        scene.remove(self.mobject)
        self.mobject[0].become(self._start)
        scene.add(self.to_add_on_completion)


class FadeTransformPieces(FadeTransform):
    """Cross-fade a mobject into another, part by part.

    The parts of the two are matched up, and each part cross-fades onto its match as
    [`FadeTransform`][manimgx.FadeTransform] does for a whole.

    Args:
        mobject: The mobject to fade out.
        target_mobject: The mobject to fade in; it joins the scene.
        stretch: Whether each part is stretched to its match's width and height; if not,
            it is scaled evenly to match the dimension `dim_to_match`.
        dim_to_match: The dimension matched when not stretching: 0 the width, 1 the
            height.
        **kwargs: [Transform options][manimgx.animation.transform.TransformOptions].

    Examples:
        ```python
        import manimgx as m


        class FadeTransformPiecesExample(m.Scene):
            def construct(self) -> None:
                source = m.VGroup(m.Square(), m.Circle().shift(m.LEFT + m.UP))
                target = m.VGroup(m.Circle(), m.Triangle().shift(m.RIGHT + m.DOWN))
                source.set_color(m.BLUE).shift(3 * m.LEFT)
                target.set_color(m.YELLOW).shift(3 * m.RIGHT)
                self.add(source)
                self.play(m.FadeTransformPieces(source, target, run_time=2))
        ```
    """

    def begin(self) -> None:
        self.mobject[0].align_submobjects(self.mobject[1])
        super().begin()

    def ghost_to(self, source: Mobject, target: Mobject) -> None:
        for sm0, sm1 in zip(source.get_family(), target.get_family(), strict=True):
            super().ghost_to(sm0, sm1)


class FocusOn(Transform):
    """Close a spotlight in on a point.

    A transparent disc covering the frame shrinks onto `focus_point`, turning `color` at
    `opacity` as it closes, and is gone when the animation finishes; it follows a
    mobject that moves. It runs 2 seconds.

    Args:
        focus_point: The point to focus on, or a mobject whose center to focus on.
        opacity: The disc's opacity at the end.
        color: The disc's color.

    Examples:
        ```python
        import manimgx as m


        class FocusOnExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(2 * m.DOWN, radius=0.2, color=m.YELLOW)
                self.add(m.Text("Focus on the dot below", font_size=60), dot)
                self.play(m.FocusOn(dot))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 2.0, "remover": True}

    def __init__(
        self,
        focus_point: Point3DLike | Mobject,
        opacity: float = 0.2,
        color: ParsableManimColor = GREY,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        from manimgx.mobjects.shapes import Dot

        self.focus_point, self.color, self.opacity = focus_point, color, opacity
        start = Dot(
            radius=config.frame_x_radius + config.frame_y_radius,
            stroke_width=0,
            fill_color=color,
            fill_opacity=0,
        )
        target = Dot(radius=0).set_fill(color, opacity=opacity)
        target.add_updater(
            lambda d: d.move_to(focus_point)
        )  # its own object, following the point
        super().__init__(start, target, **kwargs)


class UpdateFromFunc[M: Mobject = Mobject](Animation[M]):
    """Call a function on a mobject at every frame, for the animation's run time.

    The function gets the mobject, not the progress: use it to keep a mobject up to date
    while other animations play. The mobject's own updaters act on it directly
    (`suspend_mobject_updating` is False).

    Args:
        mobject: The mobject to update.
        update_function: A function of the mobject, called at every frame.

    Examples:
        ```python
        import manimgx as m


        class UpdateFromFuncExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(4 * m.LEFT, radius=0.2, color=m.YELLOW)
                label = m.Text("dot", font_size=60)
                self.add(dot, label)
                self.play(
                    dot.animate.shift(8 * m.RIGHT),
                    m.UpdateFromFunc(label, lambda mob: mob.next_to(dot, m.UP)),
                    run_time=2,
                )
        ```
    """

    keys: Sequence[Key] = ()

    defaults: ClassVar[AnimationOptions] = {"suspend_mobject_updating": False}

    def __init__(
        self,
        mobject: M,
        update_function: Callable[[M], object],
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.update_function = update_function
        super().__init__(mobject, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        self.update_function(self.mobject)


class UpdateFromAlphaFunc[M: Mobject = Mobject](Animation[M]):
    """Call a function on a mobject at every frame, with the animation's progress.

    The function gets the mobject and the progress, eased by the rate function, and sets
    the mobject as it is at that progress. The mobject's own updaters act on it directly
    (`suspend_mobject_updating` is False).

    Args:
        mobject: The mobject to update.
        update_function: A function of the mobject and the eased progress, from 0 to 1.

    Examples:
        ```python
        import manimgx as m


        class UpdateFromAlphaFuncExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)

                def slide(mob: m.Square, alpha: float) -> None:
                    mob.move_to((8 * alpha - 4) * m.RIGHT)
                    mob.set_color(m.interpolate_color(m.BLUE, m.YELLOW, alpha))

                self.play(m.UpdateFromAlphaFunc(square, slide, run_time=2))
        ```
    """

    keys: Sequence[Key] = ()

    defaults: ClassVar[AnimationOptions] = {"suspend_mobject_updating": False}

    def __init__(
        self,
        mobject: M,
        update_function: Callable[[M, float], object],
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.update_function = update_function
        super().__init__(mobject, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        self.update_function(self.mobject, self.rate_func(alpha))


class MaintainPositionRelativeTo(Animation):
    """Keep a mobject at the same offset from another's center, at every frame.

    The offset is the one between their centers when the animation is made; play it
    together with the animations that move `tracked_mobject`.

    Args:
        mobject: The mobject to keep in place.
        tracked_mobject: The mobject it follows.

    Examples:
        ```python
        import manimgx as m


        class MaintainPositionRelativeToExample(m.Scene):
            def construct(self) -> None:
                leader = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)
                follower = m.Circle(color=m.YELLOW).next_to(leader, m.RIGHT, buff=0.5)
                m.VGroup(leader, follower).shift(4 * m.LEFT + 1.5 * m.DOWN)
                self.add(leader, follower)
                self.play(
                    leader.animate.shift(5 * m.RIGHT + 3 * m.UP),
                    m.MaintainPositionRelativeTo(follower, leader),
                    run_time=2,
                )
        ```
    """

    keys: Sequence[Key] = ()

    def __init__(
        self,
        mobject: Mobject,
        tracked_mobject: Mobject,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.tracked_mobject = tracked_mobject
        self.diff = mobject.get_center() - tracked_mobject.get_center()
        super().__init__(mobject, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        self.mobject.shift(
            self.tracked_mobject.get_center() - self.mobject.get_center() + self.diff
        )


class Rotating(Rotate):
    """Rotate a mobject at a steady pace: by default, a full turn in 5 seconds.

    A [`Rotate`][manimgx.Rotate] whose angle is [`TAU`][manimgx.TAU] unless given
    another, at an even pace (`linear`), over 5 seconds.

    Args:
        mobject: The mobject to rotate.
        angle: The angle, in radians, counterclockwise about `axis`.
        axis: The axis it turns about; the default, [`OUT`][manimgx.OUT], turns it in
            the plane of the screen.
        about_point: The pivot; None to take it from `about_edge`, or the center.
        about_edge: The direction of the point of its bounding box it turns about, when
            no `about_point` is given.

    Examples:
        ```python
        import manimgx as m


        class RotatingExample(m.Scene):
            def construct(self) -> None:
                hand = m.Arrow(m.ORIGIN, 2.5 * m.UP, buff=0, color=m.YELLOW)
                self.add(m.Circle(radius=3, color=m.GREY), hand)
                self.play(m.Rotating(hand, -m.TAU, about_point=m.ORIGIN, run_time=4))
        ```
    """

    # timed as CE's Rotating (5 s, linear, a full turn): a tween along circles, not a
    # procedure (perth-e9's)
    defaults: ClassVar[AnimationOptions] = {"run_time": 5.0, "rate_func": linear}

    def __init__(
        self,
        mobject: Mobject,
        angle: float = TAU,
        axis: Vector3DLike = OUT,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(mobject, angle, axis, about_point, about_edge, **kwargs)


class MoveAlongPath(Transform):
    """Move a mobject along a path.

    Its center travels along `path` from the path's start to its end, at an even speed
    along its length (as eased by the rate function), and the mobject keeps its shape.
    It starts at the path's start, wherever it was. Its own updaters act on it directly
    while it moves (`suspend_mobject_updating` is False).

    Args:
        mobject: The mobject to move.
        path: The curve it travels along.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class MoveAlongPathExample(m.Scene):
            def construct(self) -> None:
                path = m.FunctionGraph(lambda x: 2 * np.sin(x), x_range=(-6, 6))
                dot = m.Dot(radius=0.2, color=m.ORANGE)
                self.add(path.set_color(m.GREY), dot)
                self.play(m.MoveAlongPath(dot, path, run_time=3))
        ```
    """

    # a tween whose path is the curve itself, not a procedure (perth-e9's)
    defaults: ClassVar[AnimationOptions] = {"suspend_mobject_updating": False}

    def __init__(
        self, mobject: Mobject, path: VMobject, **kwargs: Unpack[TransformOptions]
    ) -> None:
        self.path = path
        kwargs["path_func"] = Path(steps=(path.point_from_proportion,))
        super().__init__(
            mobject,
            keys=tuple(
                (
                    lambda m, end=end: m.move_to(path.point_from_proportion(end))
                    for end in (0, 1)
                )
            ),
            **kwargs,
        )


class Homotopy(Animation):
    """Deform a mobject by a homotopy: a function of each point and the progress.

    At progress t, from 0 to 1 (eased by the rate function), the mobject is the image of
    the mobject as it began: each point (x, y, z) goes to `homotopy(x, y, z, t)`, and a
    path's curves are mapped as [apply_function][manimgx.Mobject.apply_function] maps
    them. It runs 3 seconds.

    Args:
        homotopy: A function of x, y, z and t, returning where the point is at t.
        mobject: The mobject to deform.
        apply_function_kwargs: Where the coordinates are measured from:
            `{"about_point": ...}` or `{"about_edge": ...}`; None for the origin.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class HomotopyExample(m.Scene):
            def construct(self) -> None:
                line = m.FunctionGraph(lambda x: 0, x_range=(-6, 6), color=m.BLUE)

                def wave(x: float, y: float, z: float, t: float) -> tuple[float, ...]:
                    return (x, y + 1.5 * t * np.sin(2 * x - 6 * t), z)

                self.add(line)
                self.play(m.Homotopy(wave, line))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 3.0}

    def __init__(
        self,
        homotopy: Callable[[float, float, float, float], Point3DLike],
        mobject: Mobject,
        apply_function_kwargs: Pivot | None = None,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.homotopy = homotopy
        self.apply_function_kwargs: Pivot = apply_function_kwargs or {}
        super().__init__(mobject, **kwargs)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def function_at_time_t(self, t: float) -> Callable[[Point3D], Point3D]:
        """Return the homotopy at one progress, as a function of a point.

        Args:
            t: The progress, from 0 to 1.

        Returns:
            A function from a point to where it is at `t`.
        """
        return lambda p: np.array(self.homotopy(p[0], p[1], p[2], t))

    def interpolate_submobject(
        self, submobject: Mobject, starting_submobject: Mobject, alpha: float
    ) -> None:
        submobject.points = starting_submobject.points
        submobject.apply_function(
            self.function_at_time_t(alpha), **self.apply_function_kwargs
        )


class ComplexHomotopy(Homotopy):
    """Deform a mobject by a complex homotopy: a function of x + iy and the progress.

    At progress t, from 0 to 1 (eased by the rate function), the mobject is the image of
    the mobject as it began: each point (x, y, z) goes to `complex_homotopy(x + iy, t)`,
    keeping z, and a path's curves are mapped as
    [apply_function][manimgx.Mobject.apply_function] maps them. It runs 3 seconds.

    Args:
        complex_homotopy: A function of z and t, returning where the point is at t, as a
            complex number.
        mobject: The mobject to deform.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ComplexHomotopyExample(m.Scene):
            def construct(self) -> None:
                plane = m.NumberPlane(x_range=(-3, 3), y_range=(-3, 3))
                plane.prepare_for_nonlinear_transform()
                self.add(plane)
                self.play(
                    m.ComplexHomotopy(lambda z, t: z * np.exp(0.5j * t * abs(z)), plane)
                )
        ```
    """

    def __init__(
        self,
        complex_homotopy: Callable[[complex, float], complex],
        mobject: Mobject,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        def homotopy(
            x: float, y: float, z: float, t: float
        ) -> tuple[float, float, float]:
            c = complex_homotopy(complex(x, y), t)
            return (c.real, c.imag, z)

        super().__init__(homotopy, mobject, **kwargs)


class ApplyWave(Homotopy):
    """Send a wave through a mobject, from left to right.

    Its points are displaced along `direction`, by up to `amplitude`, as the wave passes
    them, and are back in place once it has passed. It runs 2 seconds.

    Args:
        mobject: The mobject to wave.
        direction: The direction the points are displaced in.
        amplitude: How far they are displaced at most, in scene units.
        wave_func: The shape of each ripple's rise: a rate function.
        time_width: The wave's width, as a fraction of the mobject's width.
        ripples: How many ripples the wave has.

    Examples:
        ```python
        import manimgx as m


        class ApplyWaveExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("WaveWaveWave", font_size=120)
                self.add(text)
                self.play(m.ApplyWave(text))
                self.play(m.ApplyWave(text, ripples=3, amplitude=0.4))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 2.0}

    def __init__(
        self,
        mobject: Mobject,
        direction: Vector3DLike = UP,
        amplitude: float = 0.2,
        wave_func: Callable[[float], float] = smooth,
        time_width: float = 1,
        ripples: int = 1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        x_min, x_max = mobject.get_left()[0], mobject.get_right()[0]
        vect = amplitude * normalize(direction)

        def wave(t: float) -> float:
            t = 1 - t
            if t >= 1 or t <= 0:
                return 0
            phases = ripples * 2
            phase = int(t * phases)
            if phase == 0:
                return wave_func(t * phases)
            if phase == phases - 1:
                t -= phase / phases
                return (1 - wave_func(t * phases)) * (2 * (ripples % 2) - 1)
            phase = int((phase - 1) / 2)
            t -= (2 * phase + 1) / phases
            return (1 - 2 * wave_func(t * ripples)) * (1 - 2 * (phase % 2))

        def homotopy(x: float, y: float, z: float, t: float) -> np.ndarray:
            upper = interpolate(0, 1 + time_width, t)
            relative_x = inverse_interpolate(x_min, x_max, x)
            return (
                np.array([x, y, z])
                + wave(inverse_interpolate(upper - time_width, upper, relative_x))
                * vect
            )

        super().__init__(homotopy, mobject, **kwargs)


class PhaseFlow(Animation):
    """Carry a mobject's points along a vector field.

    Each point moves with the velocity `function` gives it where it is, for
    `virtual_time` units of the field's time over the animation, from where it is when
    the animation begins. The flow is integrated in steps of the field's time,
    `config.simulation_rate` a second of the animation, by the classical Runge–Kutta
    method, so it is the same at every frame rate; a frame between steps shows the flow
    carried on from the step before it. A path's curves are mapped as
    [apply_function][manimgx.Mobject.apply_function] maps them. It runs at an even pace
    (`linear`), and the mobject's own updaters act on it directly
    (`suspend_mobject_updating` is False).

    Args:
        function: The vector field: a function from a point to its velocity.
        mobject: The mobject to carry.
        virtual_time: How long the points flow, in the field's units of time.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class PhaseFlowExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)
                square.shift(3 * m.RIGHT)
                self.add(m.Dot(), square)

                def spiral(p: np.ndarray) -> np.ndarray:
                    return np.array([-p[1] - 0.3 * p[0], p[0] - 0.3 * p[1], 0.0])

                self.play(m.PhaseFlow(spiral, square, virtual_time=m.PI, run_time=3))
        ```
    """

    keys: Sequence[Key] = ()

    defaults: ClassVar[AnimationOptions] = {
        "suspend_mobject_updating": False,
        "rate_func": linear,
    }

    def __init__(
        self,
        function: Callable[[Point3D], Point3D],
        mobject: Mobject,
        virtual_time: float = 1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.virtual_time, self.function = virtual_time, function
        super().__init__(mobject, **kwargs)

    def begin(self) -> None:
        super().begin()
        # the flow's steps, whenever the frames fall: those taken, and where they left it
        self._grid = max(1, round(config.simulation_rate * self.run_time))
        self._taken = 0
        self._left = [(m, m._geometry) for m in self.mobject.get_family()]

    def interpolate_mobject(self, alpha: float) -> None:
        at = self.rate_func(alpha) * self._grid  # where the flow is, in steps
        step = self.virtual_time / self._grid
        for mob, geometry in self._left:
            mob._geometry = geometry
        while self._taken != (whole := math.floor(at)):
            forward = self._taken < whole
            self._flow(step if forward else -step)
            self._taken += 1 if forward else -1
            self._left = [(m, m._geometry) for m in self.mobject.get_family()]
        if at > whole:
            self._flow((at - whole) * step)

    def _flow(self, dt: float) -> None:
        """Carry the points on by `dt` of the field's time: a Runge–Kutta step."""
        field = self.function

        def carried(p: Point3D) -> Point3D:
            k1 = field(p)
            k2 = field(p + dt / 2 * k1)
            k3 = field(p + dt / 2 * k2)
            return p + dt / 6 * (k1 + 2 * k2 + 2 * k3 + field(p + dt * k3))

        self.mobject.apply_function(carried)


class Wiggle(Animation):
    """Wiggle a mobject: rock it back and forth while it swells and shrinks back.

    It grows to `scale_value` times its size and back, while turning back and forth by
    up to `rotation_angle`, `n_wiggles` swings in all, about its center or the given
    points. It runs 2 seconds.

    Args:
        mobject: The mobject to wiggle.
        scale_value: How many times its size it grows to, halfway through.
        rotation_angle: How far it turns each way at most, in radians.
        n_wiggles: How many swings it makes.
        scale_about_point: The point it grows about; None for its center.
        rotate_about_point: The point it turns about; None for its center.

    Examples:
        ```python
        import manimgx as m


        class WiggleExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Wiggle", font_size=144)
                self.add(text)
                self.play(m.Wiggle(text))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 2.0}

    def __init__(
        self,
        mobject: Mobject,
        scale_value: float = 1.1,
        rotation_angle: float = 0.01 * TAU,
        n_wiggles: int = 6,
        scale_about_point: Point3DLike | None = None,
        rotate_about_point: Point3DLike | None = None,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.scale_value, self.rotation_angle, self.n_wiggles = (
            scale_value,
            rotation_angle,
            n_wiggles,
        )
        self.scale_about_point = (
            None if scale_about_point is None else np.array(scale_about_point)
        )
        self.rotate_about_point = (
            None if rotate_about_point is None else np.array(rotate_about_point)
        )
        super().__init__(mobject, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        # the pivot: the whole's center as it began, once a frame (not the center of a
        # mobject half of whose parts this frame has wiggled already)
        self._center = self.frames[0].get_center()
        super().interpolate_mobject(alpha)

    def interpolate_submobject(
        self, submobject: Mobject, starting_submobject: Mobject, alpha: float
    ) -> None:
        submobject._geometry = starting_submobject._geometry
        submobject.scale(
            interpolate(1, self.scale_value, there_and_back(alpha)),
            about_point=(
                self._center
                if self.scale_about_point is None
                else self.scale_about_point
            ),
        )
        submobject.rotate(
            wiggle(alpha, self.n_wiggles) * self.rotation_angle,
            about_point=(
                self._center
                if self.rotate_about_point is None
                else self.rotate_about_point
            ),
        )


class ChangingDecimal[V: (float, complex) = float](Animation["DecimalNumber[V]"]):
    """Change the value a number shows with the animation's progress.

    At every frame, the number shows `number_update_func` of the progress, from 0 to 1,
    eased by the rate function.

    Args:
        decimal_mob: The number to change.
        number_update_func: A function from the progress to the value to show.

    Examples:
        ```python
        import manimgx as m


        class ChangingDecimalExample(m.Scene):
            def construct(self) -> None:
                number = m.DecimalNumber(0, font_size=144)
                self.add(number)
                self.play(m.ChangingDecimal(number, lambda a: 100 * a, run_time=3))
        ```
    """

    keys: Sequence[Key] = ()

    defaults: ClassVar[AnimationOptions] = {"suspend_mobject_updating": False}

    def __init__(
        self,
        decimal_mob: DecimalNumber[V],
        number_update_func: Callable[[float], V],
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.number_update_func = number_update_func
        super().__init__(decimal_mob, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        self.mobject.set_value(self.number_update_func(self.rate_func(alpha)))


class ChangeDecimalToValue[V: (float, complex) = float](ChangingDecimal[V]):
    """Count a number to a value.

    It goes from the value it has when the animation is made to `target_number`, eased
    by the rate function.

    Args:
        decimal_mob: The number to change.
        target_number: The value it ends at.

    Examples:
        ```python
        import manimgx as m


        class ChangeDecimalToValueExample(m.Scene):
            def construct(self) -> None:
                number = m.DecimalNumber(0, font_size=144)
                self.add(number)
                self.play(m.ChangeDecimalToValue(number, 3.14, run_time=2))
        ```
    """

    def __init__(
        self,
        decimal_mob: DecimalNumber[V],
        target_number: V,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        start = decimal_mob.number
        super().__init__(
            decimal_mob, lambda a: interpolate(start, target_number, a), **kwargs
        )


class ShowIncreasingSubsets(Animation):
    """Show the submobjects of a group one more at a time.

    At progress p, eased by the rate function, the first ⌊p·n⌋ of its n submobjects are
    shown and the rest are hidden: left out of the picture, not changed, so each part
    shows as it is, whatever else plays on it. The group joins the scene when the
    animation begins. A part still hidden when the animation ends stays unseen, left
    transparent; a remover's group leaves the scene as it is. Pass `rate_func=linear` for
    an even pace.

    Args:
        group: The group whose submobjects are shown.
        int_func: How many are shown: a function of p·n (the default rounds down).

    Examples:
        ```python
        import manimgx as m


        class ShowIncreasingSubsetsExample(m.Scene):
            def construct(self) -> None:
                dots = m.VGroup(*(m.Dot(radius=0.4) for _ in range(8)))
                dots.arrange(buff=0.6).set_color_by_gradient(m.BLUE, m.YELLOW)
                self.play(m.ShowIncreasingSubsets(dots, rate_func=m.linear, run_time=2))
        ```
    """

    keys: Sequence[Key] = ()

    defaults: ClassVar[AnimationOptions] = {
        "suspend_mobject_updating": False,
        "introducer": True,
    }

    def __init__(
        self,
        group: Mobject,
        int_func: Callable[[float], float] = np.floor,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.all_submobs, self.int_func = list(group.submobjects), int_func
        self._hidden: list[Mobject] = []
        super().__init__(group, **kwargs)

    @property
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def hidden(self) -> Sequence[Mobject]:
        """The submobjects it has not shown yet, or no longer shows."""
        return self._hidden

    def interpolate_mobject(self, alpha: float) -> None:
        value = (
            1 - self.rate_func(alpha)
            if self.reverse_rate_function
            else self.rate_func(alpha)
        )
        self.update_submobject_list(int(self.int_func(value * len(self.all_submobs))))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def update_submobject_list(self, index: int) -> None:
        """Show the first `index` submobjects and hide the rest.

        `interpolate_mobject` calls it at every frame.

        Args:
            index: How many submobjects are shown.
        """
        self._hidden = self.all_submobs[max(index, 0) :]

    def _release(self) -> None:
        super()._release()
        # ended, what it hides stays unseen: transparent, the one way the scene holds a
        # part unseen (a remover's group leaves the scene as it is)
        if not self.is_remover():
            for part in self._hidden:
                part.set_opacity(0)
        self._hidden = []


class ShowSubmobjectsOneByOne(ShowIncreasingSubsets):
    """Show mobjects one at a time, each in place of the one before.

    At progress p, eased by the rate function, only the ⌈p·n⌉-th of the n mobjects is
    shown, as it is, and the others are hidden; when the animation ends, those it hides
    stay unseen, left transparent. Pass `rate_func=linear` for an even pace.

    Args:
        group: The mobjects to show in turn.
        int_func: Which one is shown: a function of p·n (the default rounds up).

    Examples:
        ```python
        import manimgx as m


        class ShowSubmobjectsOneByOneExample(m.Scene):
            def construct(self) -> None:
                polygons = (
                    m.VGroup(
                        *(m.RegularPolygon(n, fill_opacity=1) for n in range(3, 9))
                    )
                    .set_color(m.YELLOW)
                    .scale(2.5)
                )
                self.play(
                    m.ShowSubmobjectsOneByOne(polygons, rate_func=m.linear, run_time=3)
                )
        ```
    """

    def __init__(
        self,
        group: Iterable[Mobject],
        int_func: Callable[[float], float] = np.ceil,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        super().__init__(_gathered(*group), int_func=int_func, **kwargs)

    def update_submobject_list(self, index: int) -> None:
        self._hidden = [m for i, m in enumerate(self.all_submobs) if i != index - 1]


class AddTextLetterByLetter(ShowIncreasingSubsets):
    """Type a text in, one letter at a time.

    The letters appear one after another at an even pace (`linear`), `time_per_char`
    seconds each unless a `run_time` is given. The text joins the scene when the
    animation begins.

    Args:
        text: The text to type, whose submobjects are its letters; a text without any
            raises a ValueError.
        int_func: How many letters are shown: a function of the progress times the
            number of letters (the default rounds up, so the first shows at once).
        time_per_char: How long each letter takes, in seconds.

    Examples:
        ```python
        import manimgx as m


        class AddTextLetterByLetterExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Hello, world!", font_size=96)
                self.play(m.AddTextLetterByLetter(text, time_per_char=0.15))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": linear}

    def __init__(
        self,
        text: Mobject,
        int_func: Callable[[float], float] = np.ceil,
        time_per_char: float = 0.1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.time_per_char = time_per_char
        if not text.family_members_with_points():
            raise ValueError(
                f"The text mobject {text} does not seem to contain any characters."
            )
        kwargs.setdefault(
            "run_time", max(1 / config.frame_rate, time_per_char) * len(text)
        )
        super().__init__(text, int_func=int_func, **kwargs)


class RemoveTextLetterByLetter(AddTextLetterByLetter):
    """Remove a text one letter at a time, from the last, and take it out of the scene.

    The reverse of [`AddTextLetterByLetter`][manimgx.AddTextLetterByLetter]: the letters
    disappear from the last to the first, `time_per_char` seconds each unless a
    `run_time` is given. The text leaves the scene when the animation finishes, as it
    was before it: adding it again shows it.

    Args:
        text: The text to remove, whose submobjects are its letters; a text without any
            raises a ValueError.
        int_func: How many letters are still shown: a function of what is left of the
            progress times the number of letters (the default rounds up).
        time_per_char: How long each letter takes, in seconds.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions].

    Examples:
        ```python
        import manimgx as m


        class RemoveTextLetterByLetterExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Hello, world!", font_size=96)
                self.add(text)
                self.play(m.RemoveTextLetterByLetter(text, time_per_char=0.15))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {
        "reverse_rate_function": True,
        "introducer": False,
        "remover": True,
    }


class TypeWithCursor(AddTextLetterByLetter):
    """Type a text in letter by letter, with a cursor after the last letter typed.

    The letters appear as with [`AddTextLetterByLetter`][manimgx.AddTextLetterByLetter],
    and the cursor, shown as it is, moves along after them. The cursor becomes part of
    the text, at its end, and stays there when the animation finishes unless
    `leave_cursor_on` is False. The text joins the scene when the animation begins.

    Args:
        text: The text to type, whose submobjects are its letters.
        cursor: The cursor: any mobject, such as a thin rectangle.
        buff: The gap between the last letter and the cursor, in scene units.
        keep_cursor_y: Whether the cursor keeps its own height as it moves; if not, it
            moves at the text's middle height.
        leave_cursor_on: Whether the cursor stays at the end of the text when the
            animation finishes.
        time_per_char: How long each letter takes, in seconds.

    Examples:
        ```python
        import manimgx as m


        class TypeWithCursorExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Typing...", font_size=96, color=m.PURPLE)
                cursor = m.Rectangle(m.GREY_A, height=1.1, width=0.4, fill_opacity=1)
                cursor.move_to(text[0])
                self.play(m.TypeWithCursor(text, cursor))
        ```
    """

    def __init__(
        self,
        text: Mobject,
        cursor: Mobject,
        buff: float = 0.1,
        keep_cursor_y: bool = True,
        leave_cursor_on: bool = True,
        time_per_char: float = 0.1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.cursor, self.buff, self.keep_cursor_y, self.leave_cursor_on = (
            cursor,
            buff,
            keep_cursor_y,
            leave_cursor_on,
        )
        super().__init__(text, time_per_char=time_per_char, **kwargs)

    def begin(self) -> None:
        self.y_cursor = self.cursor.get_y()
        self.cursor_start = self.mobject.get_center()
        if self.keep_cursor_y:
            self.cursor.set_y(self.y_cursor)
        self.mobject.add(self.cursor)
        super().begin()

    def finish(self) -> None:
        if not self.leave_cursor_on:
            self.mobject.remove(self.cursor)
        super().finish()

    def clean_up_from_scene(self, scene: Scene) -> None:
        if not self.leave_cursor_on:
            scene.remove(self.cursor)
        super().clean_up_from_scene(scene)

    def update_submobject_list(self, index: int) -> None:
        super().update_submobject_list(index)
        anchor = self.all_submobs[index - 1] if index else self.all_submobs[0]
        (
            self.cursor.next_to(anchor, RIGHT, buff=self.buff)
            if index
            else self.cursor.move_to(anchor)
        ).set_y(self.cursor_start[1])
        if self.keep_cursor_y:
            self.cursor.set_y(self.y_cursor)


class UntypeWithCursor(TypeWithCursor):
    """Delete a text letter by letter, with a cursor after the last letter left.

    The reverse of [`TypeWithCursor`][manimgx.TypeWithCursor]: the letters disappear
    from the last to the first. The text leaves the scene when the animation finishes,
    as it was before it (adding it again shows it); the cursor becomes part of the
    text, and leaves with it.

    Args:
        text: The text to delete, whose submobjects are its letters.
        cursor: The cursor: any mobject, such as a thin rectangle.
        buff: The gap between the last letter and the cursor, in scene units.
        keep_cursor_y: Whether the cursor keeps its own height as it moves; if not, it
            moves at the text's middle height.
        leave_cursor_on: Whether the cursor stays part of the text when the animation
            finishes.
        time_per_char: How long each letter takes, in seconds.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions].

    Examples:
        ```python
        import manimgx as m


        class UntypeWithCursorExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Deleting...", font_size=96, color=m.PURPLE)
                cursor = m.Rectangle(m.GREY_A, height=1.1, width=0.4, fill_opacity=1)
                cursor.move_to(text[0])
                self.add(text)
                self.play(m.UntypeWithCursor(text, cursor))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {
        "reverse_rate_function": True,
        "introducer": False,
        "remover": True,
    }


class SpiralIn(Animation):
    """Fly the submobjects of a mobject in from far away, spiralling into place.

    Each comes home to where it is when the animation begins, from `scale_factor` + 1
    times as far from the mobject's center: on the way it turns once around that center
    (and back once about its own, so it keeps its orientation), and it fades in over the
    first `fade_in_fraction` of the way. The mobject joins the scene when the animation
    begins; making the animation changes nothing.

    Args:
        shapes: The mobject whose submobjects spiral in.
        scale_factor: How far out they start: `scale_factor` + 1 times as far from the
            center as their places.
        fade_in_fraction: The fraction of the way over which they fade in, from 0 to 1.

    Examples:
        ```python
        import manimgx as m


        class SpiralInExample(m.Scene):
            def construct(self) -> None:
                shapes = m.VGroup(
                    m.Circle(color=m.GREEN, fill_opacity=1),
                    m.Square(color=m.BLUE, fill_opacity=1),
                    m.Triangle(color=m.YELLOW, fill_opacity=1),
                    m.Star(color=m.RED, fill_opacity=1),
                ).arrange(buff=1)
                self.play(m.SpiralIn(shapes, run_time=2))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"introducer": True}

    def __init__(
        self,
        shapes: Mobject,
        scale_factor: float = 8,
        fade_in_fraction: float = 0.3,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.scale_factor, self.fade_in_fraction = scale_factor, fade_in_fraction
        super().__init__(shapes, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        alpha = self.rate_func(alpha)
        homes = self.frames[0]  # the first keyframe: the shapes as the animation began
        center = homes.get_center()
        for shape, home in zip(self.mobject, homes, strict=True):
            travel = (center - home.get_center()) * self.scale_factor
            fill, stroke = home.get_fill_opacity(), home.get_stroke_opacity()
            shape.become(home).shift(-travel * (1 - alpha))
            shape.rotate(TAU * alpha, about_point=center)
            shape.rotate(-TAU * alpha, about_point=shape.get_center_of_mass())
            shape.set_fill(opacity=min(fill, alpha * fill / self.fade_in_fraction))
            shape.set_stroke(
                opacity=min(stroke, alpha * stroke / self.fade_in_fraction)
            )


class AddTextWordByWord(Succession):
    """Type words in, letter by letter, pausing briefly after each word.

    Each submobject of `text_mobject` is a word, and the words come in turn: a word's own
    submobjects, its letters, appear one after another, `time_per_char` seconds each;
    then the word holds for 0.005 × (its number of letters)^1.5 seconds. Give it a group
    of words, such as a [`VGroup`][manimgx.VGroup] of [`Text`][manimgx.Text]s: the
    submobjects of a single `Text` are its letters, which have no parts of their own to
    type, so each appears whole in its turn.

    Args:
        text_mobject: The words: a group whose submobjects are words made of letters.
        time_per_char: How long each letter takes, in seconds.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions] for
            the whole.

    Examples:
        ```python
        import manimgx as m


        class AddTextWordByWordExample(m.Scene):
            def construct(self) -> None:
                words = m.VGroup(
                    *(m.Text(word, font_size=120) for word in ("Word", "by", "word"))
                ).arrange(buff=0.5)
                self.play(m.AddTextWordByWord(words, time_per_char=0.12))
        ```
    """

    def __init__(
        self,
        text_mobject: Mobject,
        time_per_char: float = 0.06,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.time_per_char = time_per_char
        anims = it.chain(
            *(
                [
                    ShowIncreasingSubsets(w, run_time=time_per_char * len(w)),
                    Animation(w, run_time=0.005 * len(w) ** 1.5),
                ]
                for w in text_mobject
            )
        )
        super().__init__(*anims, **kwargs)


class Flash(AnimationGroup):
    """Flash lines out from a point, like a burst of light.

    `num_lines` lines, `line_length` long and starting `flash_radius` from the point,
    shoot outward as passing flashes ([`ShowPassingFlash`][manimgx.ShowPassingFlash]),
    and are gone when the animation finishes. The animation options go to each line's
    flash.

    Args:
        point: The point to flash from, or a mobject whose center to flash from.
        line_length: Each line's length, in scene units.
        num_lines: How many lines.
        flash_radius: How far from the point the lines start, in scene units.
        line_stroke_width: The lines' width, in hundredths of a scene unit.
        color: The lines' color.
        time_width: Each line's flash window, as a fraction of its length.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions] for
            each line's flash.

    Examples:
        ```python
        import manimgx as m


        class FlashExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=2, color=m.BLUE, fill_opacity=0.5)
                self.add(circle)
                self.play(
                    m.Flash(
                        circle,
                        line_length=1,
                        num_lines=24,
                        flash_radius=2.2,
                        time_width=0.3,
                        run_time=2,
                    )
                )
        ```
    """

    def __init__(
        self,
        point: Point3DLike | Mobject,
        line_length: float = 0.2,
        num_lines: int = 12,
        flash_radius: float = 0.1,
        line_stroke_width: int = 3,
        color: ParsableManimColor = PURE_YELLOW,
        time_width: float = 1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        from manimgx.mobjects.shapes import Line

        self.point = (
            point.get_center()
            if isinstance(point, Mobject)
            else np.asarray(point, dtype=float)
        )
        self.color, self.time_width = color, time_width
        self.lines = VGroup()
        for angle in np.arange(0, TAU, TAU / num_lines):
            line = Line(self.point, self.point + line_length * RIGHT).shift(
                flash_radius * RIGHT
            )
            self.lines.add(line.rotate(angle, about_point=self.point))
        self.lines.set_color(color).set_stroke(width=line_stroke_width)
        super().__init__(
            *(
                ShowPassingFlash(line, time_width=time_width, **kwargs)
                for line in self.lines
            ),
            group=self.lines,
        )


class ShowPassingFlashWithThinningStrokeWidth(AnimationGroup):
    """Flash a stretch of a mobject's path along it, with a tail that thins behind it.

    `n_segments` passing flashes ([`ShowPassingFlash`][manimgx.ShowPassingFlash]) of
    copies of the mobject play together: their widths rise from none to the mobject's
    stroke width as their windows shrink from `time_width` to none, so the flash is
    widest at its head. The copies are gone when the animation finishes, and the mobject
    itself is left as it is. The animation options go to each flash.

    Args:
        vmobject: The mobject whose paths the flash travels along.
        n_segments: How many flashes make it up.
        time_width: The tail's length, as a fraction of the path's length.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions] for
            each flash.

    Examples:
        ```python
        import manimgx as m


        class ShowPassingFlashWithThinningStrokeWidthExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=2.5, color=m.YELLOW, stroke_width=16)
                self.add(circle.copy().set_stroke(m.GREY, width=4))
                self.play(
                    m.ShowPassingFlashWithThinningStrokeWidth(
                        circle, time_width=0.5, run_time=2
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"remover": True}

    def __init__(
        self,
        vmobject: Mobject,
        n_segments: int = 10,
        time_width: float = 0.1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.n_segments, self.time_width = n_segments, time_width
        widths = np.linspace(0, vmobject.get_stroke_width(), n_segments)
        time_widths = np.linspace(time_width, 0, n_segments)
        super().__init__(
            *(
                ShowPassingFlash(
                    vmobject.copy().set_stroke(width=w), time_width=tw, **kwargs
                )
                for w, tw in zip(widths, time_widths, strict=True)
            )
        )


class Circumscribe(Succession):
    """Draw attention to a mobject with a frame drawn around it.

    The frame, a rectangle or a circle `buff` away from the mobject, flashes around it
    ([`ShowPassingFlash`][manimgx.ShowPassingFlash]); with `fade_in` it fades in and is
    then undrawn, with `fade_out` it is drawn and then fades out, and with both it fades
    in and out. It is gone when the animation finishes. `run_time` times the frame (1
    second by default); the other options apply to the whole.

    Args:
        mobject: The mobject to frame.
        shape: The frame's kind: [`Rectangle`][manimgx.Rectangle] (None, the default) or
            [`Circle`][manimgx.Circle]; any other raises a ValueError.
        fade_in: Whether the frame fades in.
        fade_out: Whether the frame fades out.
        time_width: The flashing stretch's length, as a fraction of the frame's, when it
            neither fades in nor out.
        buff: The gap between the mobject and the frame, in scene units.
        color: The frame's color.
        stroke_width: The frame's width, in hundredths of a scene unit.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions]:
            `run_time` for the frame, the others for the whole.

    Examples:
        ```python
        import manimgx as m


        class CircumscribeExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Circumscribe", font_size=96)
                self.add(text)
                self.play(m.Circumscribe(text))
                self.play(m.Circumscribe(text, m.Circle, fade_out=True))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        shape: type[VMobject] | None = None,
        fade_in: bool = False,
        fade_out: bool = False,
        time_width: float = 0.3,
        buff: float = SMALL_BUFF,
        color: ParsableManimColor = PURE_YELLOW,
        stroke_width: float = DEFAULT_STROKE_WIDTH,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        from manimgx.mobjects.annotations import SurroundingRectangle
        from manimgx.mobjects.shapes import Circle, Rectangle

        shape = shape or Rectangle
        if shape is Rectangle:
            frame = SurroundingRectangle(
                mobject, color=color, buff=buff, stroke_width=stroke_width
            )
        elif shape is Circle:
            frame = Circle(color=color, stroke_width=stroke_width).surround(
                mobject, buffer_factor=1
            )
            frame.scale((frame.width / 2 + buff) / (frame.width / 2))
        else:
            raise ValueError("shape should be either Rectangle or Circle.")
        run_time = kwargs.pop("run_time", 1.0)
        half = run_time / 2
        if fade_in and fade_out:
            anims = [FadeIn(frame, run_time=half), FadeOut(frame, run_time=half)]
        elif fade_in:
            frame.reverse_direction()
            anims = [FadeIn(frame, run_time=half), Uncreate(frame, run_time=half)]
        elif fade_out:
            anims = [Create(frame, run_time=half), FadeOut(frame, run_time=half)]
        else:
            anims = [ShowPassingFlash(frame, time_width, run_time=run_time)]
        super().__init__(*anims, **kwargs)


class Blink(Succession):
    """Blink a mobject: hide it and show it again, a number of times.

    It shows for `time_on` seconds and hides for `time_off`, `blinks` times, then shows
    again for `time_on` (or stays hidden, with `hide_at_end`). It is made fully opaque
    to show it, and fully transparent to hide it.

    Args:
        mobject: The mobject to blink.
        time_on: How long it shows each time, in seconds.
        time_off: How long it hides each time, in seconds.
        blinks: How many times it blinks.
        hide_at_end: Whether it stays hidden at the end.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions] for
            the whole.

    Examples:
        ```python
        import manimgx as m


        class BlinkExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Blinking", font_size=120)
                self.add(text)
                self.play(m.Blink(text, blinks=3))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        time_on: float = 0.5,
        time_off: float = 0.5,
        blinks: int = 1,
        hide_at_end: bool = False,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        def show(opacity: float, run_time: float) -> UpdateFromFunc:
            return UpdateFromFunc(
                mobject,
                update_function=lambda m: m.set_opacity(opacity),
                run_time=run_time,
            )

        anims = [show(1.0, time_on), show(0.0, time_off)] * blinks
        super().__init__(
            *anims, *([] if hide_at_end else [show(1.0, time_on)]), **kwargs
        )


class Broadcast(LaggedStart):
    """Send copies of a mobject spreading out from a point, one after another.

    Each of `n_mobs` copies starts at `focal_point`, `initial_width` wide and at
    `initial_opacity`, and grows like a ripple to the mobject's size, centered on
    `focal_point`, as its opacity goes to `final_opacity`. They begin one after another
    (`lag_ratio` 0.2, over 3 seconds), and leave the scene when the animation finishes,
    unless given `remover=False`. The copies of a filled mobject fade as a whole, those
    of an outline in their stroke. The mobject itself is not shown.

    Args:
        mobject: The ripples' shape, at its largest.
        focal_point: Where the ripples spread from.
        n_mobs: How many copies.
        initial_opacity: The copies' opacity at the start.
        final_opacity: The copies' opacity at the end.
        initial_width: The copies' width at the start, in scene units.
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions]:
            `remover` for each copy, the others for the whole.

    Examples:
        ```python
        import manimgx as m


        class BroadcastExample(m.Scene):
            def construct(self) -> None:
                self.add(m.Dot(radius=0.2, color=m.TEAL))
                self.play(m.Broadcast(m.Circle(radius=3.5, color=m.TEAL)))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"lag_ratio": 0.2, "run_time": 3.0}

    def __init__(
        self,
        mobject: Mobject,
        focal_point: Point3DLike = ORIGIN,
        n_mobs: int = 5,
        initial_opacity: float = 1,
        final_opacity: float = 0,
        initial_width: float = 0.0,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        remover = kwargs.pop("remover", True)
        self.focal_point, self.n_mobs = focal_point, n_mobs
        filled = bool(mobject.fill_opacity)
        opacity = (
            (lambda m, o: m.set_opacity(o))
            if filled
            else (lambda m, o: m.set_stroke(opacity=o))
        )
        anims = []
        for _ in range(n_mobs):
            mob = mobject.copy()
            opacity(mob, final_opacity)
            mob.move_to(focal_point).save_state()
            mob.set(width=initial_width)
            opacity(mob, initial_opacity)
            anims.append(Restore(mob, remover=remover))
        super().__init__(*anims, **kwargs)

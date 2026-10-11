"""Transforms: keyframe evaluation, recorded method calls, and concurrent leaf composition.

A Transform moves geometry and paint between states; Animate derives those states
from recorded calls. The play's compositor combines transforms sharing a leaf."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Never, Protocol, Self, Unpack, cast, overload
from warnings import deprecated

import numpy as np

from manimgx.animation import clock
from manimgx.animation.timeline import (
    Animation,
    AnimationOptions,
    Key,
    _AnimationOptions,
    _updating,
    keyframe_at,
)
from manimgx.constants import ORIGIN, OUT, PI
from manimgx.drawing.geometry import (
    Blend,
    Floats,
    Path,
    Step,
    carried,
    path_along_arc,
    path_along_circles,
)
from manimgx.mobject import Group, Mobject, VMobject, _animate_plays
from manimgx.typing import (
    PathFunc,
    Point3D,
    Point3DLike,
    Point3DLike_Array,
    Vector3DLike,
)

if TYPE_CHECKING:
    from fractions import Fraction

    from manimgx.constants import DEFAULT_MOBJECT_TO_MOBJECT_BUFFER, RIGHT
    from manimgx.mobject import Beside
    from manimgx.mobjects.numbers import DecimalNumber
    from manimgx.scene import Scene

if TYPE_CHECKING:
    from manimgx.animation.updaters import AnimatedBoundary
    from manimgx.mobject import (
        ComplexValueTracker,
        Mobject1D,
        PMobject,
        ValueTracker,
        VDict,
        VectorizedPoint,
    )
    from manimgx.mobjects.annotations import Brace, BraceLabel
    from manimgx.mobjects.graph import GenericGraph
    from manimgx.mobjects.grid import Matrix, Table
    from manimgx.mobjects.images import ImageMobject, ImageMobjectFromCamera
    from manimgx.mobjects.plotting import (
        Axes,
        BarChart,
        ComplexPlane,
        NumberLine,
        PolarPlane,
        SampleSpace,
        _Plane,
    )
    from manimgx.mobjects.shapes import (
        Arc,
        Arrow,
        Circle,
        Line,
        Polygram,
        TipableVMobject,
    )
    from manimgx.mobjects.text import BulletedList, MathTex, Typst
    from manimgx.mobjects.three_d import (
        Cylinder,
        Line3D,
        Polyhedron,
        Surface,
        _DirectedSurface,
    )
    from manimgx.mobjects.vector_field import StreamLines, VectorField

    class _Of[T](Protocol):
        """A proxy of a T (covariant: `_Of[Circle]` is an `_Of[VMobject]`)."""

        @property
        def mobject(self) -> T: ...

    class _Method[
        S1: Mobject,
        **P1,
        S2: Mobject = Never,
        **P2 = ...,
        S3: Mobject = Never,
        **P3 = ...,
        S4: Mobject = Never,
        **P4 = ...,
    ]:
        """A mobject method as a proxy records it: for mobjects of kind S (the method's own
        class), the method's parameters P, returning the proxy — per kind, first match.
        """

        @overload
        def __get__(self, proxy: None, owner: type) -> Self: ...
        @overload
        def __get__[R](self, proxy: R, owner: type[_Of[S1]]) -> Callable[P1, R]: ...
        @overload
        def __get__[R](self, proxy: R, owner: type[_Of[S2]]) -> Callable[P2, R]: ...
        @overload
        def __get__[R](self, proxy: R, owner: type[_Of[S3]]) -> Callable[P3, R]: ...
        @overload
        def __get__[R](self, proxy: R, owner: type[_Of[S4]]) -> Callable[P4, R]: ...
        def __get__(self, proxy: object, owner: type) -> object:
            raise NotImplementedError  # typing only

    def _on[K](kind: type[K], /) -> K:
        """A K, for its bound methods: their parameters without `self`, returning K."""
        raise NotImplementedError  # typing only

    @overload
    def recorded[A: Mobject, **PA](m1: Callable[PA, A], /) -> _Method[A, PA]: ...

    @overload
    def recorded[A: Mobject, **PA, B: Mobject, **PB](
        m1: Callable[PA, A], m2: Callable[PB, B], /
    ) -> _Method[A, PA, B, PB]: ...

    @overload
    def recorded[A: Mobject, **PA, B: Mobject, **PB, C: Mobject, **PC](
        m1: Callable[PA, A], m2: Callable[PB, B], m3: Callable[PC, C], /
    ) -> _Method[A, PA, B, PB, C, PC]: ...

    @overload
    def recorded[
        A: Mobject,
        **PA,
        B: Mobject,
        **PB,
        C: Mobject,
        **PC,
        D: Mobject,
        **PD,
    ](
        m1: Callable[PA, A],
        m2: Callable[PB, B],
        m3: Callable[PC, C],
        m4: Callable[PD, D],
        /,
    ) -> _Method[A, PA, B, PB, C, PC, D, PD]: ...

    def recorded(*methods: object) -> object:
        """A method a proxy records, from each kind's bound method (its kind is what it returns)."""
        raise NotImplementedError  # typing only


__all__ = ["Animate", "Transform"]


class TransformOptions(_AnimationOptions, total=False, closed=True):
    """The options a transform takes, by keyword: the animation options and its path."""

    path_func: PathFunc | None
    """How each point travels from its start to its end: a function of the start points,
    the end points and the progress (see [paths][manimgx.Path]); it replaces
    `path_arc` and `path_arc_centers` (default None: a straight path)."""
    path_arc: float
    """The angle each point turns through on its way, in radians: 0 is a straight path,
    and a positive angle turns counterclockwise about `path_arc_axis` (default 0)."""
    path_arc_axis: Vector3DLike
    """The axis the arcs of `path_arc` turn about (default [`OUT`][manimgx.OUT]: in the
    plane of the screen)."""
    path_arc_centers: Point3DLike | Point3DLike_Array | None
    """A point the mobject turns about by `path_arc` on its way, or one for each of its
    points (default None: each point turns about the center of its own arc)."""
    replace_mobject_with_target_in_scene: bool
    """Whether the target takes the mobject's place in the scene when the animation
    finishes, as with [`ReplacementTransform`][manimgx.ReplacementTransform]
    (default False)."""


class Transform[M: Mobject = Mobject](Animation[M]):
    """Transform a mobject into the shape and style of another.

    The mobject stays in the scene and ends looking like `target_mobject`, which is not
    added (with [`ReplacementTransform`][manimgx.ReplacementTransform], the target takes
    the mobject's place). Their parts are matched up one to one (the side with fewer
    parts gains some, and so do the points of each pair), so the mobject may end with
    more parts than it had. Each point travels from its start to its end in a straight
    line, or along an arc with `path_arc`.

    Transforms that begin together on one mobject compose: `square.animate.shift(RIGHT)`
    and `Rotate(square)` played together move the square and turn it. One that begins
    later takes the mobject over from where the others have brought it. A target that
    has updaters and is not in the scene moves while the animation plays (the animation
    runs its updaters), and the mobject follows it.

    Args:
        mobject: The mobject to transform.
        target_mobject: The mobject it turns into; None creates an empty target when
            `keys` is omitted. Passing only `keys` leaves `target_mobject` as None.
        path_func: How each point travels from its start to its end: a function of the
            start points, the end points and the progress (see
            [paths][manimgx.Path]); it replaces `path_arc` and `path_arc_centers`.
            None: a straight path.
        path_arc: The angle each point turns through on its way, in radians: 0 is a
            straight path, and a positive angle turns counterclockwise.
        path_arc_axis: The axis the arcs of `path_arc` turn about.
        path_arc_centers: A point the mobject turns about by `path_arc` on its way, or
            one for each of its points; None: each point turns about the center of its
            own arc.
        replace_mobject_with_target_in_scene: Whether an independent target takes
            the mobject's place when the animation finishes. Presets without
            such a target retain their usual removal or restoration behavior.
        keys: Two or more states to pass through, in order: None for the mobject as the
            animation starts, a function of it, or a mobject, copied when the animation
            starts. Without them, the states are the mobject and `target_mobject`.

    Examples:
        ```python
        import manimgx as m


        class TransformExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                circle = m.Circle(radius=1.5, color=m.YELLOW, fill_opacity=0.5)
                square.shift(3 * m.LEFT)
                circle.shift(3 * m.RIGHT)
                self.add(square)
                self.play(m.Transform(square, circle, path_arc=m.PI / 2, run_time=2))
        ```
    """

    # each leaf moves between its keyframes along `path_func`: from the object to a target
    # of its own, or between states a preset derives (`keys`)
    _moving: bool | None = None  # `moving_target`, once decided

    def __init__(
        self,
        mobject: M | None,
        target_mobject: Mobject | None = None,
        path_func: PathFunc | None = None,
        path_arc: float = 0,
        path_arc_axis: Vector3DLike = OUT,
        path_arc_centers: Point3DLike | Point3DLike_Array | None = None,
        replace_mobject_with_target_in_scene: bool = False,
        *,
        keys: Sequence[Key] | None = None,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.path_arc_axis, self.path_arc_centers = path_arc_axis, path_arc_centers
        self.path_arc = path_arc
        if path_func is not None:
            self._path_func = path_func
        elif path_arc_centers is not None:
            self._path_func = path_along_circles(
                path_arc, path_arc_centers, path_arc_axis
            )
        self.replace_mobject_with_target_in_scene = replace_mobject_with_target_in_scene
        self.target_mobject = target_mobject
        if keys is None:
            if self.target_mobject is None:
                self.target_mobject = Mobject()
            keys = (None, self.target_mobject)
        self.keys: Sequence[Key] = keys
        self.shared: set[int] = set()  # its leaves other tweens drive too (`compose`)
        super().__init__(mobject, **kwargs)

    @property
    def path_arc(self) -> float:
        """The angle each point turns through on its way, in radians.

        Setting it makes the path an arc of that angle about `path_arc_axis`.
        """
        return self._path_arc

    @path_arc.setter
    def path_arc(self, value: float) -> None:
        self._path_arc = value
        self._path_func = path_along_arc(arc_angle=value, axis=self.path_arc_axis)

    @property
    def path_func(self) -> PathFunc:
        """How each point travels from its start to its end.

        A function of the start points, the end points and the progress; setting None
        keeps the current one.
        """
        return self._path_func

    @path_func.setter
    def path_func(self, value: PathFunc | None) -> None:
        if value is not None:
            self._path_func = value

    def begin(self) -> None:
        # the base begin (the keyframes and the object; a tween acts only when
        # interpolated), whether the target moves decided afresh: a target that moves runs
        # from now, its updaters live from when the animation begins to run them
        self._moving = None
        super().begin()
        if self.moving_target():
            cast("Mobject", self.keys[-1])._stamp(clock.now)

    def take(self) -> None:
        # take the object; in a play, join the tweens driving its leaves
        super().take()
        self.__dict__.pop("motion", None)
        self.shared = set()
        if (compositor := self._compositor()) is not None:
            compositor.join(self)

    def finish(self) -> None:
        super().finish()
        if (compositor := self._compositor()) is not None:
            compositor.finished.add(id(self))

    def _compositor(self) -> Compositor | None:
        return None if self._scene is None else self._scene.compositor

    @functools.cached_property
    @deprecated("ManimGX's machinery: the play calls it", category=None)
    def motion(self) -> tuple[tuple[Step, ...], Floats] | None:
        """The motion that carries the mobject from its first keyframe to its last, or
        None.

        For transforms that compose: its steps (turns about points of the mobject as it
        began, and moves; a straight path's is the move of its center) and the whole
        motion undone. None when the path is not a motion.
        """
        path, frames = self.path_func, self.frames
        if not (isinstance(path, Path) and path.kind == "motion" and len(frames) == 2):
            return None
        moved = frames[1].get_center() - frames[0].get_center()
        steps = path.steps or ((moved,) if np.any(moved) else ())
        return steps, np.linalg.inv(carried((step, 1.0) for step in steps))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def moving_target(self) -> bool:
        """Whether the target moves while the animation plays.

        It does when it is a mobject of its own with updaters that the scene does not
        run: the animation runs them (`advance`), and the keyframes follow it. Decided
        once, when first asked.
        """
        # decided once: not a walk of the scene per animation, nor of the target per
        # frame
        if self._moving is None:
            target = self.keys[-1]
            self._moving = (
                isinstance(target, Mobject)
                and _updating(target)
                and (
                    self._scene is None
                    or not any(
                        target is m for m in self._scene.get_mobject_family_members()
                    )
                )
            )
        return self._moving

    def advance(self, t: Fraction) -> None:
        # the object's updaters, brought to scene time `t` on its model, a moving target's
        # too; then the keyframes follow
        moving = self.moving_target()
        if self.model is None and not moving:
            return
        if self.model is not None:
            self.model.advance(t)
        if moving:
            cast("Mobject", self.keys[-1]).advance(t)
        self.rederive()

    def rederive(self) -> None:
        # the keyframes again (from the model, if the object updates; own objects copied
        # afresh), aligned with the object
        model = self.model
        self.frames = [
            (
                key.copy()
                if isinstance(key, Mobject)
                else (
                    frame
                    if model is None
                    else model.copy()
                    if key is None
                    else key(model.copy())
                )
            )
            for key, frame in zip(self.keys, self.frames, strict=True)
        ]
        for _ in range(2):
            for frame in self.frames:
                self.mobject.align_data(frame)

    def interpolate_keyframes(
        self, submobject: Mobject, keys: Sequence[Mobject], alpha: float
    ) -> None:
        i, t = keyframe_at(len(keys) - 1, alpha)  # past its ends, it runs on
        a, b = keys[i], keys[i + 1]
        shared = self.shared and id(submobject) in self.shared
        compositor = self._compositor() if shared else None
        if compositor is None or not compositor.write(submobject, self, a, b, t):
            submobject.interpolate(a, b, t, self.path_func)

    def clean_up_from_scene(self, scene: Scene) -> None:
        super().clean_up_from_scene(scene)
        if (
            self.replace_mobject_with_target_in_scene
            and self.target_mobject is not None
        ):
            scene.replace(self.mobject, self.target_mobject)


class _Call:
    """A method call, with mobject arguments captured when it is written."""

    __slots__ = ("args", "function", "kwargs")

    def __init__(
        self,
        function: Callable[..., object],
        args: tuple[object, ...],
        kwargs: dict[str, object],
        own: set[int],
    ) -> None:
        def written(value: object) -> object:
            return (
                value.copy()
                if isinstance(value, Mobject) and id(value) not in own
                else value
            )

        self.function = function
        self.args = tuple(written(value) for value in args)
        self.kwargs = {key: written(value) for key, value in kwargs.items()}

    def __call__(self, target: Mobject) -> Mobject:
        self.function(target, *self.args, **self.kwargs)
        return target


_EYE = np.eye(3)


_ZERO = np.zeros(3)


_BRUSHES = ("fill", "stroke", "background")


_FIELDS = (  # every paint field a tween changes but the sheen's direction
    "fill",
    "stroke",
    "background",
    "stroke_width",
    "background_width",
    "sheen_factor",
    "trim",
    "pace",
    "dash",
)


class Compositor:
    """A play's leaves, and the tweens driving each (`Scene.play` makes one per play)."""

    def __init__(self) -> None:
        self.leaves: dict[int, _Leaf] = {}
        self.finished: set[int] = set()  # the tweens that have finished

    def join(self, tween: Transform) -> None:
        """`tween` begins: it joins the tweens on a leaf they have not moved since they began (the leaf
        is then shared), and takes over any other leaf."""
        for leaf in tween.mobject.family_members_with_points():
            entry = self.leaves.get(id(leaf))
            if entry is not None and entry.found(leaf):
                entry.parts.append(_Part(tween))
                for part in entry.parts:
                    part.tween.shared.add(id(leaf))
                continue
            for part in entry.parts if entry is not None else ():
                if id(part.tween) not in self.finished:
                    part.tween.shared.add(id(leaf))
            self.leaves[id(leaf)] = _Leaf(leaf, tween)

    def write(
        self, leaf: Mobject, tween: Transform, a: Mobject, b: Mobject, t: float
    ) -> bool:
        """Write a shared `leaf` as `tween` has it — between keyframes a and b, at t — with
        the other tweens driving it. False: the tween writes it itself."""
        entry = self.leaves[id(leaf)]
        part = next((p for p in entry.parts if p.tween is tween), None)
        if part is None:  # the leaf was taken over from it
            return True
        part.keys, part.t = (a, b), t
        return entry.compose()


class _Part:
    def __init__(self, tween: Transform) -> None:
        self.tween = tween
        self.keys: tuple[Mobject, Mobject] | None = None  # once it has written
        self.t = 0.0


class _Leaf:
    """A leaf as its tweens found it when they began, and those tweens."""

    def __init__(self, leaf: Mobject, tween: Transform) -> None:
        self.leaf, self.geometry, self.paint = leaf, leaf._geometry, leaf.paint
        self.parts = [_Part(tween)]

    def found(self, leaf: Mobject) -> bool:
        """Is the leaf as its tweens found it (none of them has moved it)?"""
        return leaf._geometry is self.geometry and leaf.paint is self.paint

    def compose(self) -> bool:
        parts = [(p.tween, p.keys, p.t) for p in self.parts if p.keys is not None]
        n = self.geometry.n
        if any(k._geometry.n != n for _, keys, _ in parts for k in keys):
            return False
        steps: list[tuple[Step, float]] = []
        body, paint = self.geometry, self.paint
        changed: dict[str, object] = {}
        for tween, (a, b), t in parts:
            if tween.motion is None:  # not a motion: the leaf as the tween has it
                path = tween.path_func
                rest = (
                    Blend.mix(a._geometry, b._geometry, path.coefficients(t))
                    if isinstance(path, Path)
                    else Blend.of(path(a.points, b.points, t))
                )
            else:  # its chord in the frame its motion carries
                own, undo = tween.motion
                steps += [(step, t) for step in own]
                coefficients = ((1 - t) * _EYE, t * undo[:3, :3], t * undo[:3, 3])
                rest = Blend.mix(a._geometry, b._geometry, coefficients)
            body = Blend.mix(body, rest, (_EYE, _EYE, _ZERO))
            body = Blend.mix(body, self.geometry, (_EYE, -_EYE, _ZERO))
            mixed = paint.mixed(a.paint, b.paint, t)
            for name in _FIELDS:
                if (value := getattr(mixed, name)) is getattr(paint, name):
                    continue
                if name in _BRUSHES and name in changed:
                    value = _channels(changed[name], value, getattr(paint, name))
                changed[name] = value
        motion = carried(steps)
        changed["sheen_direction"] = motion[:3, :3] @ paint.sheen_direction
        self.leaf._geometry = body.transformed(motion[:3])
        self.leaf.paint = paint.but(**changed)
        return True


def _channels(before: object, value: np.ndarray, own: np.ndarray) -> np.ndarray:
    """A brush that two tweens change: its colors the last changer's, and its opacities (a
    brush of other rows: the last changer's whole)."""
    if not (
        isinstance(before, np.ndarray) and before.shape == value.shape == own.shape
    ):
        return value
    out = np.array(before)
    if not np.array_equal(value[:, :3], own[:, :3]):
        out[:, :3] = value[:, :3]
    if not np.array_equal(value[:, 3], own[:, 3]):
        out[:, 3] = value[:, 3]
    return out


class _Methods:
    """Every `-> Self` method of the library, by the class that defines it (see the module doc)."""

    if TYPE_CHECKING:
        # Mobject
        add = recorded(_on(VDict).add, _on(Group).add, _on(Mobject).add)
        add_background_rectangle = recorded(_on(Mobject).add_background_rectangle)
        add_n_more_submobjects = recorded(_on(Mobject).add_n_more_submobjects)
        add_to_back = recorded(_on(Mobject).add_to_back)
        add_updater = recorded(_on(Mobject).add_updater)
        align_data = recorded(_on(Mobject).align_data)
        align_on_border = recorded(_on(Mobject).align_on_border)
        align_points = recorded(_on(Mobject).align_points)
        align_points_with_larger = recorded(_on(Mobject).align_points_with_larger)
        align_submobjects = recorded(_on(Mobject).align_submobjects)
        align_to = recorded(_on(Mobject).align_to)
        apply_complex_function = recorded(_on(Mobject).apply_complex_function)
        apply_function = recorded(_on(Mobject).apply_function)
        apply_function_to_position = recorded(_on(Mobject).apply_function_to_position)
        apply_function_to_submobject_positions = recorded(
            _on(Mobject).apply_function_to_submobject_positions
        )
        apply_matrix = recorded(_on(Mobject).apply_matrix)
        apply_points_function_about_point = recorded(
            _on(Mobject).apply_points_function_about_point
        )
        arrange = recorded(_on(Mobject).arrange)
        arrange_in_grid = recorded(_on(Mobject).arrange_in_grid)

        @deprecated("arrange_submobjects is arrange: use it", category=None)
        def arrange_submobjects(
            self,
            direction: Vector3DLike = RIGHT,
            buff: float = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
            center: bool = True,
            **kwargs: Unpack[Beside],
        ) -> Self: ...

        become = recorded(_on(Mobject).become)
        center = recorded(_on(Mobject).center)
        clear_updaters = recorded(_on(Mobject).clear_updaters)
        fade = recorded(_on(Mobject).fade)
        fade_to = recorded(_on(Mobject).fade_to)
        flip = recorded(_on(Mobject).flip)
        generate_points = recorded(_on(Mobject).generate_points)
        generate_target = recorded(_on(Mobject).generate_target)
        init_colors = recorded(_on(Mobject).init_colors)
        init_points = recorded(_on(Mobject).init_points)
        insert = recorded(_on(Mobject).insert)
        interpolate_color = recorded(_on(Mobject).interpolate_color)
        invert = recorded(_on(Mobject).invert)
        match_color = recorded(_on(Mobject).match_color)
        match_coord = recorded(_on(Mobject).match_coord)
        match_depth = recorded(_on(Mobject).match_depth)
        match_dim_size = recorded(_on(Mobject).match_dim_size)
        match_height = recorded(_on(Mobject).match_height)
        match_points = recorded(_on(Mobject).match_points)
        match_style = recorded(_on(Mobject).match_style)
        match_updaters = recorded(_on(Mobject).match_updaters)
        match_width = recorded(_on(Mobject).match_width)
        match_x = recorded(_on(Mobject).match_x)
        match_y = recorded(_on(Mobject).match_y)
        match_z = recorded(_on(Mobject).match_z)
        move_to = recorded(_on(Mobject).move_to)
        next_to = recorded(_on(Mobject).next_to)
        null_point_align = recorded(_on(Mobject).null_point_align)
        pointwise_become_partial = recorded(_on(Mobject).pointwise_become_partial)
        push_self_into_submobjects = recorded(_on(Mobject).push_self_into_submobjects)
        put_start_and_end_on = recorded(_on(Mobject).put_start_and_end_on)
        remove = recorded(_on(VDict).remove, _on(Mobject).remove)
        remove_updater = recorded(_on(Mobject).remove_updater)
        replace = recorded(_on(Mobject).replace)
        rescale_to_fit = recorded(_on(Mobject).rescale_to_fit)
        reset_points = recorded(_on(Mobject).reset_points)
        restore = recorded(_on(Mobject).restore)
        resume_updating = recorded(_on(Mobject).resume_updating)
        reverse_points = recorded(_on(Mobject).reverse_points)
        rotate = recorded(_on(Mobject).rotate)

        @deprecated(
            "rotate_about_origin(angle, axis) is rotate(angle, axis, about_point=ORIGIN)",
            category=None,
        )
        def rotate_about_origin(
            self, angle: float, axis: Vector3DLike = OUT
        ) -> Self: ...

        save_state = recorded(_on(Mobject).save_state)
        scale = recorded(_on(Arrow).scale, _on(Typst).scale, _on(Mobject).scale)
        scale_to_fit_height = recorded(_on(Mobject).scale_to_fit_height)
        scale_to_fit_width = recorded(_on(Mobject).scale_to_fit_width)
        set = recorded(_on(Mobject).set)
        set_color = recorded(_on(ImageMobject).set_color, _on(Mobject).set_color)
        set_color_by_gradient = recorded(_on(Mobject).set_color_by_gradient)
        set_colors_by_radial_gradient = recorded(
            _on(Mobject).set_colors_by_radial_gradient
        )
        set_coord = recorded(_on(Mobject).set_coord)
        set_fill = recorded(_on(Mobject).set_fill)
        set_material = recorded(_on(Mobject).set_material)
        set_opacity = recorded(_on(ImageMobject).set_opacity, _on(Mobject).set_opacity)
        set_points = recorded(_on(Mobject).set_points)
        set_sheen = recorded(_on(Mobject).set_sheen)
        set_sheen_direction = recorded(_on(Mobject).set_sheen_direction)
        set_stroke = recorded(_on(Mobject).set_stroke)
        set_style = recorded(_on(Mobject).set_style)
        set_submobject_colors_by_gradient = recorded(
            _on(Mobject).set_submobject_colors_by_gradient
        )
        set_submobject_colors_by_radial_gradient = recorded(
            _on(Mobject).set_submobject_colors_by_radial_gradient
        )
        set_x = recorded(_on(Mobject).set_x)
        set_y = recorded(_on(Mobject).set_y)
        set_z = recorded(_on(Mobject).set_z)
        set_z_index = recorded(_on(Mobject).set_z_index)
        shift = recorded(_on(Mobject).shift)
        shift_onto_screen = recorded(_on(Mobject).shift_onto_screen)
        shuffle = recorded(_on(Mobject).shuffle)
        sort = recorded(_on(Mobject).sort)
        sort_submobjects = recorded(_on(Mobject).sort_submobjects)
        space_out_submobjects = recorded(_on(Mobject).space_out_submobjects)
        stretch = recorded(_on(Mobject).stretch)
        stretch_about_point = recorded(_on(Mobject).stretch_about_point)
        stretch_to_fit_height = recorded(_on(Mobject).stretch_to_fit_height)
        stretch_to_fit_width = recorded(_on(Mobject).stretch_to_fit_width)
        surround = recorded(_on(Circle).surround)
        suspend_updating = recorded(_on(Mobject).suspend_updating)
        to_corner = recorded(_on(Mobject).to_corner)
        to_edge = recorded(_on(Mobject).to_edge)
        to_original_color = recorded(_on(Mobject).to_original_color)
        update = recorded(_on(Mobject).update)
        # VMobject
        add_cubic_bezier_curve = recorded(_on(VMobject).add_cubic_bezier_curve)
        add_cubic_bezier_curve_to = recorded(_on(VMobject).add_cubic_bezier_curve_to)
        add_cubic_bezier_curves = recorded(_on(VMobject).add_cubic_bezier_curves)
        add_line_to = recorded(_on(VMobject).add_line_to)
        add_points_as_corners = recorded(_on(VMobject).add_points_as_corners)
        add_quadratic_bezier_curve_to = recorded(
            _on(VMobject).add_quadratic_bezier_curve_to
        )
        add_smooth_curve_to = recorded(_on(VMobject).add_smooth_curve_to)
        add_subpath = recorded(_on(VMobject).add_subpath)
        append_points = recorded(_on(VMobject).append_points)
        append_vectorized_mobject = recorded(_on(VMobject).append_vectorized_mobject)
        change_anchor_mode = recorded(_on(VMobject).change_anchor_mode)
        clear_points = recorded(_on(VMobject).clear_points)
        close_path = recorded(_on(VMobject).close_path)
        force_direction = recorded(_on(VMobject).force_direction)
        get_subcurve = recorded(_on(VMobject).get_subcurve)
        insert_n_curves = recorded(_on(VMobject).insert_n_curves)
        make_jagged = recorded(_on(VMobject).make_jagged)
        make_smooth = recorded(_on(VMobject).make_smooth)
        reverse_direction = recorded(_on(VMobject).reverse_direction)
        scale_handle_to_anchor_distances = recorded(
            _on(VMobject).scale_handle_to_anchor_distances
        )
        set_anchors_and_handles = recorded(_on(VMobject).set_anchors_and_handles)
        set_cap_style = recorded(_on(VMobject).set_cap_style)
        set_points_as_corners = recorded(_on(VMobject).set_points_as_corners)
        set_points_smoothly = recorded(_on(VMobject).set_points_smoothly)
        set_shade_in_3d = recorded(_on(VMobject).set_shade_in_3d)
        start_new_path = recorded(_on(VMobject).start_new_path)
        # the kinds' own
        add_background_to_entries = recorded(_on(Table).add_background_to_entries)
        add_bases = recorded(_on(Cylinder).add_bases)
        add_coordinates = recorded(
            _on(PolarPlane).add_coordinates,
            _on(ComplexPlane).add_coordinates,
            _on(Axes).add_coordinates,
        )
        add_display_frame = recorded(_on(ImageMobjectFromCamera).add_display_frame)
        add_highlighted_cell = recorded(_on(Table).add_highlighted_cell)
        add_key_value_pair = recorded(_on(VDict).add_key_value_pair)
        add_labels = recorded(_on(NumberLine).add_labels)
        add_line = recorded(_on(Mobject1D).add_line)
        add_numbers = recorded(_on(NumberLine).add_numbers)
        add_points = recorded(_on(PMobject).add_points)
        add_ticks = recorded(_on(NumberLine).add_ticks)
        add_tip = recorded(_on(TipableVMobject).add_tip)
        assign_tip_attr = recorded(_on(TipableVMobject).assign_tip_attr)
        change_bar_values = recorded(_on(BarChart).change_bar_values)
        change_label = recorded(_on(BraceLabel).change_label)
        change_layout = recorded(_on(GenericGraph).change_layout)
        divide_vertically = recorded(_on(SampleSpace).divide_vertically)
        fade_all_but = recorded(_on(BulletedList).fade_all_but)
        fit_to_coordinate_system = recorded(_on(VectorField).fit_to_coordinate_system)
        full_family_become_partial = recorded(
            _on(AnimatedBoundary).full_family_become_partial
        )
        increment_value = recorded(
            _on(ValueTracker[complex]).increment_value,
            _on(ValueTracker).increment_value,
            _on(DecimalNumber).increment_value,
            _on(DecimalNumber[complex]).increment_value,
        )
        match_colors = recorded(_on(PMobject).match_colors)
        move_arc_center_to = recorded(_on(Arc).move_arc_center_to)
        nudge = recorded(_on(VectorField).nudge)
        nudge_submobjects = recorded(_on(VectorField).nudge_submobjects)
        prepare_for_nonlinear_transform = recorded(
            _on(_Plane).prepare_for_nonlinear_transform
        )
        put_at_tip = recorded(_on(Brace).put_at_tip)
        reset_endpoints_based_on_tip = recorded(
            _on(TipableVMobject).reset_endpoints_based_on_tip
        )
        reset_normal_vector = recorded(_on(Arrow).reset_normal_vector)
        rotate_about_number = recorded(_on(NumberLine).rotate_about_number)
        rotate_about_zero = recorded(_on(NumberLine).rotate_about_zero)
        round_corners = recorded(_on(Polygram).round_corners)
        set_angle = recorded(_on(Line).set_angle)
        set_color_by_tex = recorded(_on(MathTex).set_color_by_tex)
        set_color_by_tex_to_color_map = recorded(
            _on(MathTex).set_color_by_tex_to_color_map
        )
        set_column_colors = recorded(
            _on(Matrix).set_column_colors, _on(Table).set_column_colors
        )
        set_direction = recorded(_on(_DirectedSurface).set_direction)
        set_fill_by_checkerboard = recorded(_on(Surface).set_fill_by_checkerboard)
        set_fill_by_value = recorded(_on(Surface).set_fill_by_value)
        set_length = recorded(_on(Line).set_length)
        set_location = recorded(_on(VectorizedPoint).set_location)
        set_path_arc = recorded(_on(Line).set_path_arc)
        set_points_by_ends = recorded(_on(Line).set_points_by_ends)
        set_resampling_algorithm = recorded(_on(ImageMobject).set_resampling_algorithm)
        set_row_colors = recorded(_on(Matrix).set_row_colors, _on(Table).set_row_colors)
        set_start_and_end_attrs = recorded(_on(Line3D).set_start_and_end_attrs)
        set_value = recorded(
            _on(ComplexValueTracker).set_value,
            _on(ValueTracker).set_value,
            _on(DecimalNumber).set_value,
            _on(DecimalNumber[complex]).set_value,
        )
        start_animation = recorded(_on(StreamLines).start_animation)
        start_submobject_movement = recorded(_on(VectorField).start_submobject_movement)
        stop_submobject_movement = recorded(_on(VectorField).stop_submobject_movement)
        thin_out = recorded(_on(PMobject).thin_out)
        update_edges = recorded(_on(GenericGraph).update_edges)
        update_faces = recorded(_on(Polyhedron).update_faces)


class Animate[M: Mobject](Transform[M], _Methods):
    """An animation of a mobject's method calls.

    It is what [`mobject.animate`][manimgx.Mobject.animate] returns. Call methods on it
    as on the mobject, `square.animate.shift(RIGHT).scale(2)`, and play it: it is the
    animation. Each call is recorded and tried at once on a copy, so a wrong call fails
    where it is written, and the calls are carried out on the mobject as it is when the
    animation begins (in a [`Succession`][manimgx.Succession], after the parts before
    it). When it finishes, the mobject is exactly what the calls make of it.

    The mobject moves as the calls do: a turn among them (`rotate`, `flip`) turns it
    rigidly, through its whole angle (`rotate(TAU)` is a full turn), about its pivot as
    the motion carries it; any other call moves its
    center in a straight line; and the rest of the change (a scale, a color, a new
    shape) happens along the way. A `path_arc` or `path_func` of its own replaces that
    motion.

    Called before any method, it takes the animation's
    [options][manimgx.animation.transform.TransformOptions]:
    `square.animate(run_time=2, rate_func=linear).shift(RIGHT)`. It also takes an edit,
    a function applied to the mobject as a method would be:
    `square.animate(lambda mob: mob.shift(RIGHT))`.

    Args:
        mobject: The mobject whose method calls are animated.

    Examples:
        ```python
        import manimgx as m


        class AnimateExample(m.Scene):
            def construct(self) -> None:
                bar = m.Rectangle(width=3, height=1, color=m.BLUE, fill_opacity=0.5)
                self.add(bar.shift(4 * m.LEFT))
                self.play(
                    bar.animate(run_time=2)
                    .shift(8 * m.RIGHT)
                    .rotate(m.PI / 2)
                    .set_color(m.YELLOW)
                )
        ```
    """

    def __init__(self, mobject: M) -> None:
        self._target = mobject.generate_target()
        self._override: Animation | None = None
        self._chaining = False
        self._anim_args: TransformOptions = {}
        self.methods: list[_Call] = []
        super().__init__(mobject, self._target)
        self._chosen: PathFunc | None = self._path_func
        self.keys = (None, self._replay)

    def __call__(
        self,
        function: Callable[[M], object] | None = None,
        /,
        **anim_args: Unpack[TransformOptions],
    ) -> Self:
        """Set the animation's options, before any method is recorded; and record a
        function of the mobject, as a method's call is recorded.

        A function can make any change, with methods of your own class too, and a type
        checker checks it against the mobject's class: `box.animate(lambda b: b.grow(2))`.
        (`box.animate.grow(2)` works as well, but through `animate` a type checker knows
        only ManimGX's methods.)

        Args:
            function: A function that changes the mobject: tried at once on a copy, so a
                wrong call fails where it is written, and carried out as recorded methods
                are. None for none.
            **anim_args: [Transform options][manimgx.animation.transform.TransformOptions].

        Returns:
            This animation, for chaining.
        """
        if self._chaining and anim_args:
            raise ValueError(
                "Animation arguments must be passed before accessing methods and can"
                " only be passed once"
            )
        if (
            anim_args
        ):  # the animation, constructed with them (an override gets them too)
            self._anim_args = anim_args
            super().__init__(self.mobject, self.mobject.target, **anim_args)
            self._chosen = (
                None
                if any(
                    k in anim_args
                    for k in ("path_func", "path_arc", "path_arc_centers")
                )
                else self._path_func
            )
            self.keys = (None, self._replay)
        if function is not None:
            if self._override is not None:
                raise NotImplementedError(
                    "Method chaining is currently not supported for overridden animations"
                )
            self._record(function, (), {})
            self._chaining = True
        return self

    def _record(
        self,
        function: Callable[..., object],
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> None:
        """Record a call of `function` on the mobject, tried at once on the target: a
        wrong call fails where it is written."""
        function(self._target, *args, **kwargs)
        own = {id(m) for mob in (self.mobject, self._target) for m in mob.get_family()}
        self.methods.append(_Call(function, args, kwargs, own))

    def _recorder(self, name: str) -> Callable[..., Animation]:
        """The mobject's method `name`, which records its calls."""
        if name.startswith("_") or "_target" not in self.__dict__:
            raise AttributeError(name)
        method = getattr(self._target, name)
        override = (
            _animate_plays.get(method.__func__) if inspect.ismethod(method) else None
        )
        if (self._chaining and override is not None) or self._override is not None:
            raise NotImplementedError(
                "Method chaining is currently not supported for overridden animations"
            )

        def record(*args: object, **kwargs: object) -> Animation:
            if override is not None:
                animation: Animation = override(
                    self.mobject, *args, anim_args=self._anim_args, **kwargs
                )
                self._override = animation
                return animation
            self._record(method.__func__, args, kwargs)
            return self

        self._chaining = True
        return record

    if (
        not TYPE_CHECKING
    ):  # a type checker knows the methods by the table, and no others
        __getattr__ = _recorder

    def _replay(self, target: Mobject) -> Mobject:
        """The recorded calls, carried out on (a copy of) the object as it is when the animation
        begins, on their arguments as written."""
        turns = [_turn(item) for item in self.methods]
        if self._path_func is not self._chosen or not any(turns):
            for item in self.methods:
                item(target)
            return target
        steps: list[Step] = []
        for item, turn in zip(self.methods, turns, strict=True):
            if turn is not None:
                angle, axis, pivot = turn
                # its pivot as a point of the object as it began: where the steps so far took it
                whole = carried((step, 1.0) for step in steps)
                point = np.linalg.solve(whole, np.append(pivot(target), 1.0))[:3]
                steps.append((angle, axis, point))
                item(target)
                continue
            before = target.get_center()
            item(target)
            moved = target.get_center() - before
            if np.any(moved):
                steps.append(moved)
        self._path_func = self._chosen = Path(steps=tuple(steps))
        return target

    def finish(self) -> None:
        for item in self.methods:
            item(self.mobject)
        super().finish()

    def build(self) -> Animation:
        return self if self._override is None else self._override


def _turn(
    item: _Call,
) -> tuple[float, Floats, Callable[[Mobject], Floats]] | None:
    """(angle, axis, pivot) of a recorded call that turns the object (`rotate`, `flip`,
    `rotate_about_origin`), the pivot as the call finds it; None for any other call."""
    func = item.function
    name = getattr(func, "__name__", "")
    if name not in ("rotate", "flip", "rotate_about_origin"):
        return None
    try:
        bound = inspect.signature(func).bind(None, *item.args, **item.kwargs)
        bound.apply_defaults()
        given = bound.arguments
        angle = PI if name == "flip" else float(cast("float", given["angle"]))
        axis = np.asarray(given["axis"], dtype=np.float64)
    except (TypeError, KeyError, ValueError):
        return None
    point = ORIGIN if name == "rotate_about_origin" else given.get("about_point")
    edge = given.get("about_edge")

    def pivot(mob: Mobject) -> Floats:
        if point is not None:
            return np.asarray(point, dtype=np.float64)
        return mob.get_critical_point(ORIGIN if edge is None else cast("Point3D", edge))

    return angle, axis, pivot


class Always[M: Mobject](_Methods):
    """A mobject's method calls, each made again at every frame.

    It is what [`mobject.always`][manimgx.Mobject.always] returns. Each call, as
    `label.always.next_to(dot, UP)`, is made at once and then at every frame, as an
    updater of the mobject; calls chain. Their arguments are taken as they are written:
    pass mobjects (`dot`), which the call reads anew at every frame, not values computed
    from them (`dot.get_center()`), which stay as they were.

    Args:
        mobject: The mobject whose method calls become updaters.
    """

    def __init__(self, mobject: M) -> None:
        self._mobject = mobject

    @property
    def mobject(self) -> M:  # (typing: the proxy of a mobject of this kind)
        """The mobject whose method calls become updaters."""
        return self._mobject

    def _updater(self, name: str) -> Callable[..., Self]:
        """The mobject's method `name`, whose calls become its updaters."""
        if name.startswith("_"):
            raise AttributeError(name)

        def add_updater(*args: object, **kwargs: object) -> Self:
            self._mobject.add_updater(
                lambda m: getattr(m, name)(*args, **kwargs), call_updater=True
            )
            return self

        return add_updater

    if (
        not TYPE_CHECKING
    ):  # a type checker knows the methods by the table, and no others
        __getattr__ = _updater

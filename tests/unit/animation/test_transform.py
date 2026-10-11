"""Recorded methods keep their arguments as written and start when played; tweens that begin
together on one mobject compose; a replacement leaves its target in its mobject's place.

- `.animate` and `ApplyMethod` take their arguments as written, and carry the calls out on the
  mobject as it is when the animation begins. A function given to `.animate` is a call too:
  tried at once, and carried out with them.
- An animation's `keys` (functions of the mobject) are applied when it begins, to a copy.
- A mobject's override (`override_animation`) plays in place of the animation it overrides,
  the animation given in a list or a generator too.
- Moves compose: shifts and turns, and a scaling about the mobject's center, played together
  end where applying them one after another puts it, whatever their order. (Changes of shape
  add: two scalings played together add their changes, as two morphs do; a scaling is not a
  step of a motion, as a turn is.)
- Paint composes channel by channel: a fade and a recolor played together both happen, the
  same in either order.
- Played, a transform made to replace its mobject (`replace_mobject_with_target_in_scene`, as
  a scene gives it) leaves the scene holding its target where the mobject was; one with no
  target of its own leaves the mobject (a remover, nothing): never an object of its own making.
- `.animate` and `.always` are typed by a table of the library's methods (`_Methods`), not by
  their `__getattr__`, which a type checker doesn't see: every public method of a mobject
  class that returns the mobject is in it, typed with the class's own parameters.
"""

import ast
import importlib
import inspect
import pkgutil
import textwrap
from collections.abc import Callable, Iterator
from functools import cache
from pathlib import Path
from typing import Self

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.scenes import Recorder, assert_same_frames, record, scene
from tests.strategies import vectors

import manimgx as m
from manimgx.animation import easing as rf
from manimgx.animation.transform import TransformOptions
from manimgx.drawing.paint import mix_rgba


@pytest.mark.parametrize("form", ["animate", "positional", "keyword"])
def test_recorded_calls_snapshot_arguments_but_replay_on_the_current_mobject(
    form: str,
) -> None:
    square = m.Square()
    destination = m.Dot(2 * m.RIGHT + m.UP)
    wanted = destination.get_center().copy()
    animation: m.Animation
    if form == "animate":
        animation = square.animate.move_to(destination)
    elif form == "positional":
        animation = m.ApplyMethod(square.move_to, destination)
    else:
        animation = m.ApplyMethod(square.move_to, {"point_or_mobject": destination})
    destination.shift(3 * m.UP)
    square.shift(2 * m.LEFT)
    start = square.get_center().copy()

    animation.begin()
    animation.interpolate(0)
    np.testing.assert_allclose(square.get_center(), start, atol=1e-12)
    animation.finish()
    np.testing.assert_allclose(square.get_center(), wanted, atol=1e-12)


def test_a_function_given_to_animate_is_a_call() -> None:
    # any change, with a method of the scene's own class too
    class Box(m.Square):
        def grow(self) -> Self:
            return self.scale(2)

    box = Box()
    animation = box.animate(lambda b: b.grow().shift(m.RIGHT), run_time=2)
    assert animation.run_time == 2
    box.shift(m.UP)
    animation.begin()
    animation.finish()
    assert box.width == pytest.approx(4)
    np.testing.assert_allclose(box.get_center(), m.UP + m.RIGHT, atol=1e-12)
    with pytest.raises(AttributeError):  # tried at once: it fails where it is written
        m.Square().animate(lambda s: s.shfit(m.RIGHT))  # ty: ignore[unresolved-attribute]


def test_keys_are_applied_as_the_animation_begins_to_a_copy() -> None:
    square = m.Square()
    copies: list[m.Mobject] = []

    def moved(copy: m.Mobject) -> m.Mobject:
        copies.append(copy)
        return copy.shift(2 * m.RIGHT)

    animation = m.Transform(square, keys=(None, moved), rate_func=rf.linear)
    assert copies == []
    animation.begin()
    assert len(copies) == 1
    assert copies[0] is not square
    animation.interpolate(0.5)
    np.testing.assert_allclose(square.get_center(), m.RIGHT)
    animation.finish()
    np.testing.assert_allclose(square.get_center(), 2 * m.RIGHT)


def test_an_override_plays_in_place_of_its_animation_given_in_iterables() -> None:
    class Waiting(m.Square):
        @m.override_animation(m.FadeIn)
        def _fade_in(self) -> m.Animation:
            return m.Wait(0.25)

    def given() -> Iterator[m.Animation]:
        yield m.FadeIn(Waiting())

    group = m.AnimationGroup(given(), [m.FadeIn(Waiting())], m.FadeIn(m.Square()))
    kinds = [type(part) for part in group.animations]
    assert kinds == [m.Wait, m.Wait, m.FadeIn]


moves = st.lists(
    st.one_of(
        st.tuples(st.just("shift"), vectors(bound=3).map(lambda v: v * [1, 1, 0])),
        st.tuples(st.just("rotate"), st.floats(-3, 3)),
        st.tuples(st.just("scale"), st.floats(0.3, 3)),
    ),
    min_size=1,
    max_size=3,
).filter(lambda calls: sum(name == "scale" for name, _ in calls) <= 1)


def played(calls: list[tuple[str, object]], reverse: bool) -> np.ndarray:
    def tell(s: Recorder) -> None:
        square = m.Square(1.5).shift(0.3 * m.LEFT)
        s.stage = [square]
        s.add(square)
        anims = [getattr(square.animate, name)(arg) for name, arg in calls]
        s.play(*(anims[::-1] if reverse else anims))

    return record(tell).stage[0].points


@given(calls=moves, reverse=st.booleans())
def test_moves_played_together_end_as_applied_in_turn(
    calls: list[tuple[str, object]], reverse: bool
) -> None:
    square = m.Square(1.5).shift(0.3 * m.LEFT)
    for name, arg in calls:
        getattr(square, name)(arg)
    np.testing.assert_allclose(played(calls, reverse), square.points, atol=1e-9)


def faded_and_recolored(recolor_first: bool) -> Recorder:
    def tell(s: Recorder) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=1)
        s.stage = [square]
        anims = [m.FadeIn(square), square.animate.set_color(m.RED)]
        s.play(*(anims[::-1] if recolor_first else anims), rate_func=rf.linear)

    return record(tell)


def test_a_fade_and_a_recolor_both_happen_in_either_order() -> None:
    first, other = faded_and_recolored(False), faded_and_recolored(True)
    assert_same_frames(first.frames, other.frames)
    halfway = first.frames[5][0]
    fill = np.frombuffer(halfway.brushes[0], dtype=float).reshape(-1, 4)
    color = mix_rgba(m.ManimColor(m.BLUE).to_rgba(), m.ManimColor(m.RED).to_rgba(), 0.5)
    np.testing.assert_allclose(fill[0, :3], color[:3], atol=1e-9)
    assert fill[0, 3] == pytest.approx(0.5)


REPLACE: TransformOptions = {"replace_mobject_with_target_in_scene": True}
# each: a transform of a square made to replace it (given the circle it may turn into)
REPLACING: dict[str, Callable[[m.Square, m.Circle], m.Transform]] = {
    "Transform": lambda sq, c: m.Transform(sq, c, **REPLACE),
    "ReplacementTransform": lambda sq, c: m.ReplacementTransform(sq, c),
    "Transform through keys": lambda sq, c: m.Transform(
        sq, c, keys=(None, lambda copy: copy.shift(m.RIGHT)), **REPLACE
    ),
    ".animate": lambda sq, c: sq.animate(**REPLACE).shift(m.RIGHT),
    "Rotate": lambda sq, c: m.Rotate(sq, 1.0, **REPLACE),
    "FadeIn": lambda sq, c: m.FadeIn(sq, **REPLACE),
    "FadeOut": lambda sq, c: m.FadeOut(sq, **REPLACE),
    "Indicate": lambda sq, c: m.Indicate(sq, **REPLACE),
    "GrowFromPoint": lambda sq, c: m.GrowFromPoint(sq, m.LEFT, **REPLACE),
    "ApplyMethod": lambda sq, c: m.ApplyMethod(sq.shift, m.RIGHT, **REPLACE),
    "ApplyFunction": lambda sq, c: m.ApplyFunction(
        lambda copy: copy.shift(m.RIGHT), sq, **REPLACE
    ),
    "MoveAlongPath": lambda sq, c: m.MoveAlongPath(
        sq, m.Line(m.LEFT, m.RIGHT), **REPLACE
    ),
    # not transforms: they have no target, and leave the square where it is
    "Create": lambda sq, c: m.Create(sq),
    "DrawBorderThenFill": lambda sq, c: m.DrawBorderThenFill(sq),
    "CyclicReplace": lambda sq, c: m.CyclicReplace(sq, **REPLACE),
}


@pytest.mark.parametrize("name", sorted(REPLACING))
def test_a_replacement_leaves_its_target_in_its_mobjects_place(name: str) -> None:
    square, circle = m.Square(), m.Circle().shift(m.RIGHT)
    before, after = m.Dot(m.UP), m.Dot(m.DOWN)
    animation = REPLACING[name](square, circle)
    target = animation.target_mobject  # its own, if it has one

    def construct(s: m.Scene) -> None:
        s.add(before, square, after)
        s.play(animation)

    told = scene(construct)
    told.render()
    if target is not None:
        middle = [target]
    else:
        middle = [] if animation.is_remover() else [square]
    assert [id(x) for x in told.mobjects] == [id(x) for x in (before, *middle, after)]


class _Unquoted(ast.NodeTransformer):
    """An annotation as its type reads, written in quotes or not."""

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, str):
            return self.visit(ast.parse(node.value, mode="eval").body)
        return node


def _text(node: ast.expr | None) -> str:
    return "" if node is None else ast.unparse(_Unquoted().visit(node))


def _parameters(args: ast.arguments) -> tuple[tuple[str, str, bool], ...]:
    """A method's parameters but `self`: each one's name, type, and whether it has a default."""
    every = [*args.posonlyargs, *args.args]
    defaults = [False] * (len(every) - len(args.defaults)) + [True] * len(args.defaults)
    found = [
        (a.arg, _text(a.annotation), d) for a, d in zip(every, defaults, strict=True)
    ]
    found += [(f"*{a.arg}", _text(a.annotation), False) for a in [args.vararg] if a]
    found += [
        (a.arg, _text(a.annotation), d is not None)
        for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True)
    ]
    found += [(f"**{a.arg}", _text(a.annotation), False) for a in [args.kwarg] if a]
    return tuple(found[1:])


@cache
def _defined(cls: type) -> dict[str, ast.FunctionDef]:
    """The methods a class's own body defines, by name (an overloaded one's implementation)."""
    body = ast.parse(textwrap.dedent(inspect.getsource(cls))).body[0]
    assert isinstance(body, ast.ClassDef)
    return {
        node.name: node
        for node in body.body
        if isinstance(node, ast.FunctionDef)
        and not any(ast.unparse(d) == "overload" for d in node.decorator_list)
    }


def _table() -> dict[str, list[str]]:
    """The names `.animate` types, each with the kinds of mobject it is typed for, in the
    order a type checker tries them (empty: a method typed by hand)."""
    source = Path(inspect.getfile(m.Animate)).read_text(encoding="utf-8")
    methods = next(
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef) and node.name == "_Methods"
    )
    table: dict[str, list[str]] = {}
    for node in ast.walk(methods):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            name = node.targets[0]
            assert isinstance(name, ast.Name)
            table[name.id] = [
                ast.unparse(arg.value.args[0]).split("[")[0]
                for arg in node.value.args
                if isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Call)
            ]
        elif isinstance(node, ast.FunctionDef):
            table[node.name] = []
    return table


def _mobject_classes() -> dict[str, type[m.Mobject]]:
    """Every mobject class the package defines, by name: its private bases too."""
    found: dict[str, type[m.Mobject]] = {}
    for module in pkgutil.walk_packages(m.__path__, "manimgx."):
        if module.name.endswith("__main__"):  # the command line, run when imported
            continue
        for value in vars(importlib.import_module(module.name)).values():
            if (
                isinstance(value, type)
                and issubclass(value, m.Mobject)
                and value.__module__ == module.name
            ):
                assert found.setdefault(value.__name__, value) is value
    return found


def test_animate_types_every_method_that_returns_the_mobject() -> None:
    table, classes = _table(), _mobject_classes()
    shadowed = set(dir(m.Animate))  # the animation's own attributes come first
    # a copy is another mobject: through `.animate`, there is nothing to record, and ty says so
    unchanging = {"copy"}

    def parameters(cls: type, name: str) -> tuple[tuple[str, str, bool], ...]:
        owner = next(c for c in cls.__mro__ if name in _defined(c))
        return _parameters(_defined(owner)[name].args)

    problems = []
    for cls in classes.values():
        for name, method in _defined(cls).items():
            decorators = [ast.unparse(d) for d in method.decorator_list]
            if (
                name.startswith("_")
                or _text(method.returns) != "Self"
                or any(d.startswith("deprecated") for d in decorators)
                or {"classmethod", "staticmethod"} & set(decorators)  # makes another
                or name in shadowed | unchanging
            ):
                continue
            if name not in table:
                problems.append(f"{cls.__name__}.{name}: not in the table")
                continue
            kinds = [classes[kind] for kind in table[name]]
            if not kinds:  # typed by hand
                continue
            first = next((kind for kind in kinds if issubclass(cls, kind)), None)
            if first is None:
                problems.append(
                    f"{cls.__name__}.{name}: none of the table's kinds is it"
                )
            elif parameters(first, name) != parameters(cls, name):
                problems.append(
                    f"{cls.__name__}.{name}: typed with {first.__name__}'s parameters"
                )
    assert not problems, "\n".join(problems)

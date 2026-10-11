"""A mobject is a tree of parts with points, a paint and updaters.

- Its family is a tree: whatever is added, removed, inserted or assigned, and however, no mobject
  holds itself (not even through another), and the family lists each member once, in preorder,
  where it last occurs. Adding anything else is an error.
- A transform is the same transform of its points: shifts, scales, turns, stretches and
  matrices, about the points their docstrings name (its box's center or edge by default), in
  any order, leave the family's points where plain arithmetic puts them.
- Its box is what it draws: for every public class, the tight box of its family's curves (by
  their derivatives' roots) and points; width, height, corners, center and coordinates all read
  that box, and a member spans the same in whatever group holds it.
- Layout does what it says: `next_to` leaves `buff` between the two, `arrange` spaces its parts
  by `buff` and centers them, `arrange_in_grid` puts each part in its cell where its row's,
  its column's or the grid's alignment says, `to_edge` puts the box `buff` in from the frame's
  edge, `replace` fits one box into another, `move_to` puts the named point there.
- Styles read back what they set, every paint attribute as the mobject's own (`family=False`
  paints the mobject alone); `fade` takes a fraction of every opacity.
- A replica is an independent, isomorphic copy that does not reach its original. `copy`,
  `generate_target`, `save_state`, the target of `.animate`, and a construction made again
  (which a class may take from what it made before: `prototype`) give, for every public class
  and for the states bugs were found in (updaters, trackers, flowing lines, generator inputs,
  shared cells, opaque keys, color maps), a mobject that looks the same; that holds the same
  graph of parts, aliases kept and plain values equal; that shares no mutable part with the
  original and reaches nothing of its family; and that changes as the original does when both
  are updated and their trackers nudged.
- Updaters keep one clock (a model runs beside a host and its part): a time-based updater is
  handed the time its clock ran since it was added, last ran or resumed (`advance`), or the
  `dt` given (`update`); a mobject's own run before its parts'; nothing in a suspended subtree
  runs; a removed updater runs no more, not even later in the pass that removed it, and
  nothing the mobject holds keeps its owner alive; a copy goes on as the original would have.
  The updaters change only through the mobject's methods: `get_updaters()` is a snapshot.
- Its inputs are values: changing what was passed in, afterwards, changes neither the mobject
  nor what it later makes of it, and making it changes no input; an input it does not show it
  does not keep, nor what an edit replaces; an iterator gives what the list of its items gives;
  an option kept for Manim's sake and ignored is ignored, and not kept. Its outputs are values:
  changing what a query returns changes nothing. Nothing it holds is one of ManimGX's writable
  constants.
- Defaults are partial application: after `C.set_default(**d)`, `C()` makes what `C(**d)` makes,
  each class's defaults over those of the classes it inherits from, as they are when `C()`
  runs; `C.set_default()` brings the class's own back. What ManimGX remembers is invisible: a
  construction made after any defaults and any other constructions, its memories warm, is what
  it is made from nothing, and mobjects made before keep their look.
- Its points are a value: assigned others, it takes them. A family grown for a transform
  (`add_n_more_submobjects`) follows each part with invisible copies of itself, spread as
  evenly as can be, the parts themselves kept.

A VMobject is a path: cubic curves, four control points each.

- It has one measure of length (nine straight pieces per curve), which its reveals, its
  proportions and its length all go by: `point_from_proportion` is by length (it used to go
  by each curve's parameter, 16% of the way at 0.5 on an uneven curve), `proportion_from_point`
  is its inverse, a reveal at a proportion has drawn exactly to that point, and the length is
  within the pieces' error of the true arc length, never over it.
- Built curve by curve, a path is the curves it was given: lines are straight curves with
  handles at the thirds, a quadratic is its cubic, a closed path ends where its last subpath
  starts, and subpaths split where a curve does not start at the one before it.
- Refining keeps the shape: `insert_n_curves` and `align_points` split curves into pieces of
  equal parameter, each exactly a part of the curve it came from.
- A part (`pointwise_become_partial`) is the path between its two proportions, by curves.
- An image under `apply_function`, of a path or of a group holding it, is within 1.5e-3 of the
  true image all along each curve (its tolerance, 1e-3, holds where it is checked, a third and
  two thirds along), not only at its control points (checked at the middle alone, a wave
  through a straight piece passed 0.6 off).
- Its orientation does not depend on where it is; reversed, it runs the other way.

A point cloud thins to every k-th point of each member, colors and all, and a point added later
takes the color it was made with. A cloud's part is every point its stretch reaches into, as a
reveal over the stretch shows.

A mesh's part is the triangles a reveal over its stretch shows, every one it reaches into, each
corner keeping its paint, and no other corner: its box is theirs. A surface's part is a surface:
its whole lattice, drawing the faces its stretch reaches into, its box theirs; its pieces share
its faces out. A lattice's triangles are derived from its grid, and replacing them with others is
an error.

A VDict that shows its keys labels each value with its key, however the value was added."""

import random
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import cast

import numpy as np
import pytest
import svgelements as se
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
)
from tests import oracles
from tests.oracles import assert_replica, look, reachable, reaches
from tests.strategies import (
    MOBJECTS,
    angles,
    arrays,
    curves,
    drawn,
    mobjects,
    paths,
    vectors,
)

import manimgx as m
from manimgx import caches
from manimgx.animation import clock
from manimgx.animation.easing import linear
from manimgx.drawing.geometry import bezier, partial_bezier_points
from manimgx.drawing.paint import Style
from manimgx.mobject import GridArrangement, ValueTracker, prototype
from manimgx.mobjects.shapes import LineOptions

DIRECTIONS = [m.RIGHT, m.LEFT, m.UP, m.DOWN, m.UR, m.UL, m.DR, m.DL]

resizable = drawn.filter(
    lambda mob: (
        not isinstance(mob, (m.Arrow, m.VectorizedPoint))
        and "Arrow" not in type(mob).__name__
    )
)


def path(points: np.ndarray) -> m.VMobject:
    mob = m.VMobject()
    mob.points = points
    return mob


def last_preorder(mob: m.Mobject) -> list[m.Mobject]:
    """A family by its definition: preorder, each member where it last occurs."""

    def preorder(x: m.Mobject) -> list[m.Mobject]:
        return [x, *(part for child in x.submobjects for part in preorder(child))]

    expanded = preorder(mob)
    last = {id(x): i for i, x in enumerate(expanded)}
    return [x for i, x in enumerate(expanded) if last[id(x)] == i]


class Family(RuleBasedStateMachine):
    """Every way a family changes keeps it a tree, listed in last-occurrence preorder."""

    mobs = Bundle("mobs")

    def __init__(self) -> None:
        super().__init__()
        self.made: list[m.Mobject] = []
        self.assigned: set[int] = (
            set()
        )  # given a list by hand, which may hold a part twice

    def keep(self, mob: m.Mobject) -> m.Mobject:
        self.made.append(mob)
        return mob

    @initialize(target=mobs)
    def root(self) -> m.Mobject:
        return self.keep(m.Mobject())

    @rule(target=mobs)
    def new(self) -> m.Mobject:
        return self.keep(m.Dot())

    @rule(target=mobs, original=mobs)
    def copy(self, original: m.Mobject) -> m.Mobject:
        copy = self.keep(original.copy())
        if id(original) in self.assigned:  # (its list, copied, holds a part twice too)
            self.assigned.add(id(copy))
        return copy

    def refused(self, parent: m.Mobject, children: list[m.Mobject]) -> bool:
        return any(
            parent is c or any(x is parent for x in c.get_family()) for c in children
        )

    @staticmethod
    def once(children: list[m.Mobject]) -> list[m.Mobject]:
        """Each child once, where it last occurs."""
        return [
            c
            for i, c in enumerate(children)
            if all(c is not d for d in children[i + 1 :])
        ]

    @rule(parent=mobs, children=st.lists(mobs, min_size=1, max_size=3))
    def add(self, parent: m.Mobject, children: list[m.Mobject]) -> None:
        if self.refused(parent, children):
            with pytest.raises(ValueError, match="cannot hold itself"):
                parent.add(*children)
        else:
            parent.add(*children)
            new = self.once(children)
            assert parent.submobjects[len(parent.submobjects) - len(new) :] == new

    @rule(parent=mobs, children=st.lists(mobs, min_size=1, max_size=3))
    def add_to_back(self, parent: m.Mobject, children: list[m.Mobject]) -> None:
        if self.refused(parent, children):
            with pytest.raises(ValueError, match="cannot hold itself"):
                parent.add_to_back(*children)
        else:
            parent.add_to_back(*children)
            new = self.once(children)
            assert parent.submobjects[: len(new)] == new

    @rule(parent=mobs, child=mobs, index=st.integers(-4, 4))
    def insert(self, parent: m.Mobject, child: m.Mobject, index: int) -> None:
        if self.refused(parent, [child]):
            with pytest.raises(ValueError, match="cannot hold itself"):
                parent.insert(index, child)
        else:
            others = [x for x in parent.submobjects if x is not child]
            parent.insert(index, child)
            others.insert(index, child)
            assert parent.submobjects == others

    @rule(parent=mobs, children=st.lists(mobs, max_size=3))
    def assign(self, parent: m.Mobject, children: list[m.Mobject]) -> None:
        if not self.refused(parent, children):
            parent.submobjects = list(children)
            self.assigned.add(id(parent))

    @rule(parent=mobs, child=mobs)
    def remove(self, parent: m.Mobject, child: m.Mobject) -> None:
        parent.remove(child)
        if (
            id(parent) not in self.assigned
        ):  # (a list given by hand loses one occurrence)
            assert all(x is not child for x in parent.submobjects)

    @invariant()
    def it_is_a_tree(self) -> None:
        for mob in self.made:
            ids = [id(x) for x in mob.submobjects]
            if id(mob) not in self.assigned:
                assert len(ids) == len(set(ids)), "a part held twice"
            stack: list[tuple[m.Mobject, frozenset[int]]] = [(mob, frozenset())]
            while stack:
                x, above = stack.pop()
                assert id(x) not in above, "a mobject holds itself"
                stack.extend((c, above | {id(x)}) for c in x.submobjects)
            assert mob.get_family() == last_preorder(mob)


TestFamily = Family.TestCase
TestFamily.settings = settings(stateful_step_count=25)


@pytest.mark.parametrize("value", [1, "a", None, np.zeros(3)])
def test_only_mobjects_join_a_family(value: object) -> None:
    for join in (
        lambda g: g.add(value),
        lambda g: g.add_to_back(value),
        lambda g: g.insert(0, value),
    ):
        with pytest.raises(TypeError):
            join(m.VGroup())


class Transforms(RuleBasedStateMachine):
    """A group of paths under any chain of transforms has the points plain arithmetic gives,
    about the pivots the docstrings name."""

    @initialize(parts=st.lists(curves(max_curves=3), min_size=1, max_size=3))
    def begin(self, parts: list[np.ndarray]) -> None:
        self.mob = m.VGroup(*(path(p) for p in parts))
        self.model = [p.copy() for p in parts]

    def pivot(self, direction: np.ndarray) -> np.ndarray:
        boxes = np.array([oracles.curve_box(p) for p in self.model])
        low, high = boxes[:, 0].min(axis=0), boxes[:, 1].max(axis=0)
        return np.where(
            direction < 0, low, np.where(direction > 0, high, (low + high) / 2)
        )

    def apply(self, linear: np.ndarray, about: np.ndarray) -> None:
        self.model = [(p - about) @ linear.T + about for p in self.model]

    @rule(vector=arrays(3, 10))
    def shift(self, vector: np.ndarray) -> None:
        self.mob.shift(vector)
        self.model = [p + vector for p in self.model]

    @rule(
        factor=st.floats(-3, 3).filter(lambda f: abs(f) > 1e-3),
        edge=st.sampled_from([m.ORIGIN, *DIRECTIONS]),
    )
    def scale(self, factor: float, edge: np.ndarray) -> None:
        about = self.pivot(edge)
        self.mob.scale(factor, about_edge=edge)
        self.apply(factor * np.eye(3), about)

    @rule(factors=arrays(3, 3).filter(lambda f: np.all(np.abs(f) > 1e-3)))
    def scale_each_axis(self, factors: np.ndarray) -> None:
        about = self.pivot(m.ORIGIN)
        self.mob.scale(factors)
        self.apply(np.diag(factors), about)

    @rule(angle=angles(), axis=vectors(), about=arrays(3, 10) | st.none())
    def rotate(self, angle: float, axis: np.ndarray, about: np.ndarray | None) -> None:
        pivot = self.pivot(m.ORIGIN) if about is None else about
        self.mob.rotate(angle, axis, about_point=about)
        self.apply(m.rotation_matrix(angle, axis), pivot)

    @rule(axis=vectors())
    def flip(self, axis: np.ndarray) -> None:
        about = self.pivot(m.ORIGIN)
        self.mob.flip(axis)
        self.apply(m.rotation_matrix(np.pi, axis), about)

    @rule(
        factor=st.floats(-3, 3).filter(lambda f: abs(f) > 1e-3), dim=st.integers(0, 2)
    )
    def stretch(self, factor: float, dim: int) -> None:
        about = self.pivot(m.ORIGIN)
        self.mob.stretch(factor, dim)
        linear = np.eye(3)
        linear[dim, dim] = factor
        self.apply(linear, about)

    @rule(matrix=arrays((3, 3), 2))
    def apply_matrix(self, matrix: np.ndarray) -> None:
        self.mob.apply_matrix(matrix)  # about the origin
        self.apply(matrix, np.zeros(3))

    @invariant()
    def its_points_are_the_arithmetic(self) -> None:
        for part, expected in zip(self.mob.submobjects, self.model, strict=True):
            scale = 1 + np.abs(expected).max()
            np.testing.assert_allclose(part.points, expected, atol=1e-9 * scale)

    @invariant()
    def its_box_is_what_it_draws(self) -> None:
        drawn = np.concatenate([oracles.sample(p, 50) for p in self.model])
        box = self.mob.boundary_box()
        assert box is not None
        low, high = box
        tolerance = 1e-9 * (1 + np.abs(drawn).max())
        assert np.all(drawn >= low - tolerance)
        assert np.all(drawn <= high + tolerance)
        np.testing.assert_allclose(
            [low, high],
            [self.pivot(-np.ones(3)), self.pivot(np.ones(3))],
            atol=tolerance,
        )


TestTransforms = Transforms.TestCase

TestTransforms.settings = settings(stateful_step_count=10)


class TestBox:
    @given(parts=st.lists(curves(max_curves=2), min_size=1, max_size=4))
    def test_a_groups_box_joins_its_members_boxes(
        self, parts: list[np.ndarray]
    ) -> None:
        group = m.VGroup(*(path(p) for p in parts))
        boxes = np.array([path(p).boundary_box() for p in parts])
        np.testing.assert_array_equal(
            group.boundary_box(), [boxes[:, 0].min(0), boxes[:, 1].max(0)]
        )

    @given(
        points=curves(), direction=st.sampled_from([m.ORIGIN, *DIRECTIONS, m.OUT, m.IN])
    )
    def test_its_critical_points_are_its_boxs(
        self, points: np.ndarray, direction: np.ndarray
    ) -> None:
        mob = path(points)
        low, high = oracles.curve_box(points)
        expected = np.where(
            direction < 0, low, np.where(direction > 0, high, (low + high) / 2)
        )
        np.testing.assert_allclose(
            mob.get_critical_point(direction),
            expected,
            atol=1e-9 * (1 + np.abs(points).max()),
        )

    @given(
        points=curves(),
        size=st.floats(0.1, 20),
        dim=st.sampled_from(["width", "height"]),
    )
    def test_setting_a_size_scales_to_it_about_the_center(
        self, points: np.ndarray, size: float, dim: str
    ) -> None:
        mob = path(points)
        assume(getattr(mob, dim) > 1e-3)
        center = mob.get_center()
        setattr(mob, dim, size)
        assert getattr(mob, dim) == pytest.approx(size, rel=1e-9)
        np.testing.assert_allclose(
            mob.get_center(), center, atol=1e-9 * (1 + np.abs(points).max() + size)
        )


PERPENDICULAR_EDGES = {  # an aligned edge across the direction a mobject is put in
    tuple(m.RIGHT): [m.ORIGIN, m.UP, m.DOWN],
    tuple(m.LEFT): [m.ORIGIN, m.UP, m.DOWN],
    tuple(m.UP): [m.ORIGIN, m.LEFT, m.RIGHT],
    tuple(m.DOWN): [m.ORIGIN, m.LEFT, m.RIGHT],
}


class TestLayout:
    @given(
        a=drawn,
        b=drawn,
        direction=st.sampled_from([m.RIGHT, m.LEFT, m.UP, m.DOWN]),
        buff=st.floats(0, 3),
        data=st.data(),
    )
    def test_next_to_leaves_buff_between_the_two(
        self,
        a: m.Mobject,
        b: m.Mobject,
        direction: np.ndarray,
        buff: float,
        data: st.DataObject,
    ) -> None:
        edge = data.draw(st.sampled_from(PERPENDICULAR_EDGES[tuple(direction)]))
        a.next_to(b, direction, buff=buff, aligned_edge=edge)
        k = 0 if direction[0] else 1
        gap = (
            a.get_critical_point(-direction)[k] - b.get_critical_point(direction)[k]
        ) * direction[k]
        assert gap == pytest.approx(buff, abs=1e-9)
        across = 1 - k
        assert a.get_critical_point(edge)[across] == pytest.approx(
            b.get_critical_point(edge)[across], abs=1e-9
        )

    @given(
        parts=st.lists(drawn, min_size=1, max_size=5),
        buff=st.floats(0, 1),
        direction=st.sampled_from([m.RIGHT, m.DOWN]),
    )
    def test_arrange_spaces_its_parts_by_buff_and_centers_them(
        self, parts: list[m.Mobject], buff: float, direction: np.ndarray
    ) -> None:
        group = m.Group(*parts).arrange(direction, buff=buff)
        k = 0 if direction[0] else 1
        for before, after in zip(group.submobjects, group.submobjects[1:]):
            gap = (
                after.get_critical_point(-direction)[k]
                - before.get_critical_point(direction)[k]
            ) * direction[k]
            assert gap == pytest.approx(buff, abs=1e-9)
        np.testing.assert_allclose(group.get_center(), 0, atol=1e-9)

    @given(mob=drawn, direction=st.sampled_from(DIRECTIONS), buff=st.floats(0, 1))
    def test_to_edge_puts_the_box_buff_in_from_the_frames_edge(
        self, mob: m.Mobject, direction: np.ndarray, buff: float
    ) -> None:
        mob.to_edge(direction, buff=buff)
        edges = np.array([m.config.frame_x_radius, m.config.frame_y_radius])
        for k in (0, 1):
            if direction[k]:
                reached = mob.get_critical_point(direction)[k] * direction[k]
                assert reached == pytest.approx(edges[k] - buff, abs=1e-9)

    @given(mob=resizable, target=resizable)
    def test_replace_fits_one_box_into_the_other(
        self, mob: m.Mobject, target: m.Mobject
    ) -> None:
        # (an arrow scales its shaft and keeps its tips: its box does not scale with it)
        assume(mob.width > 1e-3 and target.width > 1e-3)
        mob.replace(target)
        np.testing.assert_allclose(mob.get_center(), target.get_center(), atol=1e-9)
        assert mob.width == pytest.approx(target.width, rel=1e-9)

    @given(mob=drawn, point=arrays(3, 5), edge=st.sampled_from([m.ORIGIN, *DIRECTIONS]))
    def test_move_to_puts_the_named_point_there(
        self, mob: m.Mobject, point: np.ndarray, edge: np.ndarray
    ) -> None:
        mob.move_to(point, aligned_edge=edge)
        np.testing.assert_allclose(mob.get_critical_point(edge), point, atol=1e-9)

    @given(
        sizes=st.lists(
            st.tuples(st.floats(0.1, 2), st.floats(0.1, 2)), min_size=1, max_size=9
        ),
        cols=st.integers(1, 3),
        buff=st.floats(0, 1) | st.tuples(st.floats(0, 1), st.floats(0, 1)),
        cell=st.sampled_from([m.ORIGIN, *DIRECTIONS]),
        data=st.data(),
    )
    def test_arrange_in_grid_puts_each_part_in_its_cell(
        self,
        sizes: list[tuple[float, float]],
        cols: int,
        buff: float | tuple[float, float],
        cell: np.ndarray,
        data: st.DataObject,
    ) -> None:
        # rows top down and columns left to right, each as tall and as wide as its largest
        # part, `buff` apart; a part sits in its cell as its row's letter says vertically,
        # its column's horizontally, else as `cell_alignment` does
        rows = -(-len(sizes) // cols)
        row_letters = data.draw(
            st.none() | st.text("ucd", min_size=rows, max_size=rows)
        )
        col_letters = data.draw(
            st.none() | st.text("lcr", min_size=cols, max_size=cols)
        )
        parts = [m.Rectangle(width=w, height=h) for w, h in sizes]
        m.VGroup(*parts).arrange_in_grid(
            rows=rows,
            cols=cols,
            buff=buff,
            cell_alignment=cell,
            row_alignments=row_letters,
            col_alignments=col_letters,
        )
        bx, by = buff if isinstance(buff, tuple) else (buff, buff)
        widths = [max((w for w, _ in sizes[c::cols]), default=0.0) for c in range(cols)]
        heights = [
            max(h for _, h in sizes[r * cols : (r + 1) * cols]) for r in range(rows)
        ]
        offsets = []
        for i, part in enumerate(parts):
            r, c = divmod(i, cols)
            h = {"l": -1, "c": 0, "r": 1}[col_letters[c]] if col_letters else cell[0]
            v = {"u": 1, "c": 0, "d": -1}[row_letters[r]] if row_letters else cell[1]
            left = sum(widths[:c]) + c * bx
            top = -(sum(heights[:r]) + r * by)
            corner = [left + (h + 1) / 2 * widths[c], top - (1 - v) / 2 * heights[r], 0]
            offsets.append(part.get_critical_point([h, v, 0]) - corner)
        np.testing.assert_allclose(
            np.array(offsets), np.array([offsets[0]] * len(parts)), atol=1e-9
        )


PAINT_ATTRIBUTES: dict[
    str, object
] = {  # each paint attribute, with a value to set it to
    "joint_type": m.LineJointType.ROUND,
    "cap_style": m.CapStyleType.ROUND,
    "shade_in_3d": True,
    "sheen_factor": 0.5,
    "sheen_direction": np.array([0.5, -0.25, 0.125]),
    "background_stroke_width": 2.0,
    "fill_rgbas": np.array([[0.1, 0.2, 0.3, 0.4]]),
    "stroke_rgbas": np.array([[0.7, 0.6, 0.5, 0.8], [0.1, 0.2, 0.3, 1.0]]),
    "background_stroke_rgbas": np.array([[0.2, 0.3, 0.4, 1.0]]),
}


def own(mob: m.Mobject) -> tuple[object, ...]:
    """What a mobject shows of its own (its first row of `look`)."""
    return look(mob)[0]


class TestStyle:
    @given(
        mob=drawn,
        color=st.sampled_from([m.RED, m.BLUE, m.ManimColor("#123456")]),
        opacity=st.floats(0, 1),
    )
    def test_what_is_set_reads_back(
        self, mob: m.Mobject, color: m.ManimColor, opacity: float
    ) -> None:
        mob.set_fill(color, opacity).set_stroke(color, 3, opacity)
        for part in mob.get_family():
            assert part.get_fill_color().to_rgb().tolist() == color.to_rgb().tolist()
            assert part.get_fill_opacity() == opacity
            assert part.get_stroke_width() == 3

    @given(mob=drawn, name=st.sampled_from(sorted(PAINT_ATTRIBUTES)))
    def test_a_paint_attribute_reads_back_as_the_mobjects_own(
        self, mob: m.Mobject, name: str
    ) -> None:
        value = PAINT_ATTRIBUTES[name]
        others = [own(part) for part in mob.get_family()[1:]]
        setattr(mob, name, value)
        read = getattr(mob, name)
        if isinstance(value, np.ndarray):
            np.testing.assert_array_equal(read, value)
        else:
            assert read == value
        assert [own(part) for part in mob.get_family()[1:]] == others
        direction = mob.sheen_direction  # (a factor alone keeps the direction)
        mob.set_sheen(0.25, family=False)
        np.testing.assert_array_equal(mob.sheen_direction, direction)
        mob.set_sheen_direction(m.UP, family=False).set_fill(m.RED, 0.5, family=False)
        assert [own(part) for part in mob.get_family()[1:]] == others

    @given(
        mob=mobjects,
        darkness=st.floats(0, 1),
        opacities=st.lists(st.floats(0, 1), min_size=2, max_size=4),
    )
    def test_fade_takes_a_fraction_of_every_opacity(
        self, mob: m.Mobject, darkness: float, opacities: list[float]
    ) -> None:
        # (it set every row, a gradient's stops or a cloud's points, to the first one's)
        mob.set_fill([m.RED, m.BLUE, m.GREEN, m.GOLD][: len(opacities)], opacities)
        before = [
            (p.paint.fill[:, 3].copy(), p.paint.stroke[:, 3].copy())
            for p in mob.get_family()
        ]
        mob.fade(darkness)
        for part, (fill, stroke) in zip(mob.get_family(), before, strict=True):
            np.testing.assert_allclose(
                part.paint.fill[:, 3], fill * (1 - darkness), atol=1e-12
            )
            np.testing.assert_allclose(
                part.paint.stroke[:, 3], stroke * (1 - darkness), atol=1e-12
            )


def points_of(mob: m.Mobject) -> list[np.ndarray]:
    return [member.points for member in mob.get_family()]


def assert_points_close(a: m.Mobject, b: m.Mobject, scale: float = 1.0) -> None:
    pa, pb = points_of(a), points_of(b)
    assert [len(x) for x in pa] == [len(x) for x in pb]
    for x, y in zip(pa, pb, strict=True):
        np.testing.assert_allclose(x, y, atol=1e-9 * (scale + np.abs(y).max(initial=0)))


every = pytest.mark.parametrize("name", sorted(MOBJECTS))


def _arc_and_its_brace() -> m.Mobject:
    arc = m.Arc(radius=0.2, start_angle=0.3, angle=4.7)
    return m.VGroup(arc, m.ArcBrace(arc))


BOXES: dict[str, Callable[[], m.Mobject]] = {  # boxes no registry entry shows
    "rounded pentagon": lambda: m.RegularPolygon(5).round_corners(0.3),
    "arc and its brace": _arc_and_its_brace,
}


class TestEveryMobject:
    """The laws of the Mobject contract, for every public class (a subclass that overrides a
    method keeps them)."""

    @every
    def test_its_family_holds_it_once_first_and_its_points_are_finite(
        self, name: str
    ) -> None:
        mob = MOBJECTS[name]()
        family = mob.get_family()
        assert family[0] is mob
        assert sum(x is mob for x in family) == 1
        assert all(np.isfinite(points).all() for points in points_of(mob))

    @every
    def test_a_shift_moves_its_box_and_back_is_where_it_was(self, name: str) -> None:
        mob = MOBJECTS[name]()
        box, start = mob.boundary_box(), mob.copy()
        vector = np.array([1.25, -0.5, 0.75])
        mob.shift(vector)
        if box is not None:
            moved = mob.boundary_box()
            assert moved is not None
            np.testing.assert_allclose(moved, box + vector, atol=1e-9)
        assert_points_close(mob.shift(-vector), start)

    @every
    def test_a_turn_and_a_scale_undone_leave_it_where_it_was(self, name: str) -> None:
        mob = MOBJECTS[name]()
        start, about = mob.copy(), np.array([0.3, -0.2, 0.1])
        mob.rotate(0.7, m.OUT, about_point=about).rotate(-0.7, m.OUT, about_point=about)
        assert_points_close(mob, start)
        mob.scale(2, about_point=about).scale(0.5, about_point=about)
        assert_points_close(mob, start)

    @every
    def test_restore_undoes_whatever_came_between(self, name: str) -> None:
        mob = MOBJECTS[name]()
        mob.save_state()
        saved = oracles.look(mob)
        mob.shift(m.DL).rotate(1.1).scale(0.7).set_color(m.TEAL).set_opacity(0.4)
        assert oracles.look(mob.restore()) == saved

    @every
    def test_become_takes_what_another_shows(self, name: str) -> None:
        mob, other = MOBJECTS[name](), MOBJECTS[name]().shift(m.UP).set_color(m.GOLD)
        mob.become(other)
        assert oracles.look(mob) == oracles.look(other)

    @pytest.mark.parametrize("name", [*sorted(MOBJECTS), *sorted(BOXES)])
    def test_its_box_is_what_it_draws(self, name: str) -> None:
        mob = (MOBJECTS.get(name) or BOXES[name])().rotate(0.3, axis=[1.0, 2.0, 3.0])
        box, expected = mob.boundary_box(), oracles.drawn_box(mob)
        if expected is None:
            assert box is None
            return
        assert box is not None
        tolerance = 1e-9 * (1 + np.abs(expected).max())
        np.testing.assert_allclose(box, expected, atol=tolerance)
        if not isinstance(
            mob, m.VectorizedPoint
        ):  # (whose size is a number of its own)
            np.testing.assert_allclose(
                [mob.width, mob.height], (box[1] - box[0])[:2], atol=tolerance
            )
        np.testing.assert_allclose(
            mob.get_corner(m.UL)[:2], [box[0, 0], box[1, 1]], atol=tolerance
        )
        np.testing.assert_allclose([mob.get_x(), mob.get_y()], mob.get_center()[:2])
        for member in mob.submobjects:  # a member spans the same, grouped or not
            mine = member.boundary_box()
            if mine is None:
                continue
            assert np.all(mine[0] >= box[0] - tolerance)
            assert np.all(mine[1] <= box[1] + tolerance)
            drawn_by_member = oracles.drawn_box(member)
            assert drawn_by_member is not None
            np.testing.assert_allclose(mine, drawn_by_member, atol=tolerance)


# ── replicas ──────────────────────────────────────────────────────────────────────────────
class _Decimal(m.DecimalNumber):
    def _get_num_string(self, number: float | complex) -> str:
        return "v=" + super()._get_num_string(number)


class _Owner(m.Mobject):  # a mobject whose method is an updater of another
    def follow(self, mob: m.Mobject, dt: float) -> None:
        mob.shift(dt * m.RIGHT)


class _Kept(_Owner):  # a kept construction that updates itself
    @prototype
    def __init__(self) -> None:
        super().__init__()
        self.add(m.Dot())
        self.add_updater(self.follow)


class _Opaque:  # a key: an identity, never copied
    def __deepcopy__(self, memo: dict[int, object]) -> "_Opaque":
        raise AssertionError("a key is an identity, never copied")


_KEYS = (_Opaque(), _Opaque())
_SVG = Path(__file__).parents[1] / "integration/cases/svg_mobject_example/shapes.svg"


def _numbers() -> Iterator[float]:
    yield from (1.0, 2.0)


def _flowing() -> m.StreamLines:
    lines = m.StreamLines(
        lambda p: np.array([0.2, 0.3, 0.0]),
        x_range=[0, 0, 1],
        y_range=[0, 0, 1],
        noise_factor=0,
        virtual_time=0.2,
    )
    random.seed(1)
    lines.start_animation(warm_up=False, flow_speed=1.5)
    return lines


def _shared_cells() -> m.MobjectTable:
    s = m.Square(0.3)
    return m.MobjectTable(
        [[s, s], [m.Circle(0.2), s]],
        row_labels=[m.Dot(), m.Dot()],
        col_labels=[m.Dot(), m.Dot()],
        include_outer_lines=True,
        add_background_rectangles_to_entries=True,
    )


def _shared_entries() -> m.MobjectMatrix:
    s = m.Square(0.4)
    return m.MobjectMatrix([[s, s], [m.Circle(0.3), s]])


def _divided() -> m.SampleSpace:
    space = m.SampleSpace().divide_vertically(0.4)
    first = space.vertical_parts[0]
    assert isinstance(first, m.SampleSpace)
    first.divide_vertically(0.3)
    return space


def _tipped() -> m.Line:
    line = m.Line(m.ORIGIN, [1, 2, 3]).add_tip()
    line.create_tip(at_start=True)
    return line


def _with_history() -> m.Dot:
    dot = m.Dot(m.LEFT, color=m.RED).save_state()
    dot.shift(m.RIGHT).generate_target()
    return dot


def _aliased() -> m.VGroup:
    dot = m.Dot()
    group = m.VGroup(dot, m.Square())
    vars(group)["label"] = dot  # an attribute naming a member
    return group


def _updated() -> m.Mobject:
    owner = _Owner()
    host = m.Square().add_updater(owner.follow)
    host.add_updater(lambda mob: mob.set_opacity(0.5))
    host.advance(Fraction(1))
    return host


def _key_and_drawing() -> m.Graph:
    key = m.Dot()
    return m.Graph(
        [key, 1],
        [(key, 1)],
        layout={key: m.LEFT, 1: m.RIGHT},
        vertex_mobjects={key: key},
    )


class _Provider(m.Scene):
    def point(self, t: float) -> np.ndarray:
        return np.array([t, t * t, 0.0])


# every state a copy once went wrong in, made in one line or two
STATES: dict[str, Callable[[], m.Mobject]] = {
    "a group naming a member": _aliased,
    "a number line of generated numbers": lambda: m.NumberLine(
        (0, 3, 1), numbers_to_include=(x for x in (0, 2))
    ),
    "3D axes of generated numbers": lambda: m.ThreeDAxes(
        x_range=(0, 3, 1),
        y_range=(0, 3, 1),
        z_range=(0, 3, 1),
        axis_config={"numbers_to_include": _numbers(), "font_size": 18},
    ),
    "a curve with generated breaks": lambda: m.ParametricFunction(
        lambda t: np.array([t, t * t, 0.0]),
        t_range=(-2, 2, 0.25),
        discontinuities=(v for v in [-1.0, 0.5]),
        use_smoothing=False,
    ),
    "a curve of a scene's method": lambda: m.ParametricFunction(
        _Provider().point, t_range=(-2, 2, 0.25), use_smoothing=False
    ),
    "flowing stream lines": _flowing,
    "an arrow field": lambda: m.ArrowVectorField(
        lambda p: np.array([0.2, 0.3, 0.0]),
        colors=[m.RED, m.BLUE],
        x_range=[0, 0, 1],
        y_range=[0, 0, 1],
    ),
    "a table with shared cells": _shared_cells,
    "a matrix with shared entries": _shared_entries,
    "a divided sample space": _divided,
    "a plane": lambda: m.ComplexPlane(
        x_range=(-3, 3, 1), y_range=(-2, 2, 1), faded_line_ratio=2
    ),
    "3D axes in a gradient": lambda: m.ThreeDAxes(
        x_range=(-2, 2),
        y_range=(-2, 2),
        z_range=(-2, 2),
        axis_config={"stroke_color": (m.RED, m.BLUE)},
    ),
    "a graph with opaque keys": lambda: m.Graph(
        list(_KEYS), [_KEYS], layout={_KEYS[0]: m.LEFT, _KEYS[1]: m.RIGHT}
    ),
    "a graph whose key is its drawing": _key_and_drawing,
    "a labeled digraph": lambda: m.DiGraph(
        [0, 1, 2],
        [(0, 1), (1, 2), (2, 0)],
        layout={0: [-2, 0, 0], 1: [2, 0, 0], 2: [0, 2, 0]},
        labels={v: m.Square(0.1) for v in range(3)},
    ),
    "a VDict with an opaque key": lambda: m.VDict({_KEYS[0]: m.Dot()}),
    "a variable of a subclass": lambda: m.Variable(2, "x", var_type=_Decimal),
    "a variable's number alone": lambda: m.Variable(2, "x", var_type=m.Integer).value,
    "a number with unit, ellipsis and background": lambda: m.DecimalNumber(
        7.125, unit="m", include_background_rectangle=True, show_ellipsis=True
    ),
    "a formula with a color map": lambda: m.MathTex(
        "x", "+", "y", tex_to_color_map={"x": m.RED}
    ),
    "a formula colored by an array": lambda: m.MathTex(
        "x", tex_to_color_map={"x": np.array([1.0, 0.0, 0.0])}
    ),
    "a Tex": lambda: m.Tex("x", "+", "y"),
    "a ligature in a gradient": lambda: m.Text(
        "ffi", gradient=[m.RED, m.GREEN, m.BLUE]
    ),
    "a paragraph": lambda: m.Paragraph("", "office", "ffi", t2c={"f": m.RED}),
    "code in a window": lambda: m.Code(
        code_string="office é\nسلام", language="python", background="window"
    ),
    "an SVG with defaults": lambda: m.SVGMobject(
        _SVG,
        svg_default={"fill_color": m.RED},
        path_string_config={"sheen_direction": [1.0, 2.0, 3.0]},
    ),
    "an SVG path": lambda: m.VMobjectFromSVGPath(se.Path("M0 0 Q1 2 3 4 L6 0 Z")),
    "a brace": lambda: m.Brace(m.Rectangle(width=5, height=2), direction=m.UP),
    "a line with tips": _tipped,
    "an arrow with a recorded normal": lambda: (
        m.Arrow((-1, 2, 0.5), (2, -0.5, 3))
        .rotate(0.31, axis=[2.0, -1.0, 3.0])
        .reset_normal_vector()
    ),
    "a dot with a saved state and a target": _with_history,
    "a polyhedron": lambda: m.Polyhedron(
        [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
        [[0, 1, 2], [0, 1, 3]],
        graph_config={"vertex_type": m.VectorizedPoint},
    ),
    "a checkered surface": lambda: m.Surface(
        saddle,
        resolution=(2, 3),
        checkerboard_colors=[m.RED, m.BLUE],
    ),
    "a mobject with updaters": _updated,
    "a kept construction that updates itself": _Kept,
}
CASES = {**{f"the class {k}": v for k, v in MOBJECTS.items()}, **STATES}


def _target(mob: m.Mobject) -> m.Mobject:
    target = mob.generate_target()
    mob.target = None  # (the original holds its target: let the two be compared)
    return target


def _saved(mob: m.Mobject) -> m.Mobject:
    mob.save_state()
    saved = mob.saved_state
    assert saved is not None
    mob.saved_state = None
    return saved


def _animated(mob: m.Mobject) -> m.Mobject:
    target = mob.animate.shift(m.ORIGIN).target_mobject
    assert target is not None
    mob.target = None  # (`.animate` keeps its target as the original's)
    return target


REPLICATIONS: dict[str, Callable[[m.Mobject], m.Mobject]] = {
    "copy": lambda mob: mob.copy(),
    "target": _target,
    "saved": _saved,
    "animated": _animated,
}


def evolve(mob: m.Mobject) -> None:
    """Change a mobject by its own means: its trackers nudged, its updaters run."""
    for part in list(reachable(mob).values()):
        if isinstance(part, ValueTracker) and not isinstance(part.get_value(), complex):
            part.set_value(part.get_value() + 1)
    random.seed(7)  # (flowing lines draw where they restart)
    mob.update(0.03)


def borrowed(mob: m.Mobject) -> set[int]:
    """The members a mobject holds as dictionary keys: identities, borrowed by its copies."""
    keys = (
        k
        for part in reachable(mob).values()
        if isinstance(part, dict)
        for k in part
        if isinstance(k, m.Mobject)
    )
    return {id(k) for k in keys}


@pytest.mark.parametrize("how", sorted(REPLICATIONS))
@pytest.mark.parametrize("name", sorted(CASES))
def test_a_replica_is_an_independent_isomorphic_copy(name: str, how: str) -> None:
    original = CASES[name]()
    keys = borrowed(original)
    family = [x for x in original.get_family() if id(x) not in keys]
    replica = REPLICATIONS[how](original)
    assert look(replica) == look(original)
    assert_replica(original, replica)
    assert not reaches(replica, family), "the replica reaches its original"
    before = look(original)
    evolve(replica)
    assert look(original) == before, "changing the replica changed the original"
    evolve(original)
    assert look(original) == look(replica), "the replica changes unlike its original"


@pytest.mark.cold
@pytest.mark.parametrize("name", sorted(CASES))
def test_a_construction_made_again_is_an_independent_isomorphic_copy(name: str) -> None:
    first, second, third = (CASES[name]() for _ in range(3))
    for a, b in ((first, second), (second, third)):
        assert look(a) == look(b)
        assert_replica(a, b)
        keys = borrowed(a)
        assert not reaches(b, [x for x in a.get_family() if id(x) not in keys])


# ── updaters ──────────────────────────────────────────────────────────────────────────────
LOG: list[tuple[str, float | None]] = []  # what the updaters saw, in order


class Owner:  # an object whose methods are updaters
    def __init__(self, label: str) -> None:
        self.label = label

    def per_frame(self, mob: m.Mobject) -> None:
        LOG.append((self.label, None))

    def timed(self, mob: m.Mobject, dt: float) -> None:
        LOG.append((self.label, dt))


class MobjectOwner(m.Mobject):  # a mobject whose method is an updater of another
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def timed(self, mob: m.Mobject, dt: float) -> None:
        LOG.append((self.label, dt))


class Clocked:  # a callable updater on a clock of its own
    def __init__(self, label: str) -> None:
        self.label = label
        self.clock = clock.Clock()
        self.clock.warp(0, 2, 4, linear)

    def __call__(self, mob: m.Mobject, dt: float) -> None:
        LOG.append((self.label, dt))


def _labelled(label: str, timed: bool) -> Callable[..., None]:
    if timed:

        def time_based(mob: m.Mobject, dt: float) -> None:
            LOG.append((label, dt))

        return time_based

    def per_frame(mob: m.Mobject) -> None:
        LOG.append((label, None))

    return per_frame


def label_of(updater: object) -> str | None:
    owner = getattr(updater, "__self__", updater)
    label = getattr(owner, "label", None)
    if isinstance(label, str):
        return label
    for cell in getattr(updater, "__closure__", None) or ():
        if isinstance(cell.cell_contents, str):
            return cell.cell_contents
    return None


@dataclass
class Slot:
    label: str
    timed: bool
    owner: object | None  # what must be let go once the updater is gone
    clocked: Clocked | None = None
    stamp: Fraction = Fraction(0)


@dataclass
class Model:
    slots: list[Slot] = field(default_factory=list)
    suspended: bool = False


FORMS = ["function", "method", "mobject method", "clocked"]


class Updaters(RuleBasedStateMachine):
    """A host and its part, their updaters added, removed, suspended, copied and run, beside a
    model of each updater's clock."""

    def __init__(self) -> None:
        super().__init__()
        clock.reset()
        LOG.clear()
        self.host: m.Mobject = m.Group(m.Mobject())
        self.models = {"host": Model(), "part": Model()}
        self.removed: list[object] = []
        self.count = 0

    def mob(self, which: str) -> m.Mobject:
        return self.host if which == "host" else self.host.submobjects[0]

    @initialize()
    def a_time_based_updater(self) -> None:  # (something to watch from the start)
        self.add("host", "function", timed=True)

    def drop(self, which: str, label: str) -> None:
        model = self.models[which]
        for slot in [s for s in model.slots if s.label == label]:
            model.slots.remove(slot)
            if slot.owner is not None and all(s.label != label for s in model.slots):
                self.removed.append(slot.owner)

    @rule(
        which=st.sampled_from(["host", "part"]),
        form=st.sampled_from(FORMS),
        timed=st.booleans(),
    )
    def add(self, which: str, form: str, timed: bool) -> None:
        self.count += 1
        label = f"u{self.count}"
        owner: object | None = None
        clocked = None
        updater: Callable[..., object]
        if form == "function":
            updater = _labelled(label, timed)
        elif form == "method":
            plain = Owner(label)
            owner, updater = plain, plain.timed if timed else plain.per_frame
        elif form == "mobject method":
            mobject = MobjectOwner(label)
            owner, updater, timed = mobject, mobject.timed, True
        else:
            clocked = Clocked(label)
            owner, updater, timed = clocked, clocked, True
        self.mob(which).add_updater(updater)
        self.models[which].slots.append(Slot(label, timed, owner, clocked, clock.now))

    @precondition(lambda self: self.models["host"].slots)
    @rule(data=st.data())
    def add_again(self, data: st.DataObject) -> None:
        # the same updater again, or an equal one (a method bound anew): one clock between them
        slot = data.draw(st.sampled_from(self.models["host"].slots))
        updater = next(u for u in self.host.updaters if label_of(u) == slot.label)
        owner = getattr(updater, "__self__", None)
        if isinstance(owner, Owner) and data.draw(st.booleans()):
            updater = getattr(owner, getattr(updater, "__name__", ""))
        self.host.add_updater(updater)
        model = self.models["host"]
        model.slots.append(
            Slot(slot.label, slot.timed, slot.owner, slot.clocked, clock.now)
        )
        for s in model.slots:
            if s.label == slot.label:
                s.stamp = clock.now

    @precondition(lambda self: self.models["host"].slots)
    @rule(data=st.data())
    def remove(self, data: st.DataObject) -> None:
        slot = data.draw(st.sampled_from(self.models["host"].slots))
        for updater in [u for u in self.host.updaters if label_of(u) == slot.label]:
            self.host.remove_updater(updater)
        self.drop("host", slot.label)

    @rule(recursive=st.booleans(), how=st.sampled_from(["clear", "match"]))
    def clear(self, recursive: bool, how: str) -> None:
        if how == "clear":
            self.host.clear_updaters(recursive)
        else:
            self.host.match_updaters(m.Mobject())  # takes none, and clears the parts'
            recursive = True
        for which in ("host", "part") if recursive else ("host",):
            for slot in list(self.models[which].slots):
                self.drop(which, slot.label)

    @precondition(lambda self: not self.models["host"].suspended)
    @rule(recursive=st.booleans())
    def suspend(self, recursive: bool) -> None:
        self.host.suspend_updating(recursive)
        for which in ("host", "part") if recursive else ("host",):
            self.models[which].suspended = True

    @precondition(lambda self: any(model.suspended for model in self.models.values()))
    @rule(recursive=st.booleans())
    def resume(self, recursive: bool) -> None:
        self.host.resume_updating(recursive)
        for which in ("host", "part") if recursive else ("host",):
            self.models[which].suspended = False
            for slot in self.models[which].slots:
                slot.stamp = clock.now

    @precondition(lambda self: not self.models["host"].suspended)
    @rule(dt=st.sampled_from([Fraction(1, 2), Fraction(1)]), recursive=st.booleans())
    def play(self, dt: Fraction, recursive: bool) -> None:
        # an animation suspends its mobject's updating while it plays and resumes it as it
        # finishes, and the scene goes on: the time it played is not made up
        self.suspend(recursive)
        self.advance(dt, None)
        self.resume(recursive)
        self.advance(Fraction(1, 2), None)

    @rule()
    def copy(self) -> None:
        self.host = self.host.copy()  # the copy goes on as the original would have

    def expected(
        self, dt: float | None, t: Fraction, skipped: str | None
    ) -> list[object]:
        calls: list[object] = []
        if self.models["host"].suspended:  # a suspended host's subtree is not run
            return calls
        for which in ("host", "part"):
            model = self.models[which]
            if model.suspended:
                continue
            for slot in list(model.slots):
                if which == "host" and slot.label == skipped:
                    continue
                if not slot.timed:
                    calls.append((slot.label, None))
                elif dt is not None:  # update: the dt given
                    calls.append((slot.label, dt))
                else:  # advance: the time its clock ran since it last ran
                    on = slot.clocked.clock if slot.clocked else None
                    ran = (
                        on.at(float(t)) - on.at(float(slot.stamp))
                        if on
                        else float(t - slot.stamp)
                    )
                    calls.append((slot.label, ran))
                    for s in model.slots:  # one stamp a callable
                        if s.label == slot.label:
                            s.stamp = t
        return calls

    @rule(
        dt=st.sampled_from([Fraction(1, 2), Fraction(1), Fraction(3, 2)]),
        victim=st.none() | st.integers(0, 3),
    )
    def advance(self, dt: Fraction, victim: int | None) -> None:
        t = clock.now + dt
        clock.now = t
        LOG.clear()
        model = self.models["host"]
        doomed = None
        if victim is not None and model.slots and not model.suspended:
            # an updater that removes another while the pass runs: the other never runs
            doomed = model.slots[victim % len(model.slots)].label

            def remover(mob: m.Mobject, dt: float) -> None:
                for u in list(mob.updaters):
                    if label_of(u) == doomed:
                        mob.remove_updater(u)

            self.host.add_updater(remover, index=0)
        self.host.advance(t)
        expected = self.expected(None, t, doomed)
        if doomed is not None:
            self.host.remove_updater(remover)
            self.drop("host", doomed)
        assert expected == LOG

    @rule(dt=st.sampled_from([0.25, 1.0]))
    def update(self, dt: float) -> None:
        LOG.clear()
        self.host.update(dt)
        assert self.expected(dt, clock.now, None) == LOG

    @invariant()
    def nothing_removed_is_held(self) -> None:
        held = reaches(self.host, self.removed)
        assert not held, f"the host keeps removed updaters' owners alive: {held}"


TestUpdaters = Updaters.TestCase
TestUpdaters.settings = settings(stateful_step_count=25, max_examples=100)


# ── values ────────────────────────────────────────────────────────────────────────────────
def scribble(value: object) -> None:
    """Change a value in place, however it can be changed."""
    if isinstance(value, np.ndarray):
        if value.flags.writeable:
            value[...] = 0.875 if value.dtype.kind == "f" else 1
    elif isinstance(value, list):
        if value and isinstance(value[0], list):
            for row in value:
                row.reverse()
        else:
            value[:] = [*(x + 1 for x in value), 1.0]
    elif isinstance(value, dict):
        for key in value:
            value[key] = m.GREEN


def _regenerated(mob: m.Mobject) -> list[object]:
    mob.reset_points().generate_points()
    return list(look(mob))


def _meshed(mesh: m.Mobject) -> list[object]:
    assert isinstance(mesh, m.MeshMobject)
    mesh.reset_points().generate_points()
    uvs = None if mesh.uvs is None else mesh.uvs.tobytes()
    return [*look(mesh), mesh.triangles.tobytes(), uvs]


def _labelled_line(line: m.Mobject) -> list[object]:
    assert isinstance(line, m.NumberLine)
    line.add_numbers()
    line.add_ticks()
    return list(look(line))


def _faces(poly: m.Mobject) -> list[object]:
    poly.update()
    return list(look(poly))


def _texture(mesh: m.Mobject) -> list[object]:
    return [np.asarray(mesh.paint.texture).tobytes()]


@dataclass
class Given[T]:
    """A mobject made of an input: `make` it of a fresh input `given()`; `later` is what it
    makes of the input afterwards (regenerated, labelled, updated)."""

    make: Callable[[T], m.Mobject]
    given: Callable[[], T]
    later: Callable[[m.Mobject], list[object]] = _regenerated


TRIANGLE = [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [2.0, 1.0, 0.0]]
DIRECTION = [0.5, -0.25, 0.125]
RGBAS = [[0.1, 0.2, 0.3, 0.4], [0.7, 0.6, 0.5, 0.8]]
FACES = [[0, 1, 2], [0, 1, 3]]
TETRA = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _array(rows: list[list[float]] | list[float]) -> Callable[[], np.ndarray]:
    return lambda: np.array(rows, dtype=float)


def _square_with(name: str) -> Callable[[np.ndarray], m.Mobject]:
    def make(value: np.ndarray) -> m.Mobject:
        square = m.Square()
        setattr(square, name, value)
        return square

    return make


def _mesh_with(name: str) -> Callable[[np.ndarray], m.Mobject]:
    def make(value: np.ndarray) -> m.Mobject:
        mesh = m.MeshMobject(np.array(TETRA), np.array(FACES), uvs=np.zeros((4, 2)))
        setattr(mesh, name, value)
        return mesh

    return make


def saddle(u: float, v: float) -> np.ndarray:
    return np.array([u, v, u * v])


def _surface(u_range: list[float]) -> m.Mobject:
    return m.Surface(saddle, u_range=u_range, resolution=2)


INPUTS: dict[str, Given] = {
    "polygram vertices": Given(lambda v: m.Polygram(v), _array(TRIANGLE)),
    "polygram vertex lists": Given(
        lambda v: m.Polygram(v), lambda: [list(r) for r in TRIANGLE]
    ),
    "a sheen direction made with": Given(
        lambda v: m.Square(sheen_direction=v), _array(DIRECTION)
    ),
    "a sheen direction set": Given(
        lambda v: m.Square().set_sheen_direction(v), _array(DIRECTION)
    ),
    "a sheen set": Given(lambda v: m.Square().set_sheen(0.25, v), _array(DIRECTION)),
    "a style set": Given(
        lambda v: m.Square().set_style(sheen_factor=0.25, sheen_direction=v),
        _array(DIRECTION),
    ),
    "a sheen direction assigned": Given(
        _square_with("sheen_direction"), _array(DIRECTION)
    ),
    "fill rows": Given(_square_with("fill_rgbas"), _array(RGBAS)),
    "stroke rows": Given(_square_with("stroke_rgbas"), _array(RGBAS)),
    "background stroke rows": Given(
        _square_with("background_stroke_rgbas"), _array(RGBAS)
    ),
    "a large strided brush": Given(
        _square_with("fill_rgbas"),
        lambda: np.linspace(0, 1, 4096 * 8).reshape(4096, 8)[:, ::2],
    ),
    "stroke colors and opacities": Given(
        lambda v: m.Square().set_stroke(color=v, opacity=np.array([0.25, 0.75])),
        _array([0.1, 0.2, 0.3]),
    ),
    "mesh triangles assigned": Given(
        _mesh_with("triangles"), lambda: np.array([[0, 1, 2]])
    ),
    "mesh texture coordinates assigned": Given(
        _mesh_with("uvs"), _array([[0.1, 0.2]] * 4)
    ),
    "a dictionary argument": Given(
        lambda v: m.MathTex("x", "+", "y", tex_to_color_map=dict(v)),
        lambda: {"x": m.RED},
    ),
    "mesh vertices made with": Given(
        lambda v: m.MeshMobject(np.asarray(v), np.array(FACES)), _array(TETRA), _meshed
    ),
    "mesh triangles made with": Given(
        lambda v: m.MeshMobject(np.array(TETRA), np.asarray(v)),
        lambda: np.array(FACES),
        _meshed,
    ),
    "a surface's range": Given(_surface, lambda: [-1.0, 1.0]),
    "a curve's breaks": Given(
        lambda v: m.ParametricFunction(
            lambda t: np.array([t, t * t, 0.0]),
            t_range=(-2, 2, 0.25),
            discontinuities=v,
            use_smoothing=False,
        ),
        lambda: [-1.0, 0.5],
    ),
    "a number line's exclusions": Given(
        lambda v: m.NumberLine((0, 3, 1), include_ticks=False, numbers_to_exclude=v),
        lambda: [0.0, 2.0],
        _labelled_line,
    ),
    "a number line's elongated ticks": Given(
        lambda v: m.NumberLine(
            (0, 3, 1), include_ticks=False, numbers_with_elongated_ticks=v
        ),
        _array([0.0, 2.0]),
        _labelled_line,
    ),
    "a polyhedron's faces": Given(
        lambda v: m.Polyhedron(
            TETRA, v, graph_config={"vertex_type": m.VectorizedPoint}
        ),
        lambda: [list(f) for f in FACES],
        _faces,
    ),
    "a mesh's texture": Given(
        lambda v: m.MeshMobject(
            np.array(TETRA),
            np.array(FACES),
            uvs=np.zeros((4, 2)),
            texture=np.asarray(v),
        ),
        lambda: np.full((2, 2, 4), 37, dtype=np.uint8),
        _texture,
    ),
}


class _Subclass(np.ndarray):
    """An array of a subclass of ndarray: still a value."""


def _kind(given: np.ndarray, kind: str) -> tuple[np.ndarray, np.ndarray]:
    """An array input in one of the forms a caller may hold it in (`held`), and a writable
    alias of it, which the caller may still change it through (`writer`)."""
    owner = given.astype(np.float32) if kind == "float32" else given
    if kind == "strided":
        wide = np.zeros((*owner.shape[:-1], owner.shape[-1] * 2), dtype=owner.dtype)
        wide[..., ::2] = owner
        owner = wide[..., ::2]
    writer = owner.view()
    held = owner.view(_Subclass) if kind == "a subclass" else owner
    if kind == "a read-only view":
        held = owner.view()
        held.flags.writeable = False
    elif kind == "read-only":
        held.flags.writeable = False
    return held, writer


KINDS = ["owned", "a read-only view", "read-only", "strided", "float32", "a subclass"]


@pytest.mark.cold
@pytest.mark.parametrize("name", sorted(INPUTS))
def test_an_input_is_a_value(name: str) -> None:
    case = INPUTS[name]
    given, pristine = case.given(), case.given()
    writeable = given.flags.writeable if isinstance(given, np.ndarray) else None
    mob = case.make(given)
    if isinstance(given, np.ndarray):  # making it changes no input
        np.testing.assert_array_equal(given, pristine)
        assert given.flags.writeable == writeable
    shown = look(mob)
    scribble(given)
    assert look(mob) == shown, "changing the input after changed the mobject"
    assert case.later(mob) == case.later(case.make(pristine)), (
        "changing the input after changed what the mobject makes of it"
    )


ARRAYS = [  # the array inputs a caller may hold in any form
    n for n in sorted(INPUTS) if isinstance(INPUTS[n].given(), np.ndarray)
]


@pytest.mark.cold
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("name", ARRAYS)
def test_an_array_input_is_a_value_however_it_is_held(name: str, kind: str) -> None:
    case = INPUTS[name]
    given = case.given()
    assert isinstance(given, np.ndarray)
    held, writer = _kind(given, kind)
    writeable = held.flags.writeable
    mob = case.make(held)
    copy = mob.copy()
    assert held.flags.writeable == writeable
    shown = look(mob)
    writer[...] = 0.875 if writer.dtype.kind == "f" else 1
    assert look(mob) == shown, "a writable alias of the input changed the mobject"
    assert look(copy) == shown, "a writable alias of the input changed its copy"


class Probe(dict[str, object]):
    """A mapping a reachability check can find by its identity."""


class Selection:
    """A one-shot iterator of numbers, never to be copied."""

    def __init__(self) -> None:
        self.values = iter((1.0, 2.0))

    def __iter__(self) -> "Selection":
        return self

    def __next__(self) -> float:
        return next(self.values)

    def __deepcopy__(self, memo: dict[int, object]) -> "Selection":
        raise AssertionError("a consumed iterator is not drawing state")


class Factory:
    """A vertex factory: an object, kept or not by what it makes."""

    def __call__(self, **kwargs: object) -> m.VectorizedPoint:
        return m.VectorizedPoint()


def _view_of_storage() -> np.ndarray:
    storage = np.zeros((1 << 12, 3))
    storage[:4] = TETRA
    return storage[:4]


def _laid_out(probe: list[object]) -> m.Mobject:
    def layout(graph: object, **kwargs: object) -> dict[int, list[float]]:
        probe.append(graph)
        return {0: [0.0, 0.0], 1: [1.0, 0.0]}

    return m.Graph([0, 1], [(0, 1)], layout=layout)


@dataclass
class Unshown[T]:
    """A mobject made of an input it does not show: `make` it of a fresh `given()`."""

    make: Callable[[T], m.Mobject]
    given: Callable[[], T]


UNSHOWN: dict[str, Unshown] = {
    "a matrix's alignment corner": Unshown(
        lambda v: m.MobjectMatrix(
            [[m.Square(0.4)]], element_alignment_corner=np.asarray(v)
        ),
        lambda: np.array([1.0, -1.0, 0.0]),
    ),
    "a table's line options": Unshown(
        lambda v: m.MobjectTable([[m.Square(0.3)]], line_config=cast(LineOptions, v)),
        Probe,
    ),
    "a table's grid options": Unshown(
        lambda v: m.MobjectTable(
            [[m.Square(0.3)]], arrange_in_grid_config=cast(GridArrangement, v)
        ),
        Probe,
    ),
    "a plane's faded style": Unshown(
        lambda v: m.NumberPlane(faded_line_style=cast(Style, v), faded_line_ratio=2),
        lambda: Probe(stroke_color=m.RED),
    ),
    "a polar plane's background color": Unshown(
        lambda v: m.PolarPlane(background_line_style={"stroke_color": np.asarray(v)}),
        lambda: np.array([0.2, 0.4, 0.6]),
    ),
    "a number line's selection": Unshown(
        lambda v: m.NumberLine((0, 3, 1), numbers_to_include=v), Selection
    ),
    "a number line's exclusion iterator": Unshown(
        lambda v: m.NumberLine((0, 3, 1), include_ticks=False, numbers_to_exclude=v),
        Selection,
    ),
    "3D axes' selection": Unshown(
        lambda v: m.ThreeDAxes(
            x_range=(0, 3, 1),
            y_range=(0, 3, 1),
            z_range=(0, 3, 1),
            axis_config={"numbers_to_include": v, "font_size": 18},
        ),
        Selection,
    ),
    "a curve's break iterator": Unshown(
        lambda v: m.ParametricFunction(
            lambda t: np.array([t, t, 0.0]), t_range=(-2, 2, 0.5), discontinuities=v
        ),
        Selection,
    ),
    "a polyhedron's vertex views": Unshown(
        lambda v: m.Polyhedron(
            np.asarray(v), FACES, graph_config={"vertex_type": m.VectorizedPoint}
        ),
        _view_of_storage,
    ),
    "a polyhedron's vertex factory": Unshown(
        lambda v: m.Polyhedron(TETRA, FACES, graph_config={"vertex_type": v}),
        Factory,
    ),
    "a polygram's vertex view": Unshown(
        lambda v: m.Polygram(np.asarray(v)[:3]), _view_of_storage
    ),
    "an arc's ignored normal": Unshown(
        lambda v: m.Arc(normal_vector=np.asarray(v)), lambda: np.ones((1 << 12, 3))[3]
    ),
    "a surface's ignored piece options": Unshown(
        lambda v: m.Surface(
            lambda u, w: np.array([u, w, 0.0]),
            resolution=2,
            surface_piece_config=cast(Style, v),
        ),
        lambda: Probe(target=m.Group(*(m.Dot() for _ in range(8)))),
    ),
    "a rectangle's target": Unshown(
        lambda v: m.SurroundingRectangle(v),
        lambda: m.Circle().set_color(m.RED),
    ),
    "a parsed SVG path": Unshown(
        lambda v: m.VMobjectFromSVGPath(v),
        lambda: se.Path("M0 0 L2 0 L2 1 Z"),
    ),
    "a view assigned as a mesh's triangles": Unshown(
        _mesh_with("triangles"), lambda: np.ones((4096, 3), dtype=np.int64)[:2]
    ),
    "a sheen direction made with": Unshown(
        lambda v: m.Square(sheen_direction=np.asarray(v)), _array(DIRECTION)
    ),
    "fill rows assigned": Unshown(_square_with("fill_rgbas"), _array(RGBAS)),
    "the graph a layout is handed": Unshown(_laid_out, list),
}


@pytest.mark.parametrize("name", sorted(UNSHOWN))
def test_what_it_does_not_show_it_does_not_keep(name: str) -> None:
    case = UNSHOWN[name]
    given = case.given()
    mob = case.make(given)
    gone = (
        [*given] if isinstance(given, list) else [given]
    )  # (a layout's: what it was handed)
    gone += [x.base for x in gone if isinstance(x, np.ndarray) and x.base is not None]
    assert not reaches(mob, gone), "the mobject keeps an input it does not show"
    mob.copy()  # (an input it kept, a copy would copy)


# what an edit replaces is not kept either: (a mobject, the edit, what the edit replaces)
EDITS: dict[
    str,
    tuple[
        Callable[[], m.Mobject],
        Callable[[m.Mobject], object],
        Callable[[m.Mobject], object],
    ],
] = {
    "thinned": (
        lambda: m.PMobject().add_points(np.zeros((1000, 3))),
        lambda cloud: cloud.thin_out(100) if isinstance(cloud, m.PMobject) else None,
        lambda cloud: cloud.paint.fill,
    ),
    "a target replaced": (
        lambda: m.Mobject(target=m.Square()),
        lambda mob: setattr(mob, "target", None),
        lambda mob: mob.target,
    ),
    "a number's unit dropped": (
        lambda: m.DecimalNumber(7, unit="m"),
        lambda n: (
            (setattr(n, "unit", None), n.set_value(7))
            if isinstance(n, m.DecimalNumber)
            else None
        ),
        lambda n: n.submobjects[-1],
    ),
    "a number's background dropped": (
        lambda: m.DecimalNumber(7, include_background_rectangle=True),
        lambda n: (
            (setattr(n, "include_background_rectangle", False), n.set_value(7))
            if isinstance(n, m.DecimalNumber)
            else None
        ),
        lambda n: n.submobjects[0],
    ),
    "a number's added background, redrawn": (
        lambda: m.DecimalNumber(7).add_background_rectangle(),
        lambda n: n.set_value(8) if isinstance(n, m.DecimalNumber) else None,
        lambda n: n.submobjects[0],
    ),
}


@pytest.mark.parametrize("name", sorted(EDITS))
def test_what_an_edit_replaces_is_not_kept(name: str) -> None:
    make, edit, replaced = EDITS[name]
    mob = make()
    old = replaced(mob)
    edit(mob)
    assert not reaches(mob, [old]), "the mobject keeps what the edit replaced"


def _numbers_of(line: m.Mobject) -> list[object]:
    assert isinstance(line, m.NumberLine)
    line.add_numbers()
    return list(look(line))


def _regenerate(mob: m.Mobject) -> list[object]:
    return _regenerated(mob)


def _bars(one_shot: bool) -> m.Mobject:
    chart = m.BarChart([3, 0, -2], y_range=(-10, 10, 20))
    for values in ([5, 1, -4], [4], [1, -2, 0]):
        chart.change_bar_values(iter(values) if one_shot else values)
    return chart


def _line(name: str) -> Callable[[bool], m.Mobject]:
    def make(one_shot: bool) -> m.Mobject:
        values = [0.0, 2.0]
        given = iter(values) if one_shot else values
        if name == "numbers_to_include":
            return m.NumberLine((0, 3, 1), numbers_to_include=given)
        if name == "numbers_to_exclude":
            return m.NumberLine(
                (0, 3, 1), include_numbers=True, numbers_to_exclude=given
            )
        return m.NumberLine((0, 3, 1), numbers_with_elongated_ticks=given)

    return make


def _breaks(vectorized: bool) -> Callable[[bool], m.Mobject]:
    def make(one_shot: bool) -> m.Mobject:
        values = [-1.0, 0.5]
        return m.ParametricFunction(
            (lambda t: np.array([t, t * t, np.zeros_like(t)]))
            if vectorized
            else (lambda t: np.array([t, t * t, 0.0])),
            t_range=(-2, 2, 0.25),
            discontinuities=iter(values) if one_shot else values,
            use_vectorized=vectorized,
        )

    return make


def _axes(one_shot: bool) -> m.Mobject:
    values = [1.0, 2.0]
    return m.Axes(
        x_range=(0, 3, 1),
        y_range=(0, 3, 1),
        axis_config={"numbers_to_include": iter(values) if one_shot else values},
    )


def _palette(one_shot: bool) -> m.Mobject:
    colors = [m.RED, m.BLUE]
    return m.Surface(
        saddle,
        resolution=2,
        checkerboard_colors=iter(colors) if one_shot else colors,
    )


# what is made of an iterable: of its items once (one_shot) or of the list of them
ITERABLES: dict[
    str, tuple[Callable[[bool], m.Mobject], Callable[[m.Mobject], list[object]]]
] = {
    "a number line's numbers": (_line("numbers_to_include"), _numbers_of),
    "a number line's exclusions": (_line("numbers_to_exclude"), _numbers_of),
    "a number line's elongated ticks": (
        _line("numbers_with_elongated_ticks"),
        _numbers_of,
    ),
    "a curve's breaks": (_breaks(False), _regenerate),
    "a vectorized curve's breaks": (_breaks(True), _regenerate),
    "axes' numbers": (_axes, lambda mob: list(look(mob))),
    "a surface's palette": (_palette, lambda mob: list(look(mob))),
    "a chart's values, changed": (_bars, lambda mob: list(look(mob))),
}


@pytest.mark.parametrize("name", sorted(ITERABLES))
def test_an_iterator_gives_what_the_list_of_its_items_gives(name: str) -> None:
    make, later = ITERABLES[name]
    once, listed = make(True), make(False)
    assert look(once) == look(listed)
    assert look(once.copy()) == look(listed.copy())
    assert later(once) == later(listed)


IGNORED: dict[str, tuple[Callable[[], m.Mobject], Callable[[], m.Mobject]]] = {
    "an arc's normal": (lambda: m.Arc(normal_vector=[1.0, 2.0, 3.0]), lambda: m.Arc()),
    "a tipped line's normal": (
        lambda: (
            m.Line((-1, 2, 0.5), (2, -0.5, 3), normal_vector=[2.0, -1.0, 5.0])
            .add_tip()
            .add_tip(at_start=True)
            .rotate(0.37, axis=[1.0, 2.0, 3.0])
        ),
        lambda: (
            m.Line((-1, 2, 0.5), (2, -0.5, 3))
            .add_tip()
            .add_tip(at_start=True)
            .rotate(0.37, axis=[1.0, 2.0, 3.0])
        ),
    ),
    "an SVG path's options": (
        lambda: m.VMobjectFromSVGPath(
            se.Path("M0 0 Q1 2 3 4 C4 4 5 2 6 0 L6 0 Z"),
            long_lines=True,
            should_subdivide_sharp_curves=True,
            should_remove_null_curves=True,
        ),
        lambda: m.VMobjectFromSVGPath(se.Path("M0 0 Q1 2 3 4 C4 4 5 2 6 0 L6 0 Z")),
    ),
    "a surface's options": (
        lambda: m.Surface(
            saddle,
            resolution=2,
            should_make_jagged=True,
            pre_function_handle_to_anchor_scale_factor=0.25,
            surface_piece_config={"color": m.RED},
        ),
        lambda: m.Surface(saddle, resolution=2),
    ),
}


@pytest.mark.parametrize("name", sorted(IGNORED))
def test_an_ignored_option_is_ignored_and_not_kept(name: str) -> None:
    given, plain = (make() for make in IGNORED[name])
    assert_replica(
        plain, given
    )  # (the same parts, to the attribute: nothing kept of it)


# what a query answers: (the query, its arguments)
QUERIES: dict[str, tuple[object, ...]] = {
    "get_center": (),
    "get_critical_point": (m.UR,),
    "get_start": (),
    "get_end": (),
    "get_all_points": (),
    "get_points_defining_boundary": (),
    "get_anchors": (),
    "get_start_anchors": (),
    "get_subpaths": (),
    "get_cubic_bezier_tuples": (),
    "get_nth_curve_length_pieces": (0,),
    "reveal_pace": (),
    "get_gradient_start_and_end_points": (),
    "get_all_rgbas": (),
    "get_stroke_rgbas": (),
    "boundary_box": (),
    "get_updaters": (),
}  # (get_family answers with the mobject's own list: Manim's API)


def _ask(mob: m.Mobject, query: str) -> object:
    method = getattr(mob, query, None)
    if not callable(method):
        return None
    try:
        return method(*QUERIES[query])
    except Exception:  # (a query this mobject cannot answer)
        return None


def _frozen(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.copy()
    if isinstance(value, (tuple, list)):
        return [_frozen(v) for v in value]
    return value


def _same(a: object, b: object) -> bool:
    if isinstance(a, np.ndarray):
        return isinstance(b, np.ndarray) and np.array_equal(a, b, equal_nan=True)
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return len(a) == len(b) and all(map(_same, a, b))
    return a is b or a == b


def _scribble_all(value: object) -> None:
    if isinstance(value, np.ndarray) and value.flags.writeable:
        value[...] = 50
    elif isinstance(value, (tuple, list)):
        for v in value:
            _scribble_all(v)


@pytest.mark.parametrize("name", sorted(MOBJECTS))
def test_what_a_query_returns_is_a_value(name: str) -> None:
    mob = MOBJECTS[name]()
    for query in QUERIES:
        if query == "boundary_box":
            continue  # (its own law, below)
        answer = _ask(mob, query)
        before, shown = _frozen(answer), look(mob)
        _scribble_all(answer)
        assert look(mob) == shown, f"changing what {query} returned changed the mobject"
        assert _same(_ask(mob, query), before), (
            f"changing {query}'s answer changed the next"
        )


@pytest.mark.parametrize("name", sorted(MOBJECTS))
def test_the_box_returned_is_a_value(name: str) -> None:
    mob = MOBJECTS[name]()
    box = mob.boundary_box()
    if box is None:
        return
    before, shown = box.copy(), look(mob)
    if box.flags.writeable:
        box[...] = 50
    assert look(mob) == shown
    assert _same(mob.boundary_box(), before)


def _writable_constants() -> list[np.ndarray]:
    import sys

    return [
        value
        for name, module in list(sys.modules.items())
        if name.startswith("manimgx") and module is not None
        for value in vars(module).values()
        if isinstance(value, np.ndarray) and value.flags.writeable
    ]


@pytest.mark.parametrize("name", sorted(MOBJECTS))
def test_nothing_it_holds_is_a_constant(name: str) -> None:
    held = reaches(MOBJECTS[name](), _writable_constants())
    assert not held, "it holds one of manimgx's writable constants"


# ── defaults and memories ─────────────────────────────────────────────────────────────────
class Base(m.Mobject):
    def __init__(self, tag: str = "base", value: int = 0) -> None:
        super().__init__()
        self.made: tuple[object, ...] = (tag, value)


class Child(Base):
    pass


class Grand(Child):
    def __init__(self, tag: str = "grand", value: int = 0) -> None:
        super().__init__(tag=tag, value=value)


class Left(Base):
    pass


class Right(Base):
    def __init__(self, tag: str = "right", value: int = 0) -> None:
        super().__init__(tag=tag, value=value)
        self.made = (*self.made, "right")  # (what tells that this constructor ran)


class Diamond(Left, Right):
    pass


class Kept(Base):
    @prototype
    def __init__(self, tag: str = "kept", value: int = 0) -> None:
        super().__init__(tag=tag, value=value)


OWN: dict[type, dict[str, object]] = {  # the classes with constructors of their own
    Base: {"tag": "base", "value": 0},
    Grand: {"tag": "grand", "value": 0},
    Right: {"tag": "right", "value": 0},
    Kept: {"tag": "kept", "value": 0},
}
HIERARCHIES: dict[str, list[type[Base]]] = {
    "flat": [Base, Kept],
    "chain": [Base, Child, Grand],
    "diamond": [Base, Left, Right, Diamond],
}


def made_by(cls: type, configured: dict[type, dict[str, object]]) -> tuple[object, ...]:
    """What `cls()` makes, by its MRO: the classes before the first constructor of its own lend
    their defaults (the nearest's over the farther's) to that constructor, over its own."""
    lent: dict[str, object] = {}
    for klass in cls.__mro__:
        if klass in OWN:
            values = OWN[klass] | configured.get(klass, {}) | lent
            ran = [k for k in cls.__mro__ if k in OWN]  # the constructors that run
            return (
                values["tag"],
                values["value"],
                *(["right"] if Right in ran else []),
            )
        for key, value in configured.get(klass, {}).items():
            lent.setdefault(key, value)
    raise AssertionError(f"{cls.__name__} has no constructor")


steps = st.lists(
    st.tuples(
        st.integers(0, 3),
        st.none()
        | st.fixed_dictionaries(
            {"value": st.integers(1, 3)}, optional={"tag": st.sampled_from(["x", "y"])}
        ),
    ),
    max_size=6,
)


@pytest.mark.parametrize("hierarchy", ["flat", "chain", "diamond"])
@settings(max_examples=30)
@given(steps=steps)
@example(steps=[(1, {"value": 1}), (0, {"tag": "x"})])  # a child, then its parent
@example(steps=[(1, {"tag": "left"})])  # a mixin
def test_defaults_are_partial_application(
    hierarchy: str, steps: list[tuple[int, dict[str, object] | None]]
) -> None:
    classes = HIERARCHIES[hierarchy]
    configured: dict[type, dict[str, object]] = {}
    try:
        for index, given in steps:
            cls = classes[index % len(classes)]
            if given is None:
                cls.set_default()
                configured.pop(cls, None)
            else:
                cls.set_default(**given)
                configured[cls] = given
            for klass in classes:
                assert klass().made == made_by(klass, configured), klass.__name__
    finally:
        for cls in classes:
            cls.set_default()


def test_an_unknown_default_is_an_error_when_it_is_used() -> None:
    try:
        Base.set_default(unknown=True)
        with pytest.raises(TypeError, match="unknown"):
            Base()
    finally:
        Base.set_default()
    assert Base().made == ("base", 0)


# constructions whose memories defaults must reach (and what they remember)
CALLS: dict[str, Callable[[], m.Mobject]] = {
    "a text": lambda: m.Text("HH"),
    "a tabbed text": lambda: m.Text("a\tb", tab_width=4),
    "a spaced text": lambda: m.Text("a    b"),
    "an aligned formula": lambda: m.SingleStringMathTex("x", tex_environment="align*"),
    "an equation": lambda: m.SingleStringMathTex("x", tex_environment="equation*"),
    # (numbers of the same digits, told apart by their class, their unit)
    "a number in text": lambda: m.DecimalNumber(
        12, num_decimal_places=0, mob_class=m.Text
    ),
    "a number in math": lambda: m.DecimalNumber(
        12, num_decimal_places=0, mob_class=m.MathTex, color=m.RED
    ),
    "a number with a unit": lambda: m.DecimalNumber(7.125, unit="m"),
    "a number without": lambda: m.DecimalNumber(7.125),
    "code": lambda: m.Code(code_string="x\ny"),
    "a paragraph": lambda: m.Paragraph("a", "b"),
    "a division": lambda: m.SampleSpace().get_vertical_division(0.4),
    "riemann rectangles": lambda: _riemann(),
    "a red formula": lambda: m.MathTex("x+y", tex_to_color_map={"x": m.RED}),
    "a blue formula": lambda: m.MathTex("x+y", tex_to_color_map={"x": m.BLUE}),
    "a text colored ab then a": lambda: m.Text("ab", t2c={"ab": m.RED, "a": m.BLUE}),
    "a text colored a then ab": lambda: m.Text("ab", t2c={"a": m.BLUE, "ab": m.RED}),
    "a kept construction": lambda: Kept(),
    "a subclass setting its input first": lambda: _Inputs("first"),
    "the same subclass, another input": lambda: _Inputs("second"),
    "a variable of a subclass": lambda: m.Variable(1.125, "x", var_type=_Integer),
    "a checkered surface": lambda: m.Surface(lambda u, v: np.array([u, v, 0.0])),
}


class _Integer(m.Integer):
    pass


class _Marked(
    m.Mobject
):  # a kept constructor that draws by an input set before it runs
    @prototype
    def __init__(self) -> None:
        super().__init__()
        self.add(m.Square(1 + len(str(vars(self)["marker"]))))


class _Inputs(_Marked):
    def __init__(self, marker: str) -> None:
        self.marker = marker
        super().__init__()


def _riemann() -> m.Mobject:
    axes = m.Axes(x_range=(0, 3), y_range=(0, 6), tips=False)
    graph = axes.plot(lambda x: x + 2, x_range=(0, 2, 0.5))
    return axes.get_riemann_rectangles(graph, x_range=(0, 1), dx=1)


DEFAULTED: list[tuple[type[m.Mobject], dict[str, object]]] = [
    (m.Text, {"weight": m.BOLD}),
    (m.Typst, {"typst_preamble": "#set text(tracking: 8pt)"}),
    (m.VGroup, {"color": m.RED}),  # (VGroup is Group)
    (m.Rectangle, {"width": 3.7, "height": 1.9, "grid_xstep": 0.4}),
    (m.DecimalNumber, {"num_decimal_places": 3}),
    (_Integer, {"num_decimal_places": 4}),
    (m.Surface, {"checkerboard_colors": [m.RED, m.YELLOW], "resolution": 2}),
    (Base, {"tag": "configured"}),
]


@pytest.mark.cold
@pytest.mark.parametrize("call", sorted(CALLS))
@pytest.mark.parametrize(
    "defaulted", range(len(DEFAULTED)), ids=[f"{c.__name__}" for c, _ in DEFAULTED]
)
def test_a_construction_follows_the_defaults_and_remembers_nothing_else(
    call: str, defaulted: int
) -> None:
    cls, given = DEFAULTED[defaulted]
    make = CALLS[call]
    earlier = make()  # (and so remembered)
    seen = look(earlier)
    earlier.copy().shift(m.UP).set_color(
        m.PINK
    )  # (a changed copy is no construction's)
    try:
        cls.set_default(**given)
        warm = (make(), make())[1]
        caches.clear()
        cold = make()
        assert look(warm) == look(cold), (
            "a memory outlived the defaults it was made with"
        )
        assert look(earlier) == seen, (
            "changing the defaults changed a mobject made before"
        )
    finally:
        cls.set_default()
    assert look(make()) == seen, "restoring the defaults left something behind"


@pytest.mark.cold
def test_font_defaults_reach_remembered_text(two_fonts: tuple[str, str]) -> None:
    first, second = two_fonts
    try:
        m.Typst.set_default(font_paths=[first])
        before = m.Text("HH")
        explicit = m.Text("HH", font_paths=[])
        m.Typst.set_default(font_paths=[second])
        warm = m.Text("HH")
        caches.clear()
        cold = m.Text("HH")
        assert look(warm) == look(cold)
        assert (
            warm.width != before.width
        )  # (the fonts differ: the law has something to see)
        assert look(m.Text("HH", font_paths=[])) == look(explicit)
    finally:
        m.Typst.set_default()


ANY_ORDER = [*sorted(MOBJECTS), *sorted(CALLS)]


def _call(name: str) -> m.Mobject:
    return MOBJECTS[name]() if name in MOBJECTS else CALLS[name]()


@pytest.mark.cold
@settings(max_examples=3)
@given(order=st.permutations(ANY_ORDER))
def test_whatever_was_made_before_a_construction_is_as_if_made_from_nothing(
    order: list[str],
) -> None:
    warm = [_call(name) for name in order]
    for name, made in zip(order, warm, strict=True):
        caches.clear()
        cold = _call(name)
        assert look(made) == look(cold), name
        assert_replica(cold, made)
    held: dict[int, str] = {}  # and no two constructions share a mutable part
    for name, made in zip(order, warm, strict=True):
        for key in oracles.mutable_parts(made):
            assert held.setdefault(key, name) == name, f"{name} and {held[key]} share"


class TestPoints:
    @given(points=arrays((9, 3)), others=arrays((9, 3)))
    def test_others_are_taken(self, points: np.ndarray, others: np.ndarray) -> None:
        assume(not np.array_equal(points, others))
        mob = m.VMobject().set_points(points)
        mob.points = others
        np.testing.assert_array_equal(
            mob.points, m.VMobject().set_points(others).points
        )


@given(
    size=st.integers(1, 6),
    addition=st.integers(-3, 12),
    numpy=st.booleans(),
    repeated=st.booleans(),
)
@example(size=128, addition=1, numpy=False, repeated=False)
def test_a_grown_family_follows_each_part_with_invisible_copies(
    size: int, addition: int, numpy: bool, repeated: bool
) -> None:
    marks = [m.Square(0.2, fill_opacity=0.4).shift(i * m.RIGHT) for i in range(size)]
    parts = [
        *marks,
        *([marks[0]] if repeated else []),
    ]  # (one part held twice, by hand)
    owner = m.VGroup()
    owner.submobjects = list(parts)
    assert (
        owner.add_n_more_submobjects(
            cast("int", np.int64(addition)) if numpy else addition
        )
        is owner
    )
    if addition <= 0:
        assert owner.submobjects == parts
        return
    grown = owner.submobjects
    assert len(grown) == len(parts) + addition
    seen: set[int] = set()
    for index, part in enumerate(grown):
        source = index * len(parts) // len(grown)  # spread as evenly as can be
        if source not in seen:  # each part first, itself
            assert part is parts[source]
            seen.add(source)
        else:  # then copies of it, which show nothing
            assert part is not parts[source]
            np.testing.assert_array_equal(part.points, parts[source].points)
            assert part.get_fill_opacity() == part.get_stroke_opacity() == 0
    assert len({id(part) for part in grown}) == len({id(p) for p in parts}) + addition


unit = st.floats(0, 1)


class TestLength:
    @given(points=curves(max_curves=3), alpha=unit)
    def test_a_proportion_is_by_length(self, points: np.ndarray, alpha: float) -> None:
        mob = m.VMobject()
        mob.points = points
        lengths = oracles.arc_lengths(points)
        assume(lengths.sum() > 1e-2)
        u = mob._geometry.parameter_at(alpha)  # where point_from_proportion goes
        n = min(int(u), len(lengths) - 1)
        part = oracles.arc_lengths(
            partial_bezier_points(points[4 * n : 4 * n + 4], 0, u - n)
        )
        reached = (lengths[:n].sum() + part.sum()) / lengths.sum()
        # measured by nine straight pieces a curve: right to within the piece it falls in
        piece = mob._geometry.piece_lengths().max() / lengths.sum()
        assert reached == pytest.approx(alpha, abs=piece + 1e-9)
        np.testing.assert_allclose(
            mob.point_from_proportion(alpha), bezier(points[4 * n : 4 * n + 4])(u - n)
        )

    @given(mob=paths(), alpha=unit)
    def test_proportion_from_point_is_its_inverse(
        self, mob: m.VMobject, alpha: float
    ) -> None:
        assume(mob.get_arc_length() > 1e-3)
        point = mob.point_from_proportion(alpha)
        back = mob.proportion_from_point(point)
        # the first curve the point is on, to its tolerance (100 × 1e-6) counts
        np.testing.assert_allclose(
            mob.point_from_proportion(back),
            point,
            atol=1e-4 * (1 + np.abs(point).max()),
        )

    @given(mob=paths(), alpha=unit)
    def test_a_reveal_has_drawn_to_the_point_at_its_proportion(
        self, mob: m.VMobject, alpha: float
    ) -> None:
        paint = mob.paint.but(trim=np.array([0.0, alpha]), pace=mob.reveal_pace())
        _, reached = paint.window(mob.get_num_curves())
        n = min(int(reached), mob.get_num_curves() - 1)
        np.testing.assert_allclose(
            bezier(mob.get_nth_curve_points(n))(reached - n),
            mob.point_from_proportion(alpha),
            atol=1e-9,
        )

    @given(mob=paths())
    def test_the_length_is_its_straight_pieces_and_no_more_than_the_arc(
        self, mob: m.VMobject
    ) -> None:
        drawn = oracles.bezier_points(
            mob.points, np.linspace(0, 1, 10)
        )  # 9 pieces a curve
        pieces = np.linalg.norm(np.diff(drawn, axis=1), axis=2).sum()
        true = float(oracles.arc_lengths(mob.points).sum())
        measured = mob.get_arc_length()
        assert measured == pytest.approx(pieces, rel=1e-12, abs=1e-12)
        assert (
            measured <= true * (1 + 1e-9) + 1e-12
        )  # chords are never longer than arcs
        assert mob.get_arc_length(200) == pytest.approx(true, rel=1e-3, abs=1e-9)

    @given(radius=st.floats(0.1, 10))
    def test_a_circles_length_is_two_pi_r(self, radius: float) -> None:
        assert m.Circle(radius=radius).get_arc_length() == pytest.approx(
            2 * np.pi * radius, rel=5e-4
        )


class TestBuilding:
    @given(corners=st.integers(2, 8).flatmap(lambda n: arrays((n, 3), 10)))
    def test_corners_are_joined_by_straight_curves(self, corners: np.ndarray) -> None:
        mob = m.VMobject().set_points_as_corners(corners)
        curves_ = mob.points.reshape(-1, 4, 3)
        np.testing.assert_allclose(curves_[:, 0], corners[:-1], atol=1e-12)
        np.testing.assert_allclose(curves_[:, 3], corners[1:], atol=1e-12)
        for k in (1, 2):
            np.testing.assert_allclose(
                curves_[:, k],
                corners[:-1] + k / 3 * (corners[1:] - corners[:-1]),
                atol=1e-9,
            )

    @given(start=arrays(3, 10), handle=arrays(3, 10), end=arrays(3, 10), t=unit)
    def test_a_quadratic_curve_is_its_cubic(
        self, start: np.ndarray, handle: np.ndarray, end: np.ndarray, t: float
    ) -> None:
        mob = (
            m.VMobject()
            .start_new_path(start)
            .add_quadratic_bezier_curve_to(handle, end)
        )
        quadratic = (1 - t) ** 2 * start + 2 * (1 - t) * t * handle + t**2 * end
        np.testing.assert_allclose(bezier(mob.points)(t), quadratic, atol=1e-9)

    @given(corners=st.integers(2, 6).flatmap(lambda n: arrays((n, 3), 10)))
    def test_a_closed_path_ends_where_its_last_subpath_starts(
        self, corners: np.ndarray
    ) -> None:
        mob = m.VMobject().set_points_as_corners(corners).close_path()
        assert mob.is_closed()
        # to the path's tolerance: a path already ending there gets no line
        np.testing.assert_allclose(mob.points[-1], corners[0], rtol=1e-5, atol=1e-6)

    @given(
        parts=st.lists(curves(max_curves=3), min_size=1, max_size=4), gap=arrays(3, 5)
    )
    def test_subpaths_split_where_a_curve_does_not_start_at_the_last_end(
        self, parts: list[np.ndarray], gap: np.ndarray
    ) -> None:
        assume(np.linalg.norm(gap) > 1e-3)
        mob = m.VMobject()
        placed = []
        for part in parts:  # each part starts away from where the last one ended
            if placed:
                part = part - part[0] + placed[-1][-1] + gap
            placed.append(part)
            mob.append_points(part)
        subpaths = mob.get_subpaths()
        assert len(subpaths) == len(placed)
        for got, expected in zip(subpaths, placed, strict=True):
            # (to a rounding: a path's points are kept relative to its first)
            np.testing.assert_allclose(
                got, expected, rtol=0, atol=1e-12 * (1 + np.abs(expected).max())
            )


class TestRefining:
    @given(mob=paths(max_curves=4), n=st.integers(0, 12), t=unit)
    def test_inserted_curves_are_parts_of_the_curves(
        self, mob: m.VMobject, n: int, t: float
    ) -> None:
        old = mob.points.reshape(-1, 4, 3)
        mob.insert_n_curves(n)
        new = mob.points.reshape(-1, 4, 3)
        assert len(new) == len(old) + n
        # the split its docstring gives: new curve j to old curve j·m // n
        shares = np.bincount(
            np.arange(len(new)) * len(old) // len(new), minlength=len(old)
        )
        i = 0
        for curve, share in zip(old, shares, strict=True):
            for k in range(share):
                np.testing.assert_allclose(
                    bezier(new[i])(t),
                    bezier(curve)((k + t) / share),
                    atol=1e-9 * (1 + np.abs(curve).max()),
                )
                i += 1

    @given(a=paths(), b=paths())
    def test_aligned_paths_keep_their_shapes(
        self, a: m.VMobject, b: m.VMobject
    ) -> None:
        dense_a, dense_b = oracles.sample(a.points, 400), oracles.sample(b.points, 400)
        a.align_points(b)
        assert a.get_num_points() == b.get_num_points()
        for mob, dense in ((a, dense_a), (b, dense_b)):
            drawn = oracles.sample(mob.points, 20)
            gaps = np.linalg.norm(drawn[:, None] - dense[None], axis=2).min(axis=1)
            spacing = np.linalg.norm(np.diff(dense, axis=0), axis=1).max()
            assert gaps.max() <= spacing + 1e-9

    @given(mob=paths(), a=unit, b=unit, t=unit)
    def test_a_part_is_the_path_between_its_proportions_by_curves(
        self, mob: m.VMobject, a: float, b: float, t: float
    ) -> None:
        a, b = min(a, b), max(a, b)
        part = mob.copy().pointwise_become_partial(mob, a, b)
        n = mob.get_num_curves()

        # by curves: proportion x is curve int(x·n) at parameter frac(x·n)
        def at(x: float) -> np.ndarray:
            k = min(int(x * n), n - 1)
            return bezier(mob.get_nth_curve_points(k))(x * n - k)

        np.testing.assert_allclose(
            part.get_start(), at(a), atol=1e-9 * (1 + np.abs(mob.points).max())
        )
        np.testing.assert_allclose(
            part.get_end(), at(b), atol=1e-9 * (1 + np.abs(mob.points).max())
        )


FUNCTIONS = {
    "waves": lambda p: p + 0.5 * np.array([np.sin(p[1]), np.sin(p[0]), 0]),
    "square": lambda p: np.array([p[0] * abs(p[0]) / 10, p[1], p[2]]),
    "complex square": lambda p: np.array(
        [(p[0] ** 2 - p[1] ** 2) / 10, p[0] * p[1] / 5, p[2]]
    ),
}


@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize("name", FUNCTIONS)
@given(points=curves(max_curves=3))
def test_an_image_is_within_its_tolerance_all_along(
    name: str, grouped: bool, points: np.ndarray
) -> None:
    f = FUNCTIONS[name]
    mob = m.VMobject()
    mob.points = points
    image = mob.copy()
    (m.Group(image) if grouped else image).apply_function(f)
    old = mob.points.reshape(-1, 4, 3)
    new = image.points.reshape(
        len(old), -1, 4, 3
    )  # every curve cut into as many pieces
    pieces = new.shape[1]
    t = np.linspace(0, 1, 33)
    for curve, cut in zip(old, new, strict=True):
        for k, piece in enumerate(cut):
            true = np.array(
                [f(p) for p in oracles.bezier_points(curve, (k + t) / pieces)[0]]
            )
            got = oracles.bezier_points(np.asarray(piece), t)[0]
            assert np.linalg.norm(got - true, axis=1).max() <= 1.5e-3


class TestOrientation:
    @given(
        corners=st.integers(3, 8).flatmap(lambda n: arrays((n, 3), 10)),
        shift=arrays(3, 50),
    )
    def test_it_does_not_depend_on_where_the_path_is(
        self, corners: np.ndarray, shift: np.ndarray
    ) -> None:
        corners[:, 2] = 0
        area = oracles.polygon_area(corners)
        assume(abs(area) > 1e-3)
        mob = m.VMobject().set_points_as_corners([*corners, corners[0]])
        expected = "CCW" if area > 0 else "CW"
        assert mob.get_direction() == expected
        assert mob.shift(shift).get_direction() == expected
        assert mob.reverse_direction().get_direction() != expected


@given(lengths=st.tuples(*[st.integers(0, 20)] * 3), factor=st.integers(1, 25))
@example(lengths=(5, 5, 5), factor=21)
def test_thinning_keeps_every_kth_point_of_each_member_once(
    lengths: tuple[int, int, int], factor: int
) -> None:
    clouds = [
        m.PMobject().add_points(
            np.arange(3.0 * n).reshape(n, 3),
            rgbas=np.linspace(0, 1, 4 * n).reshape(n, 4),
        )
        for n in lengths
    ]
    root, a, b = clouds
    root.add(a, m.Group(a, b))  # (a held twice in the family: thinned once)
    original = [(c.points.copy(), c.paint.fill.copy()) for c in clouds]
    assert root.thin_out(factor) is root
    for cloud, (points, colors) in zip(clouds, original, strict=True):
        np.testing.assert_array_equal(cloud.points, points[::factor])
        np.testing.assert_array_equal(cloud.paint.fill, colors[::factor])


@pytest.mark.parametrize("factor", [0, -1, -5])
def test_thinning_requires_a_positive_factor_before_editing(factor: int) -> None:
    cloud = m.PMobject().add_points([[1, 2, 3], [4, 5, 6]])
    geometry, paint = cloud._geometry, cloud.paint
    with pytest.raises(ValueError, match="factor must be positive"):
        cloud.thin_out(factor)
    assert cloud._geometry is geometry
    assert cloud.paint is paint
    with pytest.raises(ValueError, match="factor must be positive"):
        m.PMobject().thin_out(factor)


def _reached(a: float, b: float, n: int) -> list[int]:
    """The steps k of n (each [k, k + 1) of them) that the stretch [na, nb] reaches into."""
    return [k for k in range(n) if a * n < k + 1 and b * n > k]


@given(a=st.floats(0, 1), b=st.floats(0, 1))
def test_a_clouds_part_is_every_point_its_stretch_reaches_into(
    a: float, b: float
) -> None:
    a, b = min(a, b), max(a, b)
    points = np.array([[x, 0.0, 0.0] for x in range(10)])
    source = m.PMobject().add_points(points, rgbas=np.linspace(0, 1, 40).reshape(10, 4))
    part = m.PMobject().pointwise_become_partial(source, a, b)
    shown = _reached(a, b, 10)
    np.testing.assert_array_equal(part.points, points[shown].reshape(-1, 3))
    np.testing.assert_array_equal(part.paint.fill, source.paint.fill[shown])


def test_point_cloud_keeps_distinct_future_point_color_and_initial_width() -> None:
    cloud = m.PMobject(color=m.RED, stroke_width=9).add_points([m.LEFT])
    cloud.set_color(m.BLUE).set_stroke(width=2)
    cloud.add_points([m.RIGHT])
    np.testing.assert_array_equal(cloud.paint.fill, [m.BLUE.to_rgba(), m.RED.to_rgba()])
    cloud.init_colors()
    assert cloud.paint.stroke_width == 9
    cloud.reset_points().add_points([m.ORIGIN])
    np.testing.assert_array_equal(cloud.paint.fill, [m.RED.to_rgba()])
    assert cloud.style["color"] == m.RED


def test_a_lattices_triangles_are_derived_from_its_grid() -> None:
    sphere = m.Sphere(resolution=(4, 6))
    triangles = sphere.triangles
    for same in (triangles, triangles.copy(), triangles.tolist()):
        sphere.triangles = same
        assert sphere.grid == (4, 6)
        np.testing.assert_array_equal(sphere.triangles, triangles)
    with pytest.raises(ValueError, match="derived triangles"):
        sphere.triangles = triangles[::-1]


@given(a=st.floats(0, 1), b=st.floats(0, 1))
@example(a=0.0, b=1.0)
@example(a=0.25, b=0.75)
@example(a=0.5, b=0.5)
def test_a_surfaces_part_is_a_surface_drawing_the_faces_its_stretch_reaches(
    a: float, b: float
) -> None:
    a, b = min(a, b), max(a, b)
    source = m.Sphere(resolution=(2, 3))
    colors = source.paint.fill.copy()
    colors[:, 3] = np.linspace(0.1, 0.9, len(colors))  # a color a cell
    source.paint = source.paint.but(fill=colors)
    part = m.MeshMobject(color=m.RED).pointwise_become_partial(source, a, b)
    faces = _reached(a, b, 6)
    assert part.grid == source.grid  # its whole lattice, as painted
    assert part.paint is source.paint
    np.testing.assert_array_equal(part.points, source.points)
    drawn = source.triangles.reshape(6, 2, 3)[faces].reshape(-1, 3)
    np.testing.assert_array_equal(part.triangles, drawn)
    box = part.boundary_box()
    corners = source.points[np.unique(drawn)]
    if faces:
        assert box is not None
        np.testing.assert_array_equal(box, [corners.min(axis=0), corners.max(axis=0)])
    else:
        assert box is None


def test_a_surfaces_part_of_a_part_and_its_pieces_share_its_faces_out() -> None:
    source = m.Torus(resolution=(4, 3))  # 12 faces
    half = source.copy().pointwise_become_partial(source, 0.5, 1.0)  # faces 6 to 12
    quarter = half.copy().pointwise_become_partial(half, 0.0, 0.5)  # 6 to 9
    np.testing.assert_array_equal(quarter.triangles, source.triangles[12:18])
    pieces = [p for p in source.get_pieces(4) if isinstance(p, m.MeshMobject)]
    assert [p.grid for p in pieces] == [(4, 3)] * 4
    np.testing.assert_array_equal(
        np.concatenate([p.triangles for p in pieces]), source.triangles
    )


@given(a=st.floats(0, 1), b=st.floats(0, 1))
@example(a=0.0, b=0.5)
def test_a_meshs_part_is_the_triangles_its_stretch_reaches_with_their_corners_alone(
    a: float, b: float
) -> None:
    a, b = min(a, b), max(a, b)
    corners = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [2, 2, 0]])
    rows = np.linspace(0, 1, 20).reshape(5, 4)  # a color a corner
    triangles = np.array([[0, 1, 2], [1, 3, 2], [3, 4, 2]])
    source = m.MeshMobject(corners, triangles)
    source.paint = source.paint.but(fill=rows)
    part = m.MeshMobject().pointwise_become_partial(source, a, b)
    reached = _reached(a, b, 3)
    if reached == [0, 1, 2]:  # the whole: the mesh itself
        np.testing.assert_array_equal(part.points, corners)
        return
    own = triangles[reached].ravel()
    np.testing.assert_array_equal(
        part.points, corners[own]
    )  # no corner it doesn't draw
    np.testing.assert_array_equal(
        part.points[part.triangles].reshape(-1, 3), corners[own]
    )
    np.testing.assert_array_equal(part.paint.fill, rows[own])
    box = part.boundary_box()
    if reached:
        assert box is not None
        drawn = corners[own]
        np.testing.assert_array_equal(box, [drawn.min(axis=0), drawn.max(axis=0)])


def test_shown_keys_label_their_values_however_added() -> None:
    shown = m.VDict([("s", m.Square())], show_keys=True)
    shown.add([("c", m.Circle())])
    shown["r"] = m.Rectangle()
    for key in ("s", "c", "r"):
        value = shown[key]
        (label,) = value.submobjects
        assert isinstance(label, m.Tex)
        assert label.tex_string == key
        assert label.get_right()[0] < value.points[:, 0].min()
    assert not m.VDict([("s", m.Square())])["s"].submobjects

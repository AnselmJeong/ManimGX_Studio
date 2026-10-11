"""Colors are read, written and mixed as their docstrings say.

- A color reads every form it documents: hex strings of 3, 4, 6 or 8 digits after `#` or
  `0x`, names in any case, integers, three or four numbers (from 0 to 1 if all are floats,
  from 0 to 255 otherwise); anything else is an error, a malformed hex string too.
- Written as hex and read back, a color is itself, to the 8 bits a digit pair holds.
- Colors mix in OKLab, weighted by opacity: exactly the ends at 0 and 1, symmetric, in the
  gamut, and a transparent end does not tint the mix. A gradient runs from its first color to
  its last, a colorscale holds its ends and hits its stops.
- The conversions are inverse: OKLab, HSV, HSL, and inverting a color.


A paint is a value: how a mobject is painted, changed only into a new paint.

- It never changes: its fields cannot be set, its brush arrays cannot be written; `updated`
  writes one brush. A number it holds, given again (another object, of another type, equal),
  is no change: the paint itself (an updater setting an unchanged width made a new paint, and
  a new film record, every frame).
- Mixed at its ends, a paint is exactly its ends (no brush left mid-tween); in between, its
  brushes read as their colors mixed; its widths never go below 0, however far past its ends an
  overshooting rate function takes it; what both ends share it keeps as it is.
- Aligned, two paints have as many rows per brush; a reveal's window runs over the curves by
  length when the paint has a pace.
- What a paint remembers is invisible, whatever the history of its derivations (`but`,
  `updated`, `aligned`, `mixed`, textures), whatever a caller hands it (fresh arrays,
  read-only ones, views of its own brushes, lists, integer colors and their float twins,
  array subclasses), and however often ids are taken again: each derivation is the one a
  paint that remembers nothing makes, with every color parsed afresh; a change that changes
  nothing (arrays, colors or numbers equal to those it holds, an equal width of another type
  too) is the paint itself; a texture is the very object given; a paint let go of is
  collected unless a live paint remembers it, and once everything is let go of and the
  memos are cleared, everything is.
"""

import colorsys
import gc
import weakref
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import numpy as np
import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule
from tests.strategies import colors, paints, rgbs
from tests.strategies import rgbas as rgba_values

import manimgx as m
from manimgx import caches
from manimgx.caches import Memo
from manimgx.drawing import paint as color
from manimgx.drawing.paint import Paint, ParsableManimColor


class TestParse:
    @pytest.mark.parametrize(
        ("value", "rgba"),
        [
            ("#FC6255", (0xFC, 0x62, 0x55, 0xFF)),
            ("#fc6255", (0xFC, 0x62, 0x55, 0xFF)),
            ("0xFC6255", (0xFC, 0x62, 0x55, 0xFF)),
            ("#F00", (0xFF, 0, 0, 0xFF)),
            ("#F008", (0xFF, 0, 0, 0x88)),
            ("#FC625580", (0xFC, 0x62, 0x55, 0x80)),
            ("blue", (0x58, 0xC4, 0xDD, 0xFF)),
            ("Blue_C", (0x58, 0xC4, 0xDD, 0xFF)),
            (0xFC6255, (0xFC, 0x62, 0x55, 0xFF)),
            ((1.0, 0.5, 0.0), (255, 127.5, 0, 255)),
            ((255, 128, 0), (255, 128, 0, 255)),
            ((1, 0.5, 0), (1, 0.5, 0, 255)),  # not all floats: 0 to 255
            ((0.0, 0.0, 1.0, 0.25), (0, 0, 255, 63.75)),
            (None, (0, 0, 0, 255)),
        ],
    )
    def test_it_reads_every_documented_form(
        self, value: ParsableManimColor | None, rgba: tuple[float, ...]
    ) -> None:
        np.testing.assert_allclose(m.ManimColor(value).to_rgba() * 255, rgba)

    @pytest.mark.parametrize(
        "value",
        [
            "#12345",
            "#1234567",
            "#123456789",
            "0x12345",
            "#GGGGGG",
            "#",
            "#12",
            "nocolor",
            "0x",
        ],
    )
    def test_anything_else_is_an_error(self, value: str) -> None:
        with pytest.raises(ValueError, match=r"not a hex color|not found"):
            m.ManimColor(value)

    @given(rgba=rgba_values)
    def test_written_as_hex_and_read_back_it_is_itself(self, rgba: np.ndarray) -> None:
        c = m.ManimColor(tuple(float(x) for x in rgba))
        np.testing.assert_allclose(
            m.ManimColor(c.to_hex(with_alpha=True)).to_rgba(),
            c.to_rgba(),
            atol=0.5 / 255,
        )
        assert str(c) == c.to_hex(with_alpha=True) or c.to_rgba()[3] > 254.5 / 255

    @given(rgba=rgba_values, alpha=st.floats(0, 1))
    def test_an_opacity_given_apart_is_kept(
        self, rgba: np.ndarray, alpha: float
    ) -> None:
        c = m.ManimColor(tuple(float(x) for x in rgba[:3]), alpha)
        assert c.to_rgba()[3] == alpha
        assert m.ManimColor(c.to_hex(), alpha).to_rgba()[3] == alpha


class TestMix:
    @given(a=rgba_values, b=rgba_values)
    def test_its_ends_are_exact(self, a: np.ndarray, b: np.ndarray) -> None:
        np.testing.assert_array_equal(color.mix_rgba(a, b, 0.0), a)
        np.testing.assert_array_equal(color.mix_rgba(a, b, 1.0), b)

    @given(a=rgba_values, b=rgba_values, t=st.floats(0, 1))
    @example(a=np.full(4, 0.04045), b=np.zeros(4), t=2.225073858507203e-309)
    def test_it_is_symmetric_and_in_the_gamut(
        self, a: np.ndarray, b: np.ndarray, t: float
    ) -> None:
        mixed = color.mix_rgba(a, b, t)
        reverse = color.mix_rgba(b, a, 1 - t)
        # Tiny t can round 1-t to an endpoint; only the other RGB takes the
        # sRGB round trip, whose rounded thresholds allow about 3e-8 RGB error.
        np.testing.assert_allclose(mixed[:3], reverse[:3], atol=1e-7)
        np.testing.assert_allclose(mixed[3], reverse[3], atol=1e-9)
        assert np.all((mixed >= 0) & (mixed <= 1))
        assert mixed[3] == pytest.approx((1 - t) * a[3] + t * b[3])

    @given(
        a=rgbs,
        b=rgbs,
        opacity=st.floats(0.01, 1),
        t=st.floats(0, 1, exclude_min=True, exclude_max=True),
    )
    def test_a_transparent_end_does_not_tint_it(
        self, a: np.ndarray, b: np.ndarray, opacity: float, t: float
    ) -> None:
        assume((1 - t) * opacity > 1e-9)  # below, the mix is unseen, and mixed straight
        mixed = color.mix_rgba(np.array([*a, opacity]), np.array([*b, 0.0]), t)
        np.testing.assert_allclose(mixed[:3], a, atol=1e-7)

    @given(
        rows=st.integers(1, 4).flatmap(lambda n: st.tuples(*[rgba_values] * n)),
        b=rgba_values,
        t=st.floats(0, 1),
    )
    def test_rows_mix_as_they_would_alone(
        self, rows: tuple[np.ndarray, ...], b: np.ndarray, t: float
    ) -> None:
        a = np.array(rows)
        together = color.mix_rgba(a, np.tile(b, (len(a), 1)), t)
        for row, mixed in zip(a, together, strict=True):
            np.testing.assert_allclose(mixed, color.mix_rgba(row, b, t), atol=1e-12)

    @given(x=rgbs)
    def test_oklab_is_inverse(self, x: np.ndarray) -> None:
        # to 1e-7: the sRGB curve's two standard thresholds are 3e-8 apart
        np.testing.assert_allclose(color.from_oklab(color.to_oklab(x)), x, atol=1e-7)


class TestGradients:
    @given(stops=st.lists(colors, min_size=1, max_size=5), n=st.integers(1, 30))
    def test_a_gradient_runs_from_its_first_color_to_its_last(
        self, stops: list[m.ManimColor], n: int
    ) -> None:
        out = m.color_gradient(stops, n)
        assert len(out) == n
        np.testing.assert_allclose(out[-1].to_rgba(), stops[-1].to_rgba(), atol=1e-12)
        if n > 1:
            np.testing.assert_allclose(out[0].to_rgba(), stops[0].to_rgba(), atol=1e-12)

    @given(
        stops=st.lists(colors, min_size=2, max_size=5),
        low=st.floats(-10, 10),
        width=st.floats(0.1, 10),
    )
    def test_a_colorscale_hits_its_stops_and_holds_its_ends(
        self, stops: list[m.ManimColor], low: float, width: float
    ) -> None:
        high = low + width
        pivots = np.linspace(low, high, len(stops))
        values = [low - 1, *pivots, high + 1]
        out = color.rgbas_by_value(stops, values, low, high)
        expected = [stops[0], *stops, stops[-1]]
        np.testing.assert_allclose(out, [c.to_rgba() for c in expected], atol=1e-9)

    @given(stops=st.lists(colors, min_size=2, max_size=4), value=st.floats(0, 1))
    def test_a_colorscale_mixes_as_colors_mix(
        self, stops: list[m.ManimColor], value: float
    ) -> None:
        (row,) = color.rgbas_by_value(stops, [value], 0, 1)
        position = value * (len(stops) - 1)
        i = min(int(position), len(stops) - 2)
        expected = color.mix_rgba(
            stops[i].to_rgba(), stops[i + 1].to_rgba(), position - i
        )
        np.testing.assert_allclose(row, expected, atol=1e-9)


class TestConversions:
    @given(c=colors)
    def test_inverting_twice_is_itself(self, c: m.ManimColor) -> None:
        np.testing.assert_allclose(
            c.invert().invert().to_rgba(), c.to_rgba(), atol=1e-12
        )

    @given(rgb=rgbs)
    def test_hsv_and_hsl_are_inverse(self, rgb: np.ndarray) -> None:
        c = m.ManimColor(tuple(float(x) for x in rgb))
        np.testing.assert_allclose(
            m.ManimColor.from_hsv(c.to_hsv()).to_rgb(), rgb, atol=1e-9
        )
        hue, lightness, saturation = colorsys.rgb_to_hls(*rgb)
        np.testing.assert_allclose(
            m.ManimColor.from_hsl((hue, saturation, lightness)).to_rgb(), rgb, atol=1e-9
        )

    @given(c=colors)
    def test_a_contrasting_color_stands_out(self, c: m.ManimColor) -> None:
        luma = 0.30 * c.to_rgb()[0] + 0.59 * c.to_rgb()[1] + 0.11 * c.to_rgb()[2]
        assume(abs(luma - 0.5) > 1e-6)
        assert c.contrasting() == (m.BLACK if luma > 0.5 else m.WHITE)


BRUSHES = ("fill", "stroke", "background")
NUMBERS: list[Callable[[int], object]] = [int, float, np.int64, np.float64]
"""Kinds of number a caller hands over: a float made anew is another object each time."""


def fields(paint: Paint) -> tuple[object, ...]:
    return tuple(
        (
            np.asarray(getattr(paint, name)).tobytes()
            if name in (*BRUSHES, "sheen_direction", "trim")
            else getattr(paint, name)
        )
        for name in (
            *BRUSHES,
            "stroke_width",
            "background_width",
            "sheen_factor",
            "sheen_direction",
            "trim",
            "dash",
        )
    )


class TestValue:
    @given(paint=paints)
    def test_it_never_changes(self, paint: Paint) -> None:
        with pytest.raises(AttributeError):
            paint.stroke_width = 3.0
        for name in BRUSHES:
            with pytest.raises(ValueError, match="read-only"):
                getattr(paint, name)[0, 0] = 0.5

    @given(
        paint=paints,
        name=st.sampled_from(["fill", "stroke"]),
        rgb=rgbs,
        opacity=st.floats(0, 1),
    )
    def test_updated_writes_one_brush(
        self, paint: Paint, name: str, rgb: np.ndarray, opacity: float
    ) -> None:
        c = m.ManimColor(tuple(float(x) for x in rgb))
        new = paint.updated(name, c, opacity)
        rows = getattr(new, name)
        np.testing.assert_allclose(
            rows[:, :3], np.broadcast_to(c.to_rgb(), rows[:, :3].shape)
        )
        np.testing.assert_allclose(rows[:, 3], opacity)
        other = "stroke" if name == "fill" else "fill"
        np.testing.assert_array_equal(getattr(new, other), getattr(paint, other))
        assert new.updated(name, c, opacity) is new  # nothing changes: itself

    @given(
        name=st.sampled_from(
            ["stroke_width", "background_width", "sheen_factor", "dash"]
        ),
        value=st.integers(0, 8),
        first=st.sampled_from(NUMBERS),
        again=st.sampled_from(NUMBERS),
    )
    def test_a_number_given_again_is_no_change(
        self,
        name: str,
        value: int,
        first: Callable[[int], object],
        again: Callable[[int], object],
    ) -> None:
        def handed(number: Callable[[int], object]) -> object:
            return (
                (number(value + 1), number(1), number(value))
                if name == "dash"
                else number(value)
            )

        paint = Paint().but(**{name: handed(first)})
        assert paint.but(**{name: handed(again)}) is paint


class TestMixed:
    @given(a=paints, b=paints)
    def test_at_its_ends_it_is_its_ends(self, a: Paint, b: Paint) -> None:
        a, b = Paint.aligned(a, b)
        for alpha, end in ((0.0, a), (1.0, b)):
            mixed = a.mixed(a, b, alpha)
            assert mixed.mix is None
            assert fields(mixed) == fields(end)

    @given(
        a=paints, b=paints, alpha=st.floats(0, 1, exclude_min=True, exclude_max=True)
    )
    def test_its_brushes_read_as_their_colors_mixed(
        self, a: Paint, b: Paint, alpha: float
    ) -> None:
        a, b = Paint.aligned(a, b)
        mixed = a.mixed(a, b, alpha)
        for name in BRUSHES:
            np.testing.assert_allclose(
                getattr(mixed, name),
                color.mix_rgba(getattr(a, name), getattr(b, name), alpha),
                atol=1e-12,
            )
        assert mixed.stroke_width == pytest.approx(
            (1 - alpha) * a.stroke_width + alpha * b.stroke_width
        )

    @given(a=paints, b=paints, alpha=st.floats(-1, 2))
    def test_no_width_goes_below_zero(self, a: Paint, b: Paint, alpha: float) -> None:
        mixed = a.mixed(a, b, alpha)
        assert mixed.stroke_width >= 0
        assert mixed.background_width >= 0

    @given(a=paints, width=st.floats(0, 8), alpha=st.floats(-1, 2))
    def test_what_both_ends_share_it_keeps_as_is(
        self, a: Paint, width: float, alpha: float
    ) -> None:
        # the compositor tells what a tween changed by identity: a field both ends share is
        # the very same object mixed
        b = a.but(stroke_width=width)
        mixed = a.mixed(a, b, alpha)
        for name in (
            "background_width",
            "sheen_factor",
            "sheen_direction",
            "trim",
            *BRUSHES,
        ):
            assert getattr(mixed, name) is getattr(a, name)


class TestAligned:
    @given(a=paints, b=paints)
    def test_both_get_as_many_rows_per_brush(self, a: Paint, b: Paint) -> None:
        a2, b2 = Paint.aligned(a, b)
        for name in BRUSHES:
            assert (
                len(getattr(a2, name))
                == len(getattr(b2, name))
                == max(len(getattr(a, name)), len(getattr(b, name)))
            )
            # stretched rows repeat the rows there were, in order
            assert {r.tobytes() for r in getattr(a2, name)} == {
                r.tobytes() for r in getattr(a, name)
            }


@given(low=st.floats(0, 1), high=st.floats(0, 1), curves=st.integers(1, 8))
def test_a_window_without_pace_runs_evenly_over_the_curves(
    low: float, high: float, curves: int
) -> None:
    paint = Paint().but(trim=np.array([low, high]))
    assert paint.window(curves) == (low * curves, high * curves)


# ── what a paint remembers ─────────────────────────────────────────────────────────────
def everything(paint: Paint) -> tuple[object, ...]:
    """What a paint shows, and what a tween left pending: its fields, its arrays' types and
    shapes, the brushes its mix holds and the ends each brush is drawn between (its own, or
    the mix's: left to the tween), and its texture, by identity."""
    arrays = tuple(
        (np.asarray(getattr(paint, name)).dtype.str, np.shape(getattr(paint, name)))
        for name in (*BRUSHES, "sheen_direction", "trim")
    )
    mix = (
        None
        if paint.mix is None
        else (*(x.tobytes() for x in (*paint.mix[0], *paint.mix[1])), paint.mix[2])
    )
    ends = tuple(b"".join(x.tobytes() for x in paint.ends(name)) for name in BRUSHES)
    return (*fields(paint), arrays, mix, ends, id(paint.texture))


def forgetful(paint: Paint) -> Paint:
    """The same paint, remembering nothing it derived."""
    replica = object.__new__(Paint)
    object.__setattr__(replica, "__dict__", {**paint.__dict__, "_derived": {}})
    return replica


@contextmanager
def cold() -> Iterator[None]:
    """Every color parsed afresh, inside."""
    held = color._PARSED
    color._PARSED = Memo(held.limit)
    try:
        yield
    finally:
        color._PARSED = held


class Brush(np.ndarray):
    """An array subclass, as a caller may hand one over."""


COLORS: list[ParsableManimColor | list[ParsableManimColor]] = [
    "#FF0000", m.RED, (0.0, 0.5, 1.0), [0, 128, 255],
    np.array([1, 0, 0], np.uint8), np.array([1.0, 0.0, 0.0], np.float32),
    [m.RED, m.BLUE], ["#00FF00", (1, 1, 1)],
]  # fmt: skip
TWINS: list[
    tuple[ParsableManimColor, ParsableManimColor]
] = [  # equal, not the same color
    ((1, 0, 0), (1.0, 0.0, 0.0)),
    ((0, 1, 1), (0.0, 1.0, 1.0)),
    ((1, 1, 0, 1), (1.0, 1.0, 0.0, 1.0)),
    (np.array([1, 0, 0], np.int64), np.array([1.0, 0.0, 0.0])),
]


class Derivations(RuleBasedStateMachine):
    """Paints derived from paints, with every kind of input, dropped and collected between."""

    @initialize()
    def begin(self) -> None:
        rows = np.linspace(0.05, 0.95, 400).reshape(100, 4)  # past 1,024 items: probed
        self.paints: list[tuple[Paint, tuple[object, ...]]] = []
        self.inputs: list[np.ndarray] = []
        self.watched: list[weakref.ref[object]] = []
        self.dropped: list[weakref.ref[Paint]] = []
        self.filler: list[np.ndarray] = []
        for paint in (Paint(), Paint().but(fill=rows)):
            self.keep(paint)

    def keep(self, paint: Paint) -> None:
        self.paints.append((paint, everything(paint)))
        self.watch(paint)

    def watch(self, thing: object) -> None:
        self.watched.append(weakref.ref(thing))

    def pick(self, i: int) -> Paint:
        return self.paints[i % len(self.paints)][0]

    def brush(self, kind: int, rows: int, source: Paint) -> object:
        """A brush as a caller hands it over."""
        values = np.linspace(0.05, 0.95, 4 * rows).reshape(rows, 4)
        own = source.fill
        return [
            lambda: values,  # fresh and writable
            lambda: values.copy(order="F").view(Brush),  # a subclass, another layout
            lambda: own[
                : max(1, min(rows, len(own)))
            ],  # a view of its own: a part, or all
            lambda: own.copy(),  # its own, equal
            lambda: own.tolist(),  # as a list
            lambda: (values * 255).astype(np.int64),  # integers
        ][kind]()

    @rule(i=st.integers(0, 99), kind=st.integers(0, 5), rows=st.integers(1, 3),
          readonly=st.booleans(), width=st.none() | st.sampled_from([0.0, 2.0]),
          number=st.sampled_from(["float", "numpy", "int"]), name=st.sampled_from(BRUSHES))  # fmt: skip
    def but(
        self,
        i: int,
        kind: int,
        rows: int,
        readonly: bool,
        width: float | None,
        number: str,
        name: str,
    ) -> None:
        paint = self.pick(i)
        value = self.brush(kind, rows, paint)
        if isinstance(value, np.ndarray):
            if readonly and value.flags.writeable and value.flags.owndata:
                value.flags.writeable = False
            self.inputs.append(value)
            self.watch(value)
        changes: dict[str, object] = {name: value}
        if width is not None:  # a number equal to one it may hold, not the same object
            changes["stroke_width"] = {
                "float": width + 0.0,
                "numpy": np.float64(width),
                "int": int(width),
            }[number]
        warm = paint.but(**changes)
        with cold():
            expected = forgetful(paint)._but(dict(changes))
        assert everything(warm) == everything(expected), "a remembered change differs"
        # nothing changes, the paint itself (what it is given is compared by value)
        if everything(expected) == everything(paint):
            assert warm is paint, "a change that changes nothing is a new paint"
        self.keep(warm)

    @rule(
        i=st.integers(0, 99),
        lengths=st.lists(st.integers(1, 4), min_size=2, max_size=8),
    )
    def slices(self, i: int, lengths: list[int]) -> None:
        """Its own brush sliced again and again, each slice let go of at once (freed ids are
        taken again)."""
        paint = self.pick(i)
        for k in lengths:
            warm = paint.but(fill=paint.fill[:k])
            with cold():
                expected = forgetful(paint)._but({"fill": paint.fill[:k]})
            assert everything(warm) == everything(expected), f"[:{k}] taken for another"

    @rule(i=st.integers(0, 99), name=st.sampled_from(["fill", "stroke"]),
          colored=st.sampled_from(COLORS), opacity=st.none() | st.sampled_from([0.0, 0.5, 1.0]))  # fmt: skip
    def updated(
        self,
        i: int,
        name: str,
        colored: ParsableManimColor | list[ParsableManimColor],
        opacity: float | None,
    ) -> None:
        paint = self.pick(i)
        warm = paint.updated(name, colored, opacity)
        with cold():
            expected = forgetful(paint)._updated(name, colored, opacity)
        assert everything(warm) == everything(expected), (
            f"{colored!r}: recolored otherwise"
        )
        if everything(expected) == everything(paint):
            assert warm is paint, "a recolor that changes nothing is a new paint"
        self.keep(warm)

    @rule(i=st.integers(0, 99), pair=st.sampled_from(TWINS),
          name=st.sampled_from(["fill", "stroke"]), opacity=st.sampled_from([None, 1, 1.0]))  # fmt: skip
    def twins(
        self,
        i: int,
        pair: tuple[ParsableManimColor, ParsableManimColor],
        name: str,
        opacity: float | None,
    ) -> None:
        """Colors equal under `==` that are not the same (integers count to 255), one after
        the other: each is itself, on a paint and on a mobject made with it."""
        paint = self.pick(i)
        for twin in pair:
            warm = paint.updated(name, twin, opacity)
            with cold():
                expected = forgetful(paint)._updated(name, twin, opacity)
            assert everything(warm) == everything(expected), (
                f"{twin!r} taken for its twin"
            )
            square = m.Square(fill_color=twin, fill_opacity=1)
            with cold():
                parsed = color._rgbas(twin, 1)
            np.testing.assert_array_equal(square.paint.fill, parsed)

    @rule(i=st.integers(0, 99), j=st.integers(0, 99), alpha=st.floats(-0.5, 1.5))
    def mixed(self, i: int, j: int, alpha: float) -> None:
        a, b = Paint.aligned(self.pick(i), self.pick(j))
        self.keep(Paint().mixed(a, b, alpha))

    @rule(i=st.integers(0, 99), writable=st.booleans(), same=st.booleans())
    def texture(self, i: int, writable: bool, same: bool) -> None:
        paint = self.pick(i)
        old = paint.texture
        if same and isinstance(old, np.ndarray):
            pixels = old  # the texture it holds, again
        else:
            pixels = np.zeros((2, 2, 4), np.uint8)
            pixels.flags.writeable = writable
            self.watch(pixels)
        changed = paint.but(texture=pixels)
        assert changed.texture is pixels, "a texture is the very object given"
        self.keep(changed)

    @rule(i=st.integers(0, 99))
    def change_an_input(self, i: int) -> None:
        if self.inputs:
            value = self.inputs[i % len(self.inputs)]
            if value.flags.writeable:
                value.reshape(-1)[0] = 1 - value.reshape(-1)[0]

    @rule(i=st.integers(0, 99))
    def let_go(self, i: int) -> None:
        if len(self.paints) > 2:
            paint, _ = self.paints.pop(i % len(self.paints))
            self.dropped.append(weakref.ref(paint))
            del paint
        if self.inputs:
            self.inputs.pop(i % len(self.inputs))
        gc.collect()
        live = [p for p, _ in self.paints]
        remembered: set[int] = set()  # what live paints remember deriving, and so on
        stack = list(live)
        while stack:
            for v in stack.pop()._derived.values():
                if isinstance(v, Paint) and id(v) not in remembered:
                    remembered.add(id(v))
                    stack.append(v)
        for ref in self.dropped:
            paint = ref()
            assert (
                paint is None
                or id(paint) in remembered
                or any(paint is q for q in live)
            )
        # arrays the size of those let go of take the freed blocks
        self.filler = [np.zeros((n, 4)) for n in (1, 2, 3, 100) for _ in range(4)]

    @invariant()
    def a_paint_is_a_value(self) -> None:
        for paint, seen in self.paints:
            assert everything(paint) == seen, "a paint changed after it was made"

    def teardown(self) -> None:
        self.paints, self.inputs, self.filler = [], [], []
        caches.clear()  # the bounded memos (OKLab by array, parsed colors) let go too
        gc.collect()
        alive = [type(ref()).__name__ for ref in self.watched if ref() is not None]
        assert not alive, f"let go of, still alive: {alive[:5]}"


TestDerivations = Derivations.TestCase
TestDerivations.settings = settings(max_examples=50, stateful_step_count=25)

"""A number spells its value, and set to a value it is the number made with it.

- Its characters are its value rounded to its places (half to even, on the value's exact
  binary digits, as decimal arithmetic rounds them: another algorithm than the formatting
  ManimGX uses; a displayed zero has no sign), grouped by commas and signed as asked, whether
  it was made with the value or set to it from another; a numpy scalar by its own value, an
  integer to a whole. A complex number spells each of its parts so, the second signed, and is
  written `a+bi`.
- Set to a value, a number is the number made with that value and with its attributes as they
  are now (its unit, its characters' class, its gaps, its ellipsis, its background), at the
  font size it has and with the edge it fixes where it was.
- A number's font size is positive.
- A variable shows its tracker's value in the number class it was asked for.
"""

from collections.abc import Callable
from decimal import ROUND_HALF_EVEN, Decimal

import numpy as np
import pytest
from hypothesis import example, given
from hypothesis import strategies as st

import manimgx as m
from manimgx.mobjects.numbers import DecimalNumberOptions


def spelled(value: float, places: int, sign: bool = False, commas: bool = False) -> str:
    """The value to its places, half to even on its exact binary digits, a zero unsigned."""
    rounded = Decimal(float(value)).quantize(
        Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN
    )
    if rounded == 0:
        rounded = abs(rounded)
    return f"{rounded:{'+' if sign else ''}{',' if commas else ''}.{places}f}"


def written[V: (float, complex)](number: m.DecimalNumber[V]) -> str:
    characters = []
    for part in number:
        assert isinstance(part, m.MathTex)
        characters.append(part.tex_string)
    return "".join(characters)


# (and the values a hair either side of a rounding: the hunt's regressions)
values = st.floats(-1e7, 1e7) | st.sampled_from([-0.005, -0.0005, -0.001, 0.005, 2.5])
SCALARS = [float, np.float64, np.float32, np.longdouble]


@given(
    value=values,
    before=values,
    places=st.integers(0, 4),
    sign=st.booleans(),
    commas=st.booleans(),
    scalar=st.sampled_from(SCALARS),
    whole=st.booleans(),
)
@example(
    value=-0.005, before=1, places=2, sign=False, commas=True, scalar=float, whole=False
)
@example(
    value=-0.005,
    before=1,
    places=2,
    sign=True,
    commas=True,
    scalar=np.float32,
    whole=False,
)
@example(
    value=-0.001, before=1, places=2, sign=True, commas=False, scalar=float, whole=False
)
@example(
    value=-1234.125,
    before=0,
    places=2,
    sign=False,
    commas=True,
    scalar=float,
    whole=False,
)
def test_a_number_spells_its_value(
    value: float,
    before: float,
    places: int,
    sign: bool,
    commas: bool,
    scalar: type[float],
    whole: bool,
) -> None:
    value = scalar(value)
    options: DecimalNumberOptions = {"include_sign": sign, "group_with_commas": commas}
    if whole:
        made = m.Integer(value, **options)
        places = 0
    else:
        made = m.DecimalNumber(value, **(options | {"num_decimal_places": places}))
    assert written(made) == spelled(value, places, sign, commas)
    assert made.get_value() == (round(value) if whole else value)
    made.set_value(before)
    made.set_value(value)  # (set to it from another)
    assert written(made) == spelled(value, places, sign, commas)


@given(
    real=values,
    imaginary=values,
    places=st.integers(0, 3),
    sign=st.booleans(),
    commas=st.booleans(),
    scalar=st.sampled_from([complex, np.complex64, np.complex128, np.clongdouble]),
)
@example(real=-0.0, imaginary=2, places=2, sign=False, commas=True, scalar=complex)
@example(
    real=-0.001, imaginary=-0.001, places=2, sign=False, commas=True, scalar=complex
)
@example(
    real=-0.005, imaginary=-0.005, places=2, sign=True, commas=True, scalar=complex
)
def test_a_complex_number_spells_each_part(
    real: float,
    imaginary: float,
    places: int,
    sign: bool,
    commas: bool,
    scalar: Callable[[complex], complex],
) -> None:
    value = scalar(complex(real, imaginary))
    number = m.DecimalNumber(
        value,
        num_decimal_places=places,
        include_sign=sign,
        group_with_commas=commas,
    )
    parts = spelled(value.real, places, sign, commas) + spelled(
        value.imag, places, True, commas
    )
    assert written(number) == parts + "i"


LAYOUTS: dict[str, DecimalNumberOptions] = {
    "plain": {},
    "with a unit": {"unit": "m"},
    "with a superscript unit": {"unit": "^2"},
    "of text": {"mob_class": m.Text},
    "spaced": {"digit_buff_per_font_unit": 0.015},
    "with a spaced unit": {"unit": "m", "unit_buff_per_font_unit": 0.025},
    "with an ellipsis": {"show_ellipsis": True},
    "on a background": {"include_background_rectangle": True},
}
PLAIN: DecimalNumberOptions = {
    "unit": None,
    "mob_class": m.MathTex,
    "digit_buff_per_font_unit": 0.001,
    "unit_buff_per_font_unit": 0,
    "show_ellipsis": False,
    "include_background_rectangle": False,
}


@given(
    before=st.sampled_from(sorted(LAYOUTS)),
    after=st.sampled_from(sorted(LAYOUTS)),
    first=st.sampled_from([7.125, -3, 82.5]),
    value=st.sampled_from([7.125, -3, 1234.5]),
    scale=st.floats(0.5, 2),
    shift=st.sampled_from([m.ORIGIN, m.UP, 2 * m.LEFT + m.DOWN]),
    edge=st.sampled_from([m.LEFT, m.RIGHT, m.DOWN]),
)
def test_a_number_set_to_a_value_is_the_one_made_with_it_where_it_was(
    before: str,
    after: str,
    first: float,
    value: float,
    scale: float,
    shift: np.ndarray,
    edge: np.ndarray,
) -> None:
    look: DecimalNumberOptions = {"edge_to_fix": edge, "color": m.RED}
    number = m.DecimalNumber(first, **(LAYOUTS[before] | look))
    number.scale(scale).shift(shift).set_value(first)  # (set, and left as it was)
    for name, setting in (PLAIN | LAYOUTS[after]).items():
        setattr(number, name, setting)
    fixed, size = number.get_critical_point(edge), number.font_size
    number.set_value(value)
    made = m.DecimalNumber(value, **(LAYOUTS[after] | look))
    made.font_size = size
    made.move_to(fixed, edge)
    parts, wanted = number.get_family(), made.get_family()
    assert [type(part) for part in parts] == [type(part) for part in wanted]
    for part, like in zip(parts, wanted, strict=True):
        np.testing.assert_allclose(part.points, like.points, atol=1e-9)
        np.testing.assert_array_equal(part.paint.fill, like.paint.fill)
        np.testing.assert_array_equal(part.paint.stroke, like.paint.stroke)


@pytest.mark.parametrize("font_size", [0, -1])
def test_numbers_require_positive_font_sizes(font_size: float) -> None:
    with pytest.raises(ValueError, match="font_size"):
        m.DecimalNumber(7, font_size=font_size)


class _Decimal(m.DecimalNumber):
    pass


class _Integer(m.Integer):
    pass


@pytest.mark.parametrize("kind", [m.DecimalNumber, m.Integer, _Decimal, _Integer])
def test_a_variable_shows_its_tracker_in_the_number_class_asked_for(
    kind: type[m.DecimalNumber],
) -> None:
    variable = m.Variable(1.125, "x", var_type=kind, num_decimal_places=3)
    assert type(variable.value) is kind
    places = 0 if issubclass(kind, m.Integer) else 3  # (an integer has no places)
    assert variable.value.num_decimal_places == places
    assert written(variable.value) == spelled(1.125, places)
    variable.tracker.set_value(2.875)
    variable.update()
    assert variable.value.number == 2.875
    assert written(variable.value) == spelled(2.875, places)


@pytest.mark.parametrize("targeted", [False, True])
def test_complex_number_animations_preserve_both_components(targeted: bool) -> None:
    start, target = 1 + 2j, -3 + 4j
    number = m.DecimalNumber(start, num_decimal_places=3)

    def value(alpha: float) -> complex:
        return start + (target - start) * (alpha if targeted else alpha**2)

    animation = (
        m.ChangeDecimalToValue(number, target, rate_func=m.linear)
        if targeted
        else m.ChangingDecimal(number, value, rate_func=m.linear)
    )
    animation.begin()
    for alpha in (0, 0.75, 0.25, 1):
        animation.interpolate(alpha)
        expected = value(alpha)
        assert number.get_value() == expected
        assert (
            written(number)
            == spelled(expected.real, 3) + spelled(expected.imag, 3, sign=True) + "i"
        )
    animation.finish()

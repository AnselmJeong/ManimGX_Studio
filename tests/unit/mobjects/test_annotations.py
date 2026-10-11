"""A rectangle surrounding mobjects is their box grown by its buffer on each side, at their
center."""

import numpy as np
from hypothesis import given
from hypothesis import strategies as st
from tests.strategies import drawn

import manimgx as m


@given(
    targets=st.lists(drawn, min_size=1, max_size=2),
    buff=st.floats(0, 1) | st.tuples(st.floats(0, 1), st.floats(0, 1)),
)
def test_a_surrounding_rectangle_is_the_box_grown_by_its_buffer(
    targets: list[m.Mobject], buff: float | tuple[float, float]
) -> None:
    box = m.Group(*targets).boundary_box()
    assert box is not None
    grown = np.array(buff if isinstance(buff, tuple) else (buff, buff))
    rectangle = m.SurroundingRectangle(*targets, buff=buff)
    tolerance = 1e-9 * (1 + np.abs(box).max())
    np.testing.assert_allclose(
        rectangle.get_corner(m.DL)[:2], box[0, :2] - grown, atol=tolerance
    )
    np.testing.assert_allclose(
        rectangle.get_corner(m.UR)[:2], box[1, :2] + grown, atol=tolerance
    )
    np.testing.assert_allclose(rectangle.get_center(), box.mean(axis=0), atol=tolerance)

"""A visual oracle compares complete films, regardless of how holds are grouped."""

from itertools import groupby

import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.integration.corpus.frozen import Comparison, Difference


class Film:
    size = (1, 1)
    fps = 10.0

    def __init__(self, pixels: list[int], *, grouped: bool = True) -> None:
        self.pixels = pixels
        self.frames = len(pixels)
        self.timeline: list[tuple[int, int]] = []
        self.drawn: list[int] = []
        first = 0
        for _, group in groupby(pixels):
            repeat = len(list(group))
            self.timeline.extend(
                [(first, repeat)]
                if grouped
                else [(first + offset, 1) for offset in range(repeat)]
            )
            first += repeat

    def render(self, frame: int) -> bytes:
        self.drawn.append(frame)
        return bytes((self.pixels[frame], 0, 0, 255))


@given(
    pairs=st.lists(st.tuples(st.integers(0, 3), st.integers(0, 3)), max_size=50),
    grouped=st.booleans(),
)
def test_every_frame_is_compared_across_independent_hold_boundaries(
    pairs: list[tuple[int, int]], grouped: bool
) -> None:
    expected = Film([old for old, _ in pairs], grouped=grouped)
    actual = Film([new for _, new in pairs], grouped=not grouped)
    differences: list[Difference] = []
    comparison = Comparison(
        expected, lambda difference, _old, _new: differences.append(difference)
    )
    for index, repeat in actual.timeline:
        comparison.add(index, repeat, bytes((actual.pixels[index], 0, 0)))
    comparison.finish(actual.frames)
    assert comparison.changed_frames == sum(old != new for old, new in pairs)
    expanded = {
        frame: (difference.changed_pixels, difference.max_channel_difference)
        for difference in differences
        for frame in range(difference.first, difference.first + difference.repeat)
    }
    assert expanded == {
        index: (1, abs(old - new))
        for index, (old, new) in enumerate(pairs)
        if old != new
    }
    assert expected.drawn == [index for index, _ in expected.timeline]


@pytest.mark.parametrize(
    ("index", "repeat"), [(1, 1), (-1, 1), (0, 0), (0, -1), (0, 3)]
)
def test_gaps_overlaps_and_nonpositive_or_excess_holds_fail(
    index: int, repeat: int
) -> None:
    comparison = Comparison(Film([0, 0]), lambda *_: None)
    with pytest.raises(ValueError, match=r"timeline|more frames"):
        comparison.add(index, repeat, bytes(3))


def test_a_repeated_callback_cannot_hide_a_missing_frame() -> None:
    comparison = Comparison(Film([0, 0]), lambda *_: None)
    comparison.add(0, 1, bytes(3))
    with pytest.raises(ValueError, match="timeline"):
        comparison.add(0, 1, bytes(3))


@pytest.mark.parametrize("reported", [0, 1, 2, 3])
def test_incomplete_callbacks_fail_even_when_film_count_matches(reported: int) -> None:
    comparison = Comparison(Film([0, 0]), lambda *_: None)
    comparison.add(0, 1, bytes(3))
    with pytest.raises(ValueError, match="frame coverage"):
        comparison.finish(reported)


@pytest.mark.parametrize("timeline", [[(1, 2)], [(0, 0)], [(0, 1), (0, 1)], [(0, 1)]])
def test_a_malformed_reference_timeline_is_rejected(
    timeline: list[tuple[int, int]],
) -> None:
    reference = Film([0, 0])
    reference.timeline = timeline
    with pytest.raises(ValueError, match="reference timeline"):
        Comparison(reference, lambda *_: None)


def test_pixel_dimensions_are_checked_before_comparing() -> None:
    comparison = Comparison(Film([0]), lambda *_: None)
    with pytest.raises(ValueError, match="image size"):
        comparison.add(0, 1, bytes(4))

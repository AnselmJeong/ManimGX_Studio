"""ManimGX's window: a process of its own, which plays the takes it is sent and closes when its
director closes it; a film sent to a closed window is cut. It needs a screen: on a Linux
without a display these are skipped; anywhere else, a window that cannot open is a failure.
"""

import os
import sys
from collections.abc import Iterator

import pytest

import manimgx as m
from manimgx.rendering.window import Window


class Held(m.Scene):
    def construct(self) -> None:
        square = m.Square()
        self.play(m.Create(square))
        self.play(square.animate.shift(m.RIGHT))
        self.wait()


pytestmark = pytest.mark.config(pixel_width=320, pixel_height=180, frame_rate=30)


@pytest.fixture
def window() -> Iterator[Window]:
    """A window, open (or the test skipped: there is no screen here)."""
    linux = sys.platform.startswith("linux")
    if linux and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        pytest.skip("no display to open a window on")
    with Window("test_window.py") as opened:
        assert not opened.wait(timeout=1.0), (
            f"the window did not open: {opened.failure}"
        )
        yield opened


def test_a_window_plays_what_it_is_sent_and_closes_with_its_director(
    window: Window,
) -> None:
    film = Held().render(take=window)
    assert film.frame_count
    assert window.open
    window.close()
    assert not window.open
    assert window.failure is None


def test_a_film_sent_to_a_closed_window_is_cut(window: Window) -> None:
    whole = Held().render().frame_count
    window.close()
    film = Held().render(take=window)
    assert film.frame_count < whole

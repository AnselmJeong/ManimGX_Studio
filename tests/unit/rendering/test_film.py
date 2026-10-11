"""A film is a row of sections, each beginning at a frame; its captions are those the scene added
and those of its speech, in order.

- A section begins at a frame: after a play that ends between frames, the world holds still
  until the next one (and nothing moves meanwhile), whatever the frame rate. A section with no
  frame gives way to the next; the first begins with the film.
- A section's first frame is sent alone, never merged into the hold before it, as a key.
- Subtitles are the captions in SubRip form, numbered, their times to the millisecond.
"""

from collections.abc import Callable
from fractions import Fraction

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import manimgx as m
from manimgx.audio import Speech, Word
from manimgx.audio.sound import RATE
from manimgx.config import config
from manimgx.rendering.film import Frame


def film_of(
    story: Callable[[m.Scene], None],
    fps: float = 10,
    frames: list[Frame] | None = None,
) -> m.Film:
    class Made(m.Scene):
        def construct(self) -> None:
            story(self)

    saved = config.frame_rate
    config.frame_rate = fps
    try:
        return Made().render(frames=None if frames is None else frames.append)
    finally:
        config.frame_rate = saved


class TestSections:
    @settings(max_examples=30)
    @given(
        run_time=st.sampled_from([0.25, 0.55, 1.0, 1.37]),
        fps=st.sampled_from([10, 24, 30, 60]),
    )
    def test_a_section_begins_at_a_frame(self, run_time: float, fps: int) -> None:
        def construct(self: m.Scene) -> None:
            self.play(m.FadeIn(m.Dot()), run_time=run_time)
            self.next_section("next", notes="go on")
            self.play(m.FadeOut(m.Dot()))

        film = film_of(construct, fps)
        first, section = film.sections
        assert (first.name, first.start, first.frame) == ("unnamed", 0, 0)
        assert section.start == Fraction(section.frame, fps)
        assert section.start >= Fraction(run_time).limit_denominator(10**6)
        assert section.start - Fraction(run_time).limit_denominator(10**6) < Fraction(
            1, fps
        )
        assert (section.name, section.notes, section.type) == (
            "next",
            "go on",
            "default.normal",
        )

    def test_the_world_holds_until_the_section_begins(self) -> None:
        dot = m.Dot()

        def construct(self: m.Scene) -> None:
            dot.add_updater(lambda d, dt: d.shift(dt * m.RIGHT))
            self.add(dot)
            self.wait(0.55)
            self.next_section()

        film_of(construct, 10)
        assert dot.get_x() == pytest.approx(
            0.55
        )  # it did not move between 0.55 and 0.6

    def test_a_section_with_no_frame_gives_way(self) -> None:
        def construct(self: m.Scene) -> None:
            self.next_section("a")
            self.next_section("b", "presentation.loop")
            self.play(m.FadeIn(m.Dot()))

        film = film_of(construct)
        assert [(s.name, s.frame, s.type) for s in film.sections] == [
            ("b", 0, "presentation.loop")
        ]

    def test_a_section_begins_with_a_key_frame_of_its_own(self) -> None:
        sent: list[Frame] = []

        def construct(self: m.Scene) -> None:
            self.add(m.Square())
            self.wait(1)  # one hold across the boundary, unless split
            self.next_section("still")
            self.wait(1)

        film = film_of(construct, 10, sent)
        _, still = film.sections
        keys = [f.index for f in sent if f.key]
        assert keys == [still.frame] == [10]


class TestCaptions:
    def test_captions_are_added_and_spoken_in_order(self) -> None:
        speech = Speech(
            np.full(RATE, 0.1, np.float32),
            text="Hello there.",
            words=[Word("Hello", 0.1, 0.4), Word("there.", 0.5, 0.9)],
            rate=RATE,
        )

        def construct(self: m.Scene) -> None:
            self.add_subcaption("first", duration=0.5)
            self.wait(1)
            self.add_sound(speech)
            self.wait(1)

        film = film_of(construct)
        assert [(c.start, c.end, c.text) for c in film.captions()] == [
            (0.0, 0.5, "first"),
            (pytest.approx(1.1), pytest.approx(1.9), "Hello there."),
        ]
        assert film.subtitles().startswith(
            "1\n00:00:00,000 --> 00:00:00,500\nfirst\n\n2\n00:00:01,100 -->"
            " 00:00:01,900\n"
        )
        assert film_of(lambda self: self.wait(1)).subtitles() == ""  # none, nothing

    def test_the_end_cuts_what_still_sounds(self) -> None:
        long = m.Sound(np.zeros(3 * RATE, np.float32), rate=RATE)

        def story(self: m.Scene) -> None:
            self.add_sound(long)
            self.wait(1)

        film = film_of(story)
        ((clip, lost),) = film.cut()
        assert clip.sound is long
        assert lost == pytest.approx(3 - film.frame_count / 10)

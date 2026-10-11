"""A take's timeline names each play as the code wrote it: a said line as what it says, with the
animations it plays (not the waits that time them), a sound by its length."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import manimgx as m
from manimgx.audio import Speech, Word
from manimgx.audio.sound import RATE
from manimgx.cli.storyboard import Sheets, describe


def test_an_animate_chain_names_its_methods_in_order() -> None:
    animation = m.Square().animate.shift(m.RIGHT).rotate(m.PI).set_color(m.RED)
    assert describe(animation) == "Square.animate.shift(…).rotate(…).set_color(…)"


def test_a_said_line_is_named_by_its_words_and_its_animations() -> None:
    speech = Speech(
        np.zeros(RATE, np.float32),
        text="Here is a dot.",
        words=[
            Word("Here", 0, 0.1),
            Word("is", 0.2, 0.3),
            Word("a", 0.4, 0.5),
            Word("dot.", 0.5, 0.9),
        ],
        rate=RATE,
    )
    line = m.AnimationGroup(speech, m.Succession(m.Wait(0.4), m.FadeIn(m.Dot())))
    assert describe(line) == "say 'Here is a dot.' with FadeIn(Dot)"


def test_a_sound_is_named_by_its_length() -> None:
    assert (
        describe(m.Sound(np.zeros(RATE // 2, np.float32), rate=RATE)) == "sound 0.5 s"
    )


def test_a_failed_sheet_write_closes_the_writer(tmp_path: Path) -> None:
    sheets = Sheets(tmp_path / "missing" / "storyboard.png")
    sheets.add("a frame", Image.new("RGB", (2, 2)))
    try:
        with pytest.raises(FileNotFoundError):
            sheets.close()
        with pytest.raises(RuntimeError, match="after shutdown"):
            sheets._writer.submit(lambda: None)
    finally:
        sheets._writer.shutdown()

"""The README's films as SVGs (`docs/svg.py`) have no background, so the page's shows
through, and a light page's variant draws the scene's white ink in the page's, leaving its
colors as they are."""

from pathlib import Path

from docs import svg

import manimgx as m


class Ink(m.Scene):
    def construct(self) -> None:
        title = m.Square(2, color=m.WHITE, fill_opacity=1)  # white ink, as a title is
        ring = m.Circle(1.5, color="#ffc94a").shift(3 * m.RIGHT)  # a color
        self.play(m.Create(ring), m.FadeIn(title), run_time=0.5)


def test_no_background_and_white_ink_dark_on_a_light_page(tmp_path: Path) -> None:
    recording = svg.record(Ink)
    dark, light = tmp_path / "dark.svg", tmp_path / "light.svg"
    svg.write(recording, dark)
    svg.write(recording, light, light=True)
    on_dark, on_light = (
        dark.read_text(encoding="utf-8"),
        light.read_text(encoding="utf-8"),
    )
    for text in (on_dark, on_light):
        assert "<rect" not in text  # nothing under the scene
        assert "#FFC94A" in text  # the color stays
    assert "#FFFFFF" in on_dark
    assert svg.INK not in on_dark
    assert svg.INK in on_light
    assert "#FFFFFF" not in on_light

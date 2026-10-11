"""A film's hooks: each frame handed over as it is sent, and `Cut`, which ends the film wherever
a hook raises it — at its last frame too, which is sent only when the film closes."""

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import manimgx as m
from manimgx.config import config
from manimgx.rendering.film import Cut, Frame, X264Preset


class Held(m.Scene):
    def construct(self) -> None:
        self.play(m.Create(m.Square()))
        self.wait()  # the last frames: one held frame, sent when the film closes


pytestmark = pytest.mark.config(pixel_width=320, pixel_height=180)


def at_the_last(error: Exception) -> tuple[list[Frame], Callable[[Frame], None]]:
    """A frame sink that raises `error` at the held frame that ends the film."""
    sent: list[Frame] = []

    def sink(frame: Frame) -> None:
        sent.append(frame)
        if frame.repeat > 1:
            raise error

    return sent, sink


def test_a_cut_at_the_last_frame_keeps_the_film(tmp_path: Path) -> None:
    sent, sink = at_the_last(Cut())
    film = Held().render(tmp_path / "held.mp4", preset="medium", crf=23, frames=sink)
    assert sent[-1].index + sent[-1].repeat == film.frame_count
    assert (tmp_path / "held.mp4").stat().st_size > 0


def test_an_error_at_the_last_frame_abandons_the_video(tmp_path: Path) -> None:
    _, sink = at_the_last(ValueError("the sink failed"))
    with pytest.raises(ValueError, match="the sink failed"):
        Held().render(tmp_path / "held.mp4", frames=sink)
    assert list(tmp_path.iterdir()) == []  # not the video, nor a part of it


def test_a_soundtrack_error_closes_the_native_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failed_soundtrack(self: m.Film) -> None:
        raise ValueError("the soundtrack failed")

    monkeypatch.setattr(m.Film, "soundtrack", failed_soundtrack)
    scene = Held()
    try:
        with pytest.raises(ValueError, match="the soundtrack failed"):
            scene.render(tmp_path / "failed.mp4")
        player = scene.film._player
        assert player is not None
        # Retain the scene and player: cleanup must not depend on garbage collection.
        player.begin_export(str(tmp_path / "next.mp4"))
        player.abort_export()
        assert list(tmp_path.iterdir()) == []
    finally:
        if (player := scene.film._player) is not None:
            player.abort_export()


def test_a_video_needs_even_sides(tmp_path: Path) -> None:
    config.pixel_width = 321  # H.264's 4:2:0 halves both sides
    with pytest.raises(ValueError, match="an even width and height, not 321x180"):
        Held().render(tmp_path / "odd.mp4")


def test_an_unknown_encoder_preset_fails_before_writing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown x264 preset"):
        Held().render(tmp_path / "bad.mp4", preset=cast(X264Preset, "unknown"))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("crf", [-0.1, 51.1, float("nan"), float("inf")])
def test_an_invalid_crf_fails_before_writing(tmp_path: Path, crf: float) -> None:
    with pytest.raises(
        ValueError, match="x264 CRF must be a finite number from 0 to 51"
    ):
        Held().render(tmp_path / "bad.mp4", crf=crf)
    assert list(tmp_path.iterdir()) == []

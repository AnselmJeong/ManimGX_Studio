"""All export entry points pass shared defaults and explicit overrides to the encoder."""

from pathlib import Path
from typing import TypedDict

import pytest
from typer import Exit
from typer.testing import CliRunner

import manimgx as m
from manimgx import _engine
from manimgx.cli import app
from manimgx.cli.scenes import Format, take
from manimgx.rendering import feed
from manimgx.rendering.film import X264Preset


class Options(TypedDict, total=False):
    preset: X264Preset
    crf: float


class EncoderReached(Exception):
    """Stop before the native encoder or GPU does any work."""


@pytest.mark.parametrize("entry", ["film", "scene", "take", "cli"])
@pytest.mark.parametrize("override", [False, True])
def test_export_settings_reach_the_encoder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str, override: bool
) -> None:
    received: list[tuple[str, float]] = []

    class Player:
        def __init__(self, width: int, height: int) -> None:
            pass

        def begin_export(self, path: str, *, fps: int, preset: str, crf: float) -> None:
            received.append((preset, crf))
            raise EncoderReached

    monkeypatch.setattr(feed, "Player", Player)
    monkeypatch.setattr(_engine, "start_gpu", lambda: None)
    options: Options = {"preset": "slow", "crf": 31.0} if override else {}
    video = tmp_path / "out.mp4"
    if entry == "cli":
        source = tmp_path / "encoding_scene.py"
        source.write_text(
            "import manimgx as m\nclass EncodingScene(m.Scene):\n"
            "    def construct(self):\n        pass\n",
            encoding="utf-8",
        )
        flags = ["--preset", "slow", "--crf", "31"] if override else []
        result = CliRunner().invoke(
            app, ["render", str(source), "-o", str(video), *flags]
        )
        assert result.exit_code == 1
    elif entry == "film":
        with pytest.raises(EncoderReached):
            m.Film(video, **options)
    elif entry == "scene":
        with pytest.raises(EncoderReached):
            m.Scene().render(video, **options)
    else:
        with pytest.raises(Exit):
            take(m.Scene, Format.own(None, None), video=video, **options)
    assert received == [("slow", 31.0) if override else ("medium", 23.0)]
    assert not video.exists()

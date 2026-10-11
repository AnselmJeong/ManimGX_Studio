"""Inspection selects and captions the same observed frame that the film shows."""

import math
import sys
from pathlib import Path

import pytest
import typer
from PIL import Image

from manimgx.cli import export
from manimgx.cli.export import inspect
from manimgx.cli.storyboard import Sheets


def test_inspections_distinguish_adjacent_times_and_finish_coincident_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "still_boundary.py"
    source.write_text(
        "import manimgx as m\n"
        "m.config.pixel_width = m.config.pixel_height = 16\n"
        "m.config.frame_rate = 10\n"
        "class Only(m.Scene):\n"
        "    def construct(self):\n"
        "        self.camera.background_color = m.RED\n"
        "        self.wait(0.1)\n"
        "        self.camera.background_color = m.BLUE\n"
        "        self.wait(1e-18)\n"
        "        self.wait(0.1)\n",
        encoding="utf-8",
    )
    captions: list[str] = []
    pictures: list[bytes] = []

    def keep(sheet: Sheets, text: str, picture: Image.Image) -> None:
        captions.append(text)
        pictures.append(picture.tobytes())

    monkeypatch.setattr(Sheets, "add", keep)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    try:
        inspect(
            source,
            time=[
                str(math.nextafter(0.1, 0)),
                "0.1",
                str(math.nextafter(0.1, math.inf)),
            ],
            output=tmp_path / "still.png",
        )
    finally:
        sys.modules.pop(source.stem, None)
    assert pictures[0] != pictures[1] == pictures[2]
    assert captions[0].startswith("#0 ")
    assert all(caption.startswith("#2 ") for caption in captions[1:])


def test_a_scene_error_finishes_its_storyboard_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "broken_scene.py"
    source.write_text(
        "import manimgx as m\n"
        "m.config.pixel_width = m.config.pixel_height = 16\n"
        "class Only(m.Scene):\n"
        "    def construct(self):\n"
        "        self.wait(0.1)\n"
        "        raise ValueError('scene failed')\n",
        encoding="utf-8",
    )
    sheets = Sheets(tmp_path / "partial.png")
    monkeypatch.setattr(export, "Sheets", lambda _: sheets)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    try:
        with pytest.raises(typer.Exit):
            export.render(source)
        assert sheets.written == [tmp_path / "partial.png"]
        assert sheets.written[0].is_file()
        with pytest.raises(RuntimeError, match="after shutdown"):
            sheets._writer.submit(lambda: None)
    finally:
        sheets._writer.shutdown()
        sys.modules.pop(source.stem, None)

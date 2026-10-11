"""Inspection uses the video's scene state, with the same checks at default and chosen times."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from typer.testing import CliRunner

from manimgx.cli import app
from manimgx.cli.scenes import scene
from manimgx.cli.storyboard import CAPTION, GAP, tile
from manimgx.rendering.film import Frame


def source(tmp_path: Path, body: str, base: str = "Scene") -> Path:
    path = tmp_path / "scene.py"
    path.write_text(
        "import manimgx as m\n"
        "m.config.pixel_width, m.config.pixel_height = 320, 180\n"
        "m.config.frame_rate = 10\n"
        f"class Example(m.{base}):\n"
        "    def construct(self) -> None:\n"
        + "\n".join(f"        {line}" for line in body.splitlines())
        + "\n",
        encoding="utf-8",
    )
    return path


def test_selected_times_check_the_picture_during_the_animation(tmp_path: Path) -> None:
    path = source(
        tmp_path,
        'moving = m.Text("moving").shift(4 * m.LEFT)\n'
        'fixed = m.Text("fixed")\n'
        "self.add(moving, fixed)\n"
        "self.play(moving.animate.shift(8 * m.RIGHT), run_time=2, rate_func=m.linear)",
    )
    runner = CliRunner()
    default = runner.invoke(app, ["inspect", str(path)])
    assert default.exit_code == 0, default.output
    assert "no problems in 1 sample" in default.output
    chosen = runner.invoke(app, ["inspect", str(path), "-t", "1.09"])
    assert chosen.exit_code == 1, chosen.output
    assert "t=1s" in chosen.output  # the frame on screen at 1.09 s is frame 10
    assert "moving (Text 'moving')" in chosen.output
    assert "texts overlap" in chosen.output
    assert "scene.py:9" in chosen.output
    with Image.open(tmp_path / "Example.storyboard.png") as image:
        pixels = np.array(image)
        assert ((pixels == [255, 64, 64]).all(axis=-1)).any()  # numbered red boxes


def test_selected_times_stop_after_their_play(tmp_path: Path) -> None:
    path = source(
        tmp_path,
        "self.add(m.Square())\nself.wait(2)\nraise RuntimeError('too far')",
    )
    chosen = CliRunner().invoke(app, ["inspect", str(path), "-t", "0.5"])
    assert chosen.exit_code == 0, chosen.output
    assert "2.00 s, 1 plays" in chosen.output
    ending = CliRunner().invoke(app, ["inspect", str(path), "-t", "end"])
    assert ending.exit_code == 1
    assert "too far" in ending.output


def test_inspection_stops_when_a_wait_ends_on_the_requested_frame(
    tmp_path: Path,
) -> None:
    path = source(
        tmp_path,
        "self.add(m.Square())\n"
        "self.wait(stop_condition=lambda: True)\n"
        "raise RuntimeError('the frame was already inspected')",
    )
    result = CliRunner().invoke(app, ["inspect", str(path), "-t", "0"])
    assert result.exit_code == 0, result.output


def test_default_inspection_deduplicates_pictures_but_checks_every_play(
    tmp_path: Path,
) -> None:
    path = source(
        tmp_path, 'self.add(m.Text("tiny", font_size=8))\nself.wait()\nself.wait()'
    )
    result = CliRunner().invoke(app, ["inspect", str(path)])
    assert result.exit_code == 1, result.output
    assert "t=1–2s" in result.output
    assert "#0" in result.output
    assert "#1" in result.output
    with Image.open(tmp_path / "Example.storyboard.png") as image:
        assert image.size == (960, 568)


def test_the_last_frame_keeps_local_names_and_problem_numbers(tmp_path: Path) -> None:
    path = source(
        tmp_path,
        'tiny = m.Text("tiny", font_size=8)\nself.add(tiny)\nself.wait()',
    )
    result = CliRunner().invoke(app, ["inspect", str(path), "-t", "end,0.5,1"])
    assert result.exit_code == 1, result.output
    assert "layout: 1 problem" in result.output
    assert "t=0.5–1s" in result.output
    assert "tiny (Text 'tiny')" in result.output


def test_notes_do_not_fail_inspection(tmp_path: Path) -> None:
    path = source(tmp_path, "self.add(m.Line(10 * m.LEFT, 10 * m.RIGHT))\nself.wait()")
    result = CliRunner().invoke(app, ["inspect", str(path)])
    assert result.exit_code == 0, result.output
    assert "layout: 0 problems, 1 note" in result.output


def test_end_inspects_changes_after_the_last_play(tmp_path: Path) -> None:
    path = source(
        tmp_path,
        'tiny = m.Text("tiny", font_size=8)\nself.add(tiny)\nself.wait()\ntiny.scale(5)',
    )
    result = CliRunner().invoke(app, ["inspect", str(path), "-t", "end"])
    assert result.exit_code == 0, result.output
    assert "no problems in 1 sample" in result.output


def test_explicit_times_keep_held_pictures_and_split_sheets(tmp_path: Path) -> None:
    path = source(tmp_path, "self.add(m.Square())\nself.wait(10)")
    output = tmp_path / "detail.png"
    result = CliRunner().invoke(
        app, ["inspect", str(path), "-t", "1,2,3", "-t", "4,5,6,end", "-o", str(output)]
    )
    assert result.exit_code == 0, result.output
    assert "no problems in 7 samples" in result.output
    with Image.open(output) as image:
        assert image.size == (1928, 1720)
    with Image.open(tmp_path / "detail-2.png") as image:
        assert image.size == (960, 568)


@pytest.mark.parametrize("times", [[], ["-t", "end"], ["-t", "0,end"]])
def test_a_scene_without_plays_still_gets_a_picture(
    tmp_path: Path, times: list[str]
) -> None:
    path = source(tmp_path, "self.add(m.Cube())", base="ThreeDScene")
    result = CliRunner().invoke(app, ["inspect", str(path), *times])
    assert result.exit_code == 0, result.output
    assert "layout: not checked (a 3D scene)" in result.output
    assert (tmp_path / "Example.storyboard.png").is_file()


@pytest.mark.parametrize("time", ["-1", "nan", "inf", "later", ""])
def test_invalid_times_are_command_errors(tmp_path: Path, time: str) -> None:
    path = source(tmp_path, "self.wait()")
    result = CliRunner().invoke(app, ["inspect", str(path), f"--time={time}"])
    assert result.exit_code == 2, result.output
    assert not list(tmp_path.glob("*.png"))


def test_a_missing_frame_is_a_scene_error(tmp_path: Path) -> None:
    path = source(tmp_path, "self.wait()")
    result = CliRunner().invoke(app, ["inspect", str(path), "-t", "4"])
    assert result.exit_code == 1, result.output
    assert "there is no frame at 4" in result.output
    assert not list(tmp_path.glob("*.png"))


def test_the_output_must_be_a_png(tmp_path: Path) -> None:
    path = source(tmp_path, "self.wait()")
    result = CliRunner().invoke(
        app, ["inspect", str(path), "-o", str(tmp_path / "x.jpg")]
    )
    assert result.exit_code == 2, result.output
    assert "*.png" in result.output
    assert not (tmp_path / "x.jpg").exists()


@pytest.mark.parametrize(
    ("base", "updating", "custom_emit"),
    [
        ("Scene", False, False),
        ("Scene", True, False),
        ("Scene", True, True),
        ("ThreeDScene", True, False),
    ],
)
def test_sampling_preserves_the_video_with_tweens_holds_and_updaters(
    tmp_path: Path,
    base: str,
    updating: bool,
    custom_emit: bool,
) -> None:
    camera = (
        "self.set_camera_orientation(phi=60 * m.DEGREES, theta=-40 * m.DEGREES)\n"
        "self.begin_ambient_camera_rotation(rate=0.3)\n"
        if base == "ThreeDScene"
        else ""
    )
    shape = "Cube" if base == "ThreeDScene" else "Square"
    path = source(
        tmp_path,
        camera + f"moving = m.{shape}(fill_opacity=1).shift(2 * m.LEFT)\n"
        "self.add(moving)\n"
        + (
            "moving.add_updater(lambda mob: mob.shift(0.01 * m.UP))\n"
            if updating
            else ""
        )
        + "self.play(moving.animate.shift(4 * m.RIGHT), rate_func=m.linear)\n"
        "self.wait(0.25)",
        base=base,
    )
    if custom_emit:
        # With an updater, both takes emit each frame rather than batching the tween.
        with path.open("a", encoding="utf-8") as out:
            out.write(
                "    def _emit(self, repeat: int = 1) -> None:\n"
                "        for mob in self.mobjects:\n"
                "            mob.set_color(m.RED)\n"
                "        super()._emit(repeat)\n"
            )

    frames: dict[int, bytes] = {}

    def keep(frame: Frame) -> None:
        pixels = frame.pixels()
        for index in range(frame.index, frame.index + frame.repeat):
            frames[index] = pixels

    normal = scene(path, None)().render(frames=keep)
    result = CliRunner().invoke(app, ["inspect", str(path), "-t", "1.3,0,1,0.5,1.2"])
    assert result.exit_code == 0, result.output
    assert normal.frame_count == 14
    with Image.open(tmp_path / "Example.storyboard.png") as sheet:
        for position, index in enumerate((0, 5, 10, 12, 13)):
            expected = tile(frames[index], 320, 180)
            row, column = divmod(position, 2)
            x = column * (expected.width + GAP)
            y = row * (expected.height + CAPTION + GAP) + CAPTION
            actual = sheet.crop((x, y, x + expected.width, y + expected.height))
            assert actual.tobytes() == expected.tobytes(), f"frame {index}"

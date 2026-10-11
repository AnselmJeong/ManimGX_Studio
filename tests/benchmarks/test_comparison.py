"""Process isolation, video validation, aggregation, chart scaling, the README's images,
and the READMEs' numbers, which are the recorded results'."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pytest
from PIL import Image

from benchmarks import chart, quality, run
from benchmarks.scenes.suite_data import ring_pose

RESULTS = json.loads((run.HERE / "results.json").read_text(encoding="utf-8"))
# the engines as the READMEs name them, in the benchmark's table's order
NAMES = {
    "manimgx": "ManimGX",
    "manimgl": "ManimGL",
    "manim_ce": "ManimCE",
    "blender_workbench": "Blender Workbench",
    "blender_eevee": "Blender EEVEE",
}


def test_unsupported_cpu_accounting_never_starts_a_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delattr(run.os, "wait4", raising=False)
    monkeypatch.setattr(run, "command", lambda *args: [sys.executable, "-c", "pass"])

    def launch(*args: object, **kwargs: object) -> None:
        pytest.fail("the unsupported benchmark started a process")

    monkeypatch.setattr(run.subprocess, "Popen", launch)
    with pytest.raises(RuntimeError, match="macOS and Linux"):
        run.run_one(
            "manimgx",
            "linked_rings",
            1,
            argparse.Namespace(out=tmp_path, dry_run=False),
        )


@pytest.mark.skipif(
    not hasattr(run.os, "wait4"), reason="CPU timing runs on macOS and Linux"
)
@pytest.mark.parametrize("timeout", [False, True])
def test_unsuccessful_processes_are_retained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, timeout: bool
) -> None:
    code = (
        "import time; print('started', flush=True); time.sleep(30)"
        if timeout
        else "import sys; print('failed deliberately', flush=True); sys.exit(7)"
    )
    monkeypatch.setattr(run, "command", lambda *args: [sys.executable, "-c", code])
    args = argparse.Namespace(out=tmp_path, timeout=0.5, dry_run=False)
    result = run.run_one("manimgx", "linked_rings", 1, args)
    assert result.status == ("timeout" if timeout else "failed")
    assert result.wall_seconds < 5
    assert not result.video
    assert Path(result.log).exists()
    assert ("started" if timeout else "failed deliberately") in result.error


def test_a_run_never_overwrites_an_existing_run(tmp_path: Path) -> None:
    folder = tmp_path / "linked_rings/manimgx/1"
    folder.mkdir(parents=True)
    marker = folder / "retained.txt"
    marker.write_text("measurement", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run.run_one("manimgx", "linked_rings", 1, argparse.Namespace(out=tmp_path))
    assert marker.read_text(encoding="utf-8") == "measurement"


@pytest.mark.parametrize("tool", run.TOOLS)
def test_encoder_options_must_match_fastest_preset_and_crf23(
    tmp_path: Path, tool: str
) -> None:
    path = tmp_path / "out.mp4"
    options = (
        "crf=23.0 subme=1 me=dia bframes=0"
        if tool.startswith("blender_")
        else "crf=23.0 cabac=0 subme=0 bframes=0"
    )
    path.write_bytes(f"x264 - core 165 - options: {options}\x00".encode())
    assert "crf=23.0" in run.encoder_evidence(path, tool)
    path.write_bytes(path.read_bytes().replace(b"crf=23.0", b"crf=18.0"))
    with pytest.raises(ValueError, match="Unexpected encoder"):
        run.encoder_evidence(path, tool)


def test_only_gx_can_use_explicit_cli_encoding_evidence(tmp_path: Path) -> None:
    path = tmp_path / "out.mp4"
    path.write_bytes(b"no x264 options")
    assert "Explicit ultrafast" in run.encoder_evidence(path, "manimgx")
    for tool in run.TOOLS[1:]:
        with pytest.raises(ValueError, match="Unexpected encoder"):
            run.encoder_evidence(path, tool)


def test_totals_require_every_scene_and_repeat() -> None:
    samples = [
        run.Run("orbit", "manimgx", i, [], status="complete", wall_seconds=value)
        for i, value in enumerate((1, 3), 1)
    ]
    result = run.summarize(samples, ["orbit", "linked_rings"], {"manimgx": 2})
    assert not result["complete"]
    assert result["totals"] == {}
    samples += [
        run.Run("linked_rings", "manimgx", i, [], status="complete", wall_seconds=value)
        for i, value in enumerate((2, 8), 1)
    ]
    assert run.summarize(samples, ["orbit", "linked_rings"], {"manimgx": 2})[
        "totals"
    ] == {"manimgx": 7}
    samples[-1].status = "invalid"
    assert not run.summarize(samples, ["orbit", "linked_rings"], {"manimgx": 2})[
        "complete"
    ]


def test_recorded_totals_match_every_run() -> None:
    rows = [
        run.Run(
            r["scene"],
            r["tool"],
            r["repeat"],
            [],
            status=r["status"],
            wall_seconds=r["wall_seconds"],
        )
        for r in RESULTS["runs"]
    ]
    result = run.summarize(rows, list(run.DURATIONS), run.REPEATS)
    assert len(rows) == 45
    assert result["complete"]
    assert result["totals"] == RESULTS["totals"]
    assert result["per_scene"] == RESULTS["per_scene"]


def test_the_benchmark_s_readme_tabulates_the_recorded_results() -> None:
    rows = (run.HERE / "README.md").read_text(encoding="utf-8").splitlines()
    assert list(NAMES) == list(run.TOOLS)
    assert f"| Scene | Video | {' | '.join(NAMES.values())} |" in rows
    for scene, means in RESULTS["per_scene"].items():
        cells = [f"{run.DURATIONS[scene]:g} s"]
        cells += [f"{means[tool]['mean_seconds']:.3f}" for tool in run.TOOLS]
        assert any(row.endswith(f"(`{scene}`) | {' | '.join(cells)} |") for row in rows)
    totals = RESULTS["totals"]
    video = sum(RESULTS["settings"]["scenes"].values())
    cells = [f"{video:g} s", *(f"{totals[tool]:.3f}" for tool in run.TOOLS)]
    assert f"| Total | {' | '.join(cells)} |" in rows
    ratios = ["1×", *(f"{totals[t] / totals['manimgx']:.1f}×" for t in run.TOOLS[1:])]
    assert f"| Relative to ManimGX | | {' | '.join(ratios)} |" in rows
    # where and when the results were recorded, as their manifest says
    text = " ".join(rows)
    machine = RESULTS["machine"]
    measured = datetime.strptime(RESULTS["date"], "%Y-%m-%dT%H:%M:%S%z")
    assert f"Measured on {measured:%B} {measured.day}, {measured.year}," in text
    assert f"({machine['cpus']} CPU cores," in text
    assert f"macOS {machine['os'].split('-')[1]}:" in text
    assert f"holds all {len(RESULTS['runs'])} runs" in text


def test_the_readme_quotes_the_benchmark_and_links_it() -> None:
    readme = (run.HERE.parent / "README.md").read_text(encoding="utf-8")
    totals = RESULTS["totals"]
    video = sum(RESULTS["settings"]["scenes"].values())
    assert (
        f"**{video:g} seconds of video, rendered in {totals['manimgx']:.2f} seconds.**"
        in readme
    )
    for tool in ("manim_ce", "manimgl", "blender_workbench"):
        ratio = totals[tool] / totals["manimgx"]
        assert f"**{ratio:.1f}× faster than {NAMES[tool]}**" in readme
    fastest_first = sorted(totals, key=totals.__getitem__)
    seconds = ", ".join(f"{NAMES[tool]} {totals[tool]:.2f} s" for tool in fastest_first)
    assert f'alt="Total render times: {seconds}"' in readme
    assert "](https://github.com/academa-labs/manimgx/tree/main/benchmarks)" in readme


def test_the_readme_s_images_are_one_part_of_each_frame(tmp_path: Path) -> None:
    left, top, right, bottom = quality.CROP
    assert (right - left, bottom - top) == (302, 524)
    frame = Image.new("RGBA", (1920, 1080))
    frame.putpixel((left, top), (255, 0, 0, 255))
    frame.putpixel((left - 1, top), (0, 0, 255, 255))
    path = tmp_path / "frame.png"
    frame.save(path)
    pictures = quality.website_images(path)
    assert list(pictures) == ["", "-light"]
    for picture, ground in zip(
        pictures.values(), [(11, 12, 15), (255, 255, 255)], strict=True
    ):
        assert picture.size == (302, 524)
        assert picture.getpixel((0, 0)) == (255, 0, 0)
        colors = picture.getcolors()
        assert colors is not None
        assert {color for _, color in colors} == {(255, 0, 0), ground}
    frame.putalpha(255)
    frame.save(path)
    with pytest.raises(ValueError, match="transparent 1080p frame"):
        quality.website_images(path)


def test_static_chart_keeps_measured_seconds_and_proportional_bars() -> None:
    totals = {"manimgx": 2.0, "manimgl": 10.0, "manim_ce": 20.0}
    rows = chart.measured_rows(totals)
    assert rows == [("ManimGX", 2), ("ManimGL", 10), ("ManimCE", 20)]
    for theme in chart.THEMES.values():
        svg = chart.chart(rows, theme)
        root = ElementTree.fromstring(svg)
        widths = []
        for i, (_, seconds) in enumerate(rows):
            bar = root.find(f".//*[@id='b{i}']")
            label = root.find(f".//*[@id='t{i}']")
            assert bar is not None
            assert label is not None
            widths.append(float(bar.attrib["width"]))
            assert label.text == f"{seconds:.2f} s"
        assert widths[1] / widths[0] == pytest.approx(5)
        assert widths[2] / widths[0] == pytest.approx(10)
        assert "animation" not in svg
        assert "<animate" not in svg


@pytest.mark.parametrize("t", [0, 0.75, 1.5, 2.25, 3])
def test_ring_poses_remain_rigid(t: float) -> None:
    for i in range(8):
        rotation, position = ring_pose(i, t)
        np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1e-12)
        assert np.linalg.det(rotation) == pytest.approx(1)
        assert np.isfinite(position).all()

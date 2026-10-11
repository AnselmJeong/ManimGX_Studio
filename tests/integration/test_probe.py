"""A portability probe captures independent evidence and preserves the reviewed corpus."""

import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

import pytest
from tests.integration.corpus import probe
from tests.integration.corpus.case import ROOT, Case
from tests.integration.corpus.engines import environment

import manimgx


def test_probe_captures_two_films_and_their_scene_without_changing_references(
    tmp_path: Path,
) -> None:
    case = Case("dot_example")
    references = (case.scene, case.facts_path, case.video_hash("manimgx"))
    before = [path.read_bytes() for path in references]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.integration.corpus.probe",
            str(tmp_path),
            case.name,
        ],
        cwd=ROOT,
        env=environment(),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert [path.read_bytes() for path in references] == before
    directory = tmp_path / case.name
    first, second = (
        json.loads((directory / f"{run}.json").read_text(encoding="utf-8"))
        for run in ("first", "second")
    )
    assert first == second
    for run in ("first", "second"):
        assert (directory / f"{run}.mkv").stat().st_size > 0
        assert (directory / f"{run}.log").is_file()
    take = json.loads((directory / "recording.json").read_text(encoding="utf-8"))
    assert take["source"] == first["source"]
    assert take["frames"] == sum(n for _, n in first["render"]["frames"])
    assert (
        take["sha256"]
        == hashlib.sha256((directory / "recording.take").read_bytes()).hexdigest()
    )
    host = json.loads((tmp_path / "environment.json").read_text(encoding="utf-8"))
    assert Path(host["package"]).resolve() == Path(manimgx.__file__).resolve()


def test_metadata_describes_a_source_package_without_distribution_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed_version = importlib.metadata.version

    def version(name: str) -> str:
        if name == "manimgx":
            raise importlib.metadata.PackageNotFoundError(name)
        return installed_version(name)

    monkeypatch.setattr(importlib.metadata, "version", version)
    probe._metadata(tmp_path)
    host = json.loads((tmp_path / "environment.json").read_text(encoding="utf-8"))
    assert host["versions"]["manimgx"] is None
    assert Path(host["package"]).resolve() == Path(manimgx.__file__).resolve()

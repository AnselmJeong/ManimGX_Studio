"""Running an engine on a case: each render in a fresh process of its own, in the case's
directory, with a fixed hash seed — the only way the corpus renders anything."""

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from tests.integration.corpus.case import (
    ROOT,
    Case,
    Engine,
    Failure,
    Frames,
    frames_from_json,
)
from tests.integration.corpus.frozen import Difference

TIMEOUT: dict[Engine, float] = {"manimgx": 300, "ce": 900}


@dataclass(frozen=True, slots=True)
class Result:
    # the hash of the bytes the engine ran (None if it never got that far)
    source: str | None
    frames: Frames | Failure
    # CE's version
    manim: str | None = None
    # ManimGX asked for an MP4: the film's own frame count, and the MP4's
    film_frames: int | None = None
    mp4_frames: int | None = None
    differences: tuple[Difference, ...] = ()
    adapter: dict[str, str] | None = None
    duration: Fraction | None = None


def environment(package: Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p
        for p in (str(package) if package else "", str(ROOT), env.get("PYTHONPATH", ""))
        if p
    )
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run(
    case: Case,
    engine: Engine,
    *,
    video: Path | None = None,
    mp4: bool = False,
    package: Path | None = None,
    reference: Path | None = None,
    reference_video: Path | None = None,
    source: Path | None = None,
    differences: Path | None = None,
    log: Path | None = None,
    compact_video: bool = True,
) -> Result:
    """Render `case` with `engine`; its frames go to `video` too, if given."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "result.json"
        command = [sys.executable, "-m", f"tests.integration.corpus.run_{engine}"]
        command += [str(case.scene), "--out", str(out)]
        if video is not None:
            command += ["--video", str(video)]
        if mp4:
            command.append("--mp4")
        if not compact_video:
            command.append("--fast-video")
        for flag, path in (
            ("--reference", reference),
            ("--reference-video", reference_video),
            ("--source", source),
            ("--differences", differences),
        ):
            if path is not None:
                command += [flag, str(path)]
        if package is not None:
            command += ["--package", str(package)]
        try:
            proc = subprocess.run(
                command,
                cwd=case.dir,
                env=environment(package),
                capture_output=True,
                text=True,
                timeout=TIMEOUT[engine],
                check=False,
            )
        except subprocess.TimeoutExpired:
            if log is not None:
                log.write_text(
                    f"timed out after {TIMEOUT[engine]:.0f}s\n", encoding="utf-8"
                )
            return Result(None, Failure(f"timed out after {TIMEOUT[engine]:.0f}s"))
        if log is not None:
            log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
        if proc.returncode != 0 or not out.exists():
            return Result(None, Failure(_error(proc.stderr, proc.returncode)))
        data = json.loads(out.read_text(encoding="utf-8"))
        if log is not None:
            log.with_suffix(".result.json").write_bytes(out.read_bytes())
    return Result(
        source=str(data["source"]),
        frames=frames_from_json(data["render"]),
        manim=data.get("manim"),
        film_frames=data.get("film_frames"),
        mp4_frames=data.get("mp4_frames"),
        differences=tuple(Difference(**item) for item in data.get("differences", [])),
        adapter=data.get("adapter"),
        duration=Fraction(data["duration_exact"]) if "duration_exact" in data else None,
    )


def _error(stderr: str, code: int) -> str:
    """The line that says what went wrong: a traceback's last line, or whatever came last."""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    for line in reversed(lines):
        if not line.startswith(("File ", "^", "~")) and (
            "Error" in line or "Exception" in line
        ):
            return line[:300]
    return (lines[-1] if lines else f"exited with {code}")[:300]

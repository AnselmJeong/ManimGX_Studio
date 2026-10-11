"""Capture portability evidence without changing the corpus's references or acceptance rules.

    python -m tests.integration.corpus.probe OUTPUT CASE...

Each case runs in three fresh processes: two lossless films with their frame records, and a
take of the scene's GPU inputs. Equal takes with different pixels locate a difference after
scene evaluation; the two films distinguish a repeatable difference from an unstable render.
Every process leaves its log, including failures. Adapter details are not exposed by the
engine; metadata records the host, installed package, numerical libraries and build instead.
"""

import argparse
import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
from tests.integration.corpus.case import FPS, ROOT, SIZE, Case, discover, source_hash
from tests.integration.corpus.engines import TIMEOUT, environment
from tests.integration.corpus.runtime import load, seed, the_scene

import manimgx
from manimgx import _engine


def _version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _metadata(out: Path) -> None:
    numerical = io.StringIO()
    with contextlib.redirect_stdout(numerical):
        np.show_config()
    data = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "executable": sys.executable,
        "package": manimgx.__file__,
        "engine": _engine.__file__,
        "versions": {
            name: _version(name)
            for name in ("manimgx", "numpy", "networkx", "av", "manimgx-fonts")
        },
        "numpy_configuration": numerical.getvalue(),
        "commit": os.environ.get("GITHUB_SHA"),
        "run": os.environ.get("GITHUB_RUN_ID"),
        "size": SIZE,
        "fps": FPS,
    }
    (out / "environment.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def _take(out: Path, case: Case) -> None:
    seed()
    manimgx.config.pixel_width, manimgx.config.pixel_height = SIZE
    manimgx.config.frame_rate = FPS
    source = case.scene.read_bytes()
    module = load(case.scene, source, f"corpus_scene_{case.name}")
    scene = the_scene(module, manimgx.Scene)()
    path = out / "recording.take"
    with path.open("wb") as stream:
        film = scene.render(take=stream.write)
    data = {
        "source": source_hash(source),
        "frames": film.frame_count,
        "duration": str(scene.clock),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    (out / "recording.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def _call(module: str, args: list[str], case: Case, log: Path) -> bool:
    with log.open("wb") as stream:
        try:
            result = subprocess.run(
                [sys.executable, "-m", module, *args],
                cwd=case.dir,
                env=environment(),
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=TIMEOUT["manimgx"],
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            stream.write(f"\n{error}\n".encode())
            return False
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("cases", nargs="+")
    parser.add_argument("--take", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    known = {case.name: case for case in discover()}
    missing = set(args.cases) - known.keys()
    if missing:
        parser.error(f"unknown cases: {', '.join(sorted(missing))}")
    out = args.output.resolve()
    if out.is_relative_to(ROOT / "tests" / "integration" / "cases"):
        parser.error("probe output must be outside the reference corpus")
    out.mkdir(parents=True, exist_ok=True)
    if args.take:
        if len(args.cases) != 1:
            parser.error("a take records exactly one case")
        _take(out, known[args.cases[0]])
        return
    _metadata(out)
    failed: list[str] = []
    for name in args.cases:
        case, directory = known[name], out / name
        directory.mkdir(exist_ok=True)
        for run in ("first", "second", "recording"):
            if run == "recording":
                module = "tests.integration.corpus.probe"
                command = [str(directory), name, "--take"]
            else:
                module = "tests.integration.corpus.run_manimgx"
                command = [
                    str(case.scene),
                    "--out",
                    str(directory / f"{run}.json"),
                    "--video",
                    str(directory / f"{run}.mkv"),
                ]
            good = _call(module, command, case, directory / f"{run}.log")
            print(f"{name}/{run}: {'recorded' if good else 'failed'}", flush=True)
            if not good:
                failed.append(f"{name}/{run}")
    if failed:
        sys.exit(f"failed probes: {', '.join(failed)}")


if __name__ == "__main__":
    main()

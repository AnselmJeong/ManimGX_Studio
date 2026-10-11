"""Two ManimGX trees, timed side by side on one machine.

A `Tree` is a ManimGX package on disk, with its engine. `here()` is the imported package,
editable or installed; `checkout(ref, trees)` makes one of a commit under `trees` (its sources from git; its
engine this checkout's when the commit's engine sources are this checkout's, else built), or
takes another checkout's. A `Workload` is a scene file, rendered as a user renders it:
`manimgx render`, in a fresh process with a tree first on its path. `run` measures one render,
from launch to exit; `compare` runs a workload with two trees in turns, a round running both in
a random order.

Time is compared, never pinned: the two trees run on the same machine at the same time, so what
the machine does to one it does to the other, and a round's ratio is what is kept.
"""

import ctypes
import importlib.machinery
import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Event, Timer
from typing import IO

from tests.benchmarks.work import Work

import manimgx

ROOT = Path(__file__).resolve().parents[2]
KEEP = 4
"""How many commits' trees are kept (the least recently used go first)."""
TIMEOUT = 300
"""Each render owns its deadline, including cleanup of a stalled child."""
LAYOUTS = (
    ("src", ("src", "fonts", "LICENSE-THIRD-PARTY", "LICENSE-LAVAPIPE")),
    ("python/manimgx/src", ("python",)),
)
"""Where a commit keeps manimgx's package (`src/`), and what the package is built from
beside its engine's sources and the project's files: the package at the repository's root, as
now, or in python/, as before."""
ENGINE = ("rust",)
"""What the engine is built from: its crates, their manifest and lockfile."""


@dataclass(frozen=True, slots=True)
class Tree:
    """A ManimGX to time: `src` holds the package, its engine built; `label` names it."""

    src: Path
    label: str


@dataclass(frozen=True, slots=True)
class Workload:
    """A scene file, rendered to a video by `manimgx render` with these options."""

    scene: Path
    options: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Cost:
    """What a render cost, from launch to exit: CPU seconds (every thread's), wall seconds,
    peak memory (MB), and the instructions it retired, where the system counts them for a
    process when the host exposes its counters (otherwise None)."""

    cpu: float
    wall: float
    memory: float
    instructions: int | None

    @property
    def measure(self) -> float:
        """What a comparison judges: the instructions where they are counted, which do not
        change with the cores that ran the process or with what else the machine does (its CPU
        seconds, on a loaded Mac, move by tens of percent); else the CPU seconds."""
        return self.cpu if self.instructions is None else self.instructions


@dataclass(frozen=True, slots=True)
class Row:
    """A timed workload's line in the table a timed run ends with (`conftest.py`), in the
    workloads' `order`; `unit` names what was judged."""

    order: int
    unit: str
    cells: tuple[str, ...]


class Incomparable(Exception):
    """The tree compared with cannot render the workload: it uses what came after it."""


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _engine(src: Path) -> Path | None:
    """The engine's binary in a tree's package, if built."""
    for suffix in importlib.machinery.EXTENSION_SUFFIXES:
        path = src / "manimgx" / f"_engine{suffix}"
        if path.exists():
            return path
    return None


def here() -> Tree:
    """The package imported by this process, including an installed wheel."""
    src = Path(manimgx.__file__).resolve().parent.parent
    return Tree(src, f"this package ({_git('rev-parse', '--short', 'HEAD')})")


def checkout(ref: str, trees: Path) -> Tree:
    """The tree of `ref`: a directory holding a ManimGX checkout, or a commit (a branch, tag
    or hash), made once under `trees/<hash>/`."""
    path = Path(ref)
    for src, _ in LAYOUTS:
        if (path / src / "manimgx").is_dir():
            return _verified(Tree(path.resolve() / src, str(path)))
    try:
        sha = _git("rev-parse", "--verify", f"{ref}^{{commit}}")
    except subprocess.CalledProcessError:
        msg = f"{ref} is neither a commit of this repository nor a manimgx checkout"
        raise ValueError(msg) from None
    src, sources = _layout(sha)
    home = trees / sha
    tree = Tree(home / src, f"{ref} ({sha[:8]})")
    if _engine(tree.src) is None:
        shutil.rmtree(home, ignore_errors=True)
        _extract(sha, home, sources)
        _build(sha, home, sources)
        if _engine(tree.src) is None:
            msg = f"building {sha[:8]} made no engine"
            raise RuntimeError(msg)
    home.touch()  # recently used
    for old in sorted(trees.iterdir(), key=lambda p: p.stat().st_mtime)[:-KEEP]:
        shutil.rmtree(old, ignore_errors=True)
    return _verified(tree)


def _layout(sha: str) -> tuple[str, tuple[str, ...]]:
    """Commit `sha`'s layout, one of `LAYOUTS`."""
    for layout in LAYOUTS:
        found = subprocess.run(
            ["git", "cat-file", "-e", f"{sha}:{layout[0]}/manimgx"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
        if found.returncode == 0:
            return layout
    msg = f"{sha[:8]} holds no manimgx package"
    raise ValueError(msg)


def _extract(sha: str, home: Path, sources: tuple[str, ...]) -> None:
    """Write commit `sha`'s package, engine sources and project files into `home`."""
    home.mkdir(parents=True)
    paths = [*sources, *ENGINE, "pyproject.toml", "uv.lock", "README.md", "LICENSE"]
    archive = subprocess.run(
        ["git", "archive", "--format=tar", sha, *paths],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    with tempfile.TemporaryFile() as buffer:
        buffer.write(archive)
        buffer.seek(0)
        with tarfile.open(fileobj=buffer) as tar:
            tar.extractall(home, filter="data")


def _build(sha: str, home: Path, sources: tuple[str, ...]) -> None:
    """Give the tree in `home` its engine: this checkout's, if `sha` has the same engine
    sources, or else one built in its own directory."""
    ours = _engine(ROOT / LAYOUTS[0][0])
    same = subprocess.run(["git", "diff", "--quiet", sha, "--", *ENGINE], cwd=ROOT)
    if sources == LAYOUTS[0][1] and same.returncode == 0 and ours is not None:
        shutil.copy2(ours, home / LAYOUTS[0][0] / "manimgx" / ours.name)
        return
    # a workspace's root is no project: its package is built as a member of it
    project = tomllib.loads((home / "pyproject.toml").read_text(encoding="utf-8"))
    package = [] if "project" in project else ["--package", "manimgx"]
    env = dict(os.environ, CARGO_TARGET_DIR=str(home / "rust" / "target"))
    subprocess.run(
        ["uv", "sync", "--frozen", "--no-default-groups", "--project", str(home)]
        + package,
        env=env,
        check=True,
    )


def _environment(tree: Tree, tmp: str, *path: Path) -> dict[str, str]:
    """A run's environment: `tree` first on the path; an empty temporary directory, so no run
    finds another's Typst layouts; a fixed hash seed; and one thread for lavapipe (the software
    GPU of Linux runners), so its time is one thread's work."""
    return dict(
        os.environ,
        PYTHONPATH=os.pathsep.join(str(p) for p in (tree.src, *path)),
        PYTHONHASHSEED="0",
        TMPDIR=tmp,
        TEMP=tmp,
        TMP=tmp,
        MANIMGX_CACHE_DIR=tmp,
        LP_NUM_THREADS="1",
    )


def _verified(tree: Tree) -> Tree:
    """`tree`, once a process given its environment has been seen to import its ManimGX."""
    with tempfile.TemporaryDirectory(prefix="manimgx-benchmark-") as tmp:
        where = subprocess.run(
            [sys.executable, "-c", "import manimgx; print(manimgx.__file__)"],
            env=_environment(tree, tmp, ROOT),
            capture_output=True,
            encoding="utf-8",
            check=True,
        ).stdout.strip()
    if not Path(where).resolve().is_relative_to(tree.src.resolve()):
        msg = f"{tree.label}'s runs would import {where}, not its manimgx"
        raise RuntimeError(msg)
    return tree


@contextmanager
def _launch(
    tree: Tree, workload: Workload, tmp: str, stderr: int | IO[str], *module: str
) -> Iterator[subprocess.Popen[str]]:
    """Start `python -m manimgx render` on `workload` with `tree` (or, with `module`, that
    module's command line on the same arguments), writing its video into `tmp`."""
    video = str(Path(tmp) / "video.mp4")
    child = subprocess.Popen(
        [sys.executable, "-m", *(module or ("manimgx",)), "render", str(workload.scene)]
        + ["--output", video, *workload.options],
        cwd=workload.scene.parent,  # a scene reads its files next to it
        env=_environment(tree, tmp, ROOT),
        stdout=subprocess.DEVNULL,
        stderr=stderr,
        encoding="utf-8",
        errors="replace",
    )
    with child:
        expired = Event()

        def stop() -> None:
            expired.set()
            child.kill()

        deadline = Timer(TIMEOUT, stop)
        try:
            deadline.start()
            yield child
        finally:
            deadline.cancel()
            if deadline.ident is not None:
                deadline.join()
            if child.poll() is None:
                child.kill()
            child.wait()
            if expired.is_set():
                raise RuntimeError(
                    f"{tree.label} timed out rendering {workload.scene.name} after {TIMEOUT}s"
                )


def _failed(tree: Tree, workload: Workload, stderr: str, status: int) -> RuntimeError:
    last = (stderr.strip().splitlines() or [f"exit status {status}"])[-1]
    return RuntimeError(f"{tree.label} fails {workload.scene.name}: {last}")


def render(tree: Tree, workload: Workload, *options: str) -> None:
    """Render `workload` once with `tree`, `options` after its own (the last one given of an
    option counts); raise if it fails."""
    with tempfile.TemporaryDirectory(prefix="manimgx-benchmark-") as tmp:
        told = replace(workload, options=workload.options + options)
        with _launch(tree, told, tmp, subprocess.PIPE) as child:
            _, stderr = child.communicate()
    if child.returncode:
        raise _failed(tree, workload, stderr, child.returncode)


def _instructions(pid: int) -> int | None:
    """The instructions process `pid` retired, read once it has exited and before it is reaped
    (on macOS hosts exposing the counter; otherwise None)."""
    os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
    if sys.platform != "darwin":
        return None
    # proc_pid_rusage's rusage_info_v4 (sys/resource.h): a 16-byte uuid, then 35 counters,
    # ri_instructions the 30th
    usage = (ctypes.c_uint64 * 37)()
    if ctypes.CDLL(None).proc_pid_rusage(pid, 4, usage):
        return None
    # A successful query can return zero when hardware counters are unavailable in a VM.
    return usage[2 + 29] or None


def run(tree: Tree, workload: Workload) -> Cost:
    """Render `workload` with `tree` and measure the render, from launch to exit."""
    if not hasattr(os, "wait4"):
        msg = "the benchmarks are timed on Linux and macOS"
        raise OSError(msg)
    with (
        tempfile.TemporaryDirectory(prefix="manimgx-benchmark-") as tmp,
        open(
            Path(tmp) / "stderr.txt", "w+", encoding="utf-8", errors="replace"
        ) as stderr,
    ):
        start = time.perf_counter()
        with _launch(tree, workload, tmp, stderr) as child:
            instructions = _instructions(child.pid)
            wall = time.perf_counter() - start
            _, status, usage = os.wait4(child.pid, 0)
            child.returncode = os.waitstatus_to_exitcode(status)
        stderr.seek(0)
        if child.returncode:
            raise _failed(tree, workload, stderr.read(), child.returncode)
    peak = usage.ru_maxrss / (2**20 if sys.platform == "darwin" else 2**10)  # B, KiB
    return Cost(usage.ru_utime + usage.ru_stime, wall, peak, instructions)


def work(tree: Tree, workload: Workload) -> Work:
    """The work `tree` does rendering `workload`, counted in one run (`tests.benchmarks.work`;
    counting slows it down)."""
    with tempfile.TemporaryDirectory(prefix="manimgx-benchmark-") as tmp:
        out = Path(tmp) / "work.json"
        with _launch(
            tree, workload, tmp, subprocess.PIPE, "tests.benchmarks.work", str(out)
        ) as child:
            _, stderr = child.communicate()
        if child.returncode:
            raise _failed(tree, workload, stderr, child.returncode)
        return Work(**json.loads(out.read_text(encoding="utf-8")))


def compare(
    workload: Workload, base: Tree, head: Tree, count: int, warm: bool = True
) -> list[tuple[Cost, Cost]]:
    """(base, head) costs of each of `count` rounds. Both trees run in each round, in a random
    order; with `warm`, after a round that is not kept (each tree's files read once, its
    bytecode written). A base that cannot render the workload is `Incomparable`."""
    order = random.Random(f"{workload.scene} {warm}")
    samples: list[tuple[Cost, Cost]] = []
    for kept in [False] * warm + [True] * count:
        pair = [base, head]
        order.shuffle(pair)
        costs: dict[int, Cost] = {}
        for tree in pair:
            try:
                costs[id(tree)] = run(tree, workload)
            except RuntimeError as error:
                if tree is base:
                    raise Incomparable(str(error)) from None
                raise
        if kept:
            samples.append((costs[id(base)], costs[id(head)]))
    return samples

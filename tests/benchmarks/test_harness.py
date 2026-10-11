"""Benchmark subprocesses use the same package as their parent, wherever it is installed."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from tests.benchmarks import harness

import manimgx


@pytest.mark.parametrize("local", [False, True], ids=["missing-history", "local-ref"])
def test_workflow_acquires_its_comparison_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local: bool
) -> None:
    def git(folder: Path, *args: str) -> str:
        return subprocess.check_output(
            ["git", *args],
            cwd=folder,
            input="",
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()

    remote, checkout = tmp_path / "remote.git", tmp_path / "checkout"
    git(tmp_path, "init", "--bare", str(remote))
    git(remote, "config", "user.name", "Benchmark test")
    git(remote, "config", "user.email", "benchmark@example.invalid")
    git(remote, "config", "commit.gpgsign", "false")
    tree = git(remote, "mktree")
    before = git(remote, "commit-tree", tree, "-m", "before")
    head = git(remote, "commit-tree", tree, "-m", "rewritten")
    git(remote, "update-ref", "refs/heads/main", head)
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    # Fetch reachable history, rather than copying the remote's orphan objects.
    git(tmp_path, "clone", "--no-local", str(remote), str(checkout))
    with pytest.raises(subprocess.CalledProcessError):
        git(checkout, "cat-file", "-e", f"{before}^{{commit}}")
    if local:
        git(checkout, "remote", "remove", "origin")
    monkeypatch.setenv("AGAINST", "HEAD" if local else before)
    steps = yaml.safe_load(
        (harness.ROOT / ".github/workflows/benchmark.yaml").read_text(encoding="utf-8")
    )["jobs"]["benchmark"]["steps"]
    script = next(step["run"] for step in steps if step.get("name") == "Benchmark")
    # Git supplies its own shell on Windows, as it does when running shell aliases.
    stub = 'set -e\njust() { test "$1" = bench; git cat-file -e "${2}^{commit}"; : > invoked; }\n'
    git(checkout, "-c", f"alias.exercise=!{stub}{script}", "exercise")
    assert (checkout / "invoked").exists()
    assert git(checkout, "rev-parse", "HEAD") == head


def test_historical_engines_do_not_reuse_each_others_build_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repository"
    repo.mkdir()
    files = {
        "pyproject.toml": '[project]\nname = "manimgx"\nversion = "0.0.0"\n',
        "uv.lock": "",
        "README.md": "",
        "LICENSE": "",
        "src/manimgx/__init__.py": "",
        "rust/Cargo.toml": '[workspace]\nmembers = ["engine"]\nresolver = "2"\n',
        "rust/Cargo.lock": (
            'version = 4\n\n[[package]]\nname = "benchmark-probe"\nversion = "0.0.0"\n'
        ),
        "rust/engine/Cargo.toml": (
            '[package]\nname = "benchmark-probe"\nversion = "0.0.0"\nedition = "2021"\n'
            '[lib]\nname = "_engine"\ncrate-type = ["cdylib"]\n'
        ),
    }
    for name, data in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
    invoke = subprocess.run

    def git(*args: str, date: str = "2000-01-01T00:00:00Z") -> str:
        return invoke(
            [
                "git",
                "-c",
                "user.name=Benchmark test",
                "-c",
                "user.email=benchmark@example.invalid",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=repo,
            env=dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init")
    source = repo / "rust/engine/src/lib.rs"
    source.parent.mkdir()
    commits = []
    for value, date in [(101, "2000-01-01T00:00:00Z"), (202, "2001-01-01T00:00:00Z")]:
        source.write_text(
            f'#[no_mangle]\npub extern "C" fn identity() -> u32 {{ {value} }}\n',
            encoding="utf-8",
        )
        git("add", ".")
        git("commit", "-m", str(value), date=date)
        commits.append(git("rev-parse", "HEAD"))
    monkeypatch.setattr(harness, "ROOT", repo)
    base = tmp_path / "base"
    harness._extract(commits[0], base, ("src",))

    def command(home: Path) -> list[str]:
        return [
            "cargo",
            "build",
            "--offline",
            "--locked",
            "--release",
            "--manifest-path",
            str(home / "rust/Cargo.toml"),
        ]

    def identity(target: Path) -> int:
        library = next(
            p
            for p in (target / "release").iterdir()
            if p.suffix in (".so", ".dylib", ".dll")
        )
        return int(
            invoke(
                [
                    sys.executable,
                    "-c",
                    "import ctypes,sys; print(ctypes.CDLL(sys.argv[1]).identity())",
                    str(library),
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )

    head_target = repo / "rust/target"
    head_env = dict(os.environ, CARGO_TARGET_DIR=str(head_target))
    invoke(command(repo), env=head_env, check=True, capture_output=True)
    observed = [identity(head_target)]
    baseline_targets: list[Path] = []

    def build(
        args: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        if args[:2] == ["uv", "sync"]:
            # Exercise the real build boundary with a tiny, dependency-free native crate.
            assert env is not None
            baseline_targets.append(Path(env["CARGO_TARGET_DIR"]))
            args = command(Path(args[args.index("--project") + 1]))
        return invoke(args, cwd=cwd, env=env, check=check, capture_output=True)

    with monkeypatch.context() as patch:
        patch.setattr(harness.subprocess, "run", build)
        harness._build(commits[0], base, ("src",))
    observed.append(identity(baseline_targets[0]))
    invoke(command(repo), env=head_env, check=True, capture_output=True)
    observed.append(identity(head_target))
    assert observed == [202, 101, 202]


def test_each_measured_process_starts_with_empty_owned_caches(tmp_path: Path) -> None:
    code = """
from pathlib import Path
import os
from manimgx import _engine
from manimgx.drawing import typesetting as t
root = Path(os.environ['TMPDIR'])
assert Path(_engine.cache_directory()) == root
assert t._CACHE == root / 'layouts'
assert not list(root.iterdir())
t.typeset('a benchmark starts cold')
assert list((root / 'fonts').glob('*.bin'))
assert list((root / 'layouts').glob('*.layout'))
"""
    for run in ("first", "second"):
        directory = tmp_path / f"{run} cache Ω"
        directory.mkdir()
        subprocess.run(
            [sys.executable, "-c", code],
            env=harness._environment(harness.here(), str(directory)),
            check=True,
            capture_output=True,
            timeout=30,
        )


@pytest.mark.parametrize("location", ["checkout/src", "venv/site-packages"])
def test_children_use_the_imported_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    package = tmp_path / location / "manimgx"
    package.mkdir(parents=True)
    init = package / "__init__.py"
    init.write_text("", encoding="utf-8")
    monkeypatch.setattr(manimgx, "__file__", str(init))
    child = subprocess.run(
        [sys.executable, "-c", "import manimgx; print(manimgx.__file__)"],
        env=harness._environment(harness.here(), str(tmp_path)),
        capture_output=True,
        text=True,
        check=True,
    )
    assert Path(child.stdout.strip()).resolve() == init.resolve()


@pytest.mark.parametrize("finish", ["deadline", "caller_error", "success"])
def test_a_render_process_is_reaped_on_every_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, finish: str
) -> None:
    popen = subprocess.Popen
    children: list[subprocess.Popen[str]] = []

    def spawn(*args: object, **kwargs: object) -> subprocess.Popen[str]:
        # Exercise an actual process without paying for a render to test supervision.
        code = "pass" if finish == "success" else "import time; time.sleep(60)"
        child = popen(
            [sys.executable, "-c", code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        children.append(child)
        return child

    monkeypatch.setattr(harness.subprocess, "Popen", spawn)
    monkeypatch.setattr(harness, "TIMEOUT", 0.1 if finish == "deadline" else 30)
    context = harness._launch(
        harness.Tree(tmp_path, "test package"),
        harness.Workload(tmp_path / "scene.py"),
        str(tmp_path),
        subprocess.PIPE,
    )
    if finish == "deadline":
        with (
            pytest.raises(RuntimeError, match=r"timed out rendering scene\.py"),
            context as child,
        ):
            child.communicate()
    elif finish == "caller_error":
        with pytest.raises(ValueError, match="caller failed"), context:
            raise ValueError("caller failed")
    else:
        with context as child:
            child.communicate()
        assert child.returncode == 0
    assert len(children) == 1
    assert children[0].poll() is not None

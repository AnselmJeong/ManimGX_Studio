"""Coverage belongs to the product under test, not another package with the same name."""

import os
import subprocess
import sys
from pathlib import Path

from coverage import CoverageData

ROOT = Path(__file__).resolve().parents[1]


def test_coverage_includes_current_children_and_excludes_reference_packages(
    tmp_path: Path,
) -> None:
    current = tmp_path / "current" / "manimgx"
    reference = tmp_path / "reference" / "manimgx"
    current.mkdir(parents=True)
    reference.mkdir(parents=True)
    (current / "__init__.py").write_text(
        "def parent():\n    return 'parent'\n"
        "def child():\n    return 'child'\n"
        "def unused():\n    return 'unused'\n",
        encoding="utf-8",
    )
    (reference / "__init__.py").write_text(
        "def reference():\n    return 'reference'\n", encoding="utf-8"
    )
    script = tmp_path / "run.py"
    script.write_text(
        "import os, subprocess, sys\n"
        "import manimgx\n"
        "assert manimgx.parent() == 'parent'\n"
        "for package, call in zip(sys.argv[1:], ['child', 'reference']):\n"
        "    subprocess.run([sys.executable, '-c', "
        "f\"import manimgx; assert manimgx.{call}() == '{call}'\"], "
        "env=os.environ | {'PYTHONPATH': package}, check=True)\n",
        encoding="utf-8",
    )
    data_file = tmp_path / ".coverage"
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("COVERAGE_")
    }
    env |= {
        "COVERAGE_FILE": str(data_file),
        "COVERAGE_RCFILE": str(ROOT / "pyproject.toml"),
        "MANIMGX_COVERAGE_SOURCE": str(current),
        "PYTHONPATH": str(current.parent),
    }
    for args in (
        ["run", str(script), str(current.parent), str(reference.parent)],
        ["combine", str(tmp_path)],
    ):
        done = subprocess.run(
            [sys.executable, "-m", "coverage", *args],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, done.stdout + done.stderr
    data = CoverageData(basename=str(data_file))
    data.read()
    measured = str((current / "__init__.py").relative_to(tmp_path))
    assert data.measured_files() == {measured}
    assert set(data.lines(measured) or []) == {1, 2, 3, 4, 5}

"""Run ty over an explicit file set and keep process failures distinct from diagnostics."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_DIAGNOSTIC = re.compile(r"^(?P<path>.+?):(?P<line>\d+):(?P<col>\d+): (?P<rest>.*)$")


def check(
    files: list[Path], flags: tuple[str, ...] = ()
) -> list[tuple[Path, int, int, str]]:
    """(file, line, column, message) for exactly these files, in one ty run."""
    if not files:
        return []
    # ty's response files take one literal argument per line: spaces and backslashes need
    # no shell quoting. An absolute path also cannot be mistaken for an @file or an option.
    with tempfile.TemporaryDirectory() as tmp:
        arguments = Path(tmp) / "files.txt"
        arguments.write_text(
            "".join(f"{path.resolve()}\n" for path in files), encoding="utf-8"
        )
        proc = subprocess.run(
            [sys.executable, "-m", "ty", "check", "--output-format", "concise"]
            + ["--no-progress", *flags, f"@{arguments}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
            check=False,
        )
    if "No python files found" in proc.stdout + proc.stderr:
        msg = "ty checked no files"
        raise RuntimeError(msg)
    if proc.returncode not in (0, 1):
        msg = f"ty failed ({proc.returncode}):\n{proc.stdout}{proc.stderr}"
        raise RuntimeError(msg)
    found: list[tuple[Path, int, int, str]] = []
    for line in proc.stdout.splitlines():
        match = _DIAGNOSTIC.match(line)
        if match:
            path = (ROOT / match["path"]).resolve()
            found.append((path, int(match["line"]), int(match["col"]), match["rest"]))
    return found

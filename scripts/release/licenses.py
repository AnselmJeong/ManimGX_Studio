"""Write LICENSE-THIRD-PARTY: what ManimGX's wheels hold that others hold the
copyright in, with the licenses and notices it comes with, each text once, after what it covers:

- the package's and the engine's files that name others (REUSE: by their SPDX lines, or
  REUSE.toml), with their copyright lines and their licenses' texts from LICENSES/: the modules
  ported from Manim CE, the engine's 3D lighting;
- the crates compiled into the engine, in every build of it a wheel holds, with the license and
  notice files each ships: the workspace's crates, those of the sources they fetch (x264's,
  FFmpeg's and libopus's, mitex's); a crate from crates.io that ships none, its license's text
  from LICENSES/, with its authors on the line the text keeps for them.

And check that ManimGX's `license` (pyproject.toml) covers all of it: that each
part's license is satisfied by the licenses it names. The Linux wheels' lavapipe has a notice of
its own, LICENSE-LAVAPIPE.

`python scripts/release/licenses.py` (`just licenses`) writes it; `--check` fails if it is stale or
something is not covered (tests/test_licenses.py).
"""

import json
import re
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
# the repository's files a wheel holds: the package's, installed as they are, and the engine's,
# compiled into its extension
SOURCES = PurePosixPath("src")
ENGINE_SOURCES = PurePosixPath("rust/engine/src")
OUT = ROOT / "LICENSE-THIRD-PARTY"
ENGINE = ROOT / "rust" / "engine"
# the engine's builds a wheel holds, as (target, features): the extension on each platform a
# wheel is built for (its window too); Pyodide's ([tool.cibuildwheel.pyodide]); and the
# player for a page, which Pyodide's extension carries (rust/engine/build.rs)
BUILDS = (
    ("aarch64-apple-darwin", []),
    ("x86_64-apple-darwin", []),
    ("aarch64-unknown-linux-gnu", []),
    ("x86_64-unknown-linux-gnu", []),
    ("x86_64-pc-windows-msvc", []),
    (
        "wasm32-unknown-emscripten",
        ["--no-default-features", "--features", "python,typeset"],
    ),
    ("wasm32-unknown-unknown", ["--no-default-features", "--features", "web"]),
)
LICENSE_FILE = re.compile(
    r"^(licen[cs]e|copying|notice|unlicense|copyright)", re.IGNORECASE
)
# the line a license's text keeps for the copyright notice: "Copyright (c) <year> <owner>"
TEMPLATE = re.compile(r"^Copyright\b.*<")
# licenses that ask nothing of a binary: no notice, no text
UNASKING = {"0BSD", "BSL-1.0", "CC0-1.0", "MIT-0", "Unlicense"}


def run(*command: str, cwd: Path = ROOT) -> str:
    return subprocess.run(
        command, cwd=cwd, capture_output=True, check=True, text=True, encoding="utf-8"
    ).stdout


def crates(
    directory: Path = ENGINE, builds: tuple[tuple[str, list[str]], ...] = BUILDS
) -> dict[str, dict]:
    """The packages compiled into the selected builds, as `cargo tree` shows them: their
    normal dependencies, all the way down, with the features each build turns on (a build
    script's and a test's are not in it), the workspace's own among them."""
    metadata = json.loads(
        run(
            *("cargo", "metadata", "--format-version", "1", "--locked"),
            "--all-features",
            cwd=directory,
        )
    )
    packages = {(p["name"], p["version"]): p for p in metadata["packages"]}
    linked: dict[str, dict] = {}
    for target, features in builds:
        tree = run(
            *("cargo", "tree", "--locked", "--edges", "normal", "--target", target),
            *(*features, "--prefix", "none", "--format", "{p}"),
            cwd=directory,
        )
        for name, version in re.findall(r"^(\S+) v(\S+)", tree, re.MULTILINE):
            linked[f"{name} {version}"] = packages[name, version]
    return linked


def notice(line: str) -> str:
    """A copyright line as a notice reads it, "Copyright ...", however the file wrote it."""
    return re.sub(r"^SPDX-FileCopyrightText:\s*", "Copyright ", line.strip())


def holder(line: str) -> str:
    """Who a copyright line names, without its years."""
    years = r"(\d{4}(\s*[-,]\s*\d{4})*,?\s+)?"
    return re.sub(
        rf"^(Copyright\s*(\(c\)|©)?\s*)?{years}", "", notice(line), flags=re.I
    )


def others() -> dict[tuple[str, tuple[str, ...]], list[str]]:
    """The package's and the engine's files that others hold copyright in, as REUSE finds
    them (`reuse lint`, which `just check` runs), named as the wheel holds them (the
    engine's, compiled into it, by their path in the repository): by license and copyright
    lines, ManimGX's left out (those of the holder REUSE.toml gives its own files)."""
    reuse = tomllib.loads((ROOT / "REUSE.toml").read_text(encoding="utf-8"))
    own = holder(reuse["annotations"][0]["SPDX-FileCopyrightText"])
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    name = f"manimgx {project['project']['version']}"
    report = subprocess.run(
        [sys.executable, "-m", "reuse", "lint", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    # by license: the files under it, and the copyright lines of all of them
    groups: dict[str, tuple[list[str], set[str]]] = {}
    for file in json.loads(report.stdout)["files"]:
        path = PurePosixPath(file["path"])
        lines = {notice(c["value"]) for c in file["copyrights"]}
        if path.is_relative_to(SOURCES):
            shown = path.relative_to(SOURCES).as_posix()
        elif path.is_relative_to(ENGINE_SOURCES):
            shown = path.as_posix()
        else:
            continue
        if not (theirs := {line for line in lines if holder(line) != own}):
            continue
        expression = " AND ".join(e["value"] for e in file["spdx_expressions"])
        paths, holders = groups.setdefault(expression, ([], set()))
        paths.append(f"{name}: {shown}")
        holders |= theirs
    return {
        (expression, tuple(sorted(holders))): sorted(paths)
        for expression, (paths, holders) in sorted(groups.items())
    }


def options(expression: str) -> list[list[str]]:
    """The sets of licenses that satisfy an SPDX expression, in its order: OR is a choice, AND
    needs both (a license WITH an exception is one; "A/B" is an old way to say A OR B).
    """
    tokens = re.findall(
        r"\(|\)|[\w.+-]+(?: WITH [\w.+-]+)?", expression.replace("/", " OR ")
    )

    def either(at: int) -> tuple[list[list[str]], int]:
        sets, at = both(at)
        while at < len(tokens) and tokens[at] == "OR":
            more, at = both(at + 1)
            sets += more
        return sets, at

    def both(at: int) -> tuple[list[list[str]], int]:
        sets, at = one(at)
        while at < len(tokens) and tokens[at] == "AND":
            more, at = one(at + 1)
            sets = [a + [m for m in b if m not in a] for a in sets for b in more]
        return sets, at

    def one(at: int) -> tuple[list[list[str]], int]:
        if tokens[at] == "(":
            sets, at = either(at + 1)
            return sets, at + 1
        return [[tokens[at]]], at + 1

    return either(0)[0]


def texts(expression: str, holders: list[str], above: bool) -> str | None:
    """The texts, from LICENSES/, of the first licenses that satisfy an expression whose texts
    it holds all of (None if it holds none's), with the copyright lines of what they cover on
    the line a text keeps for them, or else, if `above`, above it."""
    for option in options(expression):
        parts = [
            ROOT / "LICENSES" / f"{p}.txt" for o in option for p in o.split(" WITH ")
        ]
        if not all(part.exists() for part in parts):
            continue
        written = []
        for part in parts:
            lines = clean(part.read_text(encoding="utf-8")).splitlines()
            at = next(
                (i for i, line in enumerate(lines[:5]) if TEMPLATE.match(line)), None
            )
            if at is not None:
                lines[at : at + 1] = holders
            elif above:
                lines[:0] = [*holders, ""]
            written.append("\n".join(lines))
        return "\n\n".join(written)
    return None


def clean(text: str) -> str:
    # as the repository's hooks keep text: no trailing whitespace
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def uncovered(licenses: dict[str, str | None]) -> list[str]:
    """What of the parts given pyproject.toml's `license` does not satisfy the license of."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    named = set(project["project"]["license"].split(" AND "))
    return [
        f"{part} ({expression})"
        for part, expression in sorted(licenses.items())
        if not any(set(option) <= named for option in options(expression or "?"))
    ]


def write(
    linked: dict[str, dict],
    theirs: dict[tuple[str, tuple[str, ...]], list[str]],
    *,
    header: str | None = None,
    include_local: bool = False,
) -> tuple[str, list[str]]:
    """The notice, and what LICENSES/ has no text for."""
    found: dict[str, list[str]] = {}
    missing = []
    for (expression, holders), users in theirs.items():
        if (written := texts(expression, list(holders), above=True)) is None:
            missing += users
            continue
        found.setdefault(written, []).extend(f"{u} ({expression})" for u in users)
    for key, package in sorted(linked.items()):
        folder = Path(package["manifest_path"]).parent
        shipped = sorted(
            f for f in folder.iterdir() if f.is_file() and LICENSE_FILE.match(f.name)
        )
        declared = f"{key} ({package.get('license') or 'no license declared'})"
        for file in shipped:
            written = clean(file.read_text(encoding="utf-8", errors="replace"))
            found.setdefault(written, []).append(f"{declared}: {file.name}")
        # the workspace's own code is ManimGX's (LICENSE)
        if not shipped and (include_local or package["source"] is not None):
            authors = [re.sub(r"\s*<.*?>", "", a) for a in package["authors"]]
            by = ", ".join(authors) or f"the {package['name']} authors"
            expression = package.get("license") or "?"
            written = texts(expression, [f"Copyright (c) {by}"], above=False)
            if written is None and any(
                set(option) <= UNASKING for option in options(expression)
            ):
                written = "(its license asks nothing of a binary)"
            if written is None:
                missing.append(declared)
                continue
            found.setdefault(written, []).append(f"{declared}: no license file")
    header = header or (
        "What ManimGX's wheels hold that others hold the copyright in: modules of its"
        " Python package, files of its engine (its 3D lighting, adapted from Google's"
        " Filament, https://github.com/google/filament), and the crates compiled into"
        " the engine (the extension, on each platform, Pyodide's, and the player for a"
        " page, which the extension carries), with the sources the workspace's crates"
        " fetch; with the licenses"
        " and notices they come with, each text once, after what it covers. FFmpeg is"
        " under the LGPL-2.1-or-later, and x264, in every wheel but Pyodide's, under"
        " the GPL-2.0-or-later, which makes such a wheel, as a whole, GPL-3.0-or-later."
        " Its complete source and build recipes are on the GitHub release of its"
        " version, https://github.com/academa-labs/manimgx/releases/tag/vX.Y.Z for"
        " ManimGX X.Y.Z: manimgx-X.Y.Z-source.tar.xz, ManimGX's committed repository"
        " with every crate rust/Cargo.lock names and each archive a workspace's crate"
        " fetches, with the Linux builds' Mesa/glslang archives and exact distribution"
        " source RPMs. System build tools remain prerequisites. The Linux wheels' lavapipe"
        " is in LICENSE-LAVAPIPE. Written by"
        " scripts/release/licenses.py. The Windows wheels' DXC is in LICENSE-DXC."
    )
    parts = [textwrap.fill(header, 84, break_on_hyphens=False) + "\n"]
    for written, users in sorted(found.items(), key=lambda item: item[1][0]):
        parts.append(
            "=" * 79 + "\n" + "\n".join(users) + "\n" + "-" * 79 + "\n" + written + "\n"
        )
    return "\n".join(parts), missing


def main() -> None:
    if sys.argv[1:2] == ["--crate"]:
        directory, target, output = sys.argv[2:]
        linked = crates(Path(directory), ((target, []),))
        text, missing = write(
            linked,
            {},
            header=f"The crates compiled into the executable's launcher for {target}, "
            "as its own Cargo.lock and default features select them, with the license "
            "and notice files they supply. Its sources and lockfile accompany the release.",
            include_local=True,
        )
        if missing:
            sys.exit(f"LICENSES/ has no text for {', '.join(missing)}")
        Path(output).write_text(text, encoding="utf-8")
        return
    linked = crates()
    theirs = others()
    text, missing = write(linked, theirs)
    problems = [f"LICENSES/ has no text for {', '.join(missing)}"] if missing else []
    licenses = {key: p.get("license") for key, p in linked.items()}
    licenses |= {
        user: expression for (expression, _), us in theirs.items() for user in us
    }
    if not_covered := uncovered(licenses):
        problems.append(
            f"pyproject.toml's license does not cover {', '.join(not_covered)}"
        )
    if "--check" not in sys.argv:
        OUT.write_text(text, encoding="utf-8")
    elif not (OUT.exists() and OUT.read_text(encoding="utf-8") == text):
        problems.append(f"{OUT.relative_to(ROOT)} is stale: just licenses")
    sys.exit("\n".join(problems) or None)


if __name__ == "__main__":
    main()

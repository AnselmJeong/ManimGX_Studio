"""The corpus's three checks, per case.

1. `test_same_source`: both references were rendered from this exact `scene.py`, which is the
   case's only code and reaches the engine only through `manimgx`'s top level (and its types,
   `manimgx.typing`) — so CE and ManimGX ran the same program.
2. `test_types`: the scene is type safe as written for ManimGX — `ty` with every rule, no
   escape from the checker, and no value ManimGX leaves `Any` or `Unknown`.
3. `test_regression`: the scene renders and the product exports it; today's ManimGX holds
   exactly to the latest stable release on this host, including every pixel, frame and
   time, regardless of CE's result or the case's review status. Before the first release,
   rendering and export are checked without a release comparison.

This module only checks. `python -m tests.integration.corpus` renders and reviews.
"""

import ast
import os
import re
import shutil
from pathlib import Path

import pytest
from tests.integration.corpus import release, typecheck
from tests.integration.corpus.case import (
    FPS,
    SIZE,
    Case,
    Failure,
    Frames,
    discover,
)

CASES = discover()
IDS = [case.name for case in CASES]
DIFFS = Path(__file__).resolve().parent / "_diffs"


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_same_source(case: Case) -> None:
    others = sorted(p.name for p in case.dir.glob("*.py") if p.name != "scene.py")
    assert not others, f"a case has one source, scene.py; it also holds {others}"
    imported = _imported(ast.parse(case.scene.read_bytes()))
    direct = sorted({line for line, name in imported if name.split(".")[0] == "manim"})
    assert not direct, f"imports Manim CE directly (lines {direct}): use manimgx"
    inner = sorted(
        {
            line
            for line, name in imported
            if name.startswith("manimgx.") and name != "manimgx.typing"
        }
    )
    assert not inner, f"imports manimgx's modules (lines {inner}): use its top level"
    facts = case.facts()
    assert facts is not None, f"no references yet: just corpus render {case.name}"
    assert facts.source == case.source_hash(), (
        "scene.py changed since its references were rendered: "
        f"just corpus render {case.name}"
    )
    assert (facts.size, facts.fps) == (SIZE, FPS), "rendered at another size or rate"
    for engine in ("manimgx", "ce"):
        if isinstance(facts.render(engine), Frames):
            video = case.video(engine)
            sidecar = case.video_hash(engine)
            assert sidecar.exists(), f"{sidecar.name} is missing"
            digest, separator, filename = (
                sidecar.read_text(encoding="ascii").strip().partition("  ")
            )
            assert separator == "  ", f"{sidecar.name} is malformed"
            assert filename == video.name, f"{sidecar.name} is malformed"
            assert re.fullmatch(r"[0-9a-f]{64}", digest) is not None, (
                f"{sidecar.name} is malformed"
            )


def _imported(tree: ast.Module) -> list[tuple[int, str]]:
    """Each module a scene imports, with the line that imports it."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            found.append((node.lineno, node.module))
    return found


@pytest.fixture(scope="session")
def type_report() -> typecheck.TypeReport:
    return typecheck.report(CASES)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_types(case: Case, type_report: typecheck.TypeReport) -> None:
    problems = type_report.problems(case)
    if problems:
        pytest.fail("\n".join(problems), pytrace=False)


@pytest.fixture(scope="session")
def references(tmp_path_factory: pytest.TempPathFactory) -> release.References:
    manifest = os.environ.get("MANIMGX_CORPUS_RELEASE")
    reference = (
        release.Release.read(Path(manifest)) if manifest else release.Release.latest()
    )
    return release.References(reference, tmp_path_factory.mktemp("reference-packages"))


@pytest.mark.parametrize("case", CASES, ids=IDS)
@pytest.mark.timeout(0)  # engines.run owns each child's deadline and kills/reaps it.
def test_regression(case: Case, references: release.References) -> None:
    output = DIFFS / case.name
    try:
        result = references.compare(case, output)
    except ValueError as error:
        pytest.fail(str(error), pytrace=False)
    if isinstance(result.frames, Failure):
        pytest.fail(
            f"{case.name}: {result.frames.error}; evidence: {output}", pytrace=False
        )
    if result.differences:
        changes = result.differences
        changed = sum(d.repeat for d in changes)
        worst = max(changes, key=lambda d: d.max_channel_difference)
        pytest.fail(
            f"{case.name}: {changed} frames differ from the released package on this host; "
            f"first {changes[0].first}, last {changes[-1].first + changes[-1].repeat - 1}; "
            f"maximum RGB difference {worst.max_channel_difference} at frame {worst.first}; "
            f"evidence: {output}",
            pytrace=False,
        )
    shutil.rmtree(output)

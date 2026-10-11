"""Immutable artifacts and explicit movie fidelity govern baseline promotion."""

import hashlib
import io
import json
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from fractions import Fraction
from pathlib import Path

import pytest
from tests.integration.corpus import baseline, engines
from tests.integration.corpus import case as case_module
from tests.integration.corpus.case import FPS, SIZE, Case, Facts, Failure, Frames
from tests.integration.corpus.frames import Recorder

import manimgx

WHEEL = "manimgx-0.1.0-py3-none-any.whl"


def artifact(content: bytes) -> baseline.Artifact:
    return baseline.Artifact(
        WHEEL, hashlib.sha256(content).hexdigest(), f"https://example.test/{WHEEL}"
    )


def generation() -> baseline.Generation:
    return baseline.Generation(
        "a" * 40, "b" * 64, "c" * 64, "d" * 64, (artifact(b"wheel"),)
    )


def test_invalid_download_never_becomes_a_cached_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = artifact(b"complete wheel")
    monkeypatch.setattr(
        baseline.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: io.BytesIO(b"truncated"),
    )
    with pytest.raises(ValueError, match="SHA256"):
        expected.acquire(tmp_path)
    assert not list(tmp_path.rglob("*.whl"))


def test_concurrent_downloads_repair_a_corrupt_cache_and_then_work_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = b"verified wheel" * 10_000
    expected = artifact(content)
    target = tmp_path / expected.sha256 / expected.filename
    target.parent.mkdir()
    target.write_bytes(b"corrupt previous download")
    downloading = threading.Barrier(4)

    def download(*_args: object, **_kwargs: object) -> io.BytesIO:
        downloading.wait(timeout=10)
        return io.BytesIO(content)

    monkeypatch.setattr(baseline.urllib.request, "urlopen", download)
    with ThreadPoolExecutor(max_workers=4) as workers:
        paths = list(workers.map(lambda _: expected.acquire(tmp_path), range(4)))
    assert paths == [target] * 4
    assert target.read_bytes() == content

    def offline(*_args: object, **_kwargs: object) -> io.BytesIO:
        pytest.fail("a verified cached artifact must not need the network")

    monkeypatch.setattr(baseline.urllib.request, "urlopen", offline)
    assert expected.acquire(tmp_path).read_bytes() == content


def test_same_version_font_edits_invalidate_the_frozen_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "uv.lock").write_bytes(b"unchanged dependency lock")
    font = tmp_path / "fonts" / "font.ttf"
    font.parent.mkdir()
    font.write_bytes(b"original font")
    monkeypatch.setattr(baseline, "ROOT", tmp_path)
    monkeypatch.setattr(baseline.importlib.resources, "files", lambda _: font.parent)
    monkeypatch.setattr(
        baseline, "runtime_lock", lambda: baseline.digest(tmp_path / "uv.lock")
    )
    monkeypatch.setattr(baseline, "execution", lambda: "d" * 64)
    frozen = replace(
        generation(),
        dependency_lock=baseline.digest(tmp_path / "uv.lock"),
        font_payload=baseline.fonts(),
    )
    frozen.validate_runtime()
    font.write_bytes(b"changed font at the same package version")
    with pytest.raises(ValueError, match="font payload changed"):
        frozen.validate_runtime()
    font.write_bytes(b"original font")
    (tmp_path / "uv.lock").write_bytes(b"changed numerical dependency")
    with pytest.raises(ValueError, match="frozen runtime"):
        frozen.validate_runtime()


def test_runtime_closure_ignores_docs_but_binds_numerical_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = baseline.ROOT
    for path in [
        root / "pyproject.toml",
        root / "uv.lock",
        *root.glob("fonts/*/pyproject.toml"),
    ]:
        target = tmp_path / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    monkeypatch.setattr(baseline, "ROOT", tmp_path)
    lock = tmp_path / "uv.lock"
    original = lock.read_text(encoding="utf-8")
    frozen = baseline.runtime_lock()
    for package, unchanged in [("zensical", True), ("numpy", False)]:
        block = re.search(
            rf'\[\[package\]\]\nname = "{package}"\n.*?(?=\n\[\[package\]\]|\Z)',
            original,
            re.DOTALL,
        )
        assert block is not None
        altered, count = re.subn(
            r'hash = "sha256:[0-9a-f]+"',
            f'hash = "sha256:{"0" * 64}"',
            block.group(),
            count=1,
        )
        assert count == 1
        lock.write_text(original.replace(block.group(), altered), encoding="utf-8")
        assert (baseline.runtime_lock() == frozen) is unchanged


def test_catalog_rejects_mutated_generation_identity(tmp_path: Path) -> None:
    frozen = generation()
    catalog = baseline.Catalog({frozen.identity: frozen}, {})
    path = tmp_path / "catalog.json"
    catalog.write(path)
    assert baseline.Catalog.load(path) == catalog
    data = json.loads(path.read_text(encoding="utf-8"))
    data["generations"][frozen.identity]["wheels"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="immutable identity"):
        baseline.Catalog.load(path)


@pytest.fixture
def canonical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Case:
    monkeypatch.setattr(case_module, "CASES", tmp_path / "cases")
    case = Case("square")
    case.dir.mkdir(parents=True)
    case.scene.write_text(
        "import manimgx as m\n"
        "class Example(m.Scene):\n"
        "    def construct(self):\n"
        "        self.add(m.Square(fill_color=m.RED, fill_opacity=1))\n"
        "        self.wait(0.2)\n",
        encoding="utf-8",
    )
    result = engines.run(case, "manimgx", video=case.video("manimgx"))
    assert isinstance(result.frames, Frames), result.frames
    case.write_facts(
        Facts(
            case.source_hash(),
            SIZE,
            FPS,
            result.frames,
            Failure("no CE reference"),
            "",
            None,
        )
    )
    case.video_hash("manimgx").write_text(
        f"{baseline.digest(case.video('manimgx'))}  manimgx.mkv\n", encoding="ascii"
    )
    # Acquisition is tested separately; here the actual installed package is the frozen one.
    package = Path(manimgx.__file__).resolve().parent.parent
    monkeypatch.setattr(
        baseline.References, "generation", lambda _self, _generation: package
    )
    return case


@pytest.mark.parametrize("changed", ["source", "asset", "review", "timing"])
def test_every_case_input_and_existing_review_remains_bound(
    canonical: Case, changed: str
) -> None:
    asset = canonical.dir / "image.ppm"
    asset.write_bytes(b"original input")
    canonical.write_review("working", "reviewed")
    anchor = baseline.Anchor.capture(canonical, generation().identity)
    anchor.validate(canonical)
    if changed == "source":
        canonical.scene.write_bytes(canonical.scene.read_bytes() + b"# changed\n")
    elif changed == "asset":
        asset.write_bytes(b"changed image bytes")
    elif changed == "review":
        canonical.write_review("working", "different review")
    else:
        facts = canonical.facts()
        assert facts is not None
        assert isinstance(facts.manimgx, Frames)
        canonical.write_facts(
            replace(facts, manimgx=replace(facts.manimgx, duration=Fraction(1, 3)))
        )
    with pytest.raises(ValueError, match=r"canonical|review|inputs"):
        anchor.validate(canonical)


def test_selective_promotion_verifies_real_pixels_and_changes_only_the_proposal(
    canonical: Case, tmp_path: Path
) -> None:
    frozen = generation()
    original = baseline.Catalog(
        {frozen.identity: frozen},
        {
            "untouched": baseline.Anchor.capture(canonical, frozen.identity),
        },
    )
    before = {
        path.name: path.read_bytes()
        for path in canonical.dir.iterdir()
        if path.is_file()
    }
    promoted = baseline.promote(original, frozen, [canonical], tmp_path / "promotion")
    assert set(original.cases) == {"untouched"}
    assert promoted.cases["untouched"] == original.cases["untouched"]
    evidence = json.loads(
        (tmp_path / "promotion" / canonical.name / "result.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["duration_exact"] == "1/5"
    assert {
        path.name: path.read_bytes()
        for path in canonical.dir.iterdir()
        if path.is_file()
    } == before
    path = tmp_path / "proposal.json"
    promoted.write(path)
    assert baseline.Catalog.load(path) == promoted
    with pytest.raises(FileExistsError):
        promoted.write(path)


@pytest.mark.parametrize("changed", ["pixels", "timing", "corrupt_movie"])
def test_promotion_cannot_bless_a_package_that_differs_from_the_canonical_movie(
    canonical: Case, tmp_path: Path, changed: str
) -> None:
    facts = canonical.facts()
    assert facts is not None
    assert isinstance(facts.manimgx, Frames)
    if changed == "pixels":
        recorder = Recorder(SIZE, FPS, canonical.video("manimgx"))
        recorder.add(bytes([255]) * (SIZE[0] * SIZE[1] * 3), facts.manimgx.count)
        different = replace(facts.manimgx, runs=recorder.close())
        canonical.write_facts(replace(facts, manimgx=different))
        canonical.video_hash("manimgx").write_text(
            f"{baseline.digest(canonical.video('manimgx'))}  manimgx.mkv\n",
            encoding="ascii",
        )
    elif changed == "timing":
        canonical.write_facts(
            replace(facts, manimgx=replace(facts.manimgx, duration=Fraction(1, 3)))
        )
    else:
        canonical.video("manimgx").write_bytes(b"corrupt movie bytes")
    original = baseline.Catalog({}, {})
    with pytest.raises(ValueError, match=r"does not exactly reproduce|SHA256"):
        baseline.promote(original, generation(), [canonical], tmp_path / "rejected")
    assert asdict(original) == {"generations": {}, "cases": {}}


@pytest.mark.parametrize("changed", ["count", "duration"])
def test_paired_equality_cannot_hide_changed_canonical_timing(
    canonical: Case, tmp_path: Path, changed: str
) -> None:
    facts = canonical.facts()
    assert facts is not None
    assert isinstance(facts.manimgx, Frames)
    frames = facts.manimgx
    if changed == "count":
        frames = replace(
            frames,
            runs=((frames.runs[0][0], frames.count + 1),),
            timeline=((Fraction(0), frames.count + 1),),
        )
    else:
        frames = replace(frames, duration=Fraction(1, 3))
    canonical.write_facts(replace(facts, manimgx=frames))
    package = Path(manimgx.__file__).resolve().parent.parent
    output = tmp_path / "comparison"
    result = baseline.compare(canonical, package, output)
    assert isinstance(result.frames, Failure)
    assert "canonical frame count and timing" in result.frames.error
    assert not (output / "actual.log").exists()


def test_exact_clock_comparison_is_between_packages_on_this_host(
    canonical: Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts = canonical.facts()
    assert facts is not None
    assert isinstance(facts.manimgx, Frames)
    # Both host clocks may differ below the canonical JSON's precision. A candidate-only
    # change must still fail, even when its frame count and archival duration are unchanged.
    host_duration = Fraction(1, 5) + Fraction(1, 10**12)
    reference = engines.Result(
        facts.source,
        facts.manimgx,
        film_frames=facts.manimgx.count,
        mp4_frames=facts.manimgx.count,
        duration=host_duration,
    )
    for changed in (False, True):
        actual = replace(
            reference, duration=host_duration + int(changed) * Fraction(1, 10**12)
        )
        results = iter((reference, actual))
        monkeypatch.setattr(
            engines, "run", lambda *_args, results=results, **_kwargs: next(results)
        )
        compared = baseline.compare(canonical, tmp_path, tmp_path / str(changed))
        assert isinstance(compared.frames, Failure) is changed
        if changed:
            assert isinstance(compared.frames, Failure)
            assert "duration" in compared.frames.error


@pytest.mark.parametrize("platform_newline", ["\n", "\r\n"])
@pytest.mark.parametrize(
    ("module", "before", "after"),
    [
        ("runtime.py", "random.seed(0)", "random.seed(1)"),
        ("frames.py", "frame[:, :, :3]", "frame[:, :, :3] // 2"),
        ("engines.py", 'env["PYTHONHASHSEED"] = "0"', 'env["PYTHONHASHSEED"] = "1"'),
    ],
)
def test_shared_execution_changes_fail_before_acquisition_or_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: str,
    before: str,
    after: str,
    platform_newline: str,
) -> None:
    write_text = Path.write_text

    def platform_write(
        path: Path,
        text: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        # Exercise Windows' default text-write conversion on every host. The execution
        # contract owns bytes, so a mutation test must restore those exact bytes.
        return write_text(
            path,
            text,
            encoding=encoding,
            errors=errors,
            newline=platform_newline if newline is None else newline,
        )

    monkeypatch.setattr(Path, "write_text", platform_write)
    source = baseline.ROOT / "tests" / "integration" / "corpus"
    destination = tmp_path / "tests" / "integration" / "corpus"
    shutil.copytree(source, destination)
    monkeypatch.setattr(baseline, "ROOT", tmp_path)
    monkeypatch.setattr(baseline, "runtime_lock", lambda: "b" * 64)
    monkeypatch.setattr(baseline, "fonts", lambda: "c" * 64)
    frozen = replace(generation(), execution=baseline.execution())
    frozen.validate_runtime()
    for diagnostic in ("__main__.py", "baseline.py", "probe.py"):
        with (destination / diagnostic).open("a", encoding="utf-8") as stream:
            stream.write(
                "\n# A review or diagnostic change does not alter execution.\n"
            )
    frozen.validate_runtime()
    path = destination / module
    original = path.read_bytes()
    assert before.encode() in original
    path.write_bytes(original.replace(before.encode(), after.encode()))

    def acquire(*_args: object, **_kwargs: object) -> Path:
        pytest.fail("a changed shared execution contract must fail before acquisition")

    monkeypatch.setattr(baseline.Artifact, "acquire", acquire)
    with pytest.raises(ValueError, match="execution contract changed"):
        baseline.promote(baseline.Catalog({}, {}), frozen, [], tmp_path / "promotion")
    path.write_bytes(original)
    frozen.validate_runtime()


def test_unbound_execution_generations_require_explicit_freezing() -> None:
    legacy = asdict(generation())
    del legacy["execution"]
    with pytest.raises(ValueError, match="does not bind its execution contract"):
        baseline.Generation.read(legacy)

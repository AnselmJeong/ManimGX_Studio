"""Immutable authoring packages, anchored to the corpus's actual reviewed movies.

A catalog changes only through explicit, selective promotion after complete pixel fidelity.
Its wheel cache is disposable; the committed identities and canonical case files are not.
"""

import hashlib
import importlib.resources
import json
import re
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Self

from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename
from tests.integration.corpus import engines
from tests.integration.corpus.case import (
    ROOT,
    Case,
    Failure,
    Frames,
    _list,
    _object,
    _str,
    frames_to_json,
    pinned,
)
from tests.integration.corpus.frozen import prepare, verify

CACHE = ROOT / ".cache" / "corpus"
_RESERVED = {
    "case.json",
    "review.json",
    "manimgx.mkv",
    "ce.mkv",
    "manimgx.mkv.sha256",
    "ce.mkv.sha256",
}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _sha(value: object) -> str:
    value = _str(value)
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"invalid SHA256: {value!r}")
    return value


def payload(directory: Path, excluded: set[str] | None = None) -> str:
    """Bind names and bytes, excluding only corpus outputs and interpreter caches."""
    ignored = {"__pycache__", ".cache", "media"} | (excluded or set())
    return _hash(
        {
            path.relative_to(directory).as_posix(): digest(path)
            for path in sorted(directory.rglob("*"))
            if path.is_file()
            and not ignored.intersection(path.relative_to(directory).parts)
            and path.suffix not in {".pyc", ".pyo"}
        }
    )


def fonts() -> str:
    """Hash the installed packages' actual payloads, including editable workspace fonts."""
    return _hash(
        {
            name: payload(Path(str(importlib.resources.files(name))))
            for name in ("manimgx_fonts", "manimgx_fonts_cjk")
        }
    )


def runtime_lock() -> str:
    """Hash uv's resolved runtime closure, independently of documentation and test tools.

    This binds the intended environment. CI must first install it with frozen sync; merely
    using ``--no-sync`` does not prove which packages are installed. Workspace fonts are
    bound by their actual payloads, and the product itself by its immutable wheel hash.
    Explicitly named system fonts and the adapter remain shared host inputs.
    """
    result = subprocess.run(
        [
            "uv",
            "export",
            "--frozen",
            "--package",
            "manimgx",
            "--no-default-groups",
            "--no-emit-workspace",
            "--no-header",
            "--no-annotate",
            "--format",
            "requirements-txt",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(
            "cannot export the frozen runtime: "
            + result.stderr.decode("utf-8", errors="replace")
        )
    return hashlib.sha256(result.stdout).hexdigest()


def execution() -> str:
    """Bind the shared process, authoring and observation contract, excluding review tools.

    Both packages run through this code, so changing it can otherwise alter both sides
    together without changing the scene or either wheel. A change requires a new canonical
    movie proof, just as a change to the numerical runtime does.
    """
    directory = ROOT / "tests" / "integration" / "corpus"
    return _hash(
        {
            name: digest(directory / name)
            for name in (
                "case.py",
                "engines.py",
                "frames.py",
                "frozen.py",
                "run_manimgx.py",
                "runtime.py",
            )
        }
    )


@dataclass(frozen=True, slots=True)
class Artifact:
    filename: str
    sha256: str
    url: str

    def __post_init__(self) -> None:
        _sha(self.sha256)
        if Path(self.filename).name != self.filename or "\\" in self.filename:
            raise ValueError("an artifact filename must be a single path component")
        if parse_wheel_filename(self.filename)[0] != "manimgx":
            raise ValueError("a reference artifact must be a manimgx wheel")
        if not self.url.startswith("https://"):
            raise ValueError("reference artifacts require an HTTPS URL")

    def acquire(self, cache: Path) -> Path:
        """Publish only a verified complete download, recovering from corrupt cache bytes."""
        target = cache / self.sha256 / self.filename
        if target.exists():
            try:
                verify(target, self.sha256)
                return target
            except ValueError:
                pass
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
            fresh = Path(temporary) / self.filename
            with (
                urllib.request.urlopen(self.url, timeout=60) as source,
                fresh.open("wb") as output,
            ):
                shutil.copyfileobj(source, output)
            verify(fresh, self.sha256)
            try:
                fresh.replace(target)
            except OSError:
                # Another process may already be reading the identical published wheel.
                # A failed publication is successful only if those bytes are verified too.
                verify(target, self.sha256)
        return target


@dataclass(frozen=True, slots=True)
class Generation:
    commit: str
    dependency_lock: str
    font_payload: str
    execution: str
    wheels: tuple[Artifact, ...]

    def __post_init__(self) -> None:
        if re.fullmatch(r"[0-9a-f]{40}", self.commit) is None:
            raise ValueError("a reference generation requires a full commit SHA")
        _sha(self.dependency_lock)
        _sha(self.font_payload)
        _sha(self.execution)
        if not self.wheels or len({wheel.filename for wheel in self.wheels}) != len(
            self.wheels
        ):
            raise ValueError("a generation requires distinct wheel artifacts")

    @property
    def identity(self) -> str:
        return _hash(asdict(self))

    def wheel(self) -> Artifact:
        supported = list(sys_tags())
        order = {tag: index for index, tag in enumerate(supported)}
        ranked = [
            (min(order[tag] for tag in tags if tag in order), wheel)
            for wheel in self.wheels
            if (tags := parse_wheel_filename(wheel.filename)[3]).intersection(order)
        ]
        if not ranked:
            raise ValueError(
                "the reference generation has no wheel for this Python/platform"
            )
        return min(ranked, key=lambda pair: pair[0])[1]

    def validate_runtime(self) -> None:
        if self.execution != execution():
            raise ValueError(
                "the reference execution contract changed: review and promote its canonical "
                "movies before accepting changes to process launch, authoring or observation"
            )
        if self.dependency_lock != runtime_lock() or self.font_payload != fonts():
            raise ValueError(
                "the reference dependencies or font payload changed: use its frozen runtime "
                "or review a new baseline before accepting the change"
            )

    @classmethod
    def read(cls, value: object) -> Self:
        data = _object(value)
        if "execution" not in data:
            raise ValueError(
                "the reference generation does not bind its execution contract"
            )
        wheels = []
        for value in _list(data["wheels"]):
            item = _object(value)
            wheels.append(
                Artifact(
                    _str(item["filename"]), _sha(item["sha256"]), _str(item["url"])
                )
            )
        return cls(
            _str(data["commit"]),
            _sha(data["dependency_lock"]),
            _sha(data["font_payload"]),
            _sha(data["execution"]),
            tuple(wheels),
        )


@dataclass(frozen=True, slots=True)
class Anchor:
    generation: str
    inputs: str
    render: str
    movie: str
    review: str | None

    @classmethod
    def capture(cls, case: Case, generation: str) -> Self:
        facts = case.facts()
        if (
            facts is None
            or not case.current(facts)
            or not isinstance(facts.manimgx, Frames)
        ):
            raise ValueError(
                f"{case.name}: current canonical manimgx facts are required"
            )
        review = case.review()
        if review is not None and not pinned(review, facts):
            raise ValueError(f"{case.name}: the existing review is stale")
        checksum, separator, name = (
            case.video_hash("manimgx")
            .read_text(encoding="ascii")
            .strip()
            .partition("  ")
        )
        if separator != "  " or name != case.video("manimgx").name:
            raise ValueError(f"{case.name}: malformed canonical movie checksum")
        return cls(
            generation,
            payload(case.dir, _RESERVED),
            _hash([facts.source, facts.size, facts.fps, frames_to_json(facts.manimgx)]),
            _sha(checksum),
            digest(case.review_path) if review is not None else None,
        )

    def validate(self, case: Case) -> None:
        if self != self.capture(case, self.generation):
            raise ValueError(
                f"{case.name}: inputs, canonical facts, movie identity or review changed; promote it explicitly"
            )


@dataclass(frozen=True, slots=True)
class Catalog:
    generations: dict[str, Generation]
    cases: dict[str, Anchor]

    @classmethod
    def load(cls, path: Path) -> Self:
        data = _object(json.loads(path.read_text(encoding="utf-8")))
        if data.get("version") != 1:
            raise ValueError("unsupported baseline catalog version")
        generations = {
            key: Generation.read(value)
            for key, value in _object(data["generations"]).items()
        }
        if any(key != generation.identity for key, generation in generations.items()):
            raise ValueError(
                "a reference generation does not match its immutable identity"
            )
        cases = {}
        for name, value in _object(data["cases"]).items():
            item = _object(value)
            anchor = Anchor(
                _sha(item["generation"]),
                _sha(item["inputs"]),
                _sha(item["render"]),
                _sha(item["movie"]),
                None if item["review"] is None else _sha(item["review"]),
            )
            if anchor.generation not in generations:
                raise ValueError(f"{name}: unknown reference generation")
            cases[name] = anchor
        return cls(generations, cases)

    def write(self, path: Path) -> None:
        """Write a reviewable staged catalog; never overwrite an existing proposal."""
        with path.open("x", encoding="utf-8") as stream:
            json.dump({"version": 1, **asdict(self)}, stream, indent=2, sort_keys=True)
            stream.write("\n")


class References:
    """One verified extraction per generation for a test worker or promotion session."""

    def __init__(self, catalog: Catalog, directory: Path, cache: Path = CACHE) -> None:
        self.catalog, self.directory, self.cache = catalog, directory, cache
        self._packages: dict[str, Path] = {}

    def generation(self, generation: Generation) -> Path:
        identity = generation.identity
        if identity not in self._packages:
            generation.validate_runtime()
            wheel = generation.wheel()
            package = prepare(
                wheel.acquire(self.cache), wheel.sha256, self.directory / identity
            )
            self._packages[identity] = package
        return self._packages[identity]

    def package(self, case: Case) -> Path:
        if case.name not in self.catalog.cases:
            raise ValueError(f"{case.name}: no promoted reference baseline")
        anchor = self.catalog.cases[case.name]
        anchor.validate(case)
        return self.generation(self.catalog.generations[anchor.generation])

    def compare(self, case: Case, output: Path) -> engines.Result:
        result = compare(case, self.package(case), output)
        self.catalog.cases[case.name].validate(case)
        return result


def promote(
    catalog: Catalog,
    generation: Generation,
    cases: list[Case],
    directory: Path,
    cache: Path = CACHE,
) -> Catalog:
    """Stage selected mappings only after the frozen package matches each canonical movie.

    This never renders a replacement canonical movie or rewrites a case or review. Intended
    visual changes must already have been reviewed and made canonical before calling it.
    """
    references = References(catalog, directory / "packages", cache)
    package = references.generation(generation)
    anchors = dict(catalog.cases)
    for case in cases:
        before = Anchor.capture(case, generation.identity)
        verify(case.video("manimgx"), before.movie)
        facts = case.facts()
        assert facts is not None
        assert isinstance(facts.manimgx, Frames)
        output = directory / case.name
        output.mkdir(parents=True)
        reference = output / "canonical.json"
        reference.write_text(
            json.dumps(frames_to_json(facts.manimgx)), encoding="utf-8"
        )
        result = engines.run(
            case,
            "manimgx",
            package=package,
            reference=reference,
            reference_video=case.video("manimgx"),
            mp4=True,
            differences=output,
            log=output / "promotion.log",
        )
        if isinstance(result.frames, Failure):
            raise ValueError(f"{case.name}: {result.frames.error}")
        if (
            result.source != facts.source
            or result.differences
            or result.frames != facts.manimgx
            or result.film_frames != result.mp4_frames
            or result.film_frames != facts.manimgx.count
            or result.duration is None
        ):
            raise ValueError(
                f"{case.name}: the frozen package does not exactly reproduce its canonical movie and timing"
            )
        before.validate(case)
        (output / "result.json").write_text(
            json.dumps(
                {
                    "source": result.source,
                    "duration_exact": str(result.duration),
                    "render": frames_to_json(result.frames),
                    "film_frames": result.film_frames,
                    "mp4_frames": result.mp4_frames,
                    "adapter": result.adapter,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        anchors[case.name] = before
    return Catalog(catalog.generations | {generation.identity: generation}, anchors)


def compare(
    case: Case, package: Path, output: Path, *, source: Path | None = None
) -> engines.Result:
    """Run one baseline and one candidate through the same isolated execution boundary."""
    output.mkdir(parents=True, exist_ok=True)
    facts = case.facts()
    if not case.current(facts):
        return engines.Result(
            None, Failure("the scene source differs from its canonical facts")
        )
    baseline = engines.run(
        case,
        "manimgx",
        package=package,
        video=output / "reference.mkv",
        log=output / "reference.log",
        compact_video=False,
    )
    if isinstance(baseline.frames, Failure):
        return baseline
    if facts is None or baseline.source != facts.source:
        return replace(
            baseline, frames=Failure("the source changed while the reference rendered")
        )
    if (
        not isinstance(facts.manimgx, Frames)
        or baseline.frames.count != facts.manimgx.count
        or baseline.frames.duration != facts.manimgx.duration
        or baseline.frames.timeline != facts.manimgx.timeline
    ):
        return replace(
            baseline,
            frames=Failure(
                "the frozen package does not preserve canonical frame count and timing on this host"
            ),
        )
    reference = output / "reference.json"
    reference.write_text(json.dumps(frames_to_json(baseline.frames)), encoding="utf-8")
    actual = engines.run(
        case,
        "manimgx",
        mp4=True,
        reference=reference,
        source=source,
        differences=output,
        log=output / "actual.log",
    )
    if isinstance(actual.frames, Failure):
        return actual
    if source is None and actual.source != baseline.source:
        return replace(
            actual, frames=Failure("the source changed between the two renders")
        )
    if baseline.adapter != actual.adapter:
        return replace(
            actual, frames=Failure("the baseline and candidate used different adapters")
        )
    if baseline.duration is None or baseline.duration != actual.duration:
        return replace(
            actual,
            frames=Failure(f"duration {actual.duration}, expected {baseline.duration}"),
        )
    if baseline.frames.timeline != actual.frames.timeline:
        return replace(
            actual, frames=Failure("the candidate changed the reference timeline")
        )
    if not (
        baseline.frames.count
        == actual.frames.count
        == actual.film_frames
        == actual.mp4_frames
    ):
        return replace(
            actual,
            frames=Failure(
                f"frame counts differ: reference={baseline.frames.count}, callbacks={actual.frames.count}, film={actual.film_frames}, MP4={actual.mp4_frames}"
            ),
        )
    return actual

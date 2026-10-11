"""Stable releases supply corpus references; the first release still checks real exports."""

import hashlib
import io
import json
import urllib.error
from dataclasses import asdict
from email.message import Message
from fractions import Fraction
from pathlib import Path

import pytest
from tests.integration.corpus import engines, release
from tests.integration.corpus.case import Case, Failure, Frames

WHEEL = "manimgx-0.1.0-py3-none-any.whl"


def published() -> dict[str, object]:
    return {
        "tag_name": "v0.1.0",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": WHEEL,
                "digest": "sha256:" + hashlib.sha256(b"wheel").hexdigest(),
                "browser_download_url": f"{release.DOWNLOADS}v0.1.0/{WHEEL}",
            },
        ],
    }


def response(monkeypatch: pytest.MonkeyPatch, data: object) -> None:
    monkeypatch.setattr(
        release.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: io.BytesIO(json.dumps(data).encode()),
    )


def test_release_selects_authenticated_compatible_wheel_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    response(monkeypatch, published())
    current = release.Release.latest()
    assert current is not None
    assert current.tag == "v0.1.0"
    assert current.wheel().filename == WHEEL
    manifest = tmp_path / "release.json"
    manifest.write_text(json.dumps(asdict(current)), encoding="utf-8")
    assert release.Release.read(manifest) == current
    manifest.write_text("null\n", encoding="utf-8")
    assert release.Release.read(manifest) is None


@pytest.mark.parametrize("status", [404, 403, 429, 500])
def test_only_absent_release_allows_bootstrap(
    status: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(*_args: object, **_kwargs: object) -> None:
        raise urllib.error.HTTPError(release.LATEST, status, "error", Message(), None)

    monkeypatch.setattr(release.urllib.request, "urlopen", missing)
    if status == 404:
        assert release.Release.latest() is None
    else:
        with pytest.raises(urllib.error.HTTPError):
            release.Release.latest()


@pytest.mark.parametrize(
    ("field", "value"),
    [("draft", True), ("prerelease", True), ("tag_name", "v0.1.0rc1"), ("assets", [])],
)
def test_incomplete_or_unpublished_release_is_not_bootstrap(
    field: str, value: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = published() | {field: value}
    response(monkeypatch, data)
    with pytest.raises(ValueError, match=r"stable|no ManimGX wheels"):
        release.Release.latest()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("digest", "sha256:invalid"),
        ("digest", "md5:" + "0" * 32),
        ("browser_download_url", "https://example.test/wheel.whl"),
        ("name", "manimgx-0.2.0-py3-none-any.whl"),
    ],
)
def test_invalid_release_asset_fails_closed(
    field: str, value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = published()
    assets = data["assets"]
    assert isinstance(assets, list)
    assets[0][field] = value
    response(monkeypatch, data)
    with pytest.raises(ValueError, match=r"SHA256|download URL|version"):
        release.Release.latest()


def test_missing_platform_wheel_fails() -> None:
    current = release.Release("v0.1.0", ())
    with pytest.raises(ValueError, match="no wheel"):
        current.wheel()


@pytest.mark.parametrize("outcome", ["success", "render-error", "dropped-export-frame"])
def test_bootstrap_renders_and_checks_the_actual_export(
    outcome: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frames = Frames((("pixels", 2),), Fraction(1, 5), ((Fraction(0), 2),))
    result = engines.Result(
        "source",
        Failure("render failed") if outcome == "render-error" else frames,
        film_frames=2,
        mp4_frames=1 if outcome == "dropped-export-frame" else 2,
    )
    calls = []

    def run(case: Case, engine: str, **kwargs: object) -> engines.Result:
        calls.append((case, engine, kwargs))
        return result

    monkeypatch.setattr(release.engines, "run", run)
    reference = release.References(None, tmp_path / "packages")
    case = Case("example")
    output = tmp_path / "evidence"
    actual = reference.compare(case, output)
    assert calls == [(case, "manimgx", {"mp4": True, "log": output / "actual.log"})]
    assert isinstance(actual.frames, Failure) is (outcome != "success")
    assert (
        json.loads((output / "reference.json").read_text(encoding="utf-8"))["release"]
        is None
    )


def test_released_wheel_is_verified_and_compared_once_per_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    response(monkeypatch, published())
    current = release.Release.latest()
    assert current is not None
    wheel = current.wheel()
    acquired, prepared, compared = [], [], []
    package = tmp_path / "package"

    def acquire(self: release.baseline.Artifact, cache: Path) -> Path:
        acquired.append((self, cache))
        return tmp_path / self.filename

    def prepare(path: Path, digest: str, directory: Path) -> Path:
        prepared.append((path, digest, directory))
        return package

    def compare(case: Case, candidate: Path, output: Path) -> engines.Result:
        compared.append((case, candidate, output))
        return engines.Result("source", Failure("detected regression"))

    monkeypatch.setattr(release.baseline.Artifact, "acquire", acquire)
    monkeypatch.setattr(release, "prepare", prepare)
    monkeypatch.setattr(release.baseline, "compare", compare)
    reference = release.References(current, tmp_path / "packages")
    for name in ("one", "two"):
        output = tmp_path / name
        result = reference.compare(Case(name), output)
        assert result.frames == Failure("detected regression")
        assert (
            json.loads((output / "release.json").read_text(encoding="utf-8"))["sha256"]
            == wheel.sha256
        )
    assert len(acquired) == 1
    assert len(prepared) == 1
    assert compared == [
        (Case(name), package, tmp_path / name) for name in ("one", "two")
    ]

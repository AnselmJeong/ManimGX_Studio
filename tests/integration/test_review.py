"""The review panel must show and approve the evidence it identifies."""

import io
import os
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest
from fastapi import HTTPException
from PIL import Image
from tests.integration.corpus import case as corpus
from tests.integration.corpus.frames import Recorder, frame_hash
from tests.integration.review import app as panel


@pytest.fixture
def case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> corpus.Case:
    monkeypatch.setattr(corpus, "CASES", tmp_path)
    monkeypatch.setattr(corpus, "SIZE", (8, 8))
    example = corpus.Case("first")
    example.dir.mkdir()
    example.scene.write_text("value: int = 1\n", encoding="utf-8")
    panel._frames.cache_clear()
    panel._png.cache_clear()
    return example


def movie(case: corpus.Case, color: tuple[int, int, int]) -> corpus.Frames:
    recorder = Recorder((8, 8), 10, case.video("manimgx"), compact=False)
    recorder.add(bytes(color) * 64)
    return corpus.Frames(recorder.close(), Fraction(1, 10), ((Fraction(0), 1),))


def test_frame_url_identifies_decoded_pixels_not_recorded_frame_position(
    case: corpus.Case,
) -> None:
    red = movie(case, (255, 0, 0))
    case.write_facts(
        corpus.Facts(case.source_hash(), (8, 8), 10, red, red, "test", None)
    )
    blue = movie(case, (0, 0, 255))
    with pytest.raises(HTTPException) as missing:
        panel.read_frame(case.name, "manimgx", red.hashes()[0])
    assert missing.value.status_code == 404
    response = panel.read_frame(case.name, "manimgx", blue.hashes()[0])
    assert response.media_type == "image/png"
    pixels = Image.open(io.BytesIO(bytes(response.body))).convert("RGB").tobytes()
    assert frame_hash(pixels) == blue.hashes()[0]
    assert "immutable" in response.headers["cache-control"]


@pytest.mark.parametrize("change", ["rename", "edit"])
def test_type_report_cache_tracks_source_and_case_identity(
    case: corpus.Case, change: str
) -> None:
    reports = panel.TypeReports()
    case.scene.write_text('value: int = "wrong"\n', encoding="utf-8")
    before = reports.get([case])
    assert before.problems(case)
    stamp = case.scene.stat()
    if change == "rename":
        case.dir.rename(case.dir.with_name("renamed"))
        case = corpus.Case("renamed")
    else:
        case.scene.write_text("value: int = 1\n", encoding="utf-8")
        os.utime(case.scene, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert case.scene.stat().st_mtime_ns == stamp.st_mtime_ns
    after = reports.get([case])
    assert after is not before
    assert bool(after.problems(case)) == (change == "rename")
    assert reports.get([case]) is after


@pytest.mark.parametrize("change", ["pixels", "duration", "timeline"])
def test_review_rejects_changed_evidence_and_saved_approval_becomes_stale(
    case: corpus.Case, change: str
) -> None:
    red = movie(case, (255, 0, 0))
    facts = corpus.Facts(case.source_hash(), (8, 8), 10, red, red, "test", None)
    case.write_facts(facts)
    shown = panel.read_case(case.name)
    assert shown.revision is not None
    body = panel.ReviewIn(revision=shown.revision, verdict="working", note="saw red")
    assert panel.review_case(case.name, body).reviewed
    review = case.review()
    assert review is not None
    assert corpus.pinned(review, facts)
    if change == "pixels":
        changed = movie(case, (0, 0, 255))
    elif change == "duration":
        changed = replace(red, duration=Fraction(1, 5))
    else:
        changed = replace(red, timeline=((Fraction(1, 10), 1),))
    newer = replace(facts, manimgx=changed)
    case.write_facts(newer)
    assert not corpus.pinned(review, newer)
    with pytest.raises(HTTPException) as stale:
        panel.review_case(case.name, body)
    assert stale.value.status_code == 409
    assert "changed" in str(stale.value.detail)
    assert case.review() == review
    current = panel.read_case(case.name)
    assert current.stale_review
    assert not current.reviewed


def test_review_checks_and_pins_one_facts_snapshot(
    case: corpus.Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    red = movie(case, (255, 0, 0))
    facts = corpus.Facts(case.source_hash(), (8, 8), 10, red, red, "test", None)
    changed = replace(facts, manimgx=replace(red, duration=Fraction(1)))
    reads = 0

    def changing_facts(_: corpus.Case) -> corpus.Facts:
        nonlocal reads
        reads += 1
        return facts if reads == 1 else changed

    monkeypatch.setattr(corpus.Case, "facts", changing_facts)
    review = case.write_review("working", "saw red", expected=facts.revision())
    assert review is not None
    assert reads == 1
    assert corpus.pinned(review, facts)
    assert not corpus.pinned(review, changed)


def test_legacy_review_keeps_its_note_but_cannot_approve_unbound_timing(
    case: corpus.Case,
) -> None:
    red = movie(case, (255, 0, 0))
    facts = corpus.Facts(case.source_hash(), (8, 8), 10, red, red, "test", None)
    legacy = corpus.review_from_json(
        {
            "source": facts.source,
            "manimgx": facts.identity("manimgx"),
            "ce": facts.identity("ce"),
            "verdict": "working",
            "note": "the original review",
            "at": "2026-10-01",
        }
    )
    assert legacy.note == "the original review"
    assert legacy.verdict == "working"
    assert not corpus.pinned(legacy, facts)

"""The review panel's server: the corpus as JSON, frames as PNG, and what a reviewer changes —
a verdict, the settings, a fresh render. It serves the built panel (`web/dist`) too.

    just review            # build the panel, then serve both at http://127.0.0.1:8000
    uv run fastapi dev     # the server alone, reloading (`bun run dev` in web/ for the panel)
"""

import io
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel
from tests.integration.corpus import references, typecheck
from tests.integration.corpus.case import (
    FPS,
    METRICS,
    Case,
    Engine,
    Failure,
    Frames,
    Settings,
    State,
    Verdict,
    discover,
    pinned,
    save_settings,
    settings,
)
from tests.integration.corpus.compare import slots
from tests.integration.corpus.frames import Pixels, decode, frame_hash

PANEL = Path(__file__).resolve().parent / "web" / "dist"


# ── the API's shapes ──────────────────────────────────────────────────────────


class Checks(BaseModel):
    source: bool  # both references were rendered from this exact scene.py
    types: bool  # strict ty, no escapes, no Any/Unknown from ManimGX


class CaseSummary(BaseModel):
    name: str
    state: State  # a current review's verdict, else the comparison's
    auto: State  # the comparison's alone
    reviewed: bool
    noted: bool
    checks: Checks
    worst: (
        float | None
    )  # the largest error of any same-time pair, in the current metric


class Render(BaseModel):
    version: str
    frames: list[str]  # each frame's hash, in order
    duration: float | None
    error: str | None


class Slot(BaseModel):
    time: float
    ce: int | None
    ce_time: float | None  # the scene time CE's frame shows (up to a frame earlier)
    manimgx: int | None
    errors: dict[str, float] | None  # per metric, when both engines show this time


class Review(BaseModel):
    verdict: Verdict | None  # None: a note, and the comparison's verdict stands
    note: str
    at: str


class CaseDetail(CaseSummary):
    revision: str | None  # the exact facts shown, required when saving a review
    source: str
    problems: list[str]
    manimgx: Render
    ce: Render
    slots: list[Slot]
    reasons: list[str]  # why the comparison differs, under the current settings
    review: Review | None
    stale_review: bool  # the review was given for other renders


class ReviewIn(BaseModel):
    revision: str
    verdict: Verdict | Literal["auto"]
    note: str = ""


class RenderIn(BaseModel):
    engine: Literal["manimgx", "ce", "both"] = "both"


@dataclass(frozen=True, slots=True)
class SettingsOut(Settings):
    metrics: list[str]


# ── the type report: made once, again when a scene changes ────────────────────


class TypeReports:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._report: typecheck.TypeReport | None = None
        self._made_for: tuple[tuple[str, str], ...] = ()

    def get(self, cases: list[Case]) -> typecheck.TypeReport:
        stamp = tuple((case.name, case.source_hash()) for case in cases)
        with self._lock:
            if self._report is None or stamp != self._made_for:
                self._report, self._made_for = typecheck.report(cases), stamp
            return self._report


types = TypeReports()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    types.get(discover())  # a few seconds, once, before the first request
    yield


app = FastAPI(title="ManimGX corpus review", lifespan=lifespan)


# ── the corpus ────────────────────────────────────────────────────────────────


def _case(name: str) -> Case:
    case = Case(name)
    if not case.scene.exists():
        raise HTTPException(status_code=404, detail=f"no case named {name!r}")
    return case


def _summary(
    case: Case, current: Settings, report: typecheck.TypeReport
) -> CaseSummary:
    standing = case.standing(current)
    facts, review = standing.facts, standing.review
    worst = None
    if facts is not None and facts.comparison is not None:
        worst = round(facts.comparison.worst(current.metric), 2)
    return CaseSummary(
        name=case.name,
        state=standing.state,
        auto=standing.auto,
        reviewed=standing.reviewed,
        noted=review is not None and bool(review.note),
        checks=Checks(source=case.current(facts), types=not report.problems(case)),
        worst=worst,
    )


def _render(render: Frames | Failure | None, version: str) -> Render:
    if isinstance(render, Frames):
        return Render(
            version=version,
            frames=render.hashes(),
            duration=float(render.duration),
            error=None,
        )
    return Render(
        version=version,
        frames=[],
        duration=None,
        error="not rendered" if render is None else render.error,
    )


def _detail(case: Case) -> CaseDetail:
    current = settings()
    report = types.get(discover())
    summary = _summary(case, current, report)
    facts = case.facts()
    review = case.review()
    manimgx = None if facts is None else facts.manimgx
    ce = None if facts is None else facts.ce
    errors: dict[tuple[int, int], dict[str, float]] = {}
    if facts is not None and facts.comparison is not None:
        for i, k, measured in facts.comparison.pairs:
            errors[(i, k)] = dict(zip(METRICS, measured, strict=True))
    timeline = slots(
        ce if isinstance(ce, Frames) else None,
        manimgx if isinstance(manimgx, Frames) else None,
        FPS if facts is None else facts.fps,
    )
    return CaseDetail(
        **summary.model_dump(),
        revision=None if facts is None else facts.revision(),
        source=case.scene.read_text(encoding="utf-8"),
        problems=report.problems(case),
        manimgx=_render(manimgx, ""),
        ce=_render(ce, "" if facts is None else facts.ce_version),
        slots=[
            Slot(
                time=float(s.time),
                ce=s.ce,
                ce_time=None if s.ce_time is None else float(s.ce_time),
                manimgx=s.manimgx,
                errors=(
                    errors.get((s.ce, s.manimgx))
                    if s.ce is not None and s.manimgx is not None
                    else None
                ),
            )
            for s in timeline
        ],
        reasons=[] if facts is None else list(facts.reasons(current)),
        review=(
            None
            if review is None
            else Review(verdict=review.verdict, note=review.note, at=review.at)
        ),
        stale_review=review is not None
        and (facts is None or not pinned(review, facts)),
    )


@app.get("/api/cases")
def list_cases() -> list[CaseSummary]:
    cases = discover()
    current, report = settings(), types.get(cases)
    return [_summary(case, current, report) for case in cases]


@app.get("/api/sources")
def list_sources() -> dict[str, str]:
    return {case.name: case.scene.read_text(encoding="utf-8") for case in discover()}


@app.get("/api/cases/{name}")
def read_case(name: str) -> CaseDetail:
    return _detail(_case(name))


@app.put("/api/cases/{name}/review")
def review_case(name: str, body: ReviewIn) -> CaseDetail:
    case = _case(name)
    verdict = None if body.verdict == "auto" else body.verdict
    try:
        case.write_review(verdict, body.note, expected=body.revision)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _detail(case)


_rendering = threading.Lock()


@app.post("/api/cases/{name}/render")
def render_case(name: str, body: RenderIn) -> CaseDetail:
    case = _case(name)
    wanted: set[Engine] = {"manimgx", "ce"} if body.engine == "both" else {body.engine}
    with _rendering:  # one render at a time: each takes most of the machine it asks for
        references.render(case, wanted)
    return _detail(case)


@app.get("/api/settings")
def read_settings() -> SettingsOut:
    current = settings()
    return SettingsOut(
        metric=current.metric, tolerance=current.tolerance, metrics=list(METRICS)
    )


@app.put("/api/settings")
def write_settings(body: Settings) -> SettingsOut:
    save_settings(body)
    return read_settings()


# ── frames ────────────────────────────────────────────────────────────────────

_decoding = threading.Lock()


@lru_cache(maxsize=6)
def _frames(name: str, engine: Engine, stamp: int) -> dict[str, Pixels]:
    """Each distinct frame of a case's video, by hash (`stamp`: the file's mtime)."""
    case = Case(name)
    facts = case.facts()
    render = None if facts is None else facts.render(engine)
    if facts is None or not isinstance(render, Frames):
        return {}
    found: dict[str, Pixels] = {}
    for pixels in decode(case.video(engine), facts.size):
        found.setdefault(frame_hash(pixels.tobytes()), pixels)
    return found


@lru_cache(maxsize=512)
def _png(name: str, engine: Engine, frame: str, stamp: int) -> bytes | None:
    with _decoding:
        pixels = _frames(name, engine, stamp).get(frame)
    if pixels is None:
        return None
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="PNG", compress_level=1)
    return buffer.getvalue()


@app.get("/api/cases/{name}/frames/{engine}/{frame}.png")
def read_frame(name: str, engine: Engine, frame: str) -> Response:
    video = _case(name).video(engine)
    png = (
        _png(name, engine, frame, video.stat().st_mtime_ns) if video.exists() else None
    )
    if png is None:
        raise HTTPException(status_code=404, detail=f"no {engine} frame {frame}")
    # a frame's URL is its pixels' hash: it never changes
    headers = {"Cache-Control": "public, max-age=31536000, immutable"}
    return Response(content=png, media_type="image/png", headers=headers)


# the panel itself, once built (`bun run build` in web/)
if PANEL.exists():
    app.mount("/", StaticFiles(directory=PANEL, html=True), name="panel")

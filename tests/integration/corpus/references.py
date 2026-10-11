"""Making a case's references: render each engine, keep a video only when its pixels change,
compare the two, and record the facts."""

import hashlib
import importlib.metadata
import importlib.util
import shutil
import tempfile
from pathlib import Path

from tests.integration.corpus import compare as comparing
from tests.integration.corpus import engines
from tests.integration.corpus.case import (
    ENGINES,
    FPS,
    SIZE,
    Case,
    Comparison,
    Engine,
    Facts,
    Failure,
    Frames,
)


def render(case: Case, wanted: set[Engine]) -> tuple[Facts, str]:
    """Render `case` with the wanted engines (both when its source changed), compare, and
    record the facts; them, and what changed."""
    old = case.facts()
    source = case.source_hash()
    if not case.current(old):
        wanted = set(ENGINES)
    renders_ce = "ce" in wanted or old is None or old.render("ce") is None
    if renders_ce and importlib.util.find_spec("manim") is None:
        msg = f"{case.name}: CE's references need Manim CE (`uv sync --group ce`)"
        raise RuntimeError(msg)
    renders: dict[Engine, Frames | Failure] = {}
    notes: list[str] = []
    changed = False
    ce_version = old.ce_version if old is not None else ""
    with tempfile.TemporaryDirectory() as tmp:
        for engine in ENGINES:
            previous = None if old is None else old.render(engine)
            if engine not in wanted and previous is not None:
                renders[engine] = previous
                continue
            fresh = Path(tmp) / f"{engine}.mkv"
            result = engines.run(case, engine, video=fresh)
            if result.source is not None and result.source != source:
                msg = f"{case.name}: scene.py changed while it rendered"
                raise RuntimeError(msg)
            if engine == "ce":
                ce_version = result.manim or importlib.metadata.version("manim")
            renders[engine] = result.frames
            changed |= previous != result.frames
            video = case.video(engine)
            if isinstance(result.frames, Failure):
                video.unlink(missing_ok=True)
                case.video_hash(engine).unlink(missing_ok=True)
                notes.append(f"{engine} failed: {result.frames.error}")
            elif (
                isinstance(previous, Frames)
                and previous.runs == result.frames.runs
                and video.exists()
                and case.video_hash(engine).exists()
                and case.video_hash(engine).read_text(encoding="ascii")
                == f"{hashlib.sha256(video.read_bytes()).hexdigest()}  {video.name}\n"
            ):
                notes.append(f"{engine} unchanged")
            else:
                shutil.move(fresh, video)
                digest = hashlib.sha256(video.read_bytes()).hexdigest()
                case.video_hash(engine).write_text(
                    f"{digest}  {video.name}\n",
                    encoding="ascii",
                )
                notes.append(f"{engine} {'new' if previous is None else 'changed'}")
    kept = None if old is None or changed else old.comparison
    facts = _facts(case, source, renders["manimgx"], renders["ce"], ce_version, kept)
    case.write_facts(facts)
    return facts, "; ".join(notes)


def recompare(case: Case) -> str:
    """Compare a case's references again (after the metrics changed)."""
    facts = case.facts()
    if facts is None:
        return "not rendered"
    facts = _facts(
        case, facts.source, facts.manimgx, facts.ce, facts.ce_version, kept=None
    )
    case.write_facts(facts)
    return "compared" if facts.comparison is not None else "nothing to compare"


def _facts(
    case: Case,
    source: str,
    manimgx: Frames | Failure,
    ce: Frames | Failure,
    ce_version: str,
    kept: Comparison | None,
) -> Facts:
    comparison = None
    if isinstance(manimgx, Frames) and isinstance(ce, Frames):
        if kept is None:
            missing = [engine for engine in ENGINES if not case.video(engine).exists()]
            if missing:
                msg = (
                    f"{case.name}: reference video(s) missing ({', '.join(missing)}); "
                    f"run `just corpus render {case.name}` to regenerate them"
                )
                raise FileNotFoundError(msg)
        comparison = kept or comparing.compare(
            ce, manimgx, case.video("ce"), case.video("manimgx"), SIZE, FPS
        )
    return Facts(
        source=source,
        size=SIZE,
        fps=FPS,
        manimgx=manimgx,
        ce=ce,
        ce_version=ce_version,
        comparison=comparison,
    )

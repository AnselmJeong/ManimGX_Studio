"""A case, and everything recorded about it.

A case is a directory under `cases/`:

- `scene.py`: the only source. It is Manim CE's code, and it reaches the engine only through
  `manimgx`'s top level (and its types, `manimgx.typing`): ManimGX runs it as written, and CE
  runs the same bytes with `manimgx` resolving to `manim` (`run_ce.py`).
- `manimgx.mkv`, `ce.mkv`: each engine's lossless frames, generated locally and ignored by Git.
- `manimgx.mkv.sha256`, `ce.mkv.sha256`: hashes of the reviewed reference videos.
- `case.json`: facts, written by the tool — the source both renders came from, every frame's
  hash (so a change is found without decoding video), and how the two compare, frame by frame,
  in every metric.
- `review.json`: a person's verdict and note, pinned to the hashes they were given for.

A case's state is a verdict — `working`, `not_matching` or `not_working` — or `stale` /
`unrendered` while it has no current renders to judge. The comparison gives a verdict under
the metric and tolerance of `settings.json`: working when, at every ManimGX frame's scene time,
the frame CE has on screen is within tolerance of it and the scenes last as long; not_matching
otherwise, or when CE could not render the scene; not_working when ManimGX could not. A
person's verdict on exactly these renders overrides it: CE is a reference to look at, not a
definition of correct.
"""

import datetime
import hashlib
import json
import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Literal, cast

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "src" / "manimgx"
CASES = ROOT / "tests" / "integration" / "cases"
SETTINGS = ROOT / "tests" / "integration" / "settings.json"
SIZE = (960, 540)
FPS = 10

type Engine = Literal["manimgx", "ce"]
ENGINES: tuple[Engine, ...] = ("manimgx", "ce")

METRICS: tuple[str, ...] = ("local_max", "mae", "rmse", "max")
"""How a pair of frames is measured (see `compare`); every pair is measured in all of them."""

type Run = tuple[str, int]
"""A frame's hash, and how many frames in a row show it."""

type Stretch = tuple[Fraction, int]
"""Frames 1/fps apart: the scene time of the first, and how many."""

type Verdict = Literal["working", "not_matching", "not_working"]
VERDICTS: tuple[Verdict, ...] = ("working", "not_matching", "not_working")

type State = Literal["working", "not_matching", "not_working", "stale", "unrendered"]


def seconds(value: Fraction) -> float:
    """A time as JSON holds it."""
    return round(float(value), 9)


def exact(value: float | str) -> Fraction:
    """A time read back, or a CE duration, as the rational number it stands for."""
    return Fraction(value).limit_denominator(10**6)


@dataclass(frozen=True, slots=True)
class Settings:
    """The comparison's metric and tolerance (`settings.json`)."""

    metric: str
    tolerance: float

    def __post_init__(self) -> None:
        if self.metric not in METRICS:
            raise ValueError(f"unknown metric {self.metric!r}; one of {METRICS}")
        if not math.isfinite(self.tolerance) or not 0 <= self.tolerance <= 255:
            raise ValueError("tolerance must be finite and between 0 and 255")


def settings() -> Settings:
    data = _object(json.loads(SETTINGS.read_text(encoding="utf-8")))
    return Settings(metric=_str(data["metric"]), tolerance=_number(data["tolerance"]))


def save_settings(value: Settings) -> None:
    SETTINGS.write_text(
        dump({"metric": value.metric, "tolerance": value.tolerance}), encoding="utf-8"
    )


@dataclass(frozen=True, slots=True)
class Frames:
    """What one engine drew from one source: its frames, the scene's length, and when each
    frame shows the scene (ManimGX's frame k shows k/fps; CE places each play's frames from the
    play's start)."""

    runs: tuple[Run, ...]
    duration: Fraction
    timeline: tuple[Stretch, ...]

    @property
    def count(self) -> int:
        return sum(n for _, n in self.runs)

    def hashes(self) -> list[str]:
        return [h for h, n in self.runs for _ in range(n)]

    def times(self, fps: int) -> list[Fraction]:
        dt = Fraction(1, fps)
        return [start + j * dt for start, n in self.timeline for j in range(n)]

    def identity(self, size: tuple[int, int], fps: int) -> str:
        """One hash for the render's pixel sequence and resolution."""
        payload = json.dumps([list(size), fps, [list(run) for run in self.runs]])
        return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Failure:
    """An engine could not render the source."""

    error: str


@dataclass(frozen=True, slots=True)
class Comparison:
    """CE's frames against ManimGX's at the same scene times: `pairs` are (the CE frame on
    screen at a ManimGX frame's time, that ManimGX frame, their difference in each of
    `METRICS`); `unpaired` are the CE frames on screen at no ManimGX frame's time."""

    pairs: tuple[tuple[int, int, tuple[float, ...]], ...]
    unpaired: tuple[int, ...]

    def errors(self, metric: str) -> list[float]:
        column = METRICS.index(metric)
        return [errors[column] for _, _, errors in self.pairs]

    def worst(self, metric: str) -> float:
        return max(self.errors(metric), default=0.0)


@dataclass(frozen=True, slots=True)
class Facts:
    """Everything the tool recorded about a case (`case.json`)."""

    source: str
    size: tuple[int, int]
    fps: int
    manimgx: Frames | Failure
    ce: Frames | Failure
    ce_version: str
    comparison: Comparison | None

    def render(self, engine: Engine) -> Frames | Failure:
        return self.manimgx if engine == "manimgx" else self.ce

    def identity(self, engine: Engine) -> str | None:
        render = self.render(engine)
        return (
            None
            if isinstance(render, Failure)
            else render.identity(self.size, self.fps)
        )

    def revision(self) -> str:
        """The complete facts a reviewer saw, including timing and comparison results."""
        return source_hash(dump(facts_to_json(self)).encode("utf-8"))

    def reasons(self, settings: Settings) -> tuple[str, ...]:
        """Why the renders are not the same under these settings (none: they are)."""
        if isinstance(self.manimgx, Failure):
            return ("manimgx failed",)
        if isinstance(self.ce, Failure):
            return ("ce failed",)
        if self.comparison is None:
            return ("not compared",)
        found: list[str] = []
        if abs(self.ce.duration - self.manimgx.duration) > 1e-6:
            found.append("duration")
        if self.comparison.worst(settings.metric) > settings.tolerance:
            found.append("pixels")
        return tuple(found)

    def verdict(self, settings: Settings) -> Verdict:
        """The comparison's own verdict."""
        if isinstance(self.manimgx, Failure):
            return "not_working"
        return "not_matching" if self.reasons(settings) else "working"


@dataclass(frozen=True, slots=True)
class Review:
    """A person's word on a case (`review.json`): a verdict that overrides the comparison's,
    or none (a note alone). The verdict holds only for the complete facts it names.
    """

    verdict: Verdict | None
    note: str
    facts: str | None  # None: a legacy review without a complete evidence binding
    at: str


@dataclass(frozen=True, slots=True)
class Standing:
    """Where a case stands: its state, what the comparison alone says, and its review."""

    state: State
    auto: State
    review: Review | None
    reviewed: bool  # the review's verdict decides the state
    facts: Facts | None


@dataclass(frozen=True, slots=True)
class Case:
    name: str

    @property
    def dir(self) -> Path:
        return CASES / self.name

    @property
    def scene(self) -> Path:
        return self.dir / "scene.py"

    def video(self, engine: Engine) -> Path:
        return self.dir / f"{engine}.mkv"

    def video_hash(self, engine: Engine) -> Path:
        return self.dir / f"{engine}.mkv.sha256"

    @property
    def facts_path(self) -> Path:
        return self.dir / "case.json"

    @property
    def review_path(self) -> Path:
        return self.dir / "review.json"

    def source_hash(self) -> str:
        return source_hash(self.scene.read_bytes())

    def facts(self) -> Facts | None:
        path = self.facts_path
        return (
            facts_from_json(json.loads(path.read_text(encoding="utf-8")))
            if path.exists()
            else None
        )

    def review(self) -> Review | None:
        path = self.review_path
        return (
            review_from_json(json.loads(path.read_text(encoding="utf-8")))
            if path.exists()
            else None
        )

    def current(self, facts: Facts | None) -> bool:
        """Whether these facts were rendered from today's scene.py, at the corpus's size."""
        return (
            facts is not None
            and facts.source == self.source_hash()
            and (facts.size, facts.fps) == (SIZE, FPS)
        )

    def standing(self, settings: Settings) -> Standing:
        facts, review = self.facts(), self.review()
        if facts is None:
            return Standing("unrendered", "unrendered", review, False, None)
        if not self.current(facts):
            return Standing("stale", "stale", review, False, facts)
        auto: State = facts.verdict(settings)
        if review is not None and review.verdict is not None and pinned(review, facts):
            return Standing(review.verdict, auto, review, True, facts)
        return Standing(auto, auto, review, False, facts)

    def state(self, settings: Settings) -> State:
        return self.standing(settings).state

    def write_facts(self, facts: Facts) -> bool:
        """Record the facts; whether the file changed (equal facts leave it untouched)."""
        text = dump(facts_to_json(facts))
        path = self.facts_path
        if path.exists() and path.read_text(encoding="utf-8") == text:
            return False
        path.write_text(text, encoding="utf-8")
        return True

    def write_review(
        self, verdict: Verdict | None, note: str, *, expected: str | None = None
    ) -> Review | None:
        """Record a verdict (None: the comparison's stands) and a note on exactly the current
        source and renders; with neither, the case has no review."""
        facts = self.facts()
        if facts is None or not self.current(facts):
            msg = f"{self.name}: its renders are missing or stale; render it first"
            raise ValueError(msg)
        if expected is not None and facts.revision() != expected:
            msg = f"{self.name}: its renders changed; inspect them before reviewing"
            raise ValueError(msg)
        if verdict is None and not note.strip():
            self.review_path.unlink(missing_ok=True)
            return None
        review = Review(
            verdict=verdict,
            note=note.strip(),
            facts=facts.revision(),
            at=datetime.date.today().isoformat(),
        )
        self.review_path.write_text(dump(review_to_json(review)), encoding="utf-8")
        return review


def pinned(review: Review, facts: Facts) -> bool:
    """Whether this review names all the evidence currently shown."""
    return review.facts == facts.revision()


def source_hash(source: bytes) -> str:
    return "sha256:" + hashlib.sha256(source).hexdigest()


def discover() -> list[Case]:
    """Every case: each directory under `cases/` holding a `scene.py`."""
    return sorted(
        (Case(p.parent.name) for p in CASES.glob("*/scene.py")), key=lambda c: c.name
    )


# ── JSON ──────────────────────────────────────────────────────────────────────
# Written by hand so that equal facts are equal bytes, and each frame run is one line.

type Json = bool | int | float | str | list[Json] | dict[str, Json] | None


def dump(value: Json) -> str:
    return _dump(value, 0) + "\n"


def _dump(value: Json, depth: int) -> str:
    pad, inner = "  " * depth, "  " * (depth + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [
            f"{inner}{json.dumps(k)}: {_dump(v, depth + 1)}" for k, v in value.items()
        ]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    if isinstance(value, list):
        if all(not isinstance(v, (list, dict)) for v in value):
            return json.dumps(value)
        return (
            "[\n" + ",\n".join(inner + _dump(v, depth + 1) for v in value) + f"\n{pad}]"
        )
    return json.dumps(value)


def frames_to_json(render: Frames | Failure) -> Json:
    if isinstance(render, Failure):
        return {"error": render.error}
    return {
        "duration": seconds(render.duration),
        "frames": [[h, n] for h, n in render.runs],
        "timeline": [[seconds(start), n] for start, n in render.timeline],
    }


def facts_to_json(facts: Facts) -> Json:
    comparison: Json = None
    if facts.comparison is not None:
        comparison = {
            "metrics": list(METRICS),
            "pairs": [
                [i, k, *(round(e, 2) for e in errors)]
                for i, k, errors in facts.comparison.pairs
            ],
            "unpaired": list(facts.comparison.unpaired),
        }
    manimgx, ce = frames_to_json(facts.manimgx), frames_to_json(facts.ce)
    for render, engine in ((manimgx, "manimgx"), (ce, "ce")):
        identity = facts.identity(engine)
        if identity is not None and isinstance(render, dict):
            render["id"] = identity
    ce_json = {"manim": facts.ce_version, **ce} if isinstance(ce, dict) else ce
    return {
        "source": facts.source,
        "size": list(facts.size),
        "fps": facts.fps,
        "manimgx": manimgx,
        "ce": ce_json,
        "comparison": comparison,
    }


def review_to_json(review: Review) -> Json:
    return {
        "verdict": review.verdict,
        "note": review.note,
        "facts": review.facts,
        "at": review.at,
    }


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        msg = f"expected a JSON object, got {value!r}"
        raise TypeError(msg)
    return {str(k): v for k, v in cast("dict[object, object]", value).items()}


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        msg = f"expected a JSON array, got {value!r}"
        raise TypeError(msg)
    return list(cast("list[object]", value))


def _str(value: object) -> str:
    if not isinstance(value, str):
        msg = f"expected a string, got {value!r}"
        raise TypeError(msg)
    return value


def _int(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f"expected an integer, got {value!r}"
        raise TypeError(msg)
    return value


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = f"expected a number, got {value!r}"
        raise TypeError(msg)
    return float(value)


def _pair(value: object) -> tuple[object, object]:
    items = _list(value)
    if len(items) != 2:
        msg = f"expected a pair, got {value!r}"
        raise TypeError(msg)
    return items[0], items[1]


def frames_from_json(value: object) -> Frames | Failure:
    data = _object(value)
    if "error" in data:
        return Failure(_str(data["error"]))
    return Frames(
        runs=tuple((_str(h), _int(n)) for h, n in map(_pair, _list(data["frames"]))),
        duration=exact(_number(data["duration"])),
        timeline=tuple(
            (exact(_number(t)), _int(n)) for t, n in map(_pair, _list(data["timeline"]))
        ),
    )


def comparison_from_json(value: object) -> Comparison | None:
    """The comparison, or None when there is none — or it measured other metrics than
    `METRICS` (then it is measured again)."""
    if value is None:
        return None
    data = _object(value)
    if tuple(_str(m) for m in _list(data.get("metrics", []))) != METRICS:
        return None
    pairs: list[tuple[int, int, tuple[float, ...]]] = []
    for item in _list(data["pairs"]):
        i, k, *errors = _list(item)
        pairs.append((_int(i), _int(k), tuple(_number(e) for e in errors)))
    return Comparison(
        pairs=tuple(pairs), unpaired=tuple(_int(i) for i in _list(data["unpaired"]))
    )


def facts_from_json(value: object) -> Facts:
    data = _object(value)
    width, height = map(_int, _pair(data["size"]))
    ce = _object(data["ce"])
    return Facts(
        source=_str(data["source"]),
        size=(width, height),
        fps=_int(data["fps"]),
        manimgx=frames_from_json(data["manimgx"]),
        ce=frames_from_json(ce),
        ce_version=_str(ce.get("manim", "")),
        comparison=comparison_from_json(data["comparison"]),
    )


def review_from_json(value: object) -> Review:
    data = _object(value)
    verdict = data.get("verdict")
    if verdict is not None and verdict not in VERDICTS:
        msg = f"unknown verdict {verdict!r}; one of {VERDICTS} or null"
        raise ValueError(msg)
    facts = data.get("facts")
    return Review(
        verdict=next((v for v in VERDICTS if v == verdict), None),
        note=_str(data.get("note", "")),
        facts=None if facts is None else _str(facts),
        at=_str(data.get("at", "")),
    )

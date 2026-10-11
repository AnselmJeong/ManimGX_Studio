"""Review comparisons authenticate whole movies, including held and unpaired frames."""

from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest
from tests.integration.corpus import case as corpus
from tests.integration.corpus import compare, references
from tests.integration.corpus.frames import Recorder

RED = (255, 0, 0)
BLUE = (0, 0, 255)


@pytest.fixture
def case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> corpus.Case:
    monkeypatch.setattr(corpus, "CASES", tmp_path)
    monkeypatch.setattr(corpus, "SIZE", (8, 8))
    monkeypatch.setattr(references, "SIZE", (8, 8))
    example = corpus.Case("comparison")
    example.dir.mkdir()
    example.scene.write_text("import manimgx\n", encoding="utf-8")
    red = movie(example, "manimgx", [RED, RED])
    movie(example, "ce", [RED, RED])
    example.write_facts(
        corpus.Facts(example.source_hash(), (8, 8), 10, red, red, "test", None)
    )
    return example


def movie(
    case: corpus.Case, engine: corpus.Engine, colors: list[tuple[int, int, int]]
) -> corpus.Frames:
    recorder = Recorder((8, 8), 10, case.video(engine), compact=False)
    for color in colors:
        recorder.add(bytes(color) * 64)
    return corpus.Frames(
        recorder.close(), Fraction(len(colors), 10), ((Fraction(0), len(colors)),)
    )


@pytest.mark.parametrize("engine", ["ce", "manimgx"])
@pytest.mark.parametrize("colors", [[RED, BLUE], [RED], [RED, RED, RED]])
def test_recompare_rejects_replaced_or_incomplete_movies_without_writing_facts(
    case: corpus.Case, engine: corpus.Engine, colors: list[tuple[int, int, int]]
) -> None:
    before = case.facts_path.read_bytes()
    movie(case, engine, colors)
    with pytest.raises(ValueError, match="differs from its record"):
        references.recompare(case)
    assert case.facts_path.read_bytes() == before


def test_unpaired_movie_tail_is_still_authenticated(case: corpus.Case) -> None:
    facts = case.facts()
    assert facts is not None
    shorter = movie(case, "manimgx", [RED])
    case.write_facts(replace(facts, manimgx=shorter))
    before = case.facts_path.read_bytes()
    movie(case, "ce", [RED, BLUE])
    with pytest.raises(ValueError, match="frame 1 differs"):
        references.recompare(case)
    assert case.facts_path.read_bytes() == before


def test_validated_holds_still_share_one_measurement(
    case: corpus.Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    measure = compare.measure
    measured = 0

    def count(a: compare.Pixels, b: compare.Pixels) -> tuple[float, ...]:
        nonlocal measured
        measured += 1
        return measure(a, b)

    monkeypatch.setattr(compare, "measure", count)
    assert references.recompare(case) == "compared"
    facts = case.facts()
    assert facts is not None
    assert facts.verdict(corpus.Settings("max", 0)) == "working"
    assert measured == 1

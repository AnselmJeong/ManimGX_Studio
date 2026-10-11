"""A comparison uses one available measure, including every retained retry sample."""

import ctypes
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from tests.benchmarks import harness
from tests.benchmarks import test_speed as speed
from tests.benchmarks.conftest import pytest_terminal_summary
from tests.benchmarks.harness import Cost, Row
from tests.benchmarks.test_speed import Change
from tests.benchmarks.work import Work


@pytest.mark.parametrize(
    ("status", "count", "expected"),
    [(0, 0, None), (0, 123_456, 123_456), (1, 123_456, None)],
)
def test_instruction_queries_require_a_positive_available_counter(
    monkeypatch: pytest.MonkeyPatch, status: int, count: int, expected: int | None
) -> None:
    def query(pid: int, flavor: int, usage: ctypes.Array[ctypes.c_uint64]) -> int:
        assert (pid, flavor) == (123, 4)
        usage[31] = count
        return status

    monkeypatch.setattr(
        harness,
        "os",
        SimpleNamespace(P_PID=1, WEXITED=4, WNOWAIT=8, waitid=lambda *a: None),
    )
    monkeypatch.setattr(harness, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(
        harness,
        "ctypes",
        SimpleNamespace(
            c_uint64=ctypes.c_uint64,
            CDLL=lambda _: SimpleNamespace(proc_pid_rusage=query),
        ),
    )
    assert harness._instructions(123) == expected


def test_positive_counters_judge_instructions_despite_different_cpu_times() -> None:
    samples = [(Cost(10, 20, 30, 1_000), Cost(11, 22, 33, 900))] * 5
    change = Change.of(samples)
    assert change.ratios == pytest.approx((0.9,) * 5)
    assert (change.base.instructions, change.head.instructions) == (1_000, 900)
    assert not change.slower


@pytest.mark.parametrize("unavailable", [None, 0, -1])
@pytest.mark.parametrize("position", range(10))
def test_one_missing_counter_selects_cpu_for_every_pair_and_detects_regression(
    unavailable: int | None, position: int
) -> None:
    costs = [Cost(10, 20, 30, 1_000), Cost(11, 22, 33, 900)] * 5
    costs[position] = replace(costs[position], instructions=unavailable)
    samples = list(zip(costs[::2], costs[1::2], strict=True))
    change = Change.of(samples)
    assert change.ratios == pytest.approx((1.1,) * 5)
    assert change.base == Cost(10, 20, 30, None)
    assert change.head == Cost(11, 22, 33, None)
    assert change.slower
    # Choosing a comparison channel does not discard its raw observations.
    assert samples[position // 2][position % 2].instructions == unavailable


def test_cpu_only_samples_compare_in_cpu_seconds() -> None:
    change = Change.of([(Cost(10, 20, 30, None), Cost(11, 22, 33, None))] * 5)
    assert change.ratio == pytest.approx(1.1)
    assert change.slower


def test_retry_reselects_one_measure_for_all_retained_samples() -> None:
    samples = [(Cost(10, 20, 30, 1_000), Cost(9, 18, 27, 1_100))] * 5
    assert Change.of(samples).slower
    retry = samples[:4] + [(samples[0][0], replace(samples[0][1], instructions=None))]
    change = Change.of(samples + retry)
    assert change.ratios == pytest.approx((0.9,) * 10)
    assert change.base.instructions is change.head.instructions is None
    assert not change.slower


@pytest.mark.parametrize("invalid", [0.0, -1.0, float("nan"), float("inf")])
@pytest.mark.parametrize("side", [0, 1])
def test_unusable_cpu_measurements_fail_instead_of_producing_a_ratio(
    invalid: float, side: int
) -> None:
    pair = [Cost(10, 20, 30, None), Cost(11, 22, 33, None)]
    pair[side] = replace(pair[side], cpu=invalid)
    with pytest.raises(ValueError, match="CPU seconds must be finite and positive"):
        Change.of([(pair[0], pair[1])] * 5)


def test_regression_reports_every_round_retained_after_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        speed,
        "compare",
        lambda *args: [(Cost(10, 20, 30, None), Cost(11, 22, 33, None))] * 5,
    )
    monkeypatch.setattr(speed, "work", lambda *args: Work())
    properties: list[tuple[str, Row]] = []
    request = SimpleNamespace(node=SimpleNamespace(user_properties=properties))
    trees = (harness.Tree(tmp_path, "base"), harness.Tree(tmp_path, "head"))
    with pytest.raises(AssertionError, match=r"takes \+10\.0% CPU seconds"):
        speed.test_speed("orbit", trees, 5, cast(pytest.FixtureRequest, request))
    row = properties[0][1]
    assert row.unit == "CPU seconds"
    assert row.cells[4] == "10: +10.0% … +10.0%"


def test_terminal_and_job_summary_name_each_workloads_measure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pytestconfig: pytest.Config
) -> None:
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    rows = [
        Row(0, "instructions", ("orbit", "1G", "1G", "+0%", "+0%", "+0%", "+0%", "")),
        Row(
            1, "CPU seconds", ("morph", "1.0", "1.1", "+10%", "+10%", "+0%", "+0%", "")
        ),
    ]
    lines: list[str] = []
    reporter = SimpleNamespace(
        stats={
            "passed": [
                SimpleNamespace(when="call", user_properties=[("timed", row)])
                for row in rows
            ]
        },
        section=lines.append,
        write_line=lines.append,
    )
    pytest_terminal_summary(cast(pytest.TerminalReporter, reporter), pytestconfig)
    assert any("orbit" in line and "instructions" in line for line in lines)
    assert any("morph" in line and "CPU seconds" in line for line in lines)
    text = summary.read_text(encoding="utf-8")
    assert "| workload | unit |" in text
    assert "| orbit | instructions |" in text
    assert "| morph | CPU seconds |" in text

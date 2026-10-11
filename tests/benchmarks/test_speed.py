"""ManimGX is not slower than the ManimGX it is compared with, on any workload.

A workload is a scene rendered as a user renders it, `manimgx render`, in a process of its own
from launch to exit: three scenes as the README's benchmark (`benchmarks/`) times its own, and
six example films, small. On Linux and macOS, the suite renders each once, tiny. Windows keeps
the functional corpus and cost laws; these long benchmark films depend on its software GPU.

`just bench REF` renders each workload with this checkout and with REF's ManimGX, in turns, round
after round on one machine, and compares what the runs cost: the instructions they retired where
the host exposes positive counts for every sample, else their CPU seconds. The same measure
is used for every pair and retry. A round's two runs make a ratio. A workload has become slower
when the median ratio is
more than 5% above 1 and the rounds agree: its 95% confidence bound (exact, and free of any
assumption about the noise) is above 1, which five rounds give only if every one is slower. A
workload that looks slower is timed as many rounds again, and judged on them all. Wall time and
peak memory are shown beside it, and the work each tree did (`tests.benchmarks.work`), counted
exactly, says what changed.
"""

import math
import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path
from statistics import median

import pytest
from tests.benchmarks.harness import (
    ROOT,
    Cost,
    Incomparable,
    Row,
    Tree,
    Workload,
    compare,
    here,
    render,
    work,
)
from tests.benchmarks.work import Work

pytestmark = [
    pytest.mark.timed,
    pytest.mark.skipif(
        sys.platform == "win32",
        reason="benchmark films run on Linux and macOS; Windows runs the functional corpus",
    ),
]

SCENES = Path(__file__).resolve().parent / "scenes"
EXAMPLES = ROOT / "examples"
SMALL = ("--resolution", "480x270", "--fps", "10")
TINY = ("--resolution", "64x36", "--fps", "5")
"""How the suite renders a workload once, to see that it still renders."""

WORKLOADS: dict[str, Workload] = {
    # three scenes as the README's benchmark times its own: 1920 x 1080 at 60 fps, to MP4
    "orbit": Workload(SCENES / "orbit.py"),
    "morph": Workload(SCENES / "morph.py"),
    "explainer": Workload(SCENES / "explainer.py"),
    # example films, small: their code and the feed, most of what a film costs
    **{
        name: Workload(EXAMPLES / f"{name}.py", SMALL)
        for name in (
            "clifford_torus",  # surfaces: meshes, their normals, uploads
            "heavy_top",  # a simulation carrying meshes
            "kuramoto_fireflies",  # see-through points, sorted and blended
            "lagrange_points",  # a big surface raised by its points every frame
            "neural_untangle",  # paths traced curve by curve, thousands of small shapes
            "taylor_poles",  # axes, graphs and text
        )
    },
}

TOLERANCE = 0.05
"""How much slower a workload may become before it counts as slower: above what noise moves a
median (identical trees: instructions within 1.3% on a busy Mac, CPU time within 2.3% on a
quiet one), below the smallest regression manimgx has had (6%)."""


def bounds(ratios: tuple[float, ...]) -> tuple[float, float]:
    """The 95% confidence bounds of the ratios' median, below and above: the k-th smallest
    and largest ratio, for the largest k with P(Binomial(n, 1/2) < k) ≤ 5% (a sign test:
    exact for any noise); none (0 and ∞) for fewer than five rounds."""
    n, k = len(ratios), 0
    while sum(math.comb(n, i) for i in range(k + 1)) <= 0.05 * 2**n:
        k += 1
    ordered = sorted(ratios)
    return (ordered[k - 1], ordered[n - k]) if k else (0.0, math.inf)


@dataclass(frozen=True, slots=True)
class Change:
    """The head's cost against the base's: each round's ratio of what is judged, and the
    medians of what each tree cost."""

    ratios: tuple[float, ...]
    base: Cost
    head: Cost

    @staticmethod
    def of(samples: list[tuple[Cost, Cost]]) -> "Change":
        if not all(
            c.instructions is not None and c.instructions > 0
            for pair in samples
            for c in pair
        ):
            if any(
                not math.isfinite(c.cpu) or c.cpu <= 0 for pair in samples for c in pair
            ):
                raise ValueError("benchmark CPU seconds must be finite and positive")
            samples = [
                (replace(b, instructions=None), replace(h, instructions=None))
                for b, h in samples
            ]

        def middle(costs: list[Cost]) -> Cost:
            counted = [c.instructions for c in costs if c.instructions is not None]
            return Cost(
                median(c.cpu for c in costs),
                median(c.wall for c in costs),
                median(c.memory for c in costs),
                round(median(counted)) if counted else None,
            )

        return Change(
            tuple(h.measure / b.measure for b, h in samples),
            middle([b for b, _ in samples]),
            middle([h for _, h in samples]),
        )

    @property
    def ratio(self) -> float:
        return median(self.ratios)

    @property
    def slower(self) -> bool:
        return self.ratio > 1 + TOLERANCE and bounds(self.ratios)[0] > 1


def work_change(base: Work, head: Work) -> str:
    """The counts that differ, the most changed first: "points ×7330, calls +18%"."""
    changes = []
    for f in fields(Work):
        was, now = getattr(base, f.name), getattr(head, f.name)
        if was == now:
            continue
        factor = now / was if was else math.inf
        if 0.5 < factor < 2:
            shown = f"{factor - 1:+.2%}"
        else:
            shown = f"×{factor:.0f}" if factor >= 100 else f"×{factor:.3g}"
        change = abs(math.log(factor)) if 0 < factor < math.inf else math.inf
        changes.append((change, f"{f.name} {shown}"))
    return ", ".join(text for _, text in sorted(changes, reverse=True))


@pytest.mark.parametrize("name", list(WORKLOADS))
@pytest.mark.timeout(0)  # The harness owns each child's deadline and kills/reaps it.
def test_speed(
    name: str,
    trees: tuple[Tree, Tree] | None,
    rounds: int,
    request: pytest.FixtureRequest,
) -> None:
    workload = WORKLOADS[name]
    if trees is None:  # the suite, not a benchmark: the workload still renders
        render(here(), workload, *TINY)
        return
    base, head = trees
    try:
        samples = compare(workload, base, head, rounds)
        change = Change.of(samples)
        if change.slower:  # confirmed, or not, by as many rounds again
            change = Change.of(samples + compare(workload, base, head, rounds, False))
        worked = work_change(work(base, workload), work(head, workload))
    except Incomparable as reason:
        pytest.skip(str(reason))
    counted = change.base.instructions is not None
    low, high = min(change.ratios) - 1, max(change.ratios) - 1

    def shown(cost: Cost) -> str:
        return f"{cost.measure / 1e9:.2f}G" if counted else f"{cost.measure:.3f}"

    cells = (
        name,
        shown(change.base),
        shown(change.head),
        f"{change.ratio - 1:+.1%}",
        f"{len(change.ratios)}: {low:+.1%} … {high:+.1%}",
        f"{change.head.wall / change.base.wall - 1:+.1%}",
        f"{change.head.memory / change.base.memory - 1:+.1%}",
        worked,
    )
    unit = "instructions" if counted else "CPU seconds"
    request.node.user_properties.append(
        ("timed", Row(list(WORKLOADS).index(name), unit, cells))
    )
    assert not change.slower, (
        f"{name} takes {change.ratio - 1:+.1%} {unit} against {base.label} (the rounds"
        f" {low:+.1%} to {high:+.1%} of {len(change.ratios)})"
        + (f"; its work: {worked}" if worked else "")
    )

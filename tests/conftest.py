"""What every test starts from: the scene clock at 0, the configuration as it ships (but for
what its `config` marks change: `pytestmark = pytest.mark.config(pixel_width=320,
pixel_height=180)` for a module, or one test's own mark over it), nothing remembered for a test
marked `cold` (`manimgx.caches.clear` before and after it), and the Hypothesis profiles;
and the timed benchmarks' options (`--bench REF`, `--bench-rounds`): the tests marked `timed`
(`tests/benchmarks/test_speed.py`) render each workload once in the Linux/macOS suite,
and with `--bench` are timed against REF, alone.

Profiles: `default`; `thorough` (2,000 examples a property, for a hunt); `mutation` (for
mutmut: reproducible, and one failing example is enough). On CI (the CI variable), Hypothesis
loads its own `ci` profile: derandomized, no database, a reproduction blob on failure. Choose
one with `--hypothesis-profile NAME`.
"""

import dataclasses
import os
from collections.abc import Iterator

import pytest
from hypothesis import HealthCheck, Phase, settings

from manimgx import caches
from manimgx.animation import clock
from manimgx.config import config

settings.register_profile(
    "default", deadline=None
)  # speed is the benchmarks' to measure
settings.register_profile("thorough", max_examples=2_000, deadline=None)
settings.register_profile(
    "mutation",
    derandomize=True,
    database=None,
    deadline=None,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],
    report_multiple_bugs=False,
    suppress_health_check=[HealthCheck.differing_executors],
)
if "CI" not in os.environ:
    settings.load_profile("default")

_SHIPPED = dataclasses.asdict(config)


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("manimgx benchmarks")
    group.addoption(
        "--bench",
        default=None,
        metavar="REF",
        help=(
            "time the benchmarks (tests/benchmarks/test_speed.py), alone: this checkout"
            " against REF's manimgx (a commit, branch or tag, or another checkout's"
            " directory), side by side"
        ),
    )
    group.addoption(
        "--bench-rounds",
        type=int,
        default=5,
        metavar="N",
        help="rounds per timed benchmark (default: 5)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "timed: a benchmark, timed with --bench (and then run alone)"
    )
    config.addinivalue_line(
        "markers",
        "config(**options): the configuration a test runs with, over the shipped one",
    )
    config.addinivalue_line(
        "markers",
        "cold: the test starts and ends with nothing remembered (caches.clear)",
    )
    if config.getoption("bench") is not None and getattr(
        config.option, "numprocesses", None
    ):
        raise pytest.UsageError("time the benchmarks alone: --bench runs with -n 0")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """With --bench, the timed benchmarks run alone: nothing else runs beside what is timed."""
    if config.getoption("bench") is None:
        return
    kept, dropped = [], []
    for item in items:
        (kept if item.get_closest_marker("timed") else dropped).append(item)
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = kept


@pytest.fixture(autouse=True)
def fresh_world(request: pytest.FixtureRequest) -> Iterator[None]:
    """Each test starts at scene time 0 with the shipped configuration, changed as its `config`
    marks say (the nearest last: a test's over its class's over its module's); marked `cold`,
    or under mutmut (so that a mutant of remembered code runs), with nothing remembered."""
    clock.reset()
    cold = "MUTANT_UNDER_TEST" in os.environ or request.node.get_closest_marker("cold")
    if cold:
        caches.clear()
    for mark in reversed(list(request.node.iter_markers("config"))):
        for name, value in mark.kwargs.items():
            if not hasattr(config, name):  # a field, or a property (frame_height)
                raise pytest.UsageError(f"the configuration has no {name!r}")
            setattr(config, name, value)
    yield
    for name, value in _SHIPPED.items():
        setattr(config, name, value)
    clock.reset()
    if cold:
        caches.clear()


@pytest.fixture
def two_fonts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: os.PathLike[str]
) -> tuple[str, str]:
    """Two font search paths, `first` and `second`, whose fonts differ only in their size: the
    engine sets text as it does, and a glyph from `second` comes out half as wide and a
    quarter as tall. A capital's height tells the two apart (text is calibrated by it), and so
    do the widths calibration leaves. Layouts are cached in the test's own directory; mark the
    test `cold` so that nothing remembered from other fonts answers for these."""
    import numpy as np

    from manimgx.drawing import typesetting as tc

    first, second = os.path.join(tmp_path, "first"), os.path.join(tmp_path, "second")
    sizes = {first: (1.0, 1.0), second: (0.5, 0.25)}
    native = tc._engine.typeset

    def typeset(
        source: str, fonts: list[str], packages: str | None = None, *, revision: int = 0
    ) -> tuple[bytes, list[bytes], list[tuple[str, list[int]]], bool]:
        raw, shapes, labels, system = native(source, fonts, packages, revision=revision)
        rows = np.frombuffer(raw).reshape(-1, tc.ROW).copy()
        wide, tall = next((sizes[path] for path in fonts if path in sizes), (1.0, 1.0))
        places = rows[:, tc.PLACEMENT]  # (sx, ky, kx, sy, tx, ty): x's, then y's, apart
        places[:, ::2] *= wide
        places[:, 1::2] *= tall
        return rows.tobytes(), shapes, labels, system

    monkeypatch.setattr(tc, "_CACHE", tc.Path(tmp_path, "layouts"))
    monkeypatch.setattr(tc._engine, "typeset", typeset)
    return first, second

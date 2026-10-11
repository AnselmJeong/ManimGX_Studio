"""The unit tests mirror the package: `tests/unit/<path>/test_<module>.py` tests
`src/manimgx/<path>/<module>.py`, so a module's tests are where its path says,
and each test module opens with the properties it checks. The registries the laws run over
hold every public class: `MOBJECTS` every mobject, `ANIMATIONS` every animation."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "manimgx"
UNIT = ROOT / "tests" / "unit"


def test_every_unit_test_module_tests_a_source_module() -> None:
    strays = [
        str(test.relative_to(UNIT))
        for test in UNIT.rglob("test_*.py")
        if not (
            SOURCE / test.parent.relative_to(UNIT) / test.name.removeprefix("test_")
        ).exists()
    ]
    assert not strays, (
        f"unit test modules without a source module of that path: {strays}"
    )


def test_every_python_file_under_unit_is_a_test_module() -> None:
    others = [
        str(p.relative_to(UNIT))
        for p in UNIT.rglob("*.py")
        if not p.name.startswith("test_")
    ]
    assert not others, (
        f"shared test code goes in tests/strategies.py or tests/oracles.py: {others}"
    )


def test_every_public_mobject_class_is_in_the_registry() -> None:
    import inspect

    from tests.strategies import MOBJECTS

    import manimgx
    from manimgx.mobject import Mobject

    public = {
        name
        for name, value in vars(manimgx).items()
        if inspect.isclass(value) and issubclass(value, Mobject)
    }
    abstract = {"ArrowTip"}  # its subclasses stand for it
    missing = sorted(public - abstract - set(MOBJECTS))
    assert not missing, f"public mobject classes the laws do not reach: {missing}"


def test_every_public_animation_class_is_in_the_registry() -> None:
    import inspect

    from tests.strategies import ANIMATIONS

    import manimgx
    from manimgx.animation.timeline import Animation

    public = {
        name
        for name, value in vars(manimgx).items()
        if inspect.isclass(value) and issubclass(value, Animation)
    }
    missing = sorted(public - set(ANIMATIONS))
    assert not missing, f"public animation classes the laws do not reach: {missing}"


def test_every_unit_test_module_states_its_properties() -> None:
    silent = [
        str(test.relative_to(UNIT))
        for test in UNIT.rglob("test_*.py")
        if not ast.get_docstring(ast.parse(test.read_text(encoding="utf-8")))
    ]
    assert not silent, (
        f"test modules without a docstring stating what they check: {silent}"
    )

"""A type checker knows each keyword a mobject or an animation takes, and each method
`.animate` and `.always` call, and nothing else.

- Every TypedDict that a signature unpacks (`**kwargs: Unpack[Style]`) is closed (PEP 728):
  a keyword it doesn't name is an error to a type checker, not a key of type `object`.
- So ty reports a misspelled keyword (`m.Circle(colour=…)`), where ManimGX would ignore it,
  and a misspelled method through `.animate` or `.always` (`.animate.shfit(…)`), or in a
  function given to `.animate`, which ManimGX reports only when the scene runs; it takes the
  methods there as the mobject's.
- Mutable mappings and numbers retain their key and value types through construction,
  updates, and animation proxies.
"""

import importlib
import re
from pathlib import Path

from tests.typecheck import check
from typing_extensions import is_typeddict

PACKAGE = Path(__file__).parents[2] / "src" / "manimgx"


def unpacked() -> dict[str, set[str]]:
    """The TypedDicts that the package's signatures unpack, by module: their names."""
    found: dict[str, set[str]] = {}
    for path in PACKAGE.rglob("*.py"):
        names = set(re.findall(r"Unpack\[(\w+)", path.read_text(encoding="utf-8")))
        if names:
            module = ".".join(path.relative_to(PACKAGE.parent).with_suffix("").parts)
            found[module.removesuffix(".__init__")] = names
    return found


def test_every_typeddict_a_signature_unpacks_is_closed() -> None:
    seen = 0
    for module, names in unpacked().items():
        namespace = vars(importlib.import_module(module))
        for name in names:
            kind = namespace.get(name)
            # imported for the type checker only: checked where it is defined
            if kind is None:
                continue
            assert is_typeddict(kind), f"{module}.{name}"
            assert getattr(kind, "__closed__", False), f"{module}.{name} is open"
            seen += 1
    assert seen > 50


def _ty(scene: Path) -> dict[int, str]:
    """The rule ty breaks on each line of a scene, by line."""
    return {
        line: message.split("[", 1)[1].split("]", 1)[0]
        for _, line, _, message in check([scene])
    }


def test_ty_reports_a_misspelling(tmp_path: Path) -> None:
    scene = tmp_path / "scene.py"
    scene.write_text(
        "import manimgx as m\n"
        "\n"
        "m.Circle(colour=m.BLUE)\n"
        'm.Text("x", font_szie=20)\n'
        "m.FadeIn(m.Dot(), run_tme=2)\n"
        "m.Square().set_style(fill_opactiy=1)\n"
        "m.Square().animate.shfit(m.RIGHT)\n"
        "m.Square().animate.shift(m.RIGHT).scael(2)\n"
        "m.Dot().always.nxt_to(m.ORIGIN)\n"
        "m.Square().animate(lambda s: s.shfit(m.RIGHT))\n",
        encoding="utf-8",
    )
    assert _ty(scene) == {
        3: "unknown-argument",
        4: "unknown-argument",
        5: "unknown-argument",
        6: "unknown-argument",
        7: "unresolved-attribute",
        8: "unresolved-attribute",
        9: "unresolved-attribute",
        10: "unresolved-attribute",
    }


def test_ty_takes_the_methods_through_animate_as_the_mobjects(tmp_path: Path) -> None:
    # a kind's own parameters, where they are its own
    scene = tmp_path / "scene.py"
    scene.write_text(
        "import manimgx as m\n"
        "\n"
        "m.Axes().animate.add_coordinates([1, 2])\n"
        "m.DecimalNumber(1).animate.increment_value(2)\n"
        'm.Text("x").animate.scale(2, about_edge=m.UP)\n'
        "m.Cone().animate.set_direction(m.UP)\n"
        "m.Square().animate.close_path().make_jagged()\n"
        "m.Dot().always.next_to(m.ORIGIN, m.UP)\n"
        "m.Square().animate(lambda s: s.shift(m.UP).set_color(m.RED))\n",
        encoding="utf-8",
    )
    assert _ty(scene) == {}


def test_matching_accepts_a_typed_mapping_of_hashable_keys(tmp_path: Path) -> None:
    scene = tmp_path / "scene.py"
    scene.write_text(
        "import manimgx as m\n"
        'keys: dict[str, str] = {"a": "b"}\n'
        'm.TransformMatchingTex(m.MathTex("a"), m.MathTex("b"), key_map=keys)\n',
        encoding="utf-8",
    )
    assert _ty(scene) == {}


def test_vdict_accepts_assigned_mappings_without_widening_their_members(
    tmp_path: Path,
) -> None:
    source = tmp_path / "vdict.py"
    source.write_text(
        "from typing import assert_type\n"
        "import manimgx as m\n"
        "circles = {'circle': m.Circle()}\n"
        "numbered = {1: m.Circle()}\n"
        "shapes = m.VDict(circles)\n"
        "assert_type(shapes, m.VDict[m.Mobject])\n"
        "shapes.add(numbered)\n"
        "shapes['square'] = m.Square()\n"
        "typed = m.VDict[m.Circle](circles)\n"
        "assert_type(typed['circle'], m.Circle)\n"
        "typed.add(circles).add(numbered)\n"
        "pairs = [('circle', m.Circle())]\n"
        "typed.add(pairs)\n"
        "assert_type(m.VDict[m.Circle](pairs)['circle'], m.Circle)\n",
        encoding="utf-8",
    )
    assert check([source]) == []


def test_vdict_rejects_wrong_members_and_unhashable_keys(tmp_path: Path) -> None:
    source = tmp_path / "vdict.py"
    source.write_text(
        "import manimgx as m\n"
        "squares = {'square': m.Square()}\n"
        "m.VDict[m.Circle](squares)\n"
        "typed = m.VDict[m.Circle]()\n"
        "typed.add(squares)\n"
        "typed.add([([], m.Circle())])\n",
        encoding="utf-8",
    )
    assert [
        (line, message.split("]")[0]) for _, line, _, message in check([source])
    ] == [
        (3, "error[no-matching-overload"),
        (5, "error[invalid-argument-type"),
        (6, "error[invalid-argument-type"),
    ]


def test_decimal_number_retains_real_and_complex_value_types(tmp_path: Path) -> None:
    source = tmp_path / "numbers.py"
    source.write_text(
        "from typing import assert_type\n"
        "import manimgx as m\n"
        "real = m.DecimalNumber(1)\n"
        "assert_type(real.get_value(), float)\n"
        "assert_type(m.DecimalNumber().get_value(), float)\n"
        "assert_type(m.Integer(2).get_value(), int)\n"
        "real.set_value(1.5).increment_value(.25)\n"
        "z = m.DecimalNumber(1 + 2j)\n"
        "assert_type(z.get_value(), complex)\n"
        "z.set_value(3 + 4j).increment_value(2j)\n"
        "z.set_value(2)\n"
        "z.animate.set_value(2 + 3j).increment_value(1j)\n"
        "z.always.set_value(2 + 3j)\n"
        "m.ChangingDecimal(z, lambda t: 1 + 2j*t)\n"
        "m.ChangeDecimalToValue(z, 3j)\n"
        "declared = m.DecimalNumber[complex]()\n"
        "declared.set_value(1j)\n"
        "assert_type(declared.get_value(), complex)\n",
        encoding="utf-8",
    )
    assert check([source]) == []


def test_real_numbers_cannot_be_changed_into_complex_values(tmp_path: Path) -> None:
    source = tmp_path / "numbers.py"
    source.write_text(
        "import manimgx as m\n"
        "def complex_update(alpha: float) -> complex:\n"
        "    return 2j*alpha\n"
        "real = m.DecimalNumber(1)\n"
        "real.set_value(2j)\n"
        "real.increment_value(2j)\n"
        "real.animate.set_value(2j)\n"
        "real.always.increment_value(2j)\n"
        "m.Integer(2j)\n"
        "m.ChangeDecimalToValue(real, 2j)\n"
        "m.ChangingDecimal(real, complex_update)\n",
        encoding="utf-8",
    )
    assert [
        (line, message.split("]")[0]) for _, line, _, message in check([source])
    ] == [(line, "error[invalid-argument-type") for line in range(5, 12)]


def test_tracker_constructors_preserve_real_and_complex_value_types(
    tmp_path: Path,
) -> None:
    source = tmp_path / "trackers.py"
    source.write_text(
        "from typing import assert_type\n"
        "import manimgx as m\n"
        "class Real(m.ValueTracker): pass\n"
        "class Complex(m.ComplexValueTracker): pass\n"
        "assert_type(m.ValueTracker().get_value(), float)\n"
        "assert_type(Real(2).get_value(), float)\n"
        "assert_type(m.ComplexValueTracker(0).get_value(), complex)\n"
        "assert_type(Complex(1j).get_value(), complex)\n"
        "Complex().animate.increment_value(1j).set_value(2j)\n",
        encoding="utf-8",
    )
    assert check([source]) == []


def test_real_tracker_construction_cannot_claim_complex_storage(tmp_path: Path) -> None:
    source = tmp_path / "trackers.py"
    source.write_text(
        "import manimgx as m\n"
        "m.ValueTracker(1j)\n"
        "m.ValueTracker[complex](0)\n"
        "class Real(m.ValueTracker): pass\n"
        "Real(1j)\n",
        encoding="utf-8",
    )
    assert [line for _, line, _, _ in check([source])] == [2, 3, 5]

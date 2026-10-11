"""No example teaches a name ManimGX hides (`@deprecated`): not the pages', the README's, the
docstrings' nor the example films' (`examples/`, which the Gallery shows). ty checks each with
`deprecated` an error. The example of a hidden object's own docstring is not shown, and is
not checked."""

import ast
from functools import cache
from pathlib import Path

import pytest
from tests.typecheck import check

ROOT = Path(__file__).parents[2]


@cache
def hidden_spans(path: Path) -> list[tuple[int, int]]:
    """The lines of each definition a module decorates with `@deprecated`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        (node.lineno, node.end_lineno or node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.ClassDef)
        and any("deprecated" in ast.unparse(d) for d in node.decorator_list)
    ]


def shown(where: str) -> bool:
    """Whether an example is shown: one on a page, or in the docstring of what isn't hidden."""
    file, _, line = where.rpartition(":")
    path = ROOT / file
    if not file.startswith("src/"):
        return True
    return not any(a <= int(line) <= b for a, b in hidden_spans(path))


def test_no_example_uses_a_hidden_name(tmp_path: Path) -> None:
    pytest.importorskip("markdown")  # the docs group's, which docs.examples imports
    from docs import examples

    for n, example in enumerate(examples.examples()):
        if shown(example.where):
            (tmp_path / f"example_{n}.py").write_text(
                f"# {example.where}\n{example.code}", encoding="utf-8"
            )
    for film in sorted((ROOT / "examples").glob("*.py")):
        (tmp_path / f"film_{film.name}").write_text(
            f"# examples/{film.name}\n{film.read_text(encoding='utf-8')}",
            encoding="utf-8",
        )
    assert_no_hidden_names(sorted(tmp_path.glob("*.py")))


def assert_no_hidden_names(files: list[Path]) -> None:
    """Check explicit files, including examples outside the project's include paths."""
    uses = []
    for path, number, _, message in check(files, ("--error", "deprecated")):
        if message.startswith("error[deprecated]"):
            source = path.read_text(encoding="utf-8")
            uses.append(
                f"{source.splitlines()[0][2:]} (+{number}): {message.split('] ', 1)[1]}"
            )
    assert not uses, "examples that use a hidden name:\n" + "\n".join(uses)


def test_hidden_names_are_checked_outside_project_include_paths(tmp_path: Path) -> None:
    example = tmp_path / "example.py"
    example.write_text(
        "# example on a docs page\n"
        "from typing_extensions import deprecated\n"
        '@deprecated("not taught")\n'
        "def hidden() -> None: pass\n"
        "hidden()\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match=r"example on a docs page.*not taught"):
        assert_no_hidden_names([example])


def test_hidden_name_check_does_not_accept_checker_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    example = tmp_path / "example.py"
    example.write_text("# example on a docs page\nx = 1\n", encoding="utf-8")
    config = tmp_path / "ty.toml"
    config.write_text("not valid toml\n", encoding="utf-8")
    monkeypatch.setenv("TY_CONFIG_FILE", str(config))
    with pytest.raises(RuntimeError, match=r"ty failed \(2\)"):
        assert_no_hidden_names([example])

"""Every text file ManimGX reads or writes (its packages, tests, docs, scripts and benchmark)
names its encoding. Without one, Python takes the locale's, which on Windows is its ANSI code
page: a subtitle, a page or a scene with characters beyond it would fail to write, or read
wrong.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _unnamed(tree: ast.Module) -> list[int]:
    """The lines of the text reads and writes that name no encoding."""
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or any(
            k.arg == "encoding" for k in node.keywords
        ):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and (
            func.attr == "read_text" or (func.attr == "write_text" and node.args)
        ):
            lines.append(node.lineno)
        elif isinstance(func, ast.Name) and func.id == "open":
            mode = next((k.value for k in node.keywords if k.arg == "mode"), None)
            mode = node.args[1] if len(node.args) > 1 else mode
            if not (isinstance(mode, ast.Constant) and "b" in str(mode.value)):
                lines.append(node.lineno)
    return lines


def test_every_text_file_is_read_and_written_as_utf_8() -> None:
    unnamed = [
        f"{path.relative_to(ROOT)}:{line}"
        for folder in ("src", "fonts", "tests", "docs", "scripts", "benchmarks")
        for path in (ROOT / folder).rglob("*.py")
        # the corpus's scenes are Manim code, as users write it: what they read is theirs
        if "cases" not in path.relative_to(ROOT).parts
        for line in _unnamed(ast.parse(path.read_text(encoding="utf-8")))
    ]
    assert not unnamed, f"text read or written without an encoding: {unnamed}"

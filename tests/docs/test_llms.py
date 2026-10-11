"""The site for agents (Zensical's llmstxt plugin, set in docs/zensical.toml). Its primer,
which opens llms.txt, is written by hand, so these check it against the API: its scene runs,
and every name it teaches exists. And every page is the plugin's: it writes a page's Markdown,
which the page's Copy as Markdown button copies, for the pages its sections name only."""

import re
import tomllib
from fnmatch import fnmatchcase
from pathlib import Path

import manimgx as m
from manimgx.cli import app

CONFIG = Path(__file__).parents[2] / "docs" / "zensical.toml"
LLMSTXT = tomllib.loads(CONFIG.read_text(encoding="utf-8"))["project"]["plugins"][
    "llmstxt"
]
PRIMER: str = LLMSTXT["markdown_description"]


def test_its_scenes_run() -> None:
    blocks = re.findall(r"^```python\n(.*?)^```", PRIMER, re.MULTILINE | re.DOTALL)
    assert blocks
    for code in blocks:
        namespace: dict[str, object] = {}
        exec(compile(code, str(CONFIG), "exec"), namespace)
        scenes = [
            scene
            for scene in namespace.values()
            if isinstance(scene, type) and issubclass(scene, m.Scene)
        ]
        assert scenes, code
        for scene in scenes:
            if scene is not m.Scene:
                scene().render()  # its frames counted, not drawn


def test_its_names_exist() -> None:
    # `m.Circle`, `m.UP`; `Square`, `Brace(mob, m.DOWN)`; `.next_to(other, m.RIGHT)`
    for name in re.findall(r"\bm\.([A-Za-z_]\w*)", PRIMER):
        assert hasattr(m, name), f"m.{name}"
    for name in re.findall(r"`([A-Z]\w*)[(`]", PRIMER):
        assert hasattr(m, name), name
    for name in re.findall(r"`\.(\w+)\(", PRIMER):
        assert hasattr(m.VMobject, name), f".{name}"


def test_its_commands_exist() -> None:
    commands = {
        c.name or getattr(c.callback, "__name__", "") for c in app.registered_commands
    }
    shell = re.findall(r"^```sh\n(.*?)^```", PRIMER, re.MULTILINE | re.DOTALL)
    inline = re.findall(r"`([^`\n]+)`", PRIMER)
    for name in re.findall(r"\bmanimgx ([a-z][\w-]*)", "\n".join(shell + inline)):
        assert name in commands, name


def test_every_page_has_its_markdown() -> None:
    content = CONFIG.parent / "content"
    patterns: list[str] = [
        pattern for patterns in LLMSTXT["sections"].values() for pattern in patterns
    ]
    pages = [page.relative_to(content).as_posix() for page in content.rglob("*.md")]
    assert "index.md" in pages
    for page in pages:
        assert any(fnmatchcase(page, pattern) for pattern in patterns), page

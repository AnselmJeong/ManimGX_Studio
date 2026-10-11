"""The agent skill (`skills/manimgx/SKILL.md`) is what `npx skills add academa-labs/manimgx`
and `gh skill install academa-labs/manimgx` install: they find it by its path,
`skills/<name>/SKILL.md`, and read its front matter, which the Agent Skills specification
(https://agentskills.io/specification) constrains. This checks it against the specification:
the name is its folder's, and the description is 1 to 1,024 characters. Its authoring
examples also run against the current API."""

import re
from pathlib import Path

import yaml

import manimgx as m

SKILL = Path(__file__).parents[2] / "skills" / "manimgx" / "SKILL.md"


def test_its_front_matter_follows_the_specification() -> None:
    text = SKILL.read_text(encoding="utf-8")
    match = re.fullmatch(r"---\n(.*?)\n---\n.*", text, re.DOTALL)
    assert match, "SKILL.md opens with its front matter, between two `---` lines"
    fields = yaml.safe_load(match[1])
    assert fields["name"] == SKILL.parent.name
    assert isinstance(fields["description"], str)
    assert 1 <= len(fields["description"]) <= 1024


def test_its_authoring_examples_run() -> None:
    blocks = re.findall(
        r"^```python\n(.*?)^```",
        SKILL.read_text(encoding="utf-8"),
        re.MULTILINE | re.DOTALL,
    )
    assert blocks, "the authoring skill needs an executable scene example"
    for code in blocks:
        namespace: dict[str, object] = {}
        exec(compile(code, str(SKILL), "exec"), namespace)
        scenes = [
            value
            for value in namespace.values()
            if isinstance(value, type)
            and issubclass(value, m.Scene)
            and value is not m.Scene
        ]
        assert scenes, code
        for scene in scenes:
            scene().render()  # Evaluate and count frames without drawing a video.

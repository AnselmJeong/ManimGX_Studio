"""What ManimGX's wheels hold is licensed, and says so: their third-party notice,
`LICENSE-THIRD-PARTY`, is current, and ManimGX's `license` covers all it names
(scripts/release/licenses.py); the lavapipe's, `LICENSE-LAVAPIPE`, is of the Mesa the Linux wheels are
built with; and a module holding code ported from Manim CE carries CE's copyright lines,
wherever that code moves."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# fragments of Manim CE's code, as ManimGX's modules hold them: `Mobject.move_to`'s mask,
# `color_gradient`'s last step, `ApplyWave`'s phases (a port's own fragment goes here)
PORTED_FROM_CE = ("coor_mask", "alphas_mod1", "phases = ripples * 2")
CE_COPYRIGHT = "SPDX-FileCopyrightText: 2024 the Manim Community Developers"


def test_the_third_party_notice_is_current_and_covered_by_the_license() -> None:
    check = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "release" / "licenses.py"), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert check.returncode == 0, check.stderr


def test_the_lavapipe_notice_is_of_the_mesa_it_is_built_from() -> None:
    script = (ROOT / "scripts" / "release" / "build_lavapipe.sh").read_text(
        encoding="utf-8"
    )
    built = re.search(r"^mesa=(\S+)$", script, re.MULTILINE)
    notice = (ROOT / "LICENSE-LAVAPIPE").read_text(encoding="utf-8")
    described = re.search(r"^Mesa (\S+) \(", notice, re.MULTILINE)
    assert built
    assert described
    assert described[1] == built[1], "LICENSE-LAVAPIPE describes another Mesa"


def test_code_ported_from_manim_ce_says_whose_it_is() -> None:
    sources = ROOT / "src"
    texts = {p: p.read_text(encoding="utf-8") for p in sorted(sources.rglob("*.py"))}
    unsaid = [
        p.relative_to(sources).as_posix()
        for p, text in texts.items()
        if CE_COPYRIGHT not in text and any(f in text for f in PORTED_FROM_CE)
    ]
    gone = [f for f in PORTED_FROM_CE if not any(f in text for text in texts.values())]
    assert not unsaid, f"Manim CE's code without its copyright lines: {unsaid}"
    assert not gone, f"no module holds {gone} any more: drop it from PORTED_FROM_CE"


def test_the_dxc_notice_describes_the_pinned_compiler_and_source() -> None:
    build = (ROOT / "rust" / "dxc" / "src" / "lib.rs").read_text(encoding="utf-8")
    notice = (ROOT / "LICENSE-DXC").read_text(encoding="utf-8")
    recipe = (ROOT / "rust" / "dxc" / "README.md").read_text(encoding="utf-8")
    version = re.search(r"/releases/download/(v[\d.]+)/", build)
    sources = re.findall(r"/archive/([a-f0-9]{40})\.tar\.gz", build)
    binary = re.search(r'BINARY_HASH: &str = "([a-f0-9]{64})"', build)
    assert version
    assert version[1] in notice
    assert sources
    for source in sources:
        assert source in notice
        assert source in recipe
    assert binary
    assert binary[1] in notice
    assert "University of Illinois/NCSA" in notice
    assert "ThirdPartyNotices.txt" in notice

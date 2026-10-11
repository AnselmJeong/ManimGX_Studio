"""The rate function explorer's curves (`docs/content/javascripts/rate-functions.json`, which
`scripts/docs/rates.py` writes) are ManimGX's rate functions: the committed file is what the
script writes now, and every function a page names in an explorer (`data-rates`) is in it."""

import json
import re
from pathlib import Path

from scripts.docs import rates

PAGES = Path(__file__).parents[2] / "docs" / "content"


def test_the_curves_are_the_rate_functions_now() -> None:
    written = rates.DATA.read_text(encoding="utf-8")
    assert written == rates.text(), "run `python -m scripts.docs.rates`"


def test_every_function_an_explorer_names_has_a_curve() -> None:
    curves = json.loads(rates.DATA.read_text(encoding="utf-8"))
    named = [
        name
        for page in PAGES.rglob("*.md")
        for names in re.findall(
            r'data-rates="([^"]*)"', page.read_text(encoding="utf-8")
        )
        for name in names.split()
    ]
    assert named
    for name in named:
        assert name in curves, name

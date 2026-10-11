"""The rate functions' curves, which the docs' rate function explorer draws (`.mx-rates`, in
`docs/content/javascripts/manimgx.js`).

`python -m scripts.docs.rates` writes `docs/content/javascripts/rate-functions.json`, which is
committed, so that the site needs no step to build it: every rate function of
`manimgx.animation.easing`, by name, as its progress at `SAMPLES` times evenly spread from 0
to 1, one function a line.
"""

import inspect
import json
from pathlib import Path

from manimgx.animation import easing
from manimgx.typing import RateFunc

ROOT = Path(__file__).parents[2]
DATA = ROOT / "docs" / "content" / "javascripts" / "rate-functions.json"
# enough that a curve keeps its swings (elastic, bounce, wiggle) when drawn as straight lines
SAMPLES = 121


def functions() -> dict[str, RateFunc]:
    """Every rate function of the module, by name: each function of the time that gives
    the progress, not those that make one from another (`squish_rate_func`)."""
    return {
        name: function
        for name in easing.__all__
        if inspect.isfunction(function := getattr(easing, name))
        and inspect.signature(function).return_annotation is float
    }


def sampled(function: RateFunc) -> list[float]:
    """A rate function's progress at each sample's time, to 4 decimals (0 and 1 as
    written: `0`, not `0.0`)."""
    values = [round(function(i / (SAMPLES - 1)), 4) + 0.0 for i in range(SAMPLES)]
    return [int(value) if value.is_integer() else value for value in values]


def text() -> str:
    """The data file's text."""
    lines = (
        f"  {json.dumps(name)}: {json.dumps(sampled(function), separators=(',', ':'))}"
        for name, function in functions().items()
    )
    return "{\n" + ",\n".join(lines) + "\n}\n"


def main() -> None:
    DATA.write_text(text(), encoding="utf-8")
    print(f"{len(functions())} rate functions, {SAMPLES} samples each")


if __name__ == "__main__":
    main()

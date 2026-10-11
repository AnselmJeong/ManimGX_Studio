"""The command line's reference, from its Typer app: the one page of the API reference that is
generated.

`python -m scripts.docs.reference` writes `docs/content/reference/rendering/command-line.md`
(not committed), so the page always says what the app does. The rest of the reference is
written by hand, in `docs/content/reference/`: its story in prose, and the API in it as
mkdocstrings' `:::` blocks, which render each object from its docstring.
`tests/docs/test_reference.py` keeps the two together: every name the package documents is
on a page, once, and every name a page shows is still in the package.
"""

import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).parents[2]
PAGE = REPOSITORY / "docs" / "content" / "reference" / "rendering" / "command-line.md"


def main() -> None:
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            *(sys.executable, "-m", "typer", "manimgx.cli", "utils", "docs"),
            *("--name", "manimgx", "--title", "Command line"),
            *("--output", str(PAGE)),
        ],
        check=True,
        capture_output=True,
    )
    print(f"wrote {PAGE.relative_to(REPOSITORY)}")


if __name__ == "__main__":
    main()

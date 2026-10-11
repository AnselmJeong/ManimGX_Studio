"""The Gallery: the example films (`examples/`), a card each on its first page, and a page
each.

`python -m scripts.docs.gallery` writes `docs/content/gallery/` (not committed) from
`examples/` alone, before `docs.examples` renders the examples. The examples' README says
what the Gallery says: its introduction's first paragraph opens it, its groups are the
Gallery's, in their order, and its line for a film, `- [Title](file.py): What it shows.`,
gives the film its title, its card's sentence (the line's first) and its page's words. A
film's page holds its file, which `docs.examples` renders as it renders every example, and
`fence` folds under the film; its card shows the film's still, named by its scene
(`docs/films.py`).
"""

import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from docs.examples import Example

ROOT = Path(__file__).parents[2]
EXAMPLES = ROOT / "examples"
GALLERY = ROOT / "docs" / "content" / "gallery"
# a film's line in the README: its title, its file, and what it shows, on as many lines as it
# wraps to
LINE = re.compile(
    r"^- \[(?P<title>[^\]]+)\]\((?P<name>\w+)\.py\): (?P<words>.+?)(?=^- |\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass(frozen=True)
class Film:
    """An example film: its file's name (`hopf_fibration`), its title and what it shows."""

    name: str
    title: str
    words: str

    @property
    def page(self) -> str:
        """Its page's file in the Gallery: `hopf-fibration.md`."""
        return f"{self.name.replace('_', '-')}.md"

    @property
    def lead(self) -> str:
        """What its card says: the first sentence of what it shows."""
        first, stop, _ = self.words.partition(". ")
        return first + "." if stop else self.words

    @property
    def code(self) -> str:
        return (EXAMPLES / f"{self.name}.py").read_text(encoding="utf-8").rstrip()

    @property
    def scene(self) -> str:
        """The scene its film is made of, whose name the card gives its still."""
        scene = Example(self.code).scene
        if scene is None:
            sys.exit(f"examples/{self.name}.py defines no scene")
        return scene


def readme() -> tuple[str, list[tuple[str, list[Film]]]]:
    """The README's introduction (its first paragraph) and its groups: a title each, and its
    films, in order. Every example must be in one, once."""
    text = (EXAMPLES / "README.md").read_text(encoding="utf-8")
    intro, *sections = re.split(r"^## ", text, flags=re.MULTILINE)
    groups = []
    for section in sections:
        title, _, body = section.partition("\n")
        films = [
            Film(found["name"], found["title"], " ".join(found["words"].split()))
            for found in LINE.finditer(body)
        ]
        groups.append((title.strip(), films))
    listed = [film.name for _, films in groups for film in films]
    files = sorted(path.stem for path in EXAMPLES.glob("*.py"))
    if sorted(listed) != files:
        sys.exit(
            "examples/README.md must list every example once, as `- [Title](file.py): …`: "
            f"unlisted {sorted(set(files) - set(listed))},"
            f" missing {sorted(set(listed) - set(files))},"
            f" twice {sorted({n for n in listed if listed.count(n) > 1})}"
        )
    first = intro.partition("\n")[2].strip().split("\n\n")[0]
    return " ".join(first.split()), groups


def front(**fields: str | list[str]) -> str:
    """A page's front matter (JSON's strings are YAML's)."""
    lines = []
    for key, value in fields.items():
        if isinstance(value, list):
            lines += [f"{key}:", *(f"  - {item}" for item in value)]
        else:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    return "---\n" + "\n".join(lines) + "\n---\n\n"


def card(film: Film) -> str:
    """A film's card: its still, its title, and its first sentence, the card a link to it."""
    return (
        f"-   ![](film:{film.scene})\n\n"
        f"    [**{film.title}**]({film.page})\n\n"
        f"    {film.lead}\n"
    )


def index(intro: str, groups: list[tuple[str, list[Film]]]) -> str:
    """The Gallery's first page: the README's introduction, and each group's cards."""
    sections = [
        f"## {title}\n\n"
        '<div class="grid cards mx-cards" markdown>\n\n'
        + "\n".join(card(film) for film in films)
        + "\n</div>\n"
        for title, films in groups
    ]
    return (
        front(title="Gallery", description=intro, hide=["navigation", "toc"])
        + f"# Gallery\n\n{intro}\n\n"
        + "\n".join(sections)
    )


def page(film: Film) -> str:
    """A film's page: its title, what it shows, then the film, its code folded under it."""
    return (
        front(title=film.title, description=film.words, hide=["toc"])
        + f"# {film.title}\n\n{film.words}\n\n"
        + f'```python title="examples/{film.name}.py" fold\n{film.code}\n```\n'
    )


def nav(groups: list[tuple[str, list[Film]]]) -> str:
    """The Gallery's navigation: its first page, then each group's films."""
    lines = ["nav:", "  - All films: index.md"]
    for title, films in groups:
        lines.append(f"  - {json.dumps(title)}:")
        lines += [f"      - {film.page}" for film in films]
    return "\n".join(lines) + "\n"


def main() -> None:
    intro, groups = readme()
    shutil.rmtree(GALLERY, ignore_errors=True)
    GALLERY.mkdir(parents=True)
    (GALLERY / "index.md").write_text(index(intro, groups), encoding="utf-8")
    (GALLERY / ".nav.yml").write_text(nav(groups), encoding="utf-8")
    for _, films in groups:
        for film in films:
            (GALLERY / film.page).write_text(page(film), encoding="utf-8")
    print(f"{sum(len(films) for _, films in groups)} films in {len(groups)} groups")


if __name__ == "__main__":
    main()

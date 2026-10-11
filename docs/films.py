"""A Markdown extension: a picture named by the scene it shows, `![…](film:CircleExample)`.

A film's file is named after its scene and a digest of its code (`docs/examples.py`), so a page
can't write the name of a film whose code may change. A picture whose source is `film:` and a
scene's name shows that scene's still, wherever its code is: on a page or in a docstring. A
scene that has no film yet stops the build: a card is never without its picture.
"""

from xml.etree.ElementTree import Element

from docs import examples
from markdown import Extension, Markdown
from markdown.treeprocessors import Treeprocessor

PREFIX = "film:"


def still(scene: str) -> str:
    """The URL of a scene's still: its film's, the newest if an old one is left."""
    found = sorted(
        examples.FILMS.glob(f"{scene}-*.webp"), key=lambda path: path.stat().st_mtime
    )
    stills = [path for path in found if path.stem.rsplit("-", 1)[0] == scene]
    if not stills:
        raise ValueError(
            f"film:{scene}: no film of that scene (python -m docs.examples)"
        )
    return f"{examples.URL}/{stills[-1].name}"


class Films(Treeprocessor):
    def run(self, root: Element) -> None:
        for image in root.iter("img"):
            source = image.get("src", "")
            if source.startswith(PREFIX):
                image.set("src", still(source.removeprefix(PREFIX)))
                image.set("loading", "lazy")


class FilmsExtension(Extension):
    def extendMarkdown(self, md: Markdown) -> None:
        # after inline images are made (InlineProcessor runs at 20 as a treeprocessor)
        md.treeprocessors.register(Films(md), "films", 5)


def makeExtension(**kwargs: object) -> FilmsExtension:
    return FilmsExtension(**kwargs)

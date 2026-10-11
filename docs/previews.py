"""A Markdown extension: a reference to the API previews its target on hover, as a link does.

The theme previews a link marked `data-preview` when the pointer rests on it, and Zensical's
preview extension marks the links it finds as each page is converted. A reference to the API is
no link yet then: it is an `<autoref>` tag, from a page's Markdown (`[Scene][manimgx.Scene]`) or
from the reference's templates (a signature's types), which Zensical makes a link once every
page's URL is known, keeping the tag's attributes. So each tag is marked in the rendered page.
Text is left as it is: a code block's `<` is escaped, so no tag is ever in it.

A card's link previews nothing: the card, a link as a whole, shows its page's still, name and
words already, and a preview would cover it and the cards beside it.
"""

import re

from markdown import Extension, Markdown
from markdown.postprocessors import Postprocessor

# a reference's tag not marked yet: a docstring's pass here twice, as mkdocstrings converts the
# docstring and then as its page is converted
UNMARKED = re.compile(r"<autoref\b(?![^>]*\sdata-preview\b)")
# the cards of an index (the reference's, the Gallery's), whose links Zensical marked
CARDS = re.compile(r'<div class="grid cards mx-cards">.*?</div>', re.DOTALL)


def marked(html: str) -> str:
    """A rendered page, each reference to the API in it marked to preview its target, and
    each card's link not."""
    html = UNMARKED.sub("<autoref data-preview", html)
    return CARDS.sub(lambda cards: cards[0].replace(' data-preview=""', ""), html)


class References(Postprocessor):
    def run(self, text: str) -> str:
        return marked(text)


class Previews(Extension):
    def extendMarkdown(self, md: Markdown) -> None:
        # after the raw HTML (the reference's templates) is put back in (30)
        md.postprocessors.register(References(md), "previews", 10)


def makeExtension(**kwargs: object) -> Previews:
    return Previews(**kwargs)

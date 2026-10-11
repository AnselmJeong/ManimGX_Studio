"""A reference to the API previews its target on hover, as a link does (`docs/previews.py`):
each `<autoref>` tag of a rendered page is marked, once, and the text is left as it is. A
card's link previews nothing: the card shows what the preview would."""

import pytest


def test_each_reference_is_marked_once() -> None:
    pytest.importorskip("markdown")  # the docs group's
    from docs import previews

    page = (
        '<p><autoref identifier="manimgx.Scene">Scene</autoref> and '
        '<code><autoref identifier="manimgx.Mobject" optional hover>Mobject</autoref></code>'
        "</p>"
    )
    once = previews.marked(page)
    assert once.count("<autoref data-preview ") == 2
    # a docstring's references pass twice: as the docstring is converted, then in its page
    assert previews.marked(once) == once


def test_text_is_left_as_it_is() -> None:
    pytest.importorskip("markdown")
    from docs import previews

    # a code block's tag is text: its `<` is escaped
    code = "<pre><code>&lt;autoref identifier=&quot;x&quot;&gt;y&lt;/autoref&gt;</code></pre>"
    assert previews.marked(code) == code
    # a tag whose name only starts like it
    other = '<autorefs identifier="x"></autorefs>'
    assert previews.marked(other) == other


def test_a_cards_link_previews_nothing() -> None:
    pytest.importorskip("markdown")
    from docs import previews

    card = (
        '<div class="grid cards mx-cards">\n<ul>\n<li>\n<p><img src="/films/A.webp" /></p>\n'
        '<p><a data-preview="" href="a/"><strong>A</strong></a></p>\n</li>\n</ul>\n</div>'
    )
    link = '<p><a data-preview="" href="b/">B</a></p>'
    assert previews.marked(card + link) == card.replace(' data-preview=""', "") + link

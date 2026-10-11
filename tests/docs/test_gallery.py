"""The Gallery (`scripts/docs/gallery.py`) is `examples/` as its README tells it: a card for
each film on its first page, in the README's groups, and a page for each film, with what it
shows and its code, folded under the film."""

import re

from docs import examples
from scripts.docs import gallery


def test_every_example_has_a_page_with_its_code() -> None:
    _, groups = gallery.readme()
    films = [film for _, found in groups for film in found]
    assert sorted(film.name for film in films) == sorted(
        path.stem for path in gallery.EXAMPLES.glob("*.py")
    )
    for film in films:
        page = gallery.page(film)
        assert f"\n# {film.title}\n\n{film.words}\n" in page, film.name
        assert page.count(f'```python title="examples/{film.name}.py" fold\n') == 1


def test_every_film_has_a_card_that_links_its_page() -> None:
    intro, groups = gallery.readme()
    index = gallery.index(intro, groups)
    for title, films in groups:
        assert index.count(f"\n## {title}\n") == 1
        for film in films:
            card = (
                f"-   ![](film:{film.scene})\n\n    [**{film.title}**]({film.page})\n\n"
            )
            assert index.count(card) == 1, film.name
    nav = gallery.nav(groups)
    assert all(nav.count(f" - {film.page}\n") == 1 for _, f in groups for film in f)


def test_a_card_says_one_sentence() -> None:
    """A card's sentence is the first of what the film shows: short, and whole."""
    _, groups = gallery.readme()
    for _, films in groups:
        for film in films:
            assert re.fullmatch(r"[A-Z0-9√].*[.?!]", film.lead), film.name
            assert len(film.lead.split()) <= 24, film.name
            assert film.words.startswith(film.lead), film.name


def test_gallery_scene_names_do_not_clash_with_other_examples() -> None:
    """Scene names identify films across the entire site, including narrated lessons."""
    scenes = {
        example.scene: example.where
        for example in examples.examples()
        if not example.where.startswith(("docs/content/gallery/", "examples/"))
    }
    _, groups = gallery.readme()
    for _, films in groups:
        for film in films:
            assert film.scene not in scenes, (film.name, scenes.get(film.scene))
            scenes[film.scene] = f"examples/{film.name}.py"

"""The theme's overrides, copied from Zensical, and what they add: the header's lockup (the logo
and "by Academa" beside it, each its own link) and the footer's band, Academa's. Each copy is
checked against Zensical's templates. The logo and byline share a vertical canvas, so CSS
needs no alignment offsets. And the band offers the newsletter only with the door its field
posts to."""

import re
import tomllib
from pathlib import Path

import pytest

DOCS = Path(__file__).parents[2] / "docs"
CONFIG = tomllib.loads((DOCS / "zensical.toml").read_text(encoding="utf-8"))["project"]
PARTIALS = DOCS / "overrides" / "partials"
IMAGES = DOCS / "content" / "images"
STYLESHEET = DOCS / "content" / "stylesheets" / "manimgx.css"


def lines(path: Path) -> list[str]:
    """A template's lines, without its first comment and indentation."""
    text = re.sub(r"\A\{#-.*?-#\}\n", "", path.read_text(encoding="utf-8"), flags=re.S)
    return [line.strip() for line in text.splitlines()]


def zensicals(name: str) -> list[str]:
    """One of Zensical's partials, as `lines` reads it."""
    zensical = pytest.importorskip("zensical")  # the docs group's
    return lines(Path(zensical.__file__).parent / "templates" / "partials" / name)


def view(name: str) -> list[float]:
    """An SVG's viewBox: x, y, width, height."""
    box = re.search(r'viewBox="([^"]+)"', (IMAGES / name).read_text(encoding="utf-8"))
    assert box, name
    return [float(v) for v in box.group(1).split()]


def test_the_header_is_zensicals_but_for_the_lockup() -> None:
    theirs, ours = zensicals("header.html"), lines(PARTIALS / "header.html")
    # the lockup: a box around Zensical's link to the home page, and the byline after it
    start = ours.index('<div class="mx-lockup">')
    byline = next(i for i, line in enumerate(ours) if "mx-byline" in line)
    end = ours.index("</div>", byline)
    assert ours[:start] + ours[start + 1 : byline] + ours[end + 1 :] == theirs


def test_the_footer_is_zensicals_but_for_the_band() -> None:
    theirs, ours = zensicals("footer.html"), lines(PARTIALS / "footer.html")
    # the band, where Zensical's copyright and social links were, before the footer ends
    meta = theirs.index('<div class="md-footer-meta md-typeset">')
    end = theirs.index("</footer>")
    assert ours == [
        *theirs[:meta],
        '{% include "partials/academa.html" %}',
        *theirs[end:],
    ]


def test_the_header_images_share_a_vertical_canvas_without_css_offsets() -> None:
    for ground in ("light", "dark"):
        x, y, _, height = view(f"byline-{ground}.svg")
        _, top, _, logo_height = view(f"logo-{ground}.svg")
        assert x == 0
        assert (y, height) == (top, logo_height)
    css = STYLESHEET.read_text(encoding="utf-8")
    lockup = re.findall(r"\.mx-(?:lockup|byline)[^{}]*\{([^{}]*)\}", css)
    assert not any("transform:" in rule or "margin-top:" in rule for rule in lockup)


def band(extra: dict[str, object]) -> str:
    """The footer's band, rendered with the site's settings and this `extra`."""
    jinja2 = pytest.importorskip("jinja2")  # the docs group's
    zensical = pytest.importorskip("zensical")
    templates = [DOCS / "overrides", Path(zensical.__file__).parent / "templates"]
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(templates))
    environment.filters["url"] = lambda path: path
    config = {**CONFIG, "extra": extra}
    return environment.get_template("partials/academa.html").render(config=config)


def test_the_newsletter_field_posts_to_its_door() -> None:
    door = CONFIG["extra"]["newsletter"]
    assert door.startswith("https://")
    html = band(CONFIG["extra"])
    assert f'<form class="mx-footer__subscribe" method="post" action="{door}">' in html
    assert 'class="mx-footer__answer" role="status"' in html
    # the privacy policy that covers what the field collects
    assert 'href="https://academa.ai/privacy"' in html


def test_without_a_door_the_band_offers_no_newsletter() -> None:
    html = band({key: v for key, v in CONFIG["extra"].items() if key != "newsletter"})
    assert "<form" not in html
    assert "academa.ai/privacy" not in html
    assert "Join the Discord" in html

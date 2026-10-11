"""The README, included as the Welcome page, reaches the site's own images and pages on the
site it is on (`docs/links.py`), so `just serve-docs` shows the images it built."""

import re
from pathlib import Path

import pytest

README = Path(__file__).parents[2] / "README.md"
WELCOME = README.parent / "docs" / "content" / "index.md"


def test_the_readme_reaches_the_site_it_is_on() -> None:
    markdown = pytest.importorskip("markdown")  # the docs group's
    from docs import links

    html = markdown.markdown(
        README.read_text(encoding="utf-8"),
        extensions=[
            "tables",
            "md_in_html",
            "pymdownx.superfences",
            links.makeExtension(),
        ],
    )
    site = f"https://{links.HOST}"
    for attribute in ("src", "srcset", "href", "poster"):
        assert f'{attribute}="{site}' not in html
    # the banner, the logo on each ground
    assert 'srcset="/showcase/logo-dark.svg"' in html
    assert 'src="/showcase/logo-light.svg"' in html
    # the wall's films, and the scene's film on each ground
    assert 'src="/showcase/quadratic_formula.gif"' in html
    assert 'srcset="/films/readme-Hello3D.svg"' in html
    assert 'src="/films/readme-Hello3D-light.svg#readme"' in html
    # a URL written as text, which an agent is told to follow, stays as it is
    assert f"Follow {site}/llms.txt" in html


def test_the_welcome_page_uses_the_readme_s_same_showcase_images() -> None:
    markdown = pytest.importorskip("markdown")
    from docs import links

    readme = README.read_text(encoding="utf-8")
    raw = f"https://{links.RAW_HOST}{links.RAW_SHOWCASE}"
    images = re.findall(rf'src="{re.escape(raw)}([^"/]+\.gif)"', readme)
    assert len(images) == 9
    html = markdown.markdown(
        WELCOME.read_text(encoding="utf-8"),
        extensions=["tables", "pymdownx.snippets", links.makeExtension()],
        extension_configs={
            "pymdownx.snippets": {
                "base_path": [str(README.parent)],
                "check_paths": True,
            }
        },
    )
    assert re.findall(r'src="/showcase/([^"/]+\.gif)"', html) == images
    assert raw not in html


def test_the_banner_keeps_both_github_themes_and_a_light_fallback() -> None:
    pytest.importorskip("markdown")
    from docs import links

    readme = README.read_text(encoding="utf-8")
    banner = re.search(r"<picture>.*?</picture>", readme, re.DOTALL)
    assert banner is not None
    raw = f"https://{links.RAW_HOST}{links.RAW_SHOWCASE}"
    # GitHub's themed-picture component honors its selected theme, including overrides
    # of the OS preference. Raw repo URLs keep both variants independent of docs deploys.
    sources = re.findall(
        r'<source media="\(prefers-color-scheme: (dark|light)\)" srcset="([^"]+)">',
        banner.group(),
    )
    assert sources == [(theme, f"{raw}logo-{theme}.svg") for theme in ("dark", "light")]
    assert f'src="{raw}logo-light.svg"' in banner.group()
    local = links.paths(banner.group())
    for theme in ("dark", "light"):
        assert f'srcset="/showcase/logo-{theme}.svg"' in local
    assert 'src="/showcase/logo-light.svg"' in local


def test_comparison_markdown_renders_five_images_without_fixed_dimensions() -> None:
    markdown = pytest.importorskip("markdown")
    from docs import links

    html = markdown.markdown(
        README.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", links.makeExtension()],
    )
    tables = re.findall(r"<table\b.*?</table>", html, re.DOTALL)
    assert len(tables) == 1
    table = tables[0]
    assert len(re.findall(r"<th(?:\s|>)", table)) == 5
    images = re.findall(r"<img\b[^>]*>", table)
    assert len(images) == 5
    for image, name in zip(
        images,
        ("manimgx", "manim_ce", "manimgl", "blender_workbench", "blender_eevee"),
        strict=True,
    ):
        assert f'src="/images/benchmark-quality/{name}-light.png"' in image
        assert not re.search(r"\b(?:width|height)=", image)


def test_raw_showcase_urls_become_local_without_losing_url_parts() -> None:
    pytest.importorskip("markdown")
    from docs import links

    raw = f"https://{links.RAW_HOST}{links.RAW_SHOWCASE}"
    assert links.paths(
        f'<img src="{raw}hopf_fibration.gif?v=2#preview" '
        f'srcset="{raw}one.gif 1x, {raw}two.gif 2x">'
    ) == (
        '<img src="/showcase/hopf_fibration.gif?v=2#preview" '
        'srcset="/showcase/one.gif 1x, /showcase/two.gif 2x">'
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://raw.githubusercontent.com/other/manimgx/main/docs/content/showcase/a.gif",
        "https://raw.githubusercontent.com/academa-labs/manimgx/main/examples/a.gif",
        "https://raw.githubusercontent.com/academa-labs/manimgx/main/docs/content/showcase-other/a.gif",
        "https://raw.githubusercontent.com/academa-labs/manimgx/other/docs/content/showcase/a.gif",
        "https://raw.githubusercontent.com.example.org/academa-labs/manimgx/main/docs/content/showcase/a.gif",
    ],
)
def test_other_raw_urls_are_preserved(url: str) -> None:
    pytest.importorskip("markdown")
    from docs import links

    tag = f'<img src="{url}">'
    assert links.paths(tag) == tag


def test_only_the_site_s_own_urls_become_paths() -> None:
    pytest.importorskip("markdown")
    from docs import links

    site = f"https://{links.HOST}"
    tags = (
        f'<a href="{site}">'
        f"<img src='{site}/a.svg#readme' srcset=\"{site}/a.svg 1x, {site}/b.svg 2x\">"
        f'<img src="https://img.shields.io/badge/docs-{links.HOST}-blue">'
        f'<code>&lt;img src="{site}/c.svg"&gt;</code>'
    )
    assert links.paths(tags) == (
        '<a href="/">'
        "<img src='/a.svg#readme' srcset=\"/a.svg 1x, /b.svg 2x\">"
        f'<img src="https://img.shields.io/badge/docs-{links.HOST}-blue">'
        f'<code>&lt;img src="{site}/c.svg"&gt;</code>'
    )

"""A Markdown extension: a page's links and images on the site's own host, as its paths.

The README is written for GitHub and PyPI, so it reaches the site's images and pages by
absolute URLs (`https://manimgx.academa.ai/...`); included as the Welcome page, they would ask
the deployed site for them, even in a preview. Once a page is rendered, every URL an element
holds (`src`, `srcset`, `href`, `poster`) whose host is the site's keeps only its path, so a
page shows the images and links of the site it is on, as it was built, whatever wrote the
URL. The showcase images use the repository's raw GitHub URLs, avoiding the image proxy's
size limit and updating independently of docs deployments; those become local showcase paths
too. Text is left as it is: a code block's `<` is escaped, so no tag is ever in it.
"""

import re
import tomllib
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from markdown import Extension, Markdown
from markdown.postprocessors import Postprocessor

CONFIG = tomllib.loads(
    (Path(__file__).parent / "zensical.toml").read_text(encoding="utf-8")
)
HOST = urlsplit(CONFIG["project"]["site_url"]).netloc
RAW_HOST = "raw.githubusercontent.com"
RAW_SHOWCASE = "/academa-labs/manimgx/main/docs/content/showcase/"
# an element's start tag (a quoted value may hold ">"), and one of its URLs, quoted
TAG = re.compile(r"""<[a-zA-Z](?:"[^"]*"|'[^']*'|[^'">])*>""")
URL = re.compile(r"""(\s(src|srcset|href|poster)\s*=\s*)(["'])(.*?)\3""", re.DOTALL)


def local(url: str) -> str:
    """A site URL or the repository's raw showcase asset, as its path on the site."""
    parts = urlsplit(url)
    if parts.netloc == RAW_HOST and parts.path.startswith(RAW_SHOWCASE):
        path = "/showcase/" + parts.path.removeprefix(RAW_SHOWCASE)
        return urlunsplit(("", "", path, parts.query, parts.fragment))
    if parts.netloc != HOST:
        return url
    return urlunsplit(("", "", parts.path or "/", parts.query, parts.fragment))


def _attribute(match: re.Match[str]) -> str:
    start, name, quote, value = match.groups()
    if HOST not in value and RAW_HOST not in value:
        return match.group()
    if name == "srcset":  # candidates: a URL each, and a size or a density
        value = ", ".join(
            " ".join([local(url), *rest])
            for url, *rest in (c.split() for c in value.split(",") if c.strip())
        )
    else:
        value = local(value)
    return f"{start}{quote}{value}{quote}"


def paths(html: str) -> str:
    """A rendered page, its URLs on the site's host made the site's paths."""
    return TAG.sub(lambda tag: URL.sub(_attribute, tag.group()), html)


class Paths(Postprocessor):
    def run(self, text: str) -> str:
        return paths(text)


class SitePaths(Extension):
    def extendMarkdown(self, md: Markdown) -> None:
        # after the raw HTML (the README's images) is put back in (30)
        md.postprocessors.register(Paths(md), "site_paths", 10)


def makeExtension(**kwargs: object) -> SitePaths:
    return SitePaths(**kwargs)

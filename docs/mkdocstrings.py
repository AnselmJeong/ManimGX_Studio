"""A Markdown extension: mkdocstrings finds ManimGX's templates, `docs/templates/`.

mkdocstrings' `custom_templates` names a folder. MkDocs makes it absolute, from the folder of
its settings, before mkdocstrings reads it; Zensical passes it on as written. Then mkdocstrings
reads it from the working directory (the repository's root, where the build runs) and finds
nothing there, so its default templates show the reference, while mkdocstrings-python reads it
from the settings' folder (`docs/`). This extension makes it absolute, from the settings'
folder, as MkDocs does. It is listed before mkdocstrings, whose extension Zensical adds last, so
it does this before mkdocstrings reads the setting.
"""

from pathlib import Path

from markdown import Extension, Markdown

MKDOCSTRINGS = "zensical.extensions.mkdocstrings"


def resolve() -> None:
    """Make the settings' `custom_templates` absolute, from the settings' folder."""
    from zensical.config import get_config

    config = get_config()
    options = config["mdx_configs"].get(MKDOCSTRINGS) or {}
    templates = options.get("custom_templates")
    if templates and not Path(templates).is_absolute():
        options["custom_templates"] = str(Path(config["root_dir"]) / templates)


class Templates(Extension):
    def extendMarkdown(self, md: Markdown) -> None:
        resolve()


def makeExtension(**kwargs: object) -> Templates:
    return Templates(**kwargs)

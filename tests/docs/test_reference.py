"""The API reference shows what the package documents, once, and no more
(`docs/content/reference/`).

Its pages are written by hand: their story in prose, and the API as mkdocstrings' `:::`
blocks, which render each object from its docstring. So nothing generates the list of what
they show, and these tests keep it whole. What must be shown: every name `import manimgx as
m` exports, and every documented member of an exported class: its own, and those it inherits
from bases the package doesn't export (a private `_Grid`'s), down to its first exported base.
Not what is `@deprecated` (`docs/deprecated.py` takes it out as griffe loads the package): a
deprecated class stays in its module, for the classes made from it, but leaves the reference
with its members, what those classes inherit from it among them. Nor what is listed in
`UNDOCUMENTED`: what can't carry the decorator (an attribute, a constant, a type alias) and no
scene needs. And keywords a page shows (a TypedDict, such as `Style`) are shown whole: every
key, the ones its bases give it too.
"""

import re
import tomllib
from dataclasses import fields
from pathlib import Path

import pytest
import yaml

griffe = pytest.importorskip("griffe")  # the docs group's

ROOT = Path(__file__).parents[2]
PAGES = ROOT / "docs" / "content" / "reference"
DIRECTIVE = re.compile(r"^:::\s+(\S+)\s*\n((?:[ \t]+.*\n|\n)*)", re.MULTILINE)
CARDS = re.compile(
    r'<div class="grid cards mx-cards" markdown>\n(.*?)\n</div>', re.DOTALL
)


def test_reference_options_are_accepted_by_the_installed_handler() -> None:
    handler = pytest.importorskip("mkdocstrings_handlers.python")
    config = tomllib.loads((ROOT / "docs/zensical.toml").read_text(encoding="utf-8"))
    defaults = config["project"]["plugins"]["mkdocstrings"]["handlers"]["python"][
        "options"
    ]
    accepted = {field.name for field in fields(handler.PythonOptions)}
    handler.PythonOptions.from_data(**defaults)
    for page in sorted(PAGES.rglob("*.md")):
        for directive in DIRECTIVE.finditer(page.read_text(encoding="utf-8")):
            local = yaml.safe_load(directive[2]) or {}
            options = defaults | local.get("options", {})
            # With optional Pydantic installed the handler silently drops unknown keys;
            # the docs-only environment rejects them. Both must receive the same schema.
            assert not (unknown := options.keys() - accepted), (
                f"{page.relative_to(PAGES)}: {directive[1]}: unknown options {unknown}"
            )
            try:
                handler.PythonOptions.from_data(**options)
            except (TypeError, ValueError) as error:
                pytest.fail(f"{page.relative_to(PAGES)}: {directive[1]}: {error}")


# What the package documents for its own developers, and the reference leaves out
UNDOCUMENTED = {
    # a mobject's state, which its methods and the style keywords read and set
    *(
        f"Mobject.{name}"
        for name in [
            "background_stroke_rgbas",
            "background_stroke_width",
            "cap_style",
            "defaults",
            "dim",
            "fill_rgbas",
            "joint_type",
            "material",
            "paint",
            "shade_in_3d",
            "shared",
            "sheen_direction",
            "sheen_factor",
            "stroke_rgbas",
            "style",
            "updaters",
            "updating_suspended",
            "z_index_group",
        ]
    ),
    *(
        f"VMobject.{name}"
        for name in [
            "gradient_frame",
            "make_smooth_after_applying_functions",
            "n_points_per_curve",
            "pre_function_handle_to_anchor_scale_factor",
            "tolerance_for_point_equality",
        ]
    ),
    "Axes.num_sampled_graph_points_per_tick",
    "Animation.defaults",
    "Scene.clock",
    "Scene.updaters",
    # Manim CE's defaults and units, as constants
    *(
        f"manimgx.{name}"
        for name in [
            "DEFAULT_ARROW_TIP_LENGTH",
            "DEFAULT_DASH_LENGTH",
            "DEFAULT_DOT_RADIUS",
            "DEFAULT_FONT_SIZE",
            "DEFAULT_POINTWISE_FUNCTION_RUN_TIME",
            "DEFAULT_POINT_DENSITY_1D",
            "DEFAULT_POINT_DENSITY_2D",
            "DEFAULT_SMALL_DOT_RADIUS",
            "DEFAULT_STROKE_WIDTH",
            "DEFAULT_WAIT_TIME",
            "SCALE_FACTOR_PER_FONT_POINT",
            "START_X",
            "START_Y",
            "Pixels",
            "Degrees",
            "Munits",
        ]
    ),
    # the types of annotations
    *(
        f"manimgx.{name}"
        for name in [
            "Coefficients",
            "Colorscale",
            "Floats",
            "ParsableManimColor",
            "RateFunction",
            "Step",
        ]
    ),
}


@pytest.fixture(scope="module")
def package() -> "griffe.Module":
    from docs.deprecated import Deprecated

    loaded = griffe.load(
        "manimgx",
        search_paths=[ROOT / "src"],
        extensions=griffe.load_extensions(Deprecated),
        resolve_aliases=True,
        resolve_external=False,
    )
    assert isinstance(loaded, griffe.Module)
    return loaded


def real(obj: "griffe.Object | griffe.Alias") -> "griffe.Object | None":
    try:
        return obj.final_target if isinstance(obj, griffe.Alias) else obj
    except (griffe.AliasResolutionError, griffe.CyclicAliasError):
        return None


def resolve(package: "griffe.Module", identifier: str) -> "griffe.Object | None":
    try:
        return real(package[identifier.removeprefix("manimgx.")])
    except KeyError:
        return None


def documented(obj: "griffe.Object") -> bool:
    return bool(obj.docstring and obj.docstring.value.strip())


def members(cls: "griffe.Class", stop: set[str]) -> dict[str, "griffe.Object"]:
    """A class's documented public members, by name: its own, then its bases' down to the
    first in `stop`, or the first deprecated."""
    from docs.deprecated import deprecated

    found: dict[str, griffe.Object] = {}
    for owner in [cls, *cls.mro()]:
        if owner is not cls and (owner.path in stop or deprecated(owner)):
            break
        for name, member in owner.members.items():
            target = real(member)
            if name.startswith("_") or name in found or target is None:
                continue
            if target.path.startswith("manimgx") and documented(target):
                found[name] = target
    return found


def required(package: "griffe.Module") -> tuple[dict[str, str], set[str]]:
    """What must be shown, by path, each with a label (`manimgx.Circle`,
    `Circle.surround`); and the exported classes' paths."""
    need: dict[str, str] = {}
    classes = []
    for name, member in package.members.items():
        target = real(member)
        if name.startswith("_") or target is None or target.is_module:
            continue
        if target.path.startswith("manimgx."):
            need.setdefault(target.path, f"manimgx.{name}")
            if isinstance(target, griffe.Class):
                classes.append(target)
    exported = {cls.path for cls in classes}
    for cls in classes:
        for name, member in members(cls, exported).items():
            need.setdefault(member.path, f"{cls.name}.{name}")
    return need, exported


def shown(package: "griffe.Module") -> dict[str, list[str]]:
    """What the pages render, by path: each with the pages that render it."""
    seen: dict[str, list[str]] = {}
    for page in sorted(PAGES.rglob("*.md")):
        where = str(page.relative_to(PAGES))
        for match in DIRECTIVE.finditer(page.read_text(encoding="utf-8")):
            obj = resolve(package, match[1])
            assert obj is not None, f"{where}: {match[1]} is not in the package"
            seen.setdefault(obj.path, []).append(where)
            if not isinstance(obj, griffe.Class):
                continue
            options = match[2]
            listed = re.search(r"(?<!inherited_)members:\s*(false|\[.*?\])", options)
            inherited = re.search(r"inherited_members:\s*(true|\[.*?\])", options)
            # `inherited_members: true` makes every inherited member one to pick
            own = (
                members(obj, set())
                if inherited and inherited[1] == "true"
                else {
                    name: target
                    for name, member in obj.members.items()
                    if not name.startswith("_")
                    and (target := real(member)) is not None
                    and documented(target)
                }
            )
            if listed is None:
                chosen = own
            elif listed[1] == "false":
                chosen = {}
            else:
                chosen = {n: own[n] for n in re.findall(r"\w+", listed[1]) if n in own}
            if inherited and inherited[1] != "true":
                every = members(obj, set())
                chosen |= {n: every[n] for n in re.findall(r"\w+", inherited[1])}
            for member in chosen.values():
                seen.setdefault(member.path, []).append(where)
    return seen


def palette_shows(package: "griffe.Module", path: str) -> bool:
    """Whether a name is a named color, which the colors' page shows as its palette."""
    obj = resolve(package, path)
    return isinstance(obj, griffe.Attribute) and str(obj.value).startswith(
        "ManimColor("
    )


def test_every_documented_name_is_shown(package: "griffe.Module") -> None:
    need, _ = required(package)
    seen = shown(package)
    names: dict[str, set[str]] = {}
    for path in seen:
        owner, _, name = path.rpartition(".")
        names.setdefault(name, set()).add(owner)

    def related(path: str) -> bool:
        """Whether an override's base, or a base's override, is shown under its name."""
        owner, _, name = path.rpartition(".")
        cls = resolve(package, owner)
        if not isinstance(cls, griffe.Class):
            return False
        lineage = {cls.path, *(base.path for base in cls.mro())}
        for other in names.get(name, ()):
            other_cls = resolve(package, other)
            if other in lineage or (
                isinstance(other_cls, griffe.Class)
                and cls.path in {base.path for base in other_cls.mro()}
            ):
                return True
        return False

    def another_name(label: str) -> bool:
        """Whether an export is another name of a class shown (`VGroup = Group`)."""
        obj = resolve(package, label)
        if not isinstance(obj, griffe.Attribute) or obj.value is None:
            return False
        other = resolve(package, f"manimgx.{obj.value}")
        return isinstance(other, griffe.Class) and other.path in seen

    missing = sorted(
        label
        for path, label in need.items()
        if path not in seen
        and label not in UNDOCUMENTED
        and not palette_shows(package, label)
        and not another_name(label)
        and not related(path)
    )
    assert not missing, f"not on a page of docs/content/reference/: {missing}"


def test_nothing_is_shown_twice(package: "griffe.Module") -> None:
    """A class, a function or a constant is shown once; a member a private base gives two
    classes (`_Grid.get_rows`, Matrix's and Table's) is shown with each."""
    twice = {}
    for path, where in shown(package).items():
        obj = resolve(package, path)
        if len(where) > 1 and obj is not None and isinstance(obj.parent, griffe.Module):
            twice[path] = where
    assert not twice, f"shown on more than one page, or twice on one: {twice}"


def keywords(cls: "griffe.Class") -> bool:
    """Whether a class is a TypedDict: keywords, which a signature unpacks."""
    return any(
        "TypedDict" in str(base) for owner in [cls, *cls.mro()] for base in owner.bases
    )


def test_keywords_shown_show_every_key(package: "griffe.Module") -> None:
    """A page that shows keywords shows each of their keys: there, or with other keywords
    (`TippedBase`'s style keys are `Style`'s)."""
    seen = shown(package)
    missing = sorted(
        f"{path}.{name}"
        for path in seen
        if isinstance(cls := resolve(package, path), griffe.Class) and keywords(cls)
        for name, key in members(cls, set()).items()
        if key.path not in seen
    )
    assert not missing, f"keys not shown: {missing}"


def test_undocumented_names_exist(package: "griffe.Module") -> None:
    need, _ = required(package)
    labels = set(need.values())
    assert labels >= UNDOCUMENTED, sorted(UNDOCUMENTED - labels)


def test_every_card_has_its_film() -> None:
    """A card shows the still of a scene the docs define (`![](film:Scene)`, which
    `docs/films.py` resolves), and nothing else above its name: no count of pages."""
    from docs import examples

    scenes = {str(example.scene) for example in examples.examples()}
    for page in PAGES.rglob("*.md"):
        for block in CARDS.findall(page.read_text(encoding="utf-8")):
            for card in re.split(r"^-   ", block, flags=re.MULTILINE)[1:]:
                picture = re.match(r"!\[\]\(film:(\w+)\)\n\n    \[\*\*", card)
                where = page.relative_to(PAGES)
                assert picture, (
                    f"{where}: a card is a film, then its name: {card[:60]!r}"
                )
                assert picture[1] in scenes, (
                    f"{where}: no scene {picture[1]} in the docs"
                )


def test_nothing_deprecated_is_shown(package: "griffe.Module") -> None:
    """A deprecated class stays in its module for the classes made from it, but no page
    shows it, nor what is deprecated in a class shown."""
    from docs.deprecated import deprecated

    hidden = sorted(
        path
        for path in shown(package)
        if (obj := resolve(package, path)) is not None and deprecated(obj)
    )
    assert not hidden, f"deprecated, and shown: {hidden}"


def test_symbol_badges_in_headings_and_toc() -> None:
    """The site's settings and custom templates keep Zensical's symbol badges."""
    markdown = pytest.importorskip("markdown")
    python = pytest.importorskip("mkdocstrings_handlers.python")
    docs = ROOT / "docs"
    config = tomllib.loads((docs / "zensical.toml").read_text(encoding="utf-8"))[
        "project"
    ]["plugins"]["mkdocstrings"]
    handler = python.PythonHandler(
        config=python.PythonConfig.from_data(**config["handlers"]["python"]),
        base_dir=docs,
        theme="material",
        custom_templates=str(docs / config["custom_templates"]),
        mdx=["toc"],
        mdx_config={},
    )
    handler._update_env(markdown.Markdown(extensions=["toc"]))
    options = handler.get_options({"members": False})
    try:
        for path, symbol in [
            ("manimgx.Scene", "class"),
            ("manimgx.Scene.play", "method"),
            ("manimgx.smooth", "function"),
            ("manimgx.Scene.time", "attribute"),
            ("manimgx.UP", "attribute"),
            ("manimgx.constants", "module"),
        ]:
            html = handler.render(handler.collect(path, options), options)
            assert f'doc-symbol-heading doc-symbol-{symbol}"' in html, path
            (heading,) = handler.get_headings()
            assert (
                f'doc-symbol-toc doc-symbol-{symbol}"'
                in heading.attrib["data-toc-label"]
            ), path
    finally:
        handler.teardown()

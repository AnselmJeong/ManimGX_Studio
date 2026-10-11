"""What is deprecated is left out of the API reference (`docs/deprecated.py`): each class,
function or property decorated with `@deprecated`, in every form ty flags, and nothing else."""

from pathlib import Path

import pytest

GROUP = """
from typing import TYPE_CHECKING
from warnings import deprecated

from typing_extensions import deprecated as backported

__all__ = ["Group", "VGroup", "Moving", "Zoomed", "stretch", "stretch_to", "squash"]


class Group:
    def arrange(self) -> "Group":
        return self

    @deprecated("Use arrange.", category=None)
    def arrange_submobjects(self) -> "Group":
        return self.arrange()

    @property
    def width(self) -> float:
        return 1.0

    @width.setter
    def width(self, value: float) -> None: ...

    @property
    @deprecated("Use width.", category=None)
    def old_width(self) -> float:
        return self.width


if TYPE_CHECKING:

    @deprecated("Use Group.", category=None)
    class VGroup(Group): ...

else:
    VGroup = Group


@backported("Use Group.", category=None)
class Moving(Group): ...


class Zoomed(Moving): ...


def stretch() -> None: ...


@deprecated("Use stretch.", category=None)
def stretch_to() -> None:
    stretch()


squash = deprecated("Use stretch.", category=None)(stretch)
"""


def kept(tmp_path: Path) -> dict[str, set[str]]:
    """The names griffe keeps of a package, with the extension: its module's, its class's,
    and its own that still resolve (as the reference's exports do)."""
    pytest.importorskip("griffe")  # the docs group's
    import griffe
    from docs.deprecated import Deprecated

    folder = tmp_path / "shapes"
    folder.mkdir()
    (folder / "__init__.py").write_text(
        "from shapes.group import *\nfrom shapes.group import stretch_to as stretched\n",
        encoding="utf-8",
    )
    (folder / "group.py").write_text(GROUP, encoding="utf-8")
    package = griffe.load(
        "shapes",
        search_paths=[tmp_path],
        extensions=griffe.load_extensions(Deprecated),
        resolve_aliases=True,
    )
    assert isinstance(package, griffe.Module)
    group = package["group"]
    return {
        "group": set(group.members),
        "Group": set(group["Group"].members),
        "shapes": {
            name
            for name, member in package.members.items()
            if not isinstance(member, griffe.Alias) or member.resolved
        },
    }


def test_each_form_ty_flags_is_left_out(tmp_path: Path) -> None:
    names = kept(tmp_path)
    assert "arrange_submobjects" not in names["Group"]  # a method's second name
    assert "old_width" not in names["Group"]  # a property's, decorated on its getter
    assert "stretch_to" not in names["group"]  # a function's
    # a deprecated class stays where it is defined, for the classes made from it (Zoomed),
    # but the package names none of them, by `import *` or by name
    assert {"VGroup", "Moving"} <= names["group"]
    assert {"VGroup", "Moving", "stretch_to", "stretched"}.isdisjoint(names["shapes"])


def test_what_to_use_instead_stays(tmp_path: Path) -> None:
    names = kept(tmp_path)
    assert {"arrange", "width"} <= names["Group"]
    assert {"Group", "stretch"} <= names["group"] & names["shapes"]
    # a subclass isn't deprecated with its base, as `__deprecated__` would have it
    assert "Zoomed" in names["group"] & names["shapes"]
    # an assignment isn't deprecated, to ty or here: the decorator marks a definition
    assert "squash" in names["group"]


def test_native_properties_have_no_python_getter_to_parse(tmp_path: Path) -> None:
    pytest.importorskip("griffe")
    import griffe
    from docs import deprecated

    library = tmp_path / "_engine.pyd"
    library.write_bytes(b"\x00\xffnative code")
    module = griffe.Module("_engine", filepath=library)
    prop = griffe.Attribute("frames", parent=module)
    prop.labels.add("property")
    assert not deprecated.deprecated(prop)

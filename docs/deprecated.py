"""A griffe extension: what is deprecated is left out of the API reference.

A name ManimGX keeps for code written for Manim CE, and no longer teaches (another name of a
class, an empty subclass, a method's second name), is decorated with PEP 702's
`@deprecated(message, category=None)`: ty flags each use of it, and nothing warns as it runs.
The reference documents the name to use instead. So each object so decorated is taken out of
the package as griffe loads it, for mkdocstrings (its `extensions` option names this module)
and for the reference's tests alike: it has no entry and no place among its class's members,
and a link to it stops resolving. A deprecated class stays where it is defined, for the
classes made from it, whose constructor and members are its (TransformMatchingShapes', its
base's): only its other names go, the package's among them, and no page shows it.

The decorator is read from the source, as ty reads it, not as `__deprecated__` at run time:
another name kept the same class as it runs (a decorated class `if TYPE_CHECKING:`, an
assignment `else:`) has no `__deprecated__`, and a class's is inherited by its subclasses. A
property is decorated on its getter, which griffe turns into an attribute without decorators:
its getter's are read from the module's source.
"""

import ast
from functools import cache
from pathlib import Path

import griffe

# where `deprecated` is imported from: Python's own, since 3.13, or its backport
DECORATORS = {"warnings.deprecated", "typing_extensions.deprecated"}


def deprecated(obj: griffe.Object) -> bool:
    """Whether a class, a function or a property is decorated with `@deprecated`."""
    if isinstance(obj, griffe.Class | griffe.Function):
        return any(
            decorator.callable_path in DECORATORS for decorator in obj.decorators
        )
    if isinstance(obj, griffe.Attribute) and "property" in obj.labels:
        imports = obj.module.imports
        return any(
            imports.get(name, name) in DECORATORS for name in getter_decorators(obj)
        )
    return False


def getter_decorators(prop: griffe.Attribute) -> list[str]:
    """The names of a property's getter's decorators, as its module writes them."""
    if prop.lineno is None or prop.filepath is None or isinstance(prop.filepath, list):
        # A native descriptor has no Python definition to inspect. Its module may
        # name a shared library, which is not source code.
        return []
    for node in ast.walk(tree(Path(prop.filepath))):
        if isinstance(node, ast.FunctionDef) and (node.name, node.lineno) == (
            prop.name,
            prop.lineno,
        ):
            return [
                ast.unparse(d.func if isinstance(d, ast.Call) else d)
                for d in node.decorator_list
            ]
    return []


@cache
def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def drop(obj: griffe.Object) -> None:
    """Take every deprecated object out of a module or a class, at every depth, with each
    import of one (the package's `import *`, expanded before the hook, names it too). A
    deprecated class keeps its definition, for its subclasses: only its imports go."""
    for name, member in list(obj.members.items()):
        try:
            target = member.final_target if isinstance(member, griffe.Alias) else member
        except (griffe.AliasResolutionError, griffe.CyclicAliasError):
            continue  # another package's
        if deprecated(target):
            if isinstance(member, griffe.Alias) or not isinstance(member, griffe.Class):
                obj.del_member(name)
        elif not isinstance(member, griffe.Alias) and isinstance(
            member, griffe.Module | griffe.Class
        ):
            drop(member)


class Deprecated(griffe.Extension):
    def on_package(self, *, pkg: griffe.Module, **kwargs: object) -> None:
        drop(pkg)

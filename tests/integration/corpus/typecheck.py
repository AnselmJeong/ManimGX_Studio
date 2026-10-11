"""Whether each scene is statically type safe as written for ManimGX — and safe because
ManimGX's types are precise, not because they are loose.

Three findings, all shown in full:

- `diagnostics`: `ty` with every rule an error, except `missing-override-decorator` (CE code
  never writes `@override`) and `deprecated` (CE code uses CE's names, some of which
  ManimGX deprecates in favor of one of its own).
- `escapes`: ways a scene could quiet the checker — suppression comments, `Any`, `cast`,
  `TYPE_CHECKING`, and dynamic access (`vars`, `getattr` with a literal name, …). One is
  ManimGX's limit, not the scene's: a method of the scene's own class, called through
  `.animate` or `.always`, which ManimGX's types can't name (they list the library's
  methods), so its `# ty: ignore[unresolved-attribute]` is not an escape.
- `imprecise`: expressions whose type ManimGX leaves `Any` or `Unknown`. Every call and
  attribute in every scene is wrapped in `reveal_type` and checked in one run; a value counts
  when ManimGX produced it — a ManimGX function, or a method or attribute of a ManimGX class.
  (numpy's and the standard library's own imprecision is theirs.)

`ty` receives an explicit file set in a response file, independent of OS command-line limits.
Directories outside `[tool.ty.src]` are walked as empty and "pass", so file selection stays
explicit. Each scene must also show up in the reveal run.
"""

import ast
import io
import re
import tempfile
import tokenize
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from tests.integration.corpus.case import PACKAGE, Case
from tests.typecheck import check

# every rule an error, but two: CE code overrides without the decorator, and uses CE's
# names that ManimGX deprecates (its examples are written with them, on purpose)
STRICT = (
    "--error",
    "all",
    "--ignore",
    "missing-override-decorator",
    "--ignore",
    "deprecated",
)

_REVEAL = re.compile(r"^info\[revealed-type\] Revealed type: `(?P<type>.*)`$")
_SUPPRESSION = re.compile(r"#\s*(?:type|ty|pyright)\s*:\s*ignore")
_IMPRECISE = re.compile(r"\bUnknown\b|\bAny\b|@Todo")
_CALLABLE = re.compile(
    r"^(bound method |Overload\[|def |<class |<module |<bound method |<function"
    r" |type\[)"
)
_TYPING_ESCAPES = frozenset({"Any", "cast", "TYPE_CHECKING"})
_DYNAMIC_CALLS = frozenset({"vars", "globals", "locals", "eval", "exec"})
_NAMED_ACCESS = frozenset({"getattr", "setattr", "delattr"})


@dataclass(slots=True)
class TypeReport:
    diagnostics: dict[str, list[str]] = field(default_factory=dict)
    escapes: dict[str, list[str]] = field(default_factory=dict)
    imprecise: dict[str, list[str]] = field(default_factory=dict)

    def problems(self, case: Case) -> list[str]:
        sections = (
            ("ty (every rule an error)", self.diagnostics),
            ("escapes from the checker", self.escapes),
            ("types manimgx leaves Any/Unknown", self.imprecise),
        )
        lines: list[str] = []
        for title, found in sections:
            if found.get(case.name):
                lines.append(f"{title}:")
                lines.extend(f"  {line}" for line in found[case.name])
        return lines


def report(cases: list[Case]) -> TypeReport:
    result = TypeReport()
    by_path = {case.scene.resolve(): case for case in cases}
    for path, line, _, rest in check([case.scene for case in cases], STRICT):
        case = by_path.get(path)
        if case is not None:
            result.diagnostics.setdefault(case.name, []).append(f"line {line}: {rest}")
    for case in cases:
        found = escapes(case.scene.read_bytes())
        if found:
            result.escapes[case.name] = found
    result.imprecise = imprecise(cases)
    return result


def escapes(source: bytes) -> list[str]:
    tree = ast.parse(source)
    own = _own_methods_animated(tree)
    found: list[str] = []
    for token in tokenize.tokenize(io.BytesIO(source).readline):
        if token.type == tokenize.COMMENT and _SUPPRESSION.search(token.string):
            if token.string == _OWN_METHOD and token.start[0] in own:
                continue
            found.append(f"line {token.start[0]}: {token.string}")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in {
            "typing",
            "typing_extensions",
        }:
            names = sorted(a.name for a in node.names if a.name in _TYPING_ESCAPES)
            if names:
                found.append(f"line {node.lineno}: imports {', '.join(names)}")
        elif isinstance(node, ast.Attribute) and node.attr in _TYPING_ESCAPES:
            if isinstance(node.value, ast.Name) and node.value.id in {"typing", "t"}:
                found.append(f"line {node.lineno}: uses typing.{node.attr}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            literal = (
                len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            )
            if name in _DYNAMIC_CALLS or (name in _NAMED_ACCESS and literal):
                found.append(f"line {node.lineno}: {ast.unparse(node)[:80]}")
    return sorted(found, key=lambda s: int(s.split()[1].rstrip(":")))


_OWN_METHOD = "# ty: ignore[unresolved-attribute]"


def _own_methods(tree: ast.Module) -> frozenset[str]:
    """The names of the methods the scene's own classes define."""
    return frozenset(
        item.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        for item in node.body
        if isinstance(item, ast.FunctionDef)
    )


def _own_method_animated(node: ast.AST, own: frozenset[str]) -> bool:
    """Whether an expression is a method of the scene's own class, through `.animate` or
    `.always`: one that ManimGX's types can't name."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr in own
        and _through_proxy(node.value)
    )


def _own_methods_animated(tree: ast.Module) -> set[int]:
    """The lines that call a method of the scene's own classes through `.animate` or
    `.always` (where a type checker reports it)."""
    own = _own_methods(tree)
    return {
        node.end_lineno or node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and _own_method_animated(node, own)
    }


def _through_proxy(node: ast.expr) -> bool:
    """Whether an expression is a mobject's `.animate` or `.always`, or calls on one."""
    while isinstance(node, ast.Attribute | ast.Call):
        if isinstance(node, ast.Attribute) and node.attr in {"animate", "always"}:
            return True
        node = node.value if isinstance(node, ast.Attribute) else node.func
    return False


# ── precision ─────────────────────────────────────────────────────────────────


@cache
def _manimgx_methods() -> dict[str, frozenset[str]]:
    """Methods owned by each package class, including those inherited from its bases.

    A revealed short class name alone is not provenance: NetworkX also has a Graph.
    """
    methods: dict[str, set[str]] = defaultdict(set)
    bases: dict[str, set[str]] = defaultdict(set)
    for path in PACKAGE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_bytes())):
            if not isinstance(node, ast.ClassDef):
                continue
            methods[node.name].update(
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            for base in node.bases:
                if isinstance(base, ast.Subscript):
                    base = base.value
                if isinstance(base, ast.Name):
                    bases[node.name].add(base.id)
                elif isinstance(base, ast.Attribute):
                    bases[node.name].add(base.attr)
    changed = True
    while changed:
        changed = False
        for name, parents in bases.items():
            before = len(methods[name])
            for parent in parents:
                methods[name].update(methods.get(parent, ()))
            changed |= len(methods[name]) != before
    return {name: frozenset(found) for name, found in methods.items()}


def _manimgx_names(tree: ast.Module) -> frozenset[str]:
    """The names a scene binds to ManimGX: `m` in `import manimgx as m`, and the like."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "manimgx":
                    names.add(alias.asname or "manimgx")
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "manimgx"
        ):
            names.update(alias.asname or alias.name for alias in node.names)
    return frozenset(names)


class _Reveal(ast.NodeTransformer):
    """Wraps every call and every read attribute in `reveal_type`, remembering what each wrapper
    stands for: the scene's own expression, and its line."""

    def __init__(self) -> None:
        self.site: dict[int, tuple[str, int]] = {}  # id(wrapper) -> (expression, line)

    def _wrap(self, node: ast.expr, text: str) -> ast.expr:
        call = ast.copy_location(
            ast.Call(ast.Name("reveal_type", ast.Load()), [node], []), node
        )
        self.site[id(call)] = (text, node.lineno)
        return call

    def visit_Call(self, node: ast.Call) -> ast.expr:
        text = ast.unparse(node)
        self.generic_visit(node)
        return self._wrap(node, text)

    def visit_Attribute(self, node: ast.Attribute) -> ast.expr:
        if not isinstance(node.ctx, ast.Load):
            self.generic_visit(node)
            return node
        text = ast.unparse(node)
        self.generic_visit(node)
        return self._wrap(node, text)

    # annotations, bases and decorators are types, not values
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.body = [self.visit(s) for s in node.body]
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        node.body = [self.visit(s) for s in node.body]
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AnnAssign:
        if node.value is not None:
            node.value = self.visit(node.value)
        return node


def _reveal_calls(tree: ast.AST) -> list[ast.Call]:
    """The `reveal_type` wrappers, in an order that survives unparsing and parsing again."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "reveal_type"
    ]


def imprecise(cases: list[Case]) -> dict[str, list[str]]:
    classes = _manimgx_methods()
    found: dict[str, list[str]] = defaultdict(list)
    with tempfile.TemporaryDirectory() as tmp:
        plans: list[
            tuple[
                Case, Path, str, list[tuple[str, int]], frozenset[str], frozenset[str]
            ]
        ] = []
        for case in cases:
            tree = ast.parse(case.scene.read_bytes())
            bound = _manimgx_names(tree)
            own = _own_methods(tree)
            reveal = _Reveal()
            instrumented = reveal.visit(tree)
            sites = [reveal.site[id(w)] for w in _reveal_calls(instrumented)]
            instrumented.body.insert(
                0, ast.ImportFrom("typing", [ast.alias("reveal_type")], 0)
            )
            text = ast.unparse(ast.fix_missing_locations(instrumented))
            path = Path(tmp) / case.name / "scene.py"
            path.parent.mkdir()
            path.write_text(text, encoding="utf-8")
            plans.append((case, path.resolve(), text, sites, bound, own))

        revealed = _reveal_positions([plan[1] for plan in plans])

        for case, path, text, sites, bound, own in plans:
            lines = text.splitlines()
            wrappers = _reveal_calls(ast.parse(text))
            if len(wrappers) != len(sites):
                msg = f"{case.name}: instrumentation lost track of its sites"
                raise RuntimeError(msg)
            types: dict[int, str] = {}
            for wrapper in wrappers:
                arg = wrapper.args[0]
                column = (
                    len(lines[arg.lineno - 1].encode()[: arg.col_offset].decode()) + 1
                )
                type_ = revealed.get((path, arg.lineno, column))
                if type_ is not None:
                    types[id(arg)] = type_
            if wrappers and not types:
                msg = f"ty revealed nothing in {case.name}: was it checked?"
                raise RuntimeError(msg)
            for (expression, line), wrapper in zip(sites, wrappers, strict=True):
                type_ = types.get(id(wrapper.args[0]))
                if (
                    type_ is None
                    or _CALLABLE.match(type_)
                    or not _IMPRECISE.search(type_)
                    or _own_method_animated(_strip(wrapper.args[0]), own)
                ):
                    continue
                producer = _producer(wrapper.args[0], types, classes, bound)
                if producer is not None:
                    found[case.name].append(
                        f"line {line}: {expression[:70]} is {type_[:70]} (from"
                        f" {producer})"
                    )
    return dict(found)


def _reveal_positions(files: list[Path]) -> dict[tuple[Path, int, int], str]:
    """Revealed types by (file, line, column of the revealed expression), from one ty run."""
    return {
        (path, line, column): match["type"]
        for path, line, column, rest in check(files)
        if (match := _REVEAL.match(rest))
    }


def _unwrap(node: ast.expr) -> ast.expr:
    while (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "reveal_type"
    ):
        node = node.args[0]
    return node


def _root(node: ast.expr) -> str | None:
    node = _unwrap(node)
    while isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
        node = _unwrap(node.func if isinstance(node, ast.Call) else node.value)
    return node.id if isinstance(node, ast.Name) else None


def _type_of(node: ast.expr, types: dict[int, str]) -> str:
    """The revealed type of an instrumented subexpression, if it was wrapped."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "reveal_type"
    ):
        return types.get(id(node.args[0]), "")
    return ""


def _producer(
    node: ast.expr,
    types: dict[int, str],
    classes: dict[str, frozenset[str]],
    bound: frozenset[str],
) -> str | None:
    """Who made this value, if ManimGX did: `Class.method()`, `Class.attribute`, `m.name…`."""
    if isinstance(node, ast.Call):
        callee = _type_of(node.func, types)
        method = re.match(r"bound method (\w+)(?:\[.*?\])?\.(\w+)", callee)
        if method:
            if method[2] in classes.get(method[1], ()):
                return f"{method[1]}.{method[2]}()"
            return None
        if _root(node.func) in bound:
            return ast.unparse(_strip(node.func)) + "()"
    elif isinstance(node, ast.Attribute):
        receiver = _type_of(node.value, types)
        head = re.match(r"(\w+)", receiver)
        if head and head[1] in classes:
            return f"{head[1]}.{node.attr}"
        if _root(node) in bound:
            return ast.unparse(_strip(node))
    return None


def _strip(node: ast.expr) -> ast.expr:
    """The expression without its `reveal_type` wrappers."""

    class Strip(ast.NodeTransformer):
        def visit_Call(self, node: ast.Call) -> ast.expr:
            self.generic_visit(node)
            return _unwrap(node)

    return Strip().visit(ast.parse(ast.unparse(node), mode="eval")).body

# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Ported from Manim CE 0.21 (MIT)."""

from __future__ import annotations

__all__ = ["DiGraph", "Graph"]
import itertools as it
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from collections.abc import Set as AbstractSet
from copy import copy
from typing import (
    TYPE_CHECKING,
    Concatenate,
    Literal,
    Protocol,
    Self,
    TypeIs,
    Unpack,
    cast,
    get_args,
)

import numpy as np
from typing_extensions import TypedDict

if TYPE_CHECKING:
    import networkx as nx

    from manimgx.typing import Point3D, Point3DLike

    type NxGraph = nx.classes.graph.Graph | nx.classes.digraph.DiGraph
from manimgx.drawing.paint import BLACK, ParsableManimColor
from manimgx.mobject import Group, Mobject, VMobject
from manimgx.mobjects.annotations import LabeledDot
from manimgx.mobjects.shapes import ArrowTip, Dot, Line
from manimgx.mobjects.text import MathTex

type Edge[V] = tuple[V, V]
"""An edge: the pair of its vertices, from the first to the second."""
type Maker = Callable[
    ..., Mobject
]  # a vertex or edge class: its keywords come from the configs
"""What makes a vertex or an edge: a class, as [Dot][manimgx.Dot] or
[Line][manimgx.Line], called with the keywords of its config."""
type Config = dict[
    str, object
]  # keywords for a vertex's or an edge's class (checked by it)
type NxLayout = Callable[
    ..., Mapping[Hashable, np.ndarray]
]  # networkx's layouts, given our layout configs


def _nx_layout(
    layout: NxLayout, graph: NxGraph, **kwargs: object
) -> dict[Hashable, Point3D]:
    """A networkx layout with our layout config (networkx checks the keywords)."""
    return {k: np.asarray(p, dtype=float) for k, p in layout(graph, **kwargs).items()}


def _make(maker: Maker, config_: Config) -> Mobject:
    """A vertex or edge from its class and its config (the class checks the keywords)."""
    return maker(**config_)


class TipConfig(TypedDict, total=False):
    """The tip of a [DiGraph][manimgx.DiGraph]'s edge, given as `"tip_config"` in its
    `edge_config`: for every edge, or an edge's own (see
    [add_tip][manimgx.TipableVMobject.add_tip])."""

    tip_shape: type[ArrowTip] | None
    """The class of the tip (default None:
    [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip])."""
    tip_length: float | None
    """The tip's length, in scene units (default None: the edge's default)."""
    tip_width: float | None
    """The tip's width, in scene units, for the default filled triangle (default None:
    its length)."""


class Positions[V](Protocol):
    """Where vertices go: anything a vertex looks its point up in (a dict, a layout's result)."""

    def __getitem__(self, vertex: V, /) -> Point3DLike: ...


# A layout: the networkx graph, `scale` and the layout config's keywords, to positions.
type LayoutFunction[V] = Callable[Concatenate[NxGraph, ...], Positions[V]]
"""A layout of one's own: a function of the graph (a NetworkX graph), called with its
`scale` and the keywords of the layout config, that returns each vertex's position.
Each call receives a fresh graph of the current vertices and edges. Changes to that
graph affect only this call; keep any persistent layout state in the function itself."""


def _partite_layout(
    nx_graph: NxGraph,
    scale: float = 2,
    partitions: Sequence[Sequence[Hashable]] | None = None,
    **kwargs: object,
) -> dict[Hashable, Point3D]:
    import networkx as nx

    if partitions is None or len(partitions) == 0:
        raise ValueError(
            "The partite layout requires partitions parameter to contain the partition"
            " of the vertices"
        )
    partition_count = len(partitions)
    for i in range(partition_count):
        for v in partitions[i]:
            if nx_graph.nodes[v] is None:
                raise ValueError(
                    "The partition must contain arrays of vertices in the graph"
                )
            nx_graph.nodes[v]["subset"] = i
    for v in nx_graph.nodes:
        if "subset" not in nx_graph.nodes[v]:
            nx_graph.nodes[v]["subset"] = partition_count
    return _nx_layout(nx.layout.multipartite_layout, nx_graph, scale=scale, **kwargs)


def _tree_layout(
    T: NxGraph,
    root_vertex: Hashable | None = None,
    scale: float | tuple[float | None, float | None] | None = 2,
    vertex_spacing: tuple[float, float] | None = None,
    orientation: str = "down",
) -> dict[Hashable, Point3D]:
    import networkx as nx

    if root_vertex is None:
        raise ValueError("The tree layout requires the root_vertex parameter")
    if not nx.is_tree(T):
        raise ValueError("The tree layout must be used with trees")
    children = {root_vertex: list(T.neighbors(root_vertex))}
    stack = [list(children[root_vertex]).copy()]
    stick = [root_vertex]
    parent = dict.fromkeys(children[root_vertex], root_vertex)
    pos: dict[Hashable, tuple[float, int]] = {}
    obstruction = [0.0] * len(T)
    o = -1 if orientation == "down" else 1

    def slide(v: Hashable, dx: float) -> None:
        level = [v]
        while level:
            nextlevel = []
            for u in level:
                x, y = pos[u]
                x += dx
                obstruction[y] = max(x + 1, obstruction[y])
                pos[u] = (x, y)
                nextlevel += children[u]
            level = nextlevel

    while stack:
        C = stack[-1]
        if not C:
            p = stick.pop()
            stack.pop()
            cp = children[p]
            y = o * len(stack)
            if not cp:
                x = obstruction[y]
                pos[p] = (x, y)
            else:
                x = sum(pos[c][0] for c in cp) / float(len(cp))
                pos[p] = (x, y)
                ox = obstruction[y]
                if x < ox:
                    slide(p, ox - x)
                    x = ox
            obstruction[y] = x + 1
            continue
        t = C.pop()
        pt = parent[t]
        ct = [u for u in list(T.neighbors(t)) if u != pt]
        for c in ct:
            parent[c] = t
        children[t] = copy(ct)
        stack.append(ct)
        stick.append(t)
    x_min = min(pos.values(), key=lambda t: t[0])[0]
    x_max = max(pos.values(), key=lambda t: t[0])[0]
    y_min = min(pos.values(), key=lambda t: t[1])[1]
    y_max = max(pos.values(), key=lambda t: t[1])[1]
    center = np.array([x_min + x_max, y_min + y_max, 0]) / 2
    height = y_max - y_min
    width = x_max - x_min
    if vertex_spacing is None:
        sf: float | np.ndarray
        if isinstance(scale, (float, int)) and (width > 0 or height > 0):
            sf = 2 * scale / max(width, height)
        elif isinstance(scale, tuple):
            sw = 2 * scale[0] / width if scale[0] is not None and width > 0 else 1
            sh = 2 * scale[1] / height if scale[1] is not None and height > 0 else 1
            sf = np.array([sw, sh, 0])
        else:
            sf = 1
    else:
        sx, sy = vertex_spacing
        sf = np.array([sx, sy, 0])
    return {v: (np.array([x, y, 0]) - center) * sf for v, (x, y) in pos.items()}


def _kamada_kawai_layout(
    graph: nx.Graph,
    dist: dict[Hashable, dict[Hashable, float]] | None = None,
    pos: Mapping[Hashable, Point3DLike] | None = None,
    weight: str = "weight",
    scale: float = 1,
    center: Point3DLike | None = None,
    dim: int = 2,
) -> dict[Hashable, np.ndarray]:
    """networkx's Kamada–Kawai layout without scipy: the same energy from the same circular
    start, minimized by stress majorization (monotone, deterministic) instead of L-BFGS.
    """
    import networkx as nx

    nodes = list(graph)
    n = len(nodes)
    if n == 0:
        return {}
    if dist is None:
        dist = {
            a: dict(row) for a, row in nx.shortest_path_length(graph, weight=weight)
        }
    d = np.full((n, n), 1e6)
    for i, a in enumerate(nodes):
        for j, b in enumerate(nodes):
            if b in dist.get(a, {}):
                d[i, j] = dist[a][b]
    np.fill_diagonal(d, 0.0)
    start = nx.circular_layout(graph, dim=2) if pos is None else pos
    x = np.array([np.resize(np.asarray(start[v], dtype=float), dim) for v in nodes])
    w = np.where(d > 0, 1.0 / np.maximum(d, 1e-12) ** 2, 0.0)
    v_plus = np.linalg.pinv(np.diag(w.sum(axis=1)) - w)
    stress = np.inf
    for _ in range(3000):
        gaps = np.linalg.norm(x[:, None] - x[None], axis=2)
        b = -w * d / np.where(gaps > 1e-12, gaps, np.inf)
        np.fill_diagonal(b, -b.sum(axis=1))
        x = v_plus @ b @ x
        new = float(np.sum(w * (np.linalg.norm(x[:, None] - x[None], axis=2) - d) ** 2))
        if stress - new < 1e-12 * max(stress, 1.0):
            break
        stress = new
    x -= x.mean(axis=0)
    if (limit := np.abs(x).max()) > 0:
        x *= scale / limit
    if center is not None:
        x += np.asarray(center, dtype=float)[:dim]
    return dict(zip(nodes, x, strict=True))


def _spectral_layout(
    graph: NxGraph,
    weight: str | None = "weight",
    scale: float = 1,
    center: Point3DLike | None = None,
    dim: int = 2,
    store_pos_as: str | None = None,
) -> dict[Hashable, np.ndarray]:
    """Laplacian coordinates with axes fixed by node order, including repeated eigenvalues.

    An eigensolver chooses arbitrary signs and arbitrary orthonormal bases of repeated
    eigenspaces. Projecting node coordinate axes into each whole space and choosing the
    largest remaining projection avoids magnifying a nearly zero coordinate into an axis.
    Node order breaks numerical ties. Unresolved neighboring spaces are oriented jointly;
    like any spectral embedding, nearly degenerate weights can make coordinates sensitive
    to perturbations. The constant direction is removed explicitly, also for disconnected
    graphs.
    """
    import networkx as nx

    nodes, n = list(graph), len(graph)
    origin = np.zeros(dim) if center is None else np.asarray(center, dtype=float)
    if dim < 1 or origin.shape != (dim,):
        raise ValueError(
            "a layout needs a positive dimension and a center of that dimension"
        )
    if n == 0:
        return {}
    points = np.zeros((n, dim))
    if n > 1:
        adjacency = nx.to_numpy_array(graph, weight=weight)
        if not np.isfinite(adjacency).all():
            raise ValueError("spectral edge weights must be finite")
        if magnitude := float(np.abs(adjacency).max()):
            adjacency /= magnitude
        if graph.is_directed():
            adjacency += adjacency.T.copy()
        laplacian = np.diag(adjacency.sum(axis=1)) - adjacency
        values, vectors = np.linalg.eigh(laplacian)
        rounding = np.finfo(float).eps * n
        # Cluster only eigenvalues indistinguishable at this solve's backward error:
        # its measured residual plus the rounding in an n-term matrix product.
        error = np.linalg.norm(laplacian @ vectors - vectors * values)
        error += rounding * np.sqrt(n) * np.linalg.norm(laplacian, ord=np.inf)
        cuts = [0, *(np.flatnonzero(np.diff(values) > 2 * error) + 1), n]
        columns: list[np.ndarray] = []
        group = 0
        while group + 1 < len(cuts):
            start, end = cuts[group : group + 2]
            # A space and its orthogonal complement define the same projector. Use the
            # smaller basis: a full space is exactly I, independent of a solver's axes.
            complement = end - start > n // 2
            space = (
                np.concatenate((vectors[:, :start], vectors[:, end:]), axis=1)
                if complement
                else vectors[:, start:end]
            )
            projection = space @ space.T
            if complement:
                projection = np.eye(n) - projection
            orthogonality = np.linalg.norm(space.T @ space - np.eye(space.shape[1]))
            constant = bool(np.any(np.abs(values[start:end]) <= error))
            if constant:
                projection -= np.full((n, n), 1 / n)
            gap = min(
                values[start] - values[start - 1] if start else np.inf,
                values[end] - values[end - 1] if end < n else np.inf,
            )
            # Residual/gap estimates the uncertainty of a space, not just its eigenvalue.
            uncertainty = rounding + orthogonality + error / (gap - error)
            wanted = min(end - start - int(constant), dim - len(columns))
            basis: list[np.ndarray] = []
            projection -= projection.mean(axis=0)
            for _ in range(2):
                for previous in columns:
                    projection -= np.outer(previous, previous @ projection)
            for _ in range(wanted):
                lengths = np.linalg.norm(projection, axis=0)
                largest = float(lengths.max())
                if largest <= 2 * uncertainty:
                    break
                pivot = int(np.flatnonzero(lengths >= largest - uncertainty)[0])
                direction = projection[:, pivot] / lengths[pivot]
                basis.append(direction)
                # Pivoted, twice-orthogonalized projections keep later axes away from
                # directions already chosen, without amplifying tiny first-node entries.
                for _ in range(2):
                    projection -= np.outer(direction, direction @ projection)
            if len(basis) < wanted:
                # These directions cannot be resolved from a neighboring space with
                # this solve's accuracy. Orient their joint space instead of silently
                # losing a low-frequency coordinate or replacing it with a higher one.
                neighbors = [i for i in (group, group + 1) if 0 < i < len(cuts) - 1]
                if not neighbors:
                    raise ValueError("spectral coordinates could not be resolved")
                boundary = min(
                    neighbors, key=lambda i: values[cuts[i]] - values[cuts[i] - 1]
                )
                del cuts[boundary]
                columns, group = [], 0
                continue
            columns.extend(basis)
            if len(columns) == dim:
                break
            group += 1
        points[:, : len(columns)] = np.array(columns).T
    points = nx.rescale_layout(points, scale=scale) + origin
    positions = dict(zip(nodes, points, strict=True))
    if store_pos_as is not None:
        nx.set_node_attributes(graph, positions, store_pos_as)
    return positions


LayoutName = Literal[
    "circular",
    "kamada_kawai",
    "partite",
    "planar",
    "shell",
    "spectral",
    "spiral",
    "spring",
    "tree",
]
"""The names of the layouts a graph is laid out by (see
[GenericGraph][manimgx.mobjects.graph.GenericGraph]). The spectral layout fixes its axes by
node order, so an eigensolver's arbitrary choice of basis does not rotate or skew a graph."""


def _layout(name: LayoutName) -> LayoutFunction[Hashable]:
    import networkx as nx

    return {
        "circular": nx.layout.circular_layout,
        "kamada_kawai": _kamada_kawai_layout,
        "partite": _partite_layout,
        "planar": nx.layout.planar_layout,
        "shell": nx.layout.shell_layout,
        "spectral": _spectral_layout,
        "spiral": nx.layout.spiral_layout,
        "spring": nx.layout.spring_layout,
        "tree": _tree_layout,
    }[name]


type Layout[V] = (
    LayoutName | str | Positions[V] | LayoutFunction[V]
)  # a layout's name, checked when used
"""Where a graph's vertices go: a layout's name, the vertices' positions (a dictionary
from each vertex to its point), or a layout function."""


def _is_function[V](layout: Layout[V]) -> TypeIs[LayoutFunction[V]]:
    return callable(layout)


def _is_name(layout: object) -> TypeIs[LayoutName]:
    return isinstance(layout, str) and layout in get_args(LayoutName)


class VertexOptions[V: Hashable](TypedDict, total=False, closed=True):
    """[add_vertices][manimgx.mobjects.graph.GenericGraph.add_vertices]' keywords, for
    the methods that pass them on: where the new vertices go, their labels, their kind
    and their keywords."""

    positions: Mapping[V, Point3DLike] | None
    """Where new vertices go, by vertex (default None: at the graph's center)."""
    labels: bool | Mapping[V, bool | Mobject]
    """Whether each new vertex is labeled with its name, typeset as math: True for
    all, or by vertex, True or a label of one's own (default False)."""
    label_fill_color: ParsableManimColor
    """The color of the labels made from names (default black)."""
    vertex_type: Maker
    """The class of the new vertices (default [Dot][manimgx.Dot]; a labeled one is a
    [LabeledDot][manimgx.LabeledDot])."""
    vertex_config: Configs | None
    """Keywords for the new vertices, over the graph's: for all of them, and a vertex's
    own under its name, in place of those for all (default None: none)."""
    vertex_mobjects: Mapping[V, Mobject] | None
    """Mobjects to be vertices themselves, by vertex (default None: none)."""


class GraphOptions[V: Hashable](TypedDict, total=False, closed=True):
    """A graph's keywords but its vertices and edges, for the methods that pass them on
    ([from_networkx][manimgx.mobjects.graph.GenericGraph.from_networkx], a
    [Polyhedron][manimgx.Polyhedron]'s `graph_config`): its labels, layout, and the
    kinds and keywords of its vertices and edges."""

    labels: bool | Mapping[V, Mobject]
    """Whether each vertex is labeled with its name, typeset as math, or a label for
    each (default False)."""
    label_fill_color: ParsableManimColor
    """The color of the labels made from names (default black)."""
    layout: Layout[V]
    """Where the vertices go: a layout's name, their positions, or a layout function
    (default `"spring"`)."""
    layout_scale: float | tuple[float, float, float]
    """How far the layout reaches from the center, in scene units (default 2)."""
    layout_config: Mapping[str, object] | None
    """Keywords for the layout function: a `"spring"` layout's `seed`, … (default None:
    none)."""
    vertex_type: Maker
    """The class of the vertices (default [Dot][manimgx.Dot]; a labeled one is a
    [LabeledDot][manimgx.LabeledDot])."""
    vertex_config: Configs | None
    """Keywords for the vertices: for all of them, and a vertex's own under its name, in
    place of those for all (default None: none)."""
    vertex_mobjects: Mapping[V, Mobject] | None
    """Mobjects to be vertices themselves, by vertex (default None: none)."""
    edge_type: Maker
    """The class of the edges (default [Line][manimgx.Line])."""
    partitions: Sequence[Sequence[V]] | None
    """For the `"partite"` layout: the vertices of each column, in order (default None:
    none)."""
    root_vertex: V | None
    """For the `"tree"` layout: the vertex at its top (default None: none)."""
    edge_config: Configs | None
    """Keywords for the edges: for all of them, and an edge's own under its pair of
    vertices, in place of those for all (default None: none)."""


class Configs(Protocol):
    """Keywords for vertices (or edges): a dictionary of keywords for all of them, and
    of a vertex's own keywords under its name (an edge's under its pair of vertices)."""

    # any key type: a Mapping's key type is invariant

    def items(self) -> AbstractSet[tuple[object, object]]: ...


def _split[K: Hashable](
    configs: Configs | None, items: Iterable[K]
) -> tuple[Config, dict[K, Config]]:
    """The keywords for all, and each item's own (given under the item)."""
    given: dict[object, object] = dict(configs.items()) if configs is not None else {}
    names = set(items)
    shared: Config = {
        k: v for k, v in given.items() if isinstance(k, str) and k not in names
    }
    return shared, {
        k: dict(cast("Mapping[str, object]", given[k])) for k in names if k in given
    }


class GenericGraph[V: Hashable = Hashable](VMobject):
    """What [Graph][manimgx.Graph] and [DiGraph][manimgx.DiGraph] have in common:
    vertices and edges, laid out and kept together; white dots and lines unless
    styled.

    The vertices are any hashable values (numbers, strings, …): each is made a mobject,
    a [Dot][manimgx.Dot] by default, and `graph[v]` is the mobject of vertex `v`. The
    edges are pairs of vertices: each is made a mobject, a [Line][manimgx.Line] by
    default, drawn behind the vertices (z-index -1), and `graph[(u, v)]` is the mobject
    of edge `(u, v)`. An updater keeps the edges on their vertices: move a vertex (or
    animate it) and its edges follow. Vertices and edges can be added and removed, and
    the whole graph laid out anew.

    The layout places the vertices: by a name — NetworkX's `"circular"`,
    `"kamada_kawai"`, `"planar"`, `"shell"`, `"spectral"`, `"spiral"` and `"spring"`
    (random unless given a `seed` in `layout_config`), or `"partite"` (in columns, by
    `partitions`) and `"tree"` (down from `root_vertex`) — by a dictionary of positions,
    or by a function of one's own. It spans about `layout_scale` from the center, the
    center at the scene's origin; points of two coordinates lie in the plane z = 0.

    Args:
        vertices: The vertices: hashable values, each a vertex's name.
        edges: The edges, each a pair of vertices.
        labels: Whether each vertex is labeled with its name, typeset as math (a
            vertex that is a [Dot][manimgx.Dot] becomes a
            [LabeledDot][manimgx.LabeledDot]); or a label for each, by vertex.
        label_fill_color: The color of the labels made from names.
        layout: Where the vertices go: a layout's name, their positions (a dictionary
            from each vertex to its point), or a layout function, called with the
            NetworkX graph, `scale` and the keywords of `layout_config`.
        layout_scale: How far the layout reaches from the center, in scene units.
        layout_config: Keywords for the layout function; None for none.
        vertex_type: The class of the vertices, called with each vertex's keywords.
        vertex_config: Keywords for the vertices: for all of them, and a vertex's own
            under its name, in place of those for all, as in
            `{"radius": 0.2, 3: {"color": RED}}`; None for none.
        vertex_mobjects: Mobjects to be vertices themselves, by vertex; None for none.
        edge_type: The class of the edges, called with each edge's ends and keywords.
        partitions: For the `"partite"` layout: the vertices of each column, in order
            (those of none make a last column); None for none.
        root_vertex: For the `"tree"` layout: the vertex at its top; None for none.
        edge_config: Keywords for the edges: for all of them, and an edge's own under
            its pair of vertices, in place of those for all; a DiGraph's tips under
            `"tip_config"`. None for none.
    """

    edges: dict[Edge[V], Mobject]
    """The edges' mobjects, by pair of vertices."""

    def __init__(
        self,
        vertices: Sequence[V],
        edges: Sequence[Edge[V]],
        labels: bool | Mapping[V, Mobject] = False,
        label_fill_color: ParsableManimColor = BLACK,
        layout: Layout[V] = "spring",
        layout_scale: float | tuple[float, float, float] = 2,
        layout_config: Mapping[str, object] | None = None,
        vertex_type: Maker = Dot,
        vertex_config: Configs | None = None,
        vertex_mobjects: Mapping[V, Mobject] | None = None,
        edge_type: Maker = Line,
        partitions: Sequence[Sequence[V]] | None = None,
        root_vertex: V | None = None,
        edge_config: Configs | None = None,
    ) -> None:
        super().__init__()
        if isinstance(labels, Mapping):
            labels_by_vertex: dict[V, Mobject] = dict(labels)
        else:
            labels_by_vertex = (
                {v: MathTex(str(v), color=label_fill_color) for v in vertices}
                if labels
                else {}
            )
        if labels_by_vertex and vertex_type is Dot:
            vertex_type = LabeledDot
        self.default_vertex_config, own = _split(vertex_config, vertices)
        vertex_configs: dict[V, Config] = {
            v: own.get(v, copy(self.default_vertex_config)) for v in vertices
        }
        for v, label in labels_by_vertex.items():
            vertex_configs[v]["label"] = label
        self.vertices: dict[V, Mobject] = {
            v: _make(vertex_type, vertex_configs[v]) for v in vertices
        }
        """The vertices' mobjects, by vertex."""
        self.vertices.update(vertex_mobjects or {})
        self._place_vertices(
            edges,
            layout=layout,
            layout_scale=layout_scale,
            layout_config=layout_config,
            partitions=partitions,
            root_vertex=root_vertex,
        )
        self.default_edge_config, own_edges = _split(edge_config, edges)
        self._edge_config: dict[Edge[V], Config] = {
            e: own_edges.get(e, copy(self.default_edge_config)) for e in edges
        }
        self._populate_edge_dict(edges, edge_type)
        self.add(*self.vertices.values())
        self.add(*self.edges.values())
        self.add_updater(self.update_edges)

    @staticmethod
    def _empty_networkx_graph() -> NxGraph:
        raise NotImplementedError("To be implemented in concrete subclasses")

    def _make_edge(self, edge_type: Maker, u: V, v: V, config_: Config) -> Mobject:
        raise NotImplementedError("To be implemented in concrete subclasses")

    def update_edges(self, graph: Mobject) -> Self:
        """Put each edge back on its vertices, where they are now: the updater a graph
        runs every frame, so that its edges follow its vertices.

        Each kind of graph sets its edges' ends its own way: an undirected graph's from
        center to center, a directed graph's from outline to outline, with its tip.
        Only edges that are lines ([Line][manimgx.Line] and its kinds) follow.

        Args:
            graph: The mobject the updater runs for (the graph); unused.
        """
        raise NotImplementedError("To be implemented in concrete subclasses")

    def _populate_edge_dict(self, edges: Iterable[Edge[V]], edge_type: Maker) -> None:
        self.edges = {
            (u, v): self._make_edge(edge_type, u, v, self._edge_config[u, v])
            for u, v in edges
        }

    def __getitem__(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE: a graph is indexed by vertex and edge, not position
        self, k: V | Edge[V]
    ) -> Mobject:
        if k in self.vertices:
            return self.vertices[cast("V", k)]
        if k in self.edges:
            return self.edges[cast("Edge[V]", k)]
        raise ValueError(f"Could not find {k} in vertices or edges")

    def _create_vertex(
        self,
        vertex: V,
        position: Point3DLike | None = None,
        label: bool | Mobject = False,
        label_fill_color: ParsableManimColor = BLACK,
        vertex_type: Maker = Dot,
        vertex_config: Config | None = None,
        vertex_mobject: Mobject | None = None,
    ) -> tuple[V, Point3D, Mobject]:
        np_position: Point3D = (
            self.get_center() if position is None else np.asarray(position, dtype=float)
        )
        if vertex in self.vertices:
            raise ValueError(
                f"Vertex identifier '{vertex}' is already used for a vertex in this"
                " graph."
            )
        if label is True:
            label_mob: Mobject | None = MathTex(str(vertex), color=label_fill_color)
        else:
            label_mob = label if isinstance(label, Mobject) else None
        config_ = copy(self.default_vertex_config) | (vertex_config or {})
        if label_mob is not None:
            config_["label"] = label_mob
            if vertex_type is Dot:
                vertex_type = LabeledDot
        mob = (
            vertex_mobject
            if vertex_mobject is not None
            else _make(vertex_type, config_)
        )
        mob.move_to(np_position)
        return vertex, np_position, mob

    def _add_created_vertex(
        self,
        vertex: V,
        position: Point3DLike,
        vertex_mobject: Mobject,
    ) -> Mobject:
        if vertex in self.vertices:
            raise ValueError(
                f"Vertex identifier '{vertex}' is already used for a vertex in this"
                " graph."
            )
        self.vertices[vertex] = vertex_mobject
        vertex_mobject.move_to(position)
        self.add(vertex_mobject)
        return vertex_mobject

    def _create_vertices(
        self,
        *vertices: V,
        positions: Mapping[V, Point3DLike] | None = None,
        labels: bool | Mapping[V, bool | Mobject] = False,
        label_fill_color: ParsableManimColor = BLACK,
        vertex_type: Maker = Dot,
        vertex_config: Configs | None = None,
        vertex_mobjects: Mapping[V, Mobject] | None = None,
    ) -> list[tuple[V, Point3D, Mobject]]:
        graph_center = self.get_center()
        places = {v: (positions or {}).get(v, graph_center) for v in vertices}
        marks = {
            v: labels if isinstance(labels, bool) else labels.get(v, False)
            for v in vertices
        }
        shared, own = _split(vertex_config, vertices)
        base = copy(self.default_vertex_config) | shared
        return [
            self._create_vertex(
                v,
                position=places[v],
                label=marks[v],
                label_fill_color=label_fill_color,
                vertex_type=vertex_type,
                vertex_config=own.get(v, copy(base)),
                vertex_mobject=(vertex_mobjects or {}).get(v),
            )
            for v in vertices
        ]

    def add_vertices(self, *vertices: V, **kwargs: Unpack[VertexOptions[V]]) -> Group:
        """Add vertices to the graph, without edges.

        Each is made as the graph makes its vertices, with the keywords given over the
        graph's own, and placed at its position, or at the graph's center. A vertex
        already in the graph raises a ValueError.

        Args:
            *vertices: The new vertices: hashable values, each a vertex's name.
            **kwargs: [Vertex keywords][manimgx.mobjects.graph.VertexOptions]:
                `positions`, `labels`, `vertex_type`, `vertex_config`, ….

        Returns:
            A new group of the new vertices' mobjects.

        Examples:
            ```python
            import manimgx as m


            class GraphAddVerticesExample(m.Scene):
                def construct(self) -> None:
                    graph = m.Graph(
                        [1, 2, 3],
                        [(1, 2), (2, 3)],
                        layout={1: [-4, -1, 0], 2: [0, -2, 0], 3: [4, -1, 0]},
                        vertex_config={"radius": 0.15},
                    )
                    self.add(graph)
                    top = graph.add_vertices(
                        4, positions={4: [0, 2.5, 0]}, vertex_config={"color": m.YELLOW}
                    )
                    self.play(m.FadeIn(top, scale=3))
                    self.play(m.Create(graph.add_edges((1, 4), (3, 4))))
            ```
        """
        return Group(
            *(
                self._add_created_vertex(*v)
                for v in self._create_vertices(*vertices, **kwargs)
            )
        )

    def _remove_vertex(self, vertex: V) -> Group:
        if vertex not in self.vertices:
            raise ValueError(
                f"The graph does not contain a vertex with identifier '{vertex}'"
            )
        edge_tuples = [e for e in self.edges if vertex in e]
        for e in edge_tuples:
            self._edge_config.pop(e)
        to_remove = [self.edges.pop(e) for e in edge_tuples]
        to_remove.append(self.vertices.pop(vertex))
        self.remove(*to_remove)
        return Group(*to_remove)

    def remove_vertices(self, *vertices: V) -> Group:
        """Remove vertices from the graph, and the edges that touch them.

        A vertex not in the graph raises a ValueError.

        Args:
            *vertices: The vertices to remove.

        Returns:
            A new group of the removed mobjects (for each vertex, its edges, then the
            vertex), to fade out, for instance.

        Examples:
            ```python
            import manimgx as m


            class GraphRemoveVerticesExample(m.Scene):
                def construct(self) -> None:
                    graph = m.Graph(
                        [1, 2, 3, 4, 5],
                        [(1, 2), (2, 3), (3, 4), (4, 5), (5, 1), (1, 3)],
                        layout="circular",
                        layout_scale=3,
                    )
                    self.add(graph)
                    self.play(m.FadeOut(graph.remove_vertices(3)))
            ```
        """
        return Group(*(m for v in vertices for m in self._remove_vertex(v).submobjects))

    def _add_edge(
        self, edge: Edge[V], edge_type: Maker = Line, edge_config: Config | None = None
    ) -> Group:
        u, v = edge
        config_ = self.default_edge_config.copy() | (edge_config or {})
        self._edge_config[u, v] = config_
        edge_mobject = self._make_edge(edge_type, u, v, config_)
        self.edges[u, v] = edge_mobject
        self.add(edge_mobject)
        return Group(edge_mobject)

    def add_edges(
        self,
        *edges: Edge[V],
        edge_type: Maker = Line,
        edge_config: Configs | None = None,
        **kwargs: Unpack[VertexOptions[V]],
    ) -> Group:
        """Add edges to the graph, and the vertices they name that it lacks.

        The missing vertices are added first, as
        [add_vertices][manimgx.mobjects.graph.GenericGraph.add_vertices] adds them, with
        the vertex keywords given; each edge is then made as the graph makes its edges,
        with the edge keywords given over the graph's own.

        Args:
            *edges: The new edges, each a pair of vertices.
            edge_type: The class of the new edges.
            edge_config: Keywords for the new edges, over the graph's: for all of them,
                and an edge's own under its pair of vertices, in place of those for all;
                None for none.
            **kwargs: [Vertex keywords][manimgx.mobjects.graph.VertexOptions] for the
                vertices the edges name that the graph lacks.

        Returns:
            A new group of the new mobjects, the vertices added and then the edges.
        """
        shared, own = _split(edge_config, edges)
        base = self.default_edge_config.copy() | shared
        new_vertices = [
            v for v in dict.fromkeys(it.chain(*edges)) if v not in self.vertices
        ]
        added = list(self.add_vertices(*new_vertices, **kwargs))
        for edge in edges:
            added.extend(
                self._add_edge(
                    edge, edge_type=edge_type, edge_config=base | own.get(edge, {})
                )
            )
        return Group(*added)

    def _remove_edge(self, edge: Edge[V]) -> Mobject:
        if edge not in self.edges:
            raise ValueError(f"The graph does not contain a edge '{edge}'")
        edge_mobject = self.edges.pop(edge)
        self._edge_config.pop(edge, None)
        self.remove(edge_mobject)
        return edge_mobject

    def remove_edges(self, *edges: Edge[V]) -> Group:
        """Remove edges from the graph, keeping their vertices.

        An edge not in the graph raises a ValueError.

        Args:
            *edges: The edges to remove, each a pair of vertices.

        Returns:
            A new group of the removed edges' mobjects.
        """
        return Group(*(self._remove_edge(edge) for edge in edges))

    @classmethod
    def from_networkx(cls, nxgraph: NxGraph, **kwargs: Unpack[GraphOptions[V]]) -> Self:
        """Make a graph of a [NetworkX](https://networkx.org) graph's nodes and edges.

        Args:
            nxgraph: The NetworkX graph (a `Graph`, or a `DiGraph`).
            **kwargs: [Graph keywords][manimgx.Graph]: `layout`,
                `labels`, `vertex_config`, ….

        Returns:
            A new graph.

        Examples:
            ```python
            import networkx as nx

            import manimgx as m


            class GraphFromNetworkxExample(m.Scene):
                def construct(self) -> None:
                    petersen = nx.petersen_graph()
                    graph = m.Graph.from_networkx(
                        petersen,
                        layout="shell",
                        layout_scale=3,
                        layout_config={"nlist": [range(5, 10), range(5)]},
                    )
                    self.play(m.Create(graph), run_time=2)
            ```
        """
        return cls(list(nxgraph.nodes), list(nxgraph.edges), **kwargs)

    def change_layout(
        self,
        layout: Layout[V] = "spring",
        layout_scale: float | tuple[float, float, float] = 2,
        layout_config: Mapping[str, object] | None = None,
        partitions: Sequence[Sequence[V]] | None = None,
        root_vertex: V | None = None,
    ) -> Self:
        """Lay the graph out anew: move each vertex to its place in a layout.

        The vertices move at once, and the edges follow them at the next frame, as the
        graph's updater moves them. To animate the change, animate each vertex to its
        place in a changed copy (as below): the edges follow all the way.

        A layout function gets a fresh NetworkX graph of the current vertices and edges.
        Its node, edge and graph attributes belong to that call, not to later layouts.

        Args:
            layout: Where the vertices go: a layout's name, their positions, or a
                layout function (see
                [GenericGraph][manimgx.mobjects.graph.GenericGraph]).
            layout_scale: How far the layout reaches from the center, in scene units.
            layout_config: Keywords for the layout function; None for none.
            partitions: For the `"partite"` layout: the vertices of each column; None
                for none.
            root_vertex: For the `"tree"` layout: the vertex at its top; None for none.

        Examples:
            ```python
            import manimgx as m


            class GraphChangeLayoutExample(m.Scene):
                def construct(self) -> None:
                    graph = m.Graph(
                        [1, 2, 3, 4, 5, 6],
                        [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 1), (1, 4)],
                        layout={v: [2 * v - 7, 0, 0] for v in range(1, 7)},
                    )
                    circle = graph.copy().change_layout("circular", layout_scale=3)
                    self.add(graph)
                    self.play(
                        *(graph[v].animate.move_to(circle[v]) for v in graph.vertices)
                    )
            ```
        """
        return self._place_vertices(
            self.edges,
            layout=layout,
            layout_scale=layout_scale,
            layout_config=layout_config,
            partitions=partitions,
            root_vertex=root_vertex,
        )

    def _place_vertices(
        self,
        edges: Iterable[Edge[V]],
        layout: Layout[V] = "spring",
        layout_scale: float | tuple[float, float, float] = 2,
        layout_config: Mapping[str, object] | None = None,
        partitions: Sequence[Sequence[V]] | None = None,
        root_vertex: V | None = None,
    ) -> Self:
        """Place vertices from the edge keys: supplied before edges are made, otherwise
        the keys of the graph's edges. A computed layout owns its temporary topology."""
        config_ = dict(layout_config or {})
        if partitions is not None:
            config_.setdefault("partitions", partitions)
        if root_vertex is not None:
            config_.setdefault("root_vertex", root_vertex)
        positions: Positions[V]
        if _is_function(layout):
            place = layout
        elif _is_name(layout):
            place = _layout(layout)
        elif isinstance(layout, str):
            raise ValueError(
                f"The layout '{layout}' is neither a recognized layout, a layout"
                " function, nor a vertex placement dictionary."
            )
        else:
            place = None
            positions = layout
        if place is not None:
            graph = self._empty_networkx_graph()
            graph.add_nodes_from(self.vertices)
            graph.add_edges_from(edges)
            positions = place(graph, scale=layout_scale, **config_)
        points = {v: np.asarray(positions[v], dtype=float) for v in self.vertices}
        padded = {v: np.pad(p, (0, 3 - p.size)) for v, p in points.items()}
        for v in self.vertices:
            self[v].move_to(padded[v])
        return self

    def _edge_ends(self, edge: Edge[V]) -> tuple[float, float]:
        """An edge's buffer and bend, as its config sets them (CE read them from the wrong
        dictionary, so edges lost both at the first update)."""
        config_ = self._edge_config.get(edge, {})
        buff, path_arc = config_.get("buff", 0), config_.get("path_arc", 0)
        return (buff if isinstance(buff, (int, float)) else 0), (
            path_arc if isinstance(path_arc, (int, float)) else 0
        )


class Graph[V: Hashable = Hashable](GenericGraph[V]):
    """An undirected graph: vertices joined by edges, laid out automatically or by hand;
    white dots and lines unless styled.

    Each edge runs from the center of one vertex to the center of the other, behind
    them, and follows them as they move. It takes the arguments of a
    [GenericGraph][manimgx.mobjects.graph.GenericGraph], which lists what a graph can do.

    Examples:
        ```python
        import manimgx as m


        class GraphExample(m.Scene):
            def construct(self) -> None:
                vertices = [1, 2, 3, 4, 5, 6]
                edges = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 1), (1, 4), (2, 5)]
                graph = m.Graph(
                    vertices,
                    edges,
                    layout="circular",
                    layout_scale=3,
                    labels=True,
                    vertex_config={1: {"fill_color": m.RED}},
                    edge_config={(1, 4): {"stroke_color": m.YELLOW}},
                )
                self.play(m.Create(graph))
                self.play(graph[3].animate.move_to([0, 0, 0]))
        ```
    """

    @staticmethod
    def _empty_networkx_graph() -> NxGraph:
        import networkx as nx

        return nx.Graph()

    def _make_edge(self, edge_type: Maker, u: V, v: V, config_: Config) -> Mobject:
        style = {k: v for k, v in config_.items() if k != "tip_config"}
        return edge_type(
            start=self[u].get_center(), end=self[v].get_center(), z_index=-1, **style
        )

    def update_edges(self, graph: Mobject) -> Self:
        for (u, v), edge in self.edges.items():
            if isinstance(edge, Line):
                buff, path_arc = self._edge_ends((u, v))
                edge.set_points_by_ends(
                    self[u].get_center(),
                    self[v].get_center(),
                    buff=buff,
                    path_arc=path_arc,
                )
        return self


class DiGraph[V: Hashable = Hashable](GenericGraph[V]):
    """A directed graph: vertices joined by arrows, from the first vertex of each edge
    to the second; white dots and arrows unless styled.

    Each edge runs from the outline of one vertex to the outline of the other and ends
    in a tip, which the `"tip_config"` of `edge_config` shapes (see
    [TipConfig][manimgx.mobjects.graph.TipConfig]), for every edge or an edge's own; it
    follows its vertices as they move. It takes the arguments of a
    [GenericGraph][manimgx.mobjects.graph.GenericGraph], which lists what a graph can do.

    Examples:
        ```python
        import manimgx as m


        class DiGraphExample(m.Scene):
            def construct(self) -> None:
                edge_config = {
                    "stroke_width": 3,
                    "tip_config": {"tip_length": 0.2, "tip_width": 0.2},
                    (3, 4): {
                        "color": m.RED,
                        "tip_config": {"tip_shape": m.ArrowSquareTip},
                    },
                }
                graph = m.DiGraph(
                    [0, 1, 2, 3, 4],
                    [(0, 1), (1, 2), (3, 2), (3, 4), (4, 0)],
                    labels=True,
                    layout="circular",
                    layout_scale=3,
                    edge_config=edge_config,
                )
                self.play(m.Create(graph))
        ```
    """

    @staticmethod
    def _empty_networkx_graph() -> NxGraph:
        import networkx as nx

        return nx.DiGraph()

    def _make_edge(self, edge_type: Maker, u: V, v: V, config_: Config) -> Mobject:
        style = config_.copy()
        tips = cast(
            "TipConfig",
            style.pop("tip_config", self.default_edge_config.get("tip_config", {})),
        )
        edge = edge_type(start=self[u], end=self[v], z_index=-1, **style)
        if isinstance(edge, Line):
            edge.add_tip(**tips)
        return edge

    def update_edges(self, graph: Mobject) -> Self:
        for (u, v), edge in self.edges.items():
            if isinstance(edge, Line):
                tip = edge.pop_tips()[0]
                buff, path_arc = self._edge_ends((u, v))
                edge.set_points_by_ends(self[u], self[v], buff=buff, path_arc=path_arc)
                edge.add_tip(tip)
        return self

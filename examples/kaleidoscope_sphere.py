"""A kaleidoscope on the sphere: three mirrors make 120 tiles, and one point makes the solids.

Three mirrors (great circles) meet at the corners of a spherical triangle with angles 36°, 60°
and 90°: the Schwarz triangle (2, 3, 5). Reflect it in its mirrors, and the images in theirs,
breadth first: a tile turns over like a card at each reflection, so after an even number it shows
the triangle's own handedness (gold) and after an odd number its mirror image (blue). The waves
cover the sphere with exactly 120 tiles, the last one fifteen reflections away, opposite the
first. The count is forced by the angles: a spherical triangle's area is its angle excess
(Girard, 1629), 36° + 60° + 90° − 180° = π/30, and 120 × π/30 = 4π. Put a point in the triangle
and reflect it too: its images are the corners of a solid (Wythoff's construction) — at the
triangle's corners the icosahedron, icosidodecahedron and dodecahedron, on its sides the
truncated ones, inside it the truncated icosidodecahedron, one corner per tile.
"""

from collections.abc import Callable
from fractions import Fraction

import numpy as np

import manimgx as m

PHI = (1 + 5**0.5) / 2
RADIUS = 2.55
GRID = 8  # each tile is three GRID × GRID patches
WAVE = 0.68  # seconds per wave of reflections
GOLD, BLUE, SEA, SILVER, PIN = "#e8ae45", "#2b5ea7", "#0b1320", "#eef2f8", "#ff5d73"
CAMERA_PHI, CAMERA_THETA = 70 * m.DEGREES, -60 * m.DEGREES

Mesh = tuple[np.ndarray, np.ndarray]  # vertices, triangles


def unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def sight(phi: float, theta: float) -> np.ndarray:
    """The unit vector toward a camera at polar angle phi and azimuth theta."""
    return np.array(
        [np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)]
    )


def rotation_taking(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """The rotation about a × b taking the unit vector a to the unit vector b (Rodrigues)."""
    axis = np.cross(a, b)
    k = axis / np.linalg.norm(axis)
    cross = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.linalg.norm(axis) * cross + (1 - a @ b) * cross @ cross


def slerp(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    angle = np.arccos(np.clip(a @ b, -1, 1))
    return (np.sin((1 - t) * angle) * a + np.sin(t * angle) * b) / np.sin(angle)


def smooth01(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def rgba(color: str) -> np.ndarray:
    return np.array(m.ManimColor(color).to_rgba())


def globe(nu: int, nv: int) -> np.ndarray:
    """An (nu + 1) × (nv + 1) grid of points on the unit sphere (longitude × colatitude)."""
    u, v = np.meshgrid(
        np.linspace(0, m.TAU, nu + 1), np.linspace(0, m.PI, nv + 1), indexing="ij"
    )
    grid = np.stack([np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), np.cos(v)], -1)
    return grid.reshape(-1, 3)


def grid_triangles(nu: int, nv: int) -> np.ndarray:
    """Triangles of an (nu + 1) × (nv + 1) grid of vertices, two per cell."""
    i, j = np.meshgrid(np.arange(nu), np.arange(nv), indexing="ij")
    a = i * (nv + 1) + j
    b, c, d = a + nv + 1, a + nv + 2, a + 1
    return np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], -2).reshape(
        -1, 3
    )


# ── the kaleidoscope ─────────────────────────────────────────────────────────────────────────

# The fundamental triangle: a vertex of an icosahedron (ten tiles will meet there), the center of
# a face next to it (six) and the middle of an edge between them (four), turned to the camera.
_ICO = unit(np.array([[0, 1, PHI], [PHI, 0, 2 * PHI + 1], [0, 0, 1.0]]))
_FACING = sight(CAMERA_PHI - 0.15, CAMERA_THETA + 0.45)
CORNERS = _ICO @ rotation_taking(unit(_ICO.sum(axis=0)), _FACING).T


def mirror(k: int) -> np.ndarray:
    """The mirror opposite corner k: its unit normal, pointing into the triangle."""
    n = unit(np.cross(CORNERS[(k + 1) % 3], CORNERS[(k + 2) % 3]))
    return n if n @ CORNERS[k] > 0 else -n


MIRRORS = np.array([mirror(k) for k in range(3)])


def corner_angle(k: int) -> float:
    """The triangle's angle at corner k, in degrees, between the great arcs leaving it."""
    c = CORNERS[k]
    arms = [unit(CORNERS[j] - (CORNERS[j] @ c) * c) for j in range(3) if j != k]
    return float(np.degrees(np.arccos(arms[0] @ arms[1])))


def reflections() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Every product of the three reflections, found breadth first: the matrices, how many
    reflections each needs, and the one each is first reached from (and by which mirror).
    """
    flips = [np.eye(3) - 2 * np.outer(n, n) for n in MIRRORS]
    elements, length, parent, via = [np.eye(3)], [0], [-1], [-1]
    frontier = [0]
    while frontier:
        grown = []
        for a in frontier:
            for i in range(3):
                g = elements[a] @ flips[i]
                if np.abs(np.array(elements) - g).max(axis=(1, 2)).min() > 1e-9:
                    elements.append(g)
                    length.append(length[a] + 1)
                    parent.append(a)
                    via.append(i)
                    grown.append(len(elements) - 1)
        frontier = grown
    return np.array(elements), np.array(length), np.array(parent), np.array(via)


ELEMENTS, LENGTH, PARENT, VIA = reflections()
TILES = len(ELEMENTS)
PER_PATCH = (GRID + 1) ** 2
PER_TILE = 3 * PER_PATCH
TRIANGLES = (
    grid_triangles(GRID, GRID)[None] + PER_PATCH * np.arange(3 * TILES)[:, None, None]
)


def pieces(p: np.ndarray) -> np.ndarray:
    """The triangle cut in three by the perpendiculars from a point p to the mirrors: piece k is
    the quad (corner k, foot on one mirror through it, p, foot on the other)."""
    quads = []
    for k in range(3):
        a, b = MIRRORS[(k + 1) % 3], MIRRORS[(k + 2) % 3]
        quads.append([CORNERS[k], unit(p - (b @ p) * b), p, unit(p - (a @ p) * a)])
    return np.array(quads)


def patches(quads: np.ndarray) -> np.ndarray:
    """(3, (GRID + 1)², 3) points on the unit sphere: each quad as a bilinear grid, pushed out."""
    s = np.linspace(0, 1, GRID + 1)
    u, v = (x.ravel()[None, :, None] for x in np.meshgrid(s, s, indexing="ij"))
    a, b, c, d = (quads[:, i, None, :] for i in range(4))
    return unit((1 - u) * (1 - v) * a + u * (1 - v) * b + u * v * c + (1 - u) * v * d)


def fold(points: np.ndarray, normals: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Turn tiles (g, v, 3) over their mirrors (normals (g, 3), on the tiles' side) like cards
    over an edge: at t = 1 each is its own mirror image."""
    d = np.einsum("gvi,gi->gv", points, normals)[..., None]
    foot = points - d * normals[:, None, :]
    angle = np.pi * t[:, None, None]
    return foot + d * (np.cos(angle) * normals[:, None, :] + np.sin(angle) * unit(foot))


# ── where the point sits: at the corners, on two sides where all edges are equal, in the middle


def balance(a: np.ndarray, b: np.ndarray, i: int, j: int) -> float:
    """Where on the arc a → b the point is equally far from mirrors i and j (bisection)."""

    def gap(t: float) -> float:
        return float((MIRRORS[i] - MIRRORS[j]) @ slerp(a, b, t))

    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap(lo) * gap(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


# the middle: equally far from all three mirrors
INCENTER = unit(np.linalg.solve(MIRRORS, np.ones(3)))
STOPS = [CORNERS[0], CORNERS[2], CORNERS[1], INCENTER]
SOLIDS = [
    (0.0, "icosahedron"),
    (balance(CORNERS[0], CORNERS[2], 2, 0), "truncated icosahedron"),
    (1.0, "icosidodecahedron"),
    (1 + balance(CORNERS[2], CORNERS[1], 1, 2), "truncated dodecahedron"),
    (2.0, "dodecahedron"),
    (3.0, "truncated icosidodecahedron"),
]


def wythoff(s: float) -> np.ndarray:
    """The point, s of the way along the stops (corner 36° → 90° → 60° → the middle)."""
    k = min(int(s), len(STOPS) - 2)
    return slerp(STOPS[k], STOPS[k + 1], s - k)


# ── what is drawn ────────────────────────────────────────────────────────────────────────────


def mirror_circles(samples: int = 240) -> tuple[np.ndarray, np.ndarray]:
    """The 15 mirrors: great circles starting where a reflection first crosses each (the
    triangle's own three first), and the wave of that first crossing."""
    circles, first, seen = [], [], []
    for g in range(1, TILES):  # breadth first: first crossings come first
        normal = ELEMENTS[PARENT[g]] @ MIRRORS[VIA[g]]
        if any(abs(normal @ n) > 1 - 1e-9 for n in seen):
            continue
        seen.append(normal)
        edge = ELEMENTS[PARENT[g]] @ np.delete(CORNERS, VIA[g], axis=0).T
        start = unit(edge.sum(axis=1))  # the middle of the edge the tile turns over
        s = np.linspace(0, m.TAU, samples, endpoint=False)[:, None]
        circles.append(np.cos(s) * start + np.sin(s) * np.cross(normal, start))
        first.append(LENGTH[g])
    return np.array(circles), np.array(first)


def tube_rings(curves: np.ndarray, sides: int = 8) -> Mesh:
    """Unit rings (k, n, sides, 3) around closed curves (k, n, 3) on a sphere, and the
    triangles (k, n, 2·sides, 3) of tubes through them."""
    k, n, _ = curves.shape
    tangent = unit(np.roll(curves, -1, 1) - np.roll(curves, 1, 1))
    side = np.cross(tangent, unit(curves))
    a = np.linspace(0, m.TAU, sides, endpoint=False)[:, None]
    rings = np.cos(a) * side[:, :, None] + np.sin(a) * unit(curves)[:, :, None]
    f, i, j = np.ogrid[:k, :n, :sides]
    p, q = (f * n + i) * sides + j, (f * n + (i + 1) % n) * sides + j
    s = (f * n + (i + 1) % n) * sides + (j + 1) % sides
    t = (f * n + i) * sides + (j + 1) % sides
    tris = np.stack([np.stack([p, q, s], -1), np.stack([p, s, t], -1)], 3)
    return rings, tris.reshape(k, n, 2 * sides, 3)


class Kaleidoscope:
    """Everything drawn on and in the sphere, from a handful of trackers."""

    def __init__(self) -> None:
        self.shown = m.ValueTracker(0.3)  # the first tile grows in
        self.drawn = m.ValueTracker(0.0)  # its three mirrors are drawn round the sphere
        # tiles k reflections away turn over during wave k (0 < wave − (k − 1) < 1)
        self.wave = m.ValueTracker(0.0)
        self.flat = m.ValueTracker(
            0.0
        )  # 0: tiles on the sphere; 1: pieces flat, a solid
        self.path = m.ValueTracker(0.0)  # where the point sits (see `wythoff`)
        self.pins = m.ValueTracker(0.0)  # size of the point's images
        self.cage = m.ValueTracker(1.0)  # thickness of the mirrors (0: gone)
        self.frame = m.ValueTracker(0.0)  # thickness of the solid's edges
        self.circles, self.first = mirror_circles()
        self.rings, self.tube_tris = tube_rings(self.circles)
        self.ball = globe(10, 6), grid_triangles(10, 6)
        # gold: the triangle's own handedness (even reflections); blue: mirrored (odd)
        self.hand = np.where((LENGTH % 2 == 0)[:, None], rgba(GOLD), rgba(BLUE))
        # the mirror each tile turns over as it lands (tile 0 lies there from the start)
        self.normals = np.array(
            [ELEMENTS[PARENT[g]] @ MIRRORS[VIA[g]] for g in range(TILES)]
        )

    def point(self) -> np.ndarray:
        return wythoff(self.path.get_value())

    def tiles(self) -> tuple[np.ndarray, np.ndarray]:
        """Points and colors of all tiles: landed, turning over, or hidden inside the sphere."""
        p = self.point()
        base = patches(pieces(p))
        flat = self.flat.get_value()
        if (
            flat > 0
        ):  # each piece slides along its rays onto the plane through p square to
            # its corner: together, the flat faces of the solid
            scale = (CORNERS @ p)[:, None] / np.einsum("kvi,ki->kv", base, CORNERS)
            base = base * (1 + flat * (scale - 1))[..., None]
        landed = np.einsum("gij,kvj->gkvi", ELEMENTS, base).reshape(TILES, PER_TILE, 3)
        if self.shown.get_value() < 1:  # the first tile grows from its middle
            centre = unit(CORNERS.sum(axis=0))
            landed[0] = unit(centre + self.shown.get_value() * (landed[0] - centre))
        progress = np.clip(self.wave.get_value() - (LENGTH - 1), 0, 1)
        points = np.where((progress > 0)[:, None, None], landed, 0.5 * landed)
        colors = self.hand.copy()
        turning = np.nonzero((progress > 0) & (progress < 1))[0]
        if len(turning):
            t = smooth01(progress[turning])
            before = landed[PARENT[turning]]
            points[turning] = fold(before, self.normals[turning], t)
            mix = smooth01((t - 0.35) / 0.3)[:, None]
            colors[turning] = self.hand[PARENT[turning]] * (1 - mix)
            colors[turning] += self.hand[turning] * mix
        return RADIUS * points.reshape(-1, 3), np.repeat(colors, PER_TILE, axis=0)

    def mirrors(self) -> Mesh:
        """The mirrors drawn so far: each grows both ways round from where it is first crossed."""
        reach = np.clip((self.wave.get_value() - (self.first - 1)) / 1.5, 0, 1)
        reach[:3] = self.drawn.get_value()
        n = self.circles.shape[1]
        away = np.minimum(np.arange(n), n - 1 - np.arange(n)) / (n / 2)
        thick = 0.013 * self.cage.get_value()
        verts = 1.004 * RADIUS * self.circles[:, :, None] + thick * self.rings
        return verts.reshape(-1, 3), self.tube_tris[away < reach[:, None]].reshape(
            -1, 3
        )

    def edges(self) -> Mesh:
        """The solid's edges, as thin tubes: from each image of the point straight to the
        mirrors beside it (half the edge to its reflection there)."""
        p = self.point()
        feet = p - (MIRRORS @ p)[:, None] * MIRRORS
        starts = np.repeat(ELEMENTS @ p, 3, axis=0)
        ends = np.einsum("gij,kj->gki", ELEMENTS, feet).reshape(-1, 3)
        side = np.cross(ends - starts, starts)
        side /= np.maximum(np.linalg.norm(side, axis=1, keepdims=True), 1e-12)
        other = np.cross(unit(starts), side)
        a = np.linspace(0, m.TAU, 6, endpoint=False)[None, :, None]
        ring = np.cos(a) * side[:, None] + np.sin(a) * other[:, None]
        ring *= 0.012 * self.frame.get_value()
        verts = RADIUS * np.stack([starts[:, None] + ring, ends[:, None] + ring], 1)
        e, j = np.ogrid[: len(starts), :6]
        lo, hi = e * 12 + j, e * 12 + 6 + j
        lo2, hi2 = e * 12 + (j + 1) % 6, e * 12 + 6 + (j + 1) % 6
        tris = np.stack([np.stack([lo, hi, hi2], -1), np.stack([lo, hi2, lo2], -1)], 2)
        return verts.reshape(-1, 3), tris.reshape(-1, 3)

    def images(self) -> Mesh:
        """Small balls at the point's images: the corners of the solid."""
        verts, tris = self.ball
        centres = RADIUS * ELEMENTS @ self.point()
        size = 0.055 * self.pins.get_value() + 1e-4
        balls = (size * verts[None] + centres[:, None]).reshape(-1, 3)
        return balls, (tris[None] + len(verts) * np.arange(TILES)[:, None, None])

    def corners(self) -> int:
        """How many distinct images the point has: 120 over how many reflections fix it."""
        p = self.point()
        return TILES // int((np.linalg.norm(ELEMENTS @ p - p, axis=1) < 1e-6).sum())


def follow(mob: m.MeshMobject, shape: Callable[[], Mesh]) -> m.MeshMobject:
    """Give the mesh its shape every frame (points with triangles: triangles alone are not
    redrawn)."""

    def update(mob: m.MeshMobject) -> None:
        verts, tris = shape()
        mob.points, mob.triangles = verts, tris.reshape(-1, 3)

    update(mob)
    mob.add_updater(update)
    return mob


def blank(color: str) -> m.MeshMobject:
    return m.MeshMobject(
        np.zeros((3, 3)), np.array([[0, 1, 2]]), shade_in_3d=True, fill_color=color
    )


def spin_rate(t: float) -> float:
    """The camera's turning speed (rad/s): quicker while the waves run round the sphere."""
    rise = smooth01(np.array((t - 0.8) / 2.0))
    fall = smooth01(np.array((t - 10.4) / 3.0))
    return float(0.07 + 0.15 * rise * (1 - fall))


# ── heads-up display ─────────────────────────────────────────────────────────────────────────


def wave_chart(k: Kaleidoscope) -> tuple[m.Mobject, m.VGroup]:
    """Bars: how many tiles are first reached after 0, 1, …, 15 reflections (gold even, blue
    odd), growing with the waves; and its labels, with the running count of tiles."""
    counts = np.bincount(LENGTH)
    pitch, base = 0.21, np.array([-6.7, -3.15, 0])

    def bars() -> m.VGroup:
        grown = np.clip(k.wave.get_value() - np.arange(len(counts)) + 1, 0, 1)
        grown[0] = k.shown.get_value()
        group = m.VGroup()
        for i, count in enumerate(counts):
            height = max(float(grown[i] * count * 0.12), 1e-3)
            bar = m.Rectangle(width=0.16, height=height, stroke_width=0, fill_opacity=1)
            bar.set_fill(GOLD if i % 2 == 0 else BLUE)
            group.add(bar.move_to(base + [i * pitch, height / 2, 0]))
        return group

    count = m.Integer(1, font_size=30)
    count.add_updater(
        lambda d: d.set_value(int((k.wave.get_value() + 1e-9 >= LENGTH).sum()))
    )
    tally = m.VGroup(m.Text("tiles:", font_size=24), count).arrange(m.RIGHT, buff=0.15)
    ticks = m.VGroup(
        *[
            m.Text(word, font_size=18).move_to(base + [x * pitch, -0.22, 0])
            for word, x in (("0", 0), ("reflections", 7.5), ("15", 15))
        ]
    ).set_color(m.GREY_B)
    tally.move_to(base + [0, 1.95, 0], aligned_edge=m.LEFT)
    return m.always_redraw(bars), m.VGroup(tally, ticks)


def wythoff_panel(
    k: Kaleidoscope, angles: list[float]
) -> tuple[m.VGroup, list[m.Text]]:
    """The triangle, flattened (gnomonic), with the point in it and the perpendiculars from it
    (the solid's edges within the tile); the count of corners; the solids' names."""
    centre = unit(CORNERS.sum(axis=0))
    across = unit(
        CORNERS[1] - CORNERS[0] - ((CORNERS[1] - CORNERS[0]) @ centre) * centre
    )
    up = np.cross(centre, across)
    spot = np.array([5.1, 0.3, 0])

    def flat(x: np.ndarray) -> np.ndarray:
        g = x / (x @ centre)
        return np.array([g @ across, g @ up, 0.0])

    middle = sum(flat(c) for c in CORNERS) / 3
    zoom = 2.3 / (flat(CORNERS[1])[0] - flat(CORNERS[0])[0])

    def place(x: np.ndarray) -> np.ndarray:
        return spot + zoom * (flat(x) - middle)

    def perpendiculars() -> m.VGroup:
        q = k.point()
        feet = unit(q - (MIRRORS @ q)[:, None] * MIRRORS)
        lines = [
            m.Line(place(q), place(f), stroke_color=SILVER, stroke_width=2.5)
            for f in feet
        ]
        return m.VGroup(*lines)

    triangle = m.Polygon(
        *[place(c) for c in CORNERS], stroke_color=SILVER, stroke_width=2
    )
    triangle.set_fill(GOLD, opacity=1)
    labels = m.VGroup(
        *[
            m.Text(f"{angles[i]:.0f}°", font_size=20).move_to(
                place(CORNERS[i]) + 0.32 * unit(place(CORNERS[i]) - spot)
            )
            for i in range(3)
        ]
    )
    dot = m.Dot(place(k.point()), radius=0.07, color=PIN)
    dot.add_updater(lambda d: d.move_to(place(k.point())))
    count = m.Integer(12, font_size=26)
    count.add_updater(lambda d: d.set_value(k.corners()))
    row = m.VGroup(m.Text("corners:", font_size=22), count).arrange(m.RIGHT, buff=0.12)
    row.move_to(spot + [-0.75, -1.72, 0], aligned_edge=m.LEFT)
    names = [
        m.Text(name, font_size=22).move_to(spot + [0, -1.3, 0]) for _, name in SOLIDS
    ]
    panel = m.VGroup(triangle, labels, m.always_redraw(perpendiculars), dot, row)
    return panel, names


# ── the scene ────────────────────────────────────────────────────────────────────────────────


class KaleidoscopeSphere(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=CAMERA_PHI, theta=CAMERA_THETA, zoom=1.0)
        clock = [0.0]

        def turn(tracker: m.ValueTracker, dt: float) -> None:
            clock[0] += dt
            tracker.increment_value(spin_rate(clock[0]) * dt)

        def keep_light(mob: m.Mobject) -> None:
            """The light turns with the camera: up and to its left, 80° off the view."""
            theta = self.camera.get_theta()
            toward = sight(self.camera.get_phi(), theta)
            right = np.array([-np.sin(theta), np.cos(theta), 0.0])
            aside = np.cos(0.6) * np.cross(toward, right) - np.sin(0.6) * right
            mob.move_to(15 * (np.cos(1.4) * toward + np.sin(1.4) * aside))

        self.camera.theta_tracker.add_updater(turn)
        self.camera.light_source.add_updater(keep_light)
        self.add(self.camera.theta_tracker, self.camera.light_source)

        k = Kaleidoscope()
        # the dark sphere under the tiles sinks inside the solid as they lie flat
        ground = globe(96, 48)
        sea = m.MeshMobject(
            ground, grid_triangles(96, 48), shade_in_3d=True, fill_color=SEA
        )

        def sink(mob: m.MeshMobject) -> None:
            mob.points = RADIUS * (0.985 - 0.2 * k.flat.get_value()) * ground

        sea.add_updater(sink)
        tiles = m.MeshMobject(
            np.zeros((TILES * PER_TILE, 3)), TRIANGLES, shade_in_3d=True
        )

        def paint_tiles(mob: m.MeshMobject) -> None:
            mob.points, rows = k.tiles()
            mob.paint = mob.paint.but(fill=rows)

        tiles.add_updater(paint_tiles)
        glass, edges = follow(blank(SILVER), k.mirrors), follow(blank(SILVER), k.edges)
        pins = follow(blank(SILVER), k.images)
        # the point itself in red; its images in white
        pin_rows = np.repeat(rgba(SILVER)[None], TILES * len(k.ball[0]), axis=0)
        pin_rows[: len(k.ball[0])] = rgba(PIN)

        def paint_pins(mob: m.MeshMobject) -> None:
            mob.paint = mob.paint.but(fill=pin_rows)

        pins.add_updater(paint_pins)

        # heads-up display: every number measured from the geometry drawn
        angles = [corner_angle(i) for i in range(3)]
        title = m.Text("A kaleidoscope on the sphere", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "three mirrors at " + ", ".join(f"{a:.0f}°" for a in angles), font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.15
        )
        chart, chart_labels = wave_chart(k)
        excess = Fraction(float(np.radians(sum(angles)) / np.pi - 1)).limit_denominator(
            99
        )
        share = rf"\frac{{\pi}}{{{excess.denominator}}}"
        degrees = " + ".join(f"{a:.0f}^\\circ" for a in angles)
        area = m.VGroup(
            m.Text("a tile's area is its angle excess", font_size=22).set_color(
                m.GREY_B
            ),
            m.MathTex(rf"{degrees} - 180^\circ = {share}", font_size=32),
        ).arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.15)
        whole = m.VGroup(
            m.MathTex(rf"{TILES} \times {share} = {TILES * excess}\pi", font_size=32),
            m.Text("the whole sphere", font_size=22).set_color(m.GREY_B),
        ).arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.15)
        m.VGroup(area, whole).arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.35)
        m.VGroup(area, whole).to_corner(m.UR)
        panel, names = wythoff_panel(k, angles)
        closing = m.Text(
            "Every corner is one point, seen in another mirror.", font_size=24
        )
        closing.to_edge(m.DOWN, buff=0.3).shift(0.9 * m.RIGHT)

        hud = [subtitle, chart_labels, area, whole, panel, *names, closing]
        self.add_fixed_in_frame_mobjects(title, chart, *hud)
        self.remove(*hud)
        self.add(sea, tiles, glass, edges, pins)

        def squish(a: float, b: float) -> Callable[[float], float]:
            return m.squish_rate_func(m.smooth, a, b)

        # 0–1.6 s: the first tile, and its three mirrors drawn round the sphere
        self.play(
            k.shown.animate.set_value(1.0),
            k.drawn.animate(rate_func=squish(0.25, 1.0)).set_value(1.0),
            m.FadeIn(subtitle),
            m.FadeIn(chart_labels),
            run_time=1.6,
        )
        # 1.6–11.8 s: fifteen waves of reflections, each tile turned over from one landed before
        self.play(
            k.wave.animate.set_value(15.0), run_time=15 * WAVE, rate_func=m.linear
        )
        # 11.8–14.6 s: why 120
        self.play(m.FadeIn(area, shift=0.2 * m.DOWN), run_time=0.7)
        self.wait(0.6)
        self.play(m.FadeIn(whole, shift=0.2 * m.DOWN), run_time=0.7)
        self.wait(0.8)
        # 14.6–17.1 s: a point in the triangle; the tiles lie flat into the icosahedron
        self.play(
            k.flat.animate.set_value(1.0),
            k.pins.animate.set_value(1.0),
            k.cage.animate(rate_func=squish(0.0, 0.6)).set_value(0.0),
            k.frame.animate(rate_func=squish(0.6, 1.0)).set_value(1.0),
            self.camera.zoom_tracker.animate.set_value(1.08),
            m.FadeIn(panel),
            m.FadeIn(names[0]),
            run_time=2.0,
        )
        self.wait(0.5)
        # 17.1–26.35 s: the point slides along the triangle's sides, then into it
        for i in range(1, len(SOLIDS)):
            self.play(
                k.path.animate.set_value(SOLIDS[i][0]),
                m.FadeOut(names[i - 1], rate_func=squish(0.0, 0.3)),
                m.FadeIn(names[i], rate_func=squish(0.75, 1.0)),
                run_time=1.4,
            )
            self.wait(0.45)
        self.play(m.FadeIn(closing, shift=0.2 * m.UP), run_time=0.8)
        self.wait(2.85)


if __name__ == "__main__":
    KaleidoscopeSphere().render("kaleidoscope_sphere.mp4")

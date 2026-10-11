"""The ManimGX logo, made by ManimGX: its word typeset by ManimGX's Typst beside Manim's three
shapes made solid, seen through a camera and written as SVG paths.

`python -m scripts.showcase.logo` writes into `docs/content/`:

- `showcase/logo-dark.svg` and `showcase/logo-light.svg`, the README's banner on each ground:
  an SVG that plays itself once and holds. The word is written (Manim's Write); then Manim's
  circle, square and triangle are drawn one after another (Create), and each becomes a solid
  in its own way: the circle fills with light and shade into a sphere, the square is pulled
  out into a cube as it turns its corner to us, the triangle lifts into a pyramid as it turns
  edge on. The browser interpolates projected face paths at its refresh rate, then stops;
  reduced motion shows the completed logo immediately.
- `images/logo-dark.svg` and `images/logo-light.svg`: the logo, still, for the site's header.
- `images/byline-dark.svg` and `images/byline-light.svg`: "by Academa", beside the header's
  logo, sharing its canvas height and text baseline.
- `images/academa-dark.svg` and `images/academa-light.svg`: Academa's wordmark, its name in
  Playwrite NO, for the footer.
- `images/favicon.svg`: the three solids.

"𝕄anim" is Typst's `$bb(M)$` and New Computer Modern Bold, in the proportions of Manim's
banner; "GX" is Playwrite NO, fetched from Google Fonts at a pinned commit, and checked
against its hash, into `.cache/` the first time. Playwrite NO is Academa's face too. What this
writes is committed.
"""

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

import numpy as np

import manimgx as m

CONTENT = Path(__file__).parents[2] / "docs" / "content"
FONTS = Path(__file__).parent / ".cache" / "fonts"
PLAYWRITE = "PlaywriteNO[wght].ttf"
PLAYWRITE_URL = (
    "https://raw.githubusercontent.com/google/fonts/"
    "1278c95fab1b417005827d83a8580ff57b92a274/ofl/playwriteno/PlaywriteNO%5Bwght%5D.ttf"
)
PLAYWRITE_SHA256 = "f4c860ca1f83d5d86db52eda1d01e81e2b41f119123189247f7d3071dd60bced"

INK = {"dark": "#ece6e2", "light": "#343434"}  # Manim's banner's, on each ground
GREEN, BLUE, RED = "#81b29a", "#454866", "#e07a5f"  # its circle, square and triangle
LIGHT = np.array([-0.5, 0.78, 0.42]) / np.linalg.norm([-0.5, 0.78, 0.42])  # upper left
SOLIDS = 1.272  # the solids' height beside "GX", over the 𝕄's, about the type's middle
SECONDS = 5.2  # the opening, which then holds
TURN_SECONDS = 0.95
TURN_KEYS = 17  # projection samples, interpolated at the display's refresh rate
HEADER = 60  # the header's logo: its height, in the SVG's units
BY = '#text(font: "New Computer Modern")[x#h(1em)by #text(font: "Playwrite NO")[Academa]]'
BYLINE = 0.5684  # the byline's em over the 𝕄's height
ACADEMA = '#text(font: "Playwrite NO")[x#h(1em)Academa]'  # Academa's wordmark

type Outline = list[np.ndarray]
"""A glyph run's subpaths, each (k, 4, 2): its cubic curves' control points, an em a unit,
y up."""


def playwrite() -> Path:
    """Playwrite NO, fetched once, checked against its hash."""
    path = FONTS / PLAYWRITE
    if not path.exists():
        with urlopen(PLAYWRITE_URL) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != PLAYWRITE_SHA256:
            raise RuntimeError(f"{PLAYWRITE_URL} is not the font pinned")
        FONTS.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return path


def sample(outline: Outline, n: int = 9) -> np.ndarray:
    """Points along an outline's curves: where its ink is."""
    c = np.concatenate(outline)[:, :, None, :]
    t = np.linspace(0, 1, n)[None, :, None]
    p0, p1, p2, p3 = c[:, 0], c[:, 1], c[:, 2], c[:, 3]
    u = 1 - t
    return (u**3 * p0 + 3 * u**2 * t * p1 + 3 * u * t**2 * p2 + t**3 * p3).reshape(
        -1, 2
    )


def extent(outline: Outline) -> tuple[float, float, float, float]:
    p = sample(outline)
    return p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()


def glyphs(code: str) -> list[Outline]:
    """A run of type, set by ManimGX's Typst after a probe "x" in the same document, whose
    foot is the baseline: its glyphs, the baseline at y = 0, the run's ink starting at x = 0."""
    doc = m.Typst(code, font_size=96, font_paths=[str(playwrite().parent)])
    probe, *run = [
        [np.asarray(s)[:, :2].reshape(-1, 4, 2) for s in g.get_subpaths()]
        for g in doc.submobjects
        if isinstance(g, m.VMobject)
    ]
    origin = [extent([s for g in run for s in g])[0], sample(probe)[:, 1].min()]
    return [[s - origin for s in g] for g in run]


def set_type(code: str) -> Outline:
    """A run of type, its glyphs as one outline."""
    return [s for g in glyphs(code) for s in g]


def word() -> tuple[list[Outline], float, float]:
    """𝕄, "anim" and "GX", placed; the 𝕄's height; and the word's em, "anim"'s. "anim" is
    0.757 of the 𝕄, as in Manim's banner, and "GX" 0.9; each follows the last's ink by a
    sliver of the 𝕄."""
    big_m = set_type("$x quad bb(M)$")
    h = extent(big_m)[3]
    parts, ems = [big_m], []
    for code, size, gap in (
        ('#text(font: "New Computer Modern", weight: 700)[x#h(1em)anim]', 0.757, 0.03),
        ('#text(font: "Playwrite NO")[x#h(1em)GX]', 0.9, 0.05),
    ):
        run = set_type(code)
        k = size * h / extent(run)[3]
        parts.append([s * k + [extent(parts[-1])[2] + gap * h, 0] for s in run])
        ems.append(k)
    return parts, h, ems[0]


# --- the solids ---------------------------------------------------------------------------


def rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    """The rotation by an angle about an axis (Rodrigues)."""
    x, y, z = axis / np.linalg.norm(axis)
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * k @ k


def turned(r0: np.ndarray, r1: np.ndarray, t: float) -> np.ndarray:
    """The rotation a fraction t of the way from r0 to r1, about their one axis (t may run
    past 1, to overshoot)."""
    d = r1 @ r0.T
    angle = math.acos(np.clip((np.trace(d) - 1) / 2, -1, 1))
    if angle < 1e-9:
        return r1
    axis = np.array([d[2, 1] - d[1, 2], d[0, 2] - d[2, 0], d[1, 0] - d[0, 1]])
    return rotation(axis, t * angle) @ r0


class Camera:
    """A pinhole at `eye`, looking at `target`, y up: points to the picture plane (y down)."""

    def __init__(self, eye: np.ndarray, target: np.ndarray, fov: float) -> None:
        self.eye = eye
        f = (target - eye) / np.linalg.norm(target - eye)
        r = np.cross(f, [0, 1, 0])
        r /= np.linalg.norm(r)
        self.axes = np.stack([r, np.cross(r, f), -f])
        self.focal = 1 / math.tan(math.radians(fov) / 2)

    def project(self, points: np.ndarray) -> np.ndarray:
        c = (np.atleast_2d(points) - self.eye) @ self.axes.T
        return self.focal * np.column_stack([c[:, 0], -c[:, 1]]) / -c[:, 2:3]

    def depth(self, points: np.ndarray) -> float:
        return float(np.mean(-((np.atleast_2d(points) - self.eye) @ self.axes[2])))


def shade(color: str, k: float) -> str:
    """A color darkened (k < 1) or lightened toward white (k > 1)."""
    c = np.array([int(color[i : i + 2], 16) for i in (1, 3, 5)]) / 255
    c = c * k if k < 1 else c + (1 - c) * (k - 1)
    return "#" + "".join(f"{round(v * 255):02x}" for v in np.clip(c, 0, 1))


def mix(a: str, b: str, t: float) -> str:
    ca, cb = (np.array([int(c[i : i + 2], 16) for i in (1, 3, 5)]) for c in (a, b))
    return "#" + "".join(f"{round(v):02x}" for v in ca + (cb - ca) * min(max(t, 0), 1))


@dataclass
class Face:
    """A projected face, with its tone, camera-facing measure and distance."""

    points: np.ndarray
    color: str
    facing: float
    depth: float


@dataclass
class Solid:
    """A polyhedron: its vertices about its centre, its faces, its color, where it stands
    and how it is turned there."""

    vertices: np.ndarray
    faces: list[tuple[int, ...]]
    color: str
    center: np.ndarray
    pose: np.ndarray

    def projected(
        self, camera: Camera, turn: float = 1, depth: float = 1, lit: float = 1
    ) -> list[Face]:
        """Every face in mesh order, on the picture plane, including hidden faces.
        Squashed along its own z by `depth` and turned `turn` of the way from facing the
        camera to its pose, it grows out of its silhouette; `lit` blends flat to shaded."""
        z = (camera.eye - self.center) / np.linalg.norm(camera.eye - self.center)
        x = np.cross([0, 1, 0], z)
        x /= np.linalg.norm(x)
        facing = np.column_stack([x, np.cross(z, x), z])
        r = turned(facing, self.pose, turn)
        world = (self.vertices * [1, 1, max(depth, 1e-4)]) @ r.T + self.center
        faces = []
        for face in self.faces:
            p = world[list(face)]
            n = np.cross(p[1] - p[0], p[2] - p[0])
            length = np.linalg.norm(n)
            if length > 1e-12:
                n /= length
            if np.dot(n, p.mean(0) - world.mean(0)) < 0:
                n = -n
            tone = shade(self.color, 0.76 + 0.44 * max(0.0, float(n @ LIGHT)))
            faces.append(
                Face(
                    camera.project(p),
                    mix(self.color, tone, lit),
                    float(np.dot(n, camera.eye - p.mean(0))),
                    camera.depth(p),
                )
            )
        return faces

    def seen(
        self, camera: Camera, turn: float = 1, depth: float = 1, lit: float = 1
    ) -> list[tuple[np.ndarray, str]]:
        """Its faces toward the camera, far first, each with its tone."""
        faces = [f for f in self.projected(camera, turn, depth, lit) if f.facing > 1e-9]
        faces.sort(key=lambda f: -f.depth)
        return [(f.points, f.color) for f in faces]


def turn_y(degrees: float) -> np.ndarray:
    return rotation(np.array([0.0, 1, 0]), math.radians(degrees))


def cube(center: list[float], size: float, yaw: float) -> Solid:
    v = (
        np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)])
        * size
        / 2
    )
    faces = [
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    ]
    return Solid(v, faces, BLUE, np.array(center), turn_y(yaw))


def tetrahedron(center: list[float], size: float, yaw: float) -> Solid:
    """On a face, apex up, about its middle height; an edge of its base along x, so that
    squashed flat it is Manim's triangle (yaw 60: an edge toward us, two faces seen)."""
    r, h = size / math.sqrt(3), size * math.sqrt(2 / 3)
    base = [
        [r * math.sin(t), -h / 2, r * math.cos(t)]
        for t in (math.pi / 3, math.pi, 5 * math.pi / 3)
    ]
    v = np.array([*base, [0, h / 2, 0]])
    return Solid(
        v,
        [(0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)],
        RED,
        np.array(center),
        turn_y(yaw),
    )


@dataclass
class Scene:
    """Manim's shapes as solids: a sphere (centre, radius), a cube and a tetrahedron, and
    the camera they are seen through."""

    sphere: tuple[np.ndarray, float]
    cube: Solid
    tetrahedron: Solid
    camera: Camera

    def disc(self) -> tuple[np.ndarray, float]:
        """The sphere on the picture plane: its centre and its radius."""
        c, r = self.sphere
        side = np.cross(self.camera.eye - c, [0, 1, 0])
        rim = c + side / np.linalg.norm(side) * r
        centre = self.camera.project(c)[0]
        return centre, float(np.linalg.norm(self.camera.project(rim)[0] - centre))

    def bounds(self) -> tuple[float, float, float, float]:
        (cx, cy), r = self.disc()
        p = np.vstack(
            [q for s in (self.cube, self.tetrahedron) for q, _ in s.seen(self.camera)]
        )
        return (
            min(p[:, 0].min(), cx - r),
            min(p[:, 1].min(), cy - r),
            max(p[:, 0].max(), cx + r),
            max(p[:, 1].max(), cy + r),
        )


def scene(row: bool = True) -> Scene:
    """The logo's row: the sphere in front, the cube behind, the tetrahedron edge on; or,
    for the favicon, Manim's triangle of them: the cube above, sphere and tetrahedron below."""
    t = 1.12 * math.sqrt(2 / 3) / 2  # the tetrahedron's half height: it stands on y = 0
    if row:
        sphere, c, tet = (
            ([-0.95, 0.5, 0.55], 0.5),
            cube([0, 0.5, -0.35], 1, 45),
            tetrahedron([0.95, t, 0.35], 1.12, 60),
        )
    else:
        sphere, c, tet = (
            ([-0.62, 0.48, 0.3], 0.48),
            cube([0, 1.32, -0.5], 0.95, 45),
            tetrahedron([0.66, t, 0.3], 1.12, 60),
        )
    middle = np.mean([sphere[0], c.center, tet.center], axis=0)
    camera = Camera(middle + [0, 3.3, 9], middle, 22)
    return Scene((np.array(sphere[0], float), sphere[1]), c, tet, camera)


# --- SVG ----------------------------------------------------------------------------------


def num(v: float) -> str:
    s = f"{v:.1f}"
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return "0" if s == "-0" else s


class Canvas:
    """The lockup's units (an em a unit, y up) as the SVG's (y down), `width` wide or
    `height` tall, with a margin."""

    def __init__(
        self,
        box: tuple[float, float, float, float],
        width: float | None = None,
        height: float | None = None,
        margin: float = 0.06,
    ) -> None:
        x0, y0, x1, y1 = box
        pad = margin * (y1 - y0)
        self.x0, self.y1, self.pad = x0, y1, pad
        self.s = (
            width / (x1 - x0 + 2 * pad)
            if width
            else (height or 1) / (y1 - y0 + 2 * pad)
        )
        self.width, self.height = (
            (x1 - x0 + 2 * pad) * self.s,
            (y1 - y0 + 2 * pad) * self.s,
        )

    def xy(self, p: np.ndarray) -> np.ndarray:
        p = np.asarray(p, float).reshape(-1, 2)
        return np.column_stack(
            [
                (p[:, 0] - self.x0 + self.pad) * self.s,
                (self.y1 + self.pad - p[:, 1]) * self.s,
            ]
        )

    def curve(self, subpath: np.ndarray) -> str:
        p = self.xy(subpath.reshape(-1, 2)).reshape(-1, 4, 2)
        out = f"M{num(p[0, 0, 0])} {num(p[0, 0, 1])}"
        for c in p:
            out += "C" + " ".join(f"{num(x)} {num(y)}" for x, y in c[1:])
        return out + "Z"

    def polygon(self, p: np.ndarray) -> str:
        q = self.xy(p)
        return "M" + "L".join(f"{num(x)} {num(y)}" for x, y in q) + "Z"

    def svg(
        self, body: str, view: tuple[float, float, float, float] | None = None
    ) -> str:
        """`body` as an SVG: all of the canvas, or a view of it (x, y, width, height)."""
        x, y, w, h = view or (0, 0, self.width, self.height)
        w, h = num(w), num(h)
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{num(x)} {num(y)} {w} {h}" width="{w}" height="{h}">{body}</svg>\n'


def animate(attribute: str, keys: list[tuple[float, str]]) -> str:
    """An attribute through (time, value) keys, eased between them, held after the last."""
    keys = [(0.0, keys[0][1]), *keys, (SECONDS, keys[-1][1])]
    times = ";".join(f"{t / SECONDS:.4f}" for t, _ in keys)
    values = ";".join(v for _, v in keys)
    splines = ";".join(["0.42 0 0.58 1"] * (len(keys) - 1))
    return f'<animate attributeName="{attribute}" dur="{SECONDS}s" fill="freeze" keyTimes="{times}" values="{values}" calcMode="spline" keySplines="{splines}"/>'


def drawn(
    paths: list[str], color: str, width: float, start: float, length: float = 0.5
) -> str:
    """Strokes drawn together (Create), then faded, sharing their inherited tracks."""
    dash = animate("stroke-dashoffset", [(start, "1"), (start + length, "0")])
    fade = animate(
        "stroke-opacity",
        [(start, "1"), (start + length + 0.05, "1"), (start + length + 0.3, "0")],
    )
    contours = "".join(f'<path d="{p}" pathLength="1"/>' for p in paths)
    return f'<g fill="none" stroke="{color}" stroke-width="{num(width)}" stroke-linejoin="round" stroke-dasharray="1 1" stroke-dashoffset="0" stroke-opacity="0">{dash}{fade}{contours}</g>'


def ease_out_back(t: float, k: float = 1.1) -> float:
    t = min(max(t, 0), 1)
    return 1 + (k + 1) * (t - 1) ** 3 + k * (t - 1) ** 2


def smooth(t: float) -> float:
    t = min(max(t, 0), 1)
    return t * t * (3 - 2 * t)


@dataclass
class Turn:
    """The logo's solid unfolding: projection keys and each visible face's entrance.

    In this choreography, faces only turn toward the camera, never away again. Their
    exact entrances are extra keys, so no interpolated polygon appears before it faces
    the camera. Faces keep one path each instead of swapping discrete frame groups.
    """

    times: list[float]
    frames: list[list[Face]]
    visible: list[int]
    onsets: dict[int, float]


def turn_frame(solid: Solid, camera: Camera, progress: float) -> list[Face]:
    """The exact 3D projection at a fraction of the solid's unfolding."""
    return solid.projected(
        camera,
        ease_out_back(progress),
        smooth(1.9 * progress),
        smooth(1.5 * progress),
    )


def turn_keys(solid: Solid, camera: Camera) -> Turn:
    """Enough samples for subpixel interpolation at the banner's intrinsic width."""
    times = [float(t) for t in np.linspace(0, 1, TURN_KEYS)]
    initial, final = turn_frame(solid, camera, 0), turn_frame(solid, camera, 1)
    visible = sorted(
        (i for i, face in enumerate(final) if face.facing > 1e-9),
        key=lambda i: -final[i].depth,
    )
    onsets = {}
    for i in visible:
        if initial[i].facing > 1e-9:
            continue
        lo, hi = 0.0, 1.0
        for _ in range(45):
            mid = (lo + hi) / 2
            if turn_frame(solid, camera, mid)[i].facing > 1e-9:
                hi = mid
            else:
                lo = mid
        onsets[i] = hi
        times.append(hi)
    times = sorted(set(times))
    return Turn(times, [turn_frame(solid, camera, t) for t in times], visible, onsets)


def interpolate(
    attribute: str, values: list[str], times: list[float], begin: float
) -> str:
    """One continuous unfolding track, with final values held after its entrance."""
    keys = ";".join(f"{t:.6f}" for t in times)
    return f'<animate attributeName="{attribute}" begin="{begin}s" dur="{TURN_SECONDS}s" fill="freeze" calcMode="linear" keyTimes="{keys}" values="{";".join(values)}"/>'


def beside(parts: list[Outline], h: float, sc: Scene) -> tuple[float, float, float]:
    """Where the solids' picture goes beside "GX", in the word's units: its left edge, its
    scale and its foot."""
    _, by0, _, by1 = sc.bounds()
    return (
        extent(parts[2])[2] + 0.16 * h,
        SOLIDS * h / (by1 - by0),
        0.5 * h - SOLIDS * h / 2,
    )


def box(parts: list[Outline], h: float, sc: Scene) -> tuple[float, float, float, float]:
    """The logo's box, in the word's units: the word's ink and the solids' picture."""
    left, s, bottom = beside(parts, h, sc)
    bx0, _, bx1, _ = sc.bounds()
    x0, y0, _, y1 = extent([c for part in parts for c in part])
    return x0, min(y0, bottom), left + (bx1 - bx0) * s, max(y1, bottom + SOLIDS * h)


def logo(
    ground: str,
    width: float | None = None,
    height: float | None = None,
    opening: bool = True,
) -> str:
    """The logo on a ground: its opening if `opening`, else still."""
    parts, h, _ = word()
    sc = scene()
    canvas = Canvas(box(parts, h, sc), width, height)
    body = logo_body(ground, parts, h, sc, canvas, opening)
    if opening:
        # Hiding animate elements does not stop SMIL. Show a separate, completed vector
        # group for reduced motion; final base attributes also support non-SMIL readers.
        style = (
            "<style>.logo-still{display:none}"
            "@media(prefers-reduced-motion:reduce){"
            ".logo-motion{display:none}.logo-still{display:inline}}</style>"
        )
        still = logo_body(ground, parts, h, sc, canvas, opening=False)
        body = (
            f'{style}<g class="logo-motion">{body}</g><g class="logo-still">{still}</g>'
        )
    return canvas.svg(body)


def logo_body(
    ground: str,
    parts: list[Outline],
    h: float,
    sc: Scene,
    canvas: Canvas,
    opening: bool,
) -> str:
    """The artwork in a shared canvas, animated or still."""
    bx0, _, _, by1 = sc.bounds()
    left, s, bottom = beside(parts, h, sc)

    def placed(p: np.ndarray) -> np.ndarray:  # the solids' picture plane, beside "GX"
        return np.column_stack(
            [left + (p[:, 0] - bx0) * s, bottom + (by1 - p[:, 1]) * s]
        )

    ink, stroke = INK[ground], max(0.9, 0.012 * canvas.s)
    body = []
    # the word, written: each part's outline drawn, then filled, one part after the next
    for i, part in enumerate(parts):
        paths = [canvas.curve(c) for c in part]
        if not opening:
            body.append(f'<path fill="{ink}" d="{"".join(paths)}"/>')
            continue
        t0 = 0.1 + 0.5 * i
        strokes = drawn(paths, ink, stroke, t0, 1.05)
        fill = animate("fill-opacity", [(t0 + 0.8, "0"), (t0 + 1.35, "1")])
        body.append(f'{strokes}<path fill="{ink}" d="{"".join(paths)}">{fill}</path>')
    # the cube (the farthest), the tetrahedron, then the sphere in front
    for solid, created, turning in (
        (sc.cube, 2.05, 2.95),
        (sc.tetrahedron, 2.35, 3.45),
    ):

        def faces(turn: float, depth: float, lit: float, solid: Solid = solid) -> str:
            return "".join(
                f'<path fill="{tone}" stroke="{tone}" stroke-width="0.6" stroke-linejoin="round" d="{canvas.polygon(placed(p))}"/>'
                for p, tone in solid.seen(sc.camera, turn, depth, lit)
            )

        if not opening:
            body.append(faces(1, 1, 1))
            continue
        turn = turn_keys(solid, sc.camera)
        fade = animate("opacity", [(created + 0.4, "0"), (created + 0.65, "1")])
        body.append(f'<g stroke-width="0.6" stroke-linejoin="round">{fade}')
        for i in turn.visible:
            paths = [canvas.polygon(placed(frame[i].points)) for frame in turn.frames]
            colors = [frame[i].color for frame in turn.frames]
            # currentColor keeps the fill and antialiasing seam-cover stroke together.
            body.append(
                f'<path fill="currentColor" stroke="currentColor" color="{colors[-1]}" d="{paths[-1]}">'
            )
            if i in turn.onsets:
                onset = turning + TURN_SECONDS * turn.onsets[i]
                body.append(
                    f'<set attributeName="visibility" to="hidden" begin="0s" dur="{onset:.6f}s"/>'
                )
            for attribute, values in (("d", paths), ("color", colors)):
                body.append(
                    f'<set attributeName="{attribute}" to="{values[0]}" begin="0s" dur="{turning}s"/>'
                    + interpolate(attribute, values, turn.times, turning)
                )
            body.append("</path>")
        body.append("</g>")
        outline = "".join(
            canvas.polygon(placed(p)) for p, _ in solid.seen(sc.camera, 0, 0, 0)
        )
        body.append(drawn([outline], solid.color, stroke, created))
    # the sphere: Manim's circle, drawn, filled, then lit into a ball
    (cx, cy), r = sc.disc()
    centre = canvas.xy(placed(np.array([[cx, cy]])))[0]
    radius = r * s * canvas.s
    light, dark = shade(GREEN, 1.18), shade(GREEN, 0.78)
    gradient = f"ball-{ground}{'' if opening else '-still'}"
    stops = [(0, light), (0.6, GREEN), (1, dark)]
    if opening:
        stop = "".join(
            f'<stop offset="{o}" stop-color="{c}">{animate("stop-color", [(2.7, GREEN), (3.4, c)]) if c != GREEN else ""}</stop>'
            for o, c in stops
        )
        grow = animate(
            "r", [(2.7, num(radius)), (3.0, num(radius * 1.06)), (3.4, num(radius))]
        )
        fade = animate("fill-opacity", [(2.15, "0"), (2.4, "1")])
        ring = f"M{num(centre[0])} {num(centre[1] - radius)}a{num(radius)} {num(radius)} 0 1 0 0.01 0Z"
        body.append(
            f'<defs><radialGradient id="{gradient}" cx="0.5" cy="0.5" r="0.5" fx="0.34" fy="0.3">{stop}</radialGradient></defs>'
            f'<circle cx="{num(centre[0])}" cy="{num(centre[1])}" r="{num(radius)}" fill="url(#{gradient})">{fade}{grow}</circle>'
            + drawn([ring], GREEN, stroke, 1.75)
        )
    else:
        stop = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        body.append(
            f'<defs><radialGradient id="{gradient}" cx="0.5" cy="0.5" r="0.5" fx="0.34" fy="0.3">{stop}</radialGradient></defs>'
            f'<circle cx="{num(centre[0])}" cy="{num(centre[1])}" r="{num(radius)}" fill="url(#{gradient})"/>'
        )
    return "".join(body)


def byline(ground: str) -> str:
    """The byline, "by Academa", on the header logo's canvas and baseline.

    Both glyph runs have their baseline at y = 0. Keeping the logo's vertical viewBox means
    equally tall images align their text at any display size, without CSS offsets. Only the
    width is cropped to the byline's ink and the shared margin.
    """
    parts, h, _ = word()
    canvas = Canvas(box(parts, h, scene()), height=HEADER)
    run = [[s * BYLINE * h for s in g] for g in glyphs(BY)]
    right = canvas.xy(np.array([[extent([s for g in run for s in g])[2], 0]]))[0, 0]
    ink = INK[ground]
    # "by" is the run's first two glyphs; Playwrite NO joins "Academa"'s letters with glyphs
    by, name = (
        "".join(canvas.curve(s) for g in part for s in g) for part in (run[:2], run[2:])
    )
    return canvas.svg(
        f'<path fill="{ink}" fill-opacity="0.72" d="{by}"/><path fill="{ink}" d="{name}"/>',
        (0, 0, right + canvas.pad * canvas.s, canvas.height),
    )


def wordmark(ground: str) -> str:
    """Academa's wordmark: its name in Playwrite NO, its ink with the logo's margin."""
    run = set_type(ACADEMA)
    canvas = Canvas(extent(run), height=HEADER / 2)
    paths = "".join(canvas.curve(s) for s in run)
    return canvas.svg(f'<path fill="{INK[ground]}" d="{paths}"/>')


def favicon() -> str:
    """The three solids as Manim's triangle, still: the cube above, sphere and tetrahedron
    below."""
    sc = scene(row=False)
    bx0, by0, bx1, by1 = sc.bounds()
    canvas = Canvas((bx0, -by1, bx1, -by0), height=64, margin=0.03)
    flip = np.array([1, -1])  # the picture plane is y down; the canvas wants y up
    faces = "".join(
        f'<path fill="{tone}" stroke="{tone}" stroke-width="0.4" stroke-linejoin="round" d="{canvas.polygon(p * flip)}"/>'
        for solid in (sc.cube, sc.tetrahedron)
        for p, tone in solid.seen(sc.camera)
    )
    (cx, cy), r = sc.disc()
    c = canvas.xy(np.array([[cx, -cy]]))[0]
    stops = f'<stop offset="0" stop-color="{shade(GREEN, 1.18)}"/><stop offset="0.6" stop-color="{GREEN}"/><stop offset="1" stop-color="{shade(GREEN, 0.78)}"/>'
    ball = (
        f'<defs><radialGradient id="ball" cx="0.5" cy="0.5" r="0.5" fx="0.34" fy="0.3">{stops}</radialGradient></defs>'
        f'<circle cx="{num(c[0])}" cy="{num(c[1])}" r="{num(r * canvas.s)}" fill="url(#ball)"/>'
    )
    return canvas.svg(faces + ball)


def main() -> None:
    for ground in INK:
        (CONTENT / "showcase" / f"logo-{ground}.svg").write_text(
            logo(ground, width=900), encoding="utf-8"
        )
        (CONTENT / "images" / f"logo-{ground}.svg").write_text(
            logo(ground, height=HEADER, opening=False), encoding="utf-8"
        )
        (CONTENT / "images" / f"byline-{ground}.svg").write_text(
            byline(ground), encoding="utf-8"
        )
        (CONTENT / "images" / f"academa-{ground}.svg").write_text(
            wordmark(ground), encoding="utf-8"
        )
    (CONTENT / "images" / "favicon.svg").write_text(favicon(), encoding="utf-8")
    for path in sorted(
        [
            *(CONTENT / "showcase").glob("logo-*.svg"),
            *(CONTENT / "images").glob("logo-*.svg"),
            *(CONTENT / "images").glob("byline-*.svg"),
            *(CONTENT / "images").glob("academa-*.svg"),
            CONTENT / "images" / "favicon.svg",
        ]
    ):
        print(f"{path.relative_to(CONTENT)}: {path.stat().st_size / 1000:.0f} kB")


if __name__ == "__main__":
    main()

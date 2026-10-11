"""Turning a torus inside out: a quarter turn in four dimensions.

The Clifford torus X(u, v) = (cos u, sin u, cos v, sin v)/√2 lies in the 3-sphere and splits it
into two congruent solid tori. Stereographic projection P(x) = (x1, x2, x3)/(1 − x4) shows it as
an ordinary torus, slate outside and wine inside (a wedge is cut away to see in). Rotating S³ by t
in the x1x3- and x2x4-planes at once, the torus has to pass through the pole x4 = 1, the point at
infinity: at t = 45° it is a plane with a handle. At t = 90° it is the same torus again, with its
gold and blue circles exchanged and its wine side facing out: the inside has become the outside.
"""

from collections.abc import Callable

import numpy as np

import manimgx as m


def camera_axes(phi: float, theta: float, gamma: float) -> np.ndarray:
    """The camera's axes for its orbit angles, as rows: right, up, and toward the viewer."""

    def spin(a: float) -> np.ndarray:  # a turn about z
        return np.array(
            [[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]]
        )

    c, s = np.cos(phi), np.sin(phi)
    tilt = np.array(
        [[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]]
    )  # a turn by −φ about x
    return spin(gamma) @ tilt @ spin(-theta - np.pi / 2)


S = 1.15  # scale of the projected picture
NU, NV = (
    144,
    160,
)  # surface cells: u spans the torus minus a 30° wedge, v the full circle
LINES, RING, SIDES = (
    12,
    128,
    8,
)  # circles per family (30° apart), points per circle, tube sides
WEDGE = np.radians(-105.0), np.radians(-75.0)  # the cut-away cell
RC = 10.0  # geometry farther than this from the origin is cut away (it runs off to infinity)
TUBE = 0.05
SLATE, WINE = "#2f3648", "#781d38"
GOLD, BLUE = "#ffbe3b", "#4aa8ff"


# ── the torus in S³ and its shadow ─────────────────────────────────────────────────────────────


def rotation(t: float, s: float) -> np.ndarray:
    """The quarter turn (x1x3- and x2x4-planes by t), then the smoke-ring roll (x3x4-plane by
    s), which slides the torus along itself through its hole."""
    c, d = np.cos(t), np.sin(t)
    swap = np.array([[c, 0, d, 0], [0, c, 0, -d], [-d, 0, c, 0], [0, d, 0, c]])
    c, d = np.cos(s), np.sin(s)
    roll = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, c, -d], [0, 0, d, c]])
    return roll @ swap


def project(
    u: np.ndarray, v: np.ndarray, turn: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Projected points of the turned torus, their unit normals (pointing into the tube at
    rest), and the height x4 of each point in S³."""
    x = np.stack([np.cos(u), np.sin(u), np.cos(v), np.sin(v)], -1) @ turn.T / np.sqrt(2)
    n = (
        np.stack([np.cos(u), np.sin(u), -np.cos(v), -np.sin(v)], -1)
        @ turn.T
        / np.sqrt(2)
    )
    d = np.maximum(1 - x[..., 3:], 1e-9)
    normal = (
        n[..., :3] / d + x[..., :3] * n[..., 3:] / d**2
    )  # the differential of P, applied to n
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return S * x[..., :3] / d, normal, x[..., 3]


# ── meshes ─────────────────────────────────────────────────────────────────────────────────────


def grid_triangles(nu: int, nv: int) -> np.ndarray:
    """Triangles of an (nu + 1) × nv grid, open in u and periodic in v, ordered along u."""
    i = np.arange(nu)[:, None]
    j = np.arange(nv)[None, :]
    a, b = i * nv + j, (i + 1) * nv + j
    c, d = (i + 1) * nv + (j + 1) % nv, i * nv + (j + 1) % nv
    return np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], 2).reshape(
        -1, 3
    )


def tube_triangles(lines: int, n: int, sides: int) -> np.ndarray:
    """Triangles of closed tubes, shaped (lines, n segments, 2·sides, 3)."""
    li = np.arange(lines)[:, None, None]
    i = np.arange(n)[None, :, None]
    j = np.arange(sides)[None, None, :]
    base = li * n * sides
    a, b = base + i * sides + j, base + (i + 1) % n * sides + j
    c, d = (
        base + (i + 1) % n * sides + (j + 1) % sides,
        base + i * sides + (j + 1) % sides,
    )
    tris = np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], 3)
    return tris.reshape(lines, n, 2 * sides, 3)


def tubes(points: np.ndarray, normals: np.ndarray) -> np.ndarray:
    """Vertices of closed tubes around curves (lines, n, 3) lying on the surface."""
    tangent = np.roll(points, -1, 1) - np.roll(points, 1, 1)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=-1, keepdims=True), 1e-12)
    side = np.cross(tangent, normals)
    a = np.linspace(0, m.TAU, SIDES, endpoint=False)[:, None]
    ring = np.cos(a) * normals[:, :, None] + np.sin(a) * side[:, :, None]
    return (points[:, :, None] + TUBE * ring).reshape(-1, 3)


def clip(
    values: np.ndarray, triangles: np.ndarray, far: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Keep the part of a mesh where far < 0, cutting triangles along far = 0 so the edge is
    smooth instead of a staircase. `values` are per-vertex rows (position, normal, ...),
    interpolated at the cuts; returns them (cut rows appended) and the kept triangles.
    """
    out = far[triangles] >= 0
    count = out.sum(axis=1)
    pieces, rows = [triangles[count == 0]], [values]
    total = len(values)

    def cut(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        nonlocal total
        lam = (far[a] / (far[a] - far[b]))[:, None]
        rows.append(values[a] * (1 - lam) + values[b] * lam)
        total += len(a)
        return np.arange(total - len(a), total)

    for k in (1, 2):
        tri, o = triangles[count == k], out[count == k]
        # turn each triangle (keeping its winding) so the odd vertex is last (k = 1) or first
        first = (np.argmax(o, axis=1) + 1) % 3 if k == 1 else np.argmin(o, axis=1)
        a, b, c = np.take_along_axis(tri, (first[:, None] + np.arange(3)) % 3, 1).T
        if k == 1:  # c is out: a quad remains
            bc, ac = cut(b, c), cut(a, c)
            pieces += [np.stack([a, b, bc], 1), np.stack([a, bc, ac], 1)]
        else:  # only a is in: a small triangle remains
            pieces.append(np.stack([a, cut(a, b), cut(a, c)], 1))
    return np.concatenate(rows), np.concatenate(pieces)


def linger(x: float) -> float:
    """A smooth 0 → 1 that slows down in the middle, where the torus passes infinity."""
    ease = x / 2 - np.sin(4 * np.pi * x) / (
        8 * np.pi
    )  # speed sin²(2πx): rests at 0, ½, 1
    through = x / 2 - np.sin(2 * np.pi * x) / (
        4 * np.pi
    )  # speed sin²(πx): keeps it moving
    return float((ease + 0.3 * through) / 0.65)


def passage(t: float) -> float:
    """0 while the torus is small; 1 while it is near infinity (t within 15° of 45°)."""
    x = float(np.clip((np.radians(25) - abs(t - np.pi / 4)) / np.radians(10), 0, 1))
    return x * x * (3 - 2 * x)


def live(number: m.DecimalNumber, value: Callable[[], float]) -> m.DecimalNumber:
    """Keep a number showing value(), re-typesetting it only when its digits change."""

    def update(d: m.DecimalNumber) -> None:
        v, places = value(), d.num_decimal_places
        if round(v, places) != round(d.get_value(), places):
            d.set_value(v)

    number.add_updater(update)
    return number


def vignette() -> m.ImageMobject:
    """A screen-sized frame that darkens the edges, so the HUD stays legible when the torus
    fills the screen (invisible against the background otherwise)."""
    h, w = 180, 320
    y, x = np.mgrid[-1 : 1 : h * 1j, -1 : 1 : w * 1j]
    d = np.clip(((np.abs(x) ** 3 + np.abs(y) ** 3) ** (1 / 3) - 0.55) / 0.4, 0, 1)
    image = np.zeros((h, w, 4), np.uint8)  # black, like the background
    image[..., 3] = (230 * d * d * (3 - 2 * d)).astype(np.uint8)
    mob = m.ImageMobject(image)
    mob.stretch_to_fit_width(m.config.frame_width)
    mob.stretch_to_fit_height(m.config.frame_height)
    return mob


class Shadow:
    """Everything drawn, for the current angles and camera: recomputed once per frame."""

    def __init__(
        self, scene: m.ThreeDScene, t: m.ValueTracker, s: m.ValueTracker
    ) -> None:
        self.scene, self.t, self.s = scene, t, s
        self.grow = m.ValueTracker(0.04)
        self.key: tuple[float, ...] = ()
        us = np.linspace(WEDGE[1], WEDGE[0] + m.TAU, NU + 1)
        # v is offset by half a cell, so that no vertex ever lands exactly on the pole
        vs = (np.arange(NV) + 0.5) * m.TAU / NV
        self.u, self.v = np.meshgrid(us, vs, indexing="ij")
        self.surface_triangles = grid_triangles(NU, NV)
        ring = np.linspace(0, m.TAU, RING, endpoint=False)
        levels = WEDGE[0] + np.arange(LINES) * m.TAU / LINES
        ones = np.ones((LINES, RING))
        # gold circles: v fixed, u runs; blue circles: u fixed (both wedge edges among them)
        self.circles = {
            "gold": (ring * ones, (levels + np.pi / 12)[:, None] * ones),
            "blue": (levels[:, None] * ones, ring * ones),
        }
        self.tube_triangles = tube_triangles(LINES, RING, SIDES)
        self.meshes: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self.colors = np.zeros((0, 4))
        self.points = self.normals = np.zeros((0, 3))
        self.height = 0.0
        self.slate, self.wine = (
            np.array(m.ManimColor(c).to_rgba()) for c in (SLATE, WINE)
        )

    def update(self) -> None:
        cam = self.scene.camera
        angles = (cam.get_phi(), cam.get_theta(), cam.get_gamma())
        key = (self.t.get_value(), self.s.get_value(), self.grow.get_value(), *angles)
        if key == self.key:
            return
        self.key = key
        turn = rotation(key[0], key[1])
        p, n, x4 = project(self.u, self.v, turn)
        self.points, self.normals = p.reshape(-1, 3), n.reshape(-1, 3)
        self.height = float(x4.max())
        # the sweep that builds the torus: a front at angle `front` past the wedge
        front = key[2] * (m.TAU + 2.2)
        cells = int(np.clip(front / (m.TAU - (WEDGE[1] - WEDGE[0])), 0, 1) * NU)
        shown = self.surface_triangles[: 2 * NV * cells]
        far = np.linalg.norm(self.points, axis=1) - RC
        rows, tris = clip(np.hstack([self.points, self.normals]), shown, far)
        # two-sided paint: slate where the outer side faces the eye, wine where the inner does
        eye = cam.frame_center + cam.get_focal_distance() * camera_axes(*angles)[2]
        inner = np.sum(rows[:, 3:] * (eye - rows[:, :3]), axis=1) > 0
        self.colors = np.where(inner[:, None], self.wine, self.slate)
        self.meshes["surface"] = rows[:, :3], tris
        for name, (cu, cv) in self.circles.items():
            cp, cn, _ = project(cu, cv, turn)
            # how long ago the front passed each point of the circle
            passed = front - (cu - WEDGE[1]) % m.TAU
            # a gold circle is laid down with the front; a blue one then draws itself round
            drawn = passed >= 0 if name == "gold" else cv <= 3 * passed
            near = np.linalg.norm(cp, axis=-1) < RC
            keep = drawn & np.roll(drawn, -1, 1) & near & np.roll(near, -1, 1)
            self.meshes[name] = (
                tubes(cp, cn),
                self.tube_triangles[keep].reshape(-1, 3),
            )

    def mesh(self, name: str, color: str) -> m.MeshMobject:
        mob = m.MeshMobject(
            np.zeros((3, 3)), np.array([[0, 1, 2]]), shade_in_3d=True, fill_color=color
        )

        def follow(mob: m.MeshMobject) -> None:
            self.update()
            mob.points, mob.triangles = self.meshes[name]
            if name == "surface":
                mob.paint = mob.paint.but(fill=self.colors)

        mob.add_updater(follow)
        return mob

    def outside_is_slate(self) -> bool:
        """Measured: at the torus's farthest point, is the slate side the one facing away?"""
        self.update()
        k = int(np.argmax(np.linalg.norm(self.points, axis=1)))
        return float(self.points[k] @ self.normals[k]) < 0


class CliffordTorus(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(
            phi=66 * m.DEGREES, theta=-116 * m.DEGREES, zoom=1.0, focal_distance=40
        )
        self.begin_ambient_camera_rotation(rate=0.045)
        t, s = m.ValueTracker(0.0), m.ValueTracker(-np.pi / 2)
        shadow = Shadow(self, t, s)
        colors = {"surface": SLATE, "gold": GOLD, "blue": BLUE}
        self.add(*(shadow.mesh(name, color) for name, color in colors.items()))

        # heads-up display
        title = m.Text("Turning a torus inside out", font_size=36).to_corner(m.UL)
        subtitle = m.Text(
            "the Clifford torus, rotated in four dimensions", font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.15
        )
        formulas = m.VGroup(
            m.MathTex(
                r"X(u,v) = \frac{1}{\sqrt{2}}\,(\cos u,\ \sin u,\ \cos v,\ \sin v)",
                font_size=30,
            ),
            m.MathTex(r"P(x) = \frac{(x_1,\ x_2,\ x_3)}{1 - x_4}", font_size=30),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.25)
        formulas.to_corner(m.UR)

        def swatch(outside: bool) -> m.Square:
            box = m.Square(0.26, fill_opacity=1, stroke_color=m.WHITE, stroke_width=1)
            box.add_updater(
                lambda b: b.set_fill(
                    SLATE if shadow.outside_is_slate() == outside else WINE
                )
            )
            return box

        legend = m.VGroup(
            m.VGroup(swatch(True), m.Text("outside", font_size=24)),
            m.VGroup(swatch(False), m.Text("inside", font_size=24)),
        )
        for row in legend:
            row.arrange(m.RIGHT, buff=0.2)
        legend.arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2).to_corner(m.DL)

        plane_note = m.MathTex(
            r"\text{rotating the } x_1x_3 \text{ and } x_2x_4 \text{ planes}",
            font_size=26,
        ).set_color(m.GREY_B)
        angle = live(
            m.DecimalNumber(0, num_decimal_places=1, unit=r"^\circ", font_size=30),
            lambda: float(np.degrees(t.get_value())),
        )
        height = live(
            m.DecimalNumber(shadow.height, num_decimal_places=3, font_size=30),
            lambda: shadow.height,
        )
        readouts = m.VGroup(
            m.VGroup(m.MathTex(r"t =", font_size=30), angle),
            m.VGroup(m.MathTex(r"\max x_4 =", font_size=30), height),
        )
        for row in readouts:
            row.arrange(m.RIGHT, buff=0.15)
        readouts.arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        hud_br = m.VGroup(plane_note, readouts).arrange(
            m.DOWN, aligned_edge=m.RIGHT, buff=0.2
        )
        hud_br.to_corner(m.DR)

        caption = m.MathTex(
            r"x_4 = 1 \text{ is the point at infinity, and the torus passes"
            r" through it}",
            font_size=28,
        )
        caption.to_edge(m.DOWN, buff=0.3)
        # while the torus fills the screen, the caption replaces the formulas and the subtitle
        formulas_on = m.ValueTracker(0.0)
        caption.add_updater(lambda c: c.set_opacity(passage(t.get_value())))
        subtitle.add_updater(lambda c: c.set_opacity(1 - passage(t.get_value())))
        formulas.add_updater(
            lambda f: f.set_opacity(
                formulas_on.get_value() * (1 - passage(t.get_value()))
            )
        )

        self.add_fixed_in_frame_mobjects(vignette(), title, subtitle)
        self.add_fixed_in_frame_mobjects(formulas, legend, hud_br, caption)
        self.remove(legend, hud_br)

        # 0–2.5 s: the torus is swept in; its open end shows the wine inside
        self.play(shadow.grow.animate.set_value(1.0), run_time=2.5, rate_func=m.smooth)
        # 2.5–7 s: the smoke ring: the gold circles roll through the hole
        self.play(
            s.animate.set_value(0.0),
            m.Succession(
                formulas_on.animate(run_time=1.2).set_value(1.0),
                m.FadeIn(legend, run_time=1.2),
            ),
            run_time=4.5,
            rate_func=m.linear,
        )
        # 7–18 s: the quarter turn in 4D, through the point at infinity
        self.play(m.FadeIn(hud_br), run_time=0.6)
        self.play(t.animate.set_value(np.pi / 2), run_time=10.5, rate_func=linger)
        # 18–24 s: the smoke ring again: now the blue circles roll through the hole
        self.move_camera(
            phi=54 * m.DEGREES,
            zoom=1.1,
            run_time=6,
            added_anims=[s.animate(rate_func=m.linear).set_value(np.pi / 2)],
        )
        closing = m.Text("A quarter turn in 4D swaps inside and outside.", font_size=28)
        closing.to_edge(m.DOWN, buff=0.3)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(
            m.FadeIn(closing, shift=0.2 * m.UP),
            s.animate.set_value(0.6 * np.pi),
            run_time=1.5,
            rate_func=m.linear,
        )
        self.play(s.animate.set_value(0.9 * np.pi), run_time=4.4, rate_func=m.linear)


if __name__ == "__main__":
    CliffordTorus().render("clifford_torus.mp4")

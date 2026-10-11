"""Why a spinning handle flips: the tennis-racket theorem (Dzhanibekov effect).

Three identical T-handles spin at the same rate about their three principal axes. About the
axes of least and greatest moment of inertia the spin is steady; about the middle one the
handle turns over every few seconds, though nothing pushes it and its angular momentum L
(gold) never moves. Torque-free Euler equations I₁ω̇₁ = (I₂ − I₃)ω₂ω₃ (cyclic), RK4 with a
quaternion; the moments are computed from the drawn handle. Seen from the handle, L keeps
its length and the energy E = Σ L_k²/2I_k, so it slides along level curves of E on a sphere
(the polhodes). The separatrix, two great circles, cuts that sphere into four panels that
meet only at the middle axis, a saddle: a state near it is carried to the opposite side.
"""

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


SPIN = 0.7 * m.TAU  # rad/s, the same for all three handles
WOBBLE = 0.005  # the small off-axis part of every initial spin, relative to SPIN
RATE, SUBSTEPS, DURATION = 60, 2, 31.0  # samples/s of the motion, RK4 steps per sample
STEEL, CORAL, GOLD = "#9db4cf", "#ef6f6c", "#f4c95d"
AXIS1, AXIS3 = "#2bb3a3", "#6a5acd"  # the glass panels around axes 1 and 3
BAR, BAR_R, STEM, STEM_R, KNOB_R = 2.8, 0.12, 1.3, 0.08, 0.16  # crossbar ∥ x, stem ∥ y


def moments() -> tuple[np.ndarray, np.ndarray]:
    """Center of mass and principal moments (per unit mass) of the solid T of one density:
    crossbar and stem cylinders and a ball. By symmetry the body axes are principal."""
    bar, stem, knob = BAR_R**2 * BAR, STEM_R**2 * STEM, 4 / 3 * KNOB_R**3  # masses / π
    across = [(3 * r * r + h * h) / 12 for r, h in ((BAR_R, BAR), (STEM_R, STEM))]
    parts = [
        (bar, 0.0, [BAR_R**2 / 2, across[0], across[0]]),
        (stem, STEM / 2, [across[1], STEM_R**2 / 2, across[1]]),
        (knob, STEM, [0.4 * KNOB_R**2] * 3),
    ]
    total = bar + stem + knob
    com = sum(mass * y for mass, y, _ in parts) / total
    inertia = np.zeros(3)
    for mass, y, own in parts:  # parallel axes: the offsets are along y
        inertia += mass * (np.array(own) + (y - com) ** 2 * np.array([1, 0, 1]))
    return np.array([0, com, 0]), inertia / total


def simulate(inertia: np.ndarray, omega0: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Body angular velocities (n, k, 3) and turns (n, k, 3, 3) of k free bodies started
    at the body rates omega0 (k, 3): Euler's equations and Ṙ = R [ω]×, by RK4."""
    i1, i2, i3 = inertia
    p, q, r = (i2 - i3) / i1, (i3 - i1) / i2, (i1 - i2) / i3

    def deriv(w: np.ndarray, turn: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        w1, w2, w3 = w.T
        o = 0 * w1
        cross = np.array([[o, -w3, w2], [w3, o, -w1], [-w2, w1, o]]).transpose(2, 0, 1)
        return np.stack([p * w2 * w3, q * w3 * w1, r * w1 * w2], -1), turn @ cross

    h = 1 / (RATE * SUBSTEPS)
    w, turn = omega0, np.tile(np.eye(3), (len(omega0), 1, 1))
    samples = [(w, turn)]
    for step in range(1, int(DURATION * RATE) * SUBSTEPS + 1):
        a1, b1 = deriv(w, turn)
        a2, b2 = deriv(w + h / 2 * a1, turn + h / 2 * b1)
        a3, b3 = deriv(w + h / 2 * a2, turn + h / 2 * b2)
        a4, b4 = deriv(w + h * a3, turn + h * b3)
        w = w + h / 6 * (a1 + 2 * a2 + 2 * a3 + a4)
        turn = turn + h / 6 * (b1 + 2 * b2 + 2 * b3 + b4)
        if step % SUBSTEPS == 0:
            samples.append((w, turn))
    return np.array([w for w, _ in samples]), np.array([t for _, t in samples])


def toward_z(u: np.ndarray, hint: np.ndarray) -> np.ndarray:
    """A rotation taking the unit vector u to +z (and hint, as far as it can, to +x)."""
    x = hint - (hint @ u) * u
    x /= np.linalg.norm(x)
    return np.array([x, np.cross(u, x), u])


# ── smooth lit parts: surfaces of revolution and tubes ──────────────────────────────────


def revolve(profile: np.ndarray, sides: int = 28) -> np.ndarray:
    """An (rows, sides + 1, 3) grid: profile rows (r, z) swept around the z axis. A row
    given twice makes a sharp rim (normals average over faces of nonzero area)."""
    a = np.linspace(0, m.TAU, sides + 1)
    r, z = profile[:, :1], profile[:, 1:]
    return np.stack([r * np.cos(a), r * np.sin(a), z + 0 * a], -1)


def ball(radius: float, rows: int = 14) -> np.ndarray:
    t = np.linspace(-np.pi / 2, np.pi / 2, rows + 1)[:, None]
    return radius * np.hstack([np.cos(t), np.sin(t)])


def rod(length: float, radius: float) -> np.ndarray:
    """A rod with round ends, centered, along z."""
    cap = ball(radius)
    return np.vstack([cap[:8] - [0, length / 2], cap[7:] + [0, length / 2]])


def arrow(length: float, radius: float, head: float, width: float) -> np.ndarray:
    shaft = length - head
    rows = [(0, 0), (radius, 0), (radius, 0), (radius, shaft), (radius, shaft)]
    return np.array(rows + [(width, shaft), (width, shaft), (0, length)])


def surface(grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vertices and triangles of an (rows + 1, cols + 1, 3) grid of points."""
    rows, cols = grid.shape[0] - 1, grid.shape[1] - 1
    i, j = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    a = (i * (cols + 1) + j).ravel()
    b, c = a + cols + 1, a + cols + 2
    tris = np.vstack([np.stack([a, b, c], 1), np.stack([a, c, a + 1], 1)])
    return grid.reshape(-1, 3), tris


def tube(points: np.ndarray, radius: float, sides: int = 7) -> np.ndarray:
    """A grid around a polyline (parallel-transport frames), for `surface`."""
    tangent = np.gradient(points, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    normals = [np.cross(tangent[0], [0.3, 0.5, 0.8])]
    for t in tangent:
        n = normals[-1] - (normals[-1] @ t) * t
        normals.append(n / np.linalg.norm(n))
    n_ = np.array(normals[1:])
    a = np.linspace(0, m.TAU, sides + 1)[:, None]
    ring = np.cos(a) * n_[:, None] + np.sin(a) * np.cross(tangent, n_)[:, None]
    return points[:, None] + radius * ring


def mesh(grid: np.ndarray, color: str) -> m.MeshMobject:
    return m.MeshMobject(*surface(grid), shade_in_3d=True, fill_color=color)


def handle_parts(com: np.ndarray) -> list[m.MeshMobject]:
    """The T in its body frame, around its center of mass: crossbar, stem and knob."""
    along_x, along_y = np.roll(np.eye(3), 1, 1), np.roll(np.eye(3), 2, 1)
    return [
        mesh(revolve(rod(BAR, BAR_R)) @ along_x - com, STEEL),
        mesh(revolve(rod(STEM, STEM_R)) @ along_y + [0, STEM / 2, 0] - com, CORAL),
        mesh(revolve(ball(KNOB_R)) + [0, STEM, 0] - com, CORAL),
    ]


class Rigid:
    """Pose a group absolutely each frame: points = base · Rᵀ + center."""

    def __init__(self, group: m.Mobject) -> None:
        self.parts = [
            (mob, mob.points.copy()) for mob in group.family_members_with_points()
        ]

    def pose(self, turn: np.ndarray, center: np.ndarray) -> None:
        for mob, base in self.parts:
            mob.points = base @ turn.T + center


# ── the handle's own frame: the sphere of directions of L ───────────────────────────────


def polhodes(inertia: np.ndarray) -> list[np.ndarray]:
    """Level curves of E = ½ Σ n_k²/I_k on the unit sphere: loops around ±axis 1 and ±axis 3,
    then the separatrix, two great circles through ±axis 2."""
    inv = 1 / inertia
    s = np.linspace(0, m.TAU, 181)[:, None]
    curves = []
    for k in (0.35, 0.75):  # 0: the separatrix, 1: the axis
        a = np.sqrt(1 - k)
        b = np.sqrt((1 - k) * (inv[1] - inv[2]) / (inv[0] - inv[2]))
        c = np.sqrt((1 - k) * (inv[0] - inv[1]) / (inv[0] - inv[2]))
        for sign in (1, -1):
            n2, n3 = a * np.cos(s), c * np.sin(s)  # around ±axis 1
            curves.append(np.hstack([sign * np.sqrt(1 - n2**2 - n3**2), n2, n3]))
            n1, n2 = b * np.cos(s), a * np.sin(s)  # around ±axis 3
            curves.append(np.hstack([n1, n2, sign * np.sqrt(1 - n1**2 - n2**2)]))
    tilt = np.array([np.sqrt(inv[1] - inv[2]), 0, np.sqrt(inv[0] - inv[1])])
    tilt /= np.linalg.norm(tilt)
    for sign in (1, -1):
        curves.append(np.cos(s) * [0, 1, 0] + np.sin(s) * tilt * [1, 0, sign])
    return curves


def panel_colors(n: np.ndarray, inertia: np.ndarray, alpha: float) -> np.ndarray:
    """Glass tint: the panels around ±axis 1 (energy above the saddle's) and ±axis 3,
    each brightening toward its axis."""
    inv = 1 / inertia
    e = (n**2 @ inv - inv[2]) / (inv[0] - inv[2])  # 0 at axis 3, 1 at axis 1
    saddle = (inv[1] - inv[2]) / (inv[0] - inv[2])
    upper = (e > saddle)[:, None]
    depth = np.where(upper, e[:, None] - saddle, saddle - e[:, None])
    depth /= np.where(upper, 1 - saddle, saddle)
    hue = np.where(upper, m.ManimColor(AXIS1).to_rgb(), m.ManimColor(AXIS3).to_rgb())
    return np.hstack([hue * (0.45 + 0.55 * depth**0.6), np.full((len(n), 1), alpha)])


def rgba(color: str, alpha: float) -> np.ndarray:
    return np.array([*m.ManimColor(color).to_rgb(), alpha])


class Globe(m.Group):
    """Glass with things inside and on it: a mesh a part, each shown with its points and colors
    of the moment (what shows through the glass is the engine's to composite)."""

    def __init__(self, parts: list[tuple[np.ndarray, np.ndarray, np.ndarray]]) -> None:
        self.base = [verts for verts, _, _ in parts]
        self.tint = [np.broadcast_to(c, (len(v), 4)) for v, _, c in parts]
        super().__init__(
            *(m.MeshMobject(v, tris, shade_in_3d=True) for v, tris, _ in parts)
        )

    def show(self, points: list[np.ndarray], colors: list[np.ndarray]) -> None:
        for part, p, c in zip(self.submobjects, points, colors, strict=True):
            part.points = p
            part.paint = part.paint.but(fill=c)


def project(camera: m.Camera, point: np.ndarray) -> np.ndarray:
    """Where a 3D point lands on the screen, in frame coordinates (for HUD labels)."""
    turn = camera_axes(camera.get_phi(), camera.get_theta(), camera.get_gamma())
    p = turn @ (point - camera.frame_center)
    depth = 1 - p[2] / camera.get_focal_distance()
    return np.array([*(camera.get_zoom() * p[:2] / depth), 0.0])


class TennisRacket(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(
            phi=70 * m.DEGREES, theta=-90 * m.DEGREES, zoom=1.12, focal_distance=30
        )
        com, inertia = moments()

        # the motion, once: three handles spun about axes 1, 2, 3 with the same wobble
        omega, turn = simulate(inertia, SPIN * (WOBBLE + (1 - WOBBLE) * np.eye(3)))
        spin_l = omega * inertia  # L in each body frame, (n, 3, 3)
        hints = np.eye(3)[[1, 0, 0]]  # the body axis that starts along +x
        units = spin_l[0] / np.linalg.norm(spin_l[0], axis=1, keepdims=True)
        start = np.array([toward_z(units[k], hints[k]) for k in range(3)])
        world = np.einsum("kij,nkjl->nkil", start, turn)  # L stays along +z
        stem_up = world[:, 1, 2, 1]  # the height of handle 2's stem axis
        flips = np.flatnonzero(np.diff(np.sign(stem_up))) / RATE
        seen = spin_l[:, 1] / np.linalg.norm(spin_l[:, 1], axis=1, keepdims=True)

        spots = [np.array([x, 0.0, -0.25]) for x in (-4.1, 0.0, 4.1)]
        handles = [m.Group(*handle_parts(com)) for _ in spots]
        rigs = [Rigid(h) for h in handles]
        axes = [
            mesh(revolve(arrow(3.6, 0.02, 0.32, 0.085)) + p + [0, 0, -1.75], GOLD)
            for p in spots
        ]
        slide = m.ValueTracker(0.0)  # handle 2 moving to the left
        goal = np.array([-3.5, 0.0, -0.25])
        clock = [0.0]

        def now() -> int:
            return min(round(clock[0] * RATE), len(world) - 1)

        def advance(mob: m.Mobject, dt: float) -> None:
            clock[0] += dt
            for k, rig in enumerate(rigs):
                moved = slide.get_value() * (goal - spots[1]) if k == 1 else 0
                rig.pose(world[now(), k], spots[k] + moved)

        driver = m.Mobject().add_updater(advance)
        advance(driver, 0)
        self.add(driver, *handles, *axes)

        # the handle's own frame: a glass globe of the directions of L, seen from between
        # its axes (closest to axis 2, which points up)
        center, radius = np.array([2.75, 0.0, -0.55]), 2.45
        cam = camera_axes(
            70 * m.DEGREES, -90 * m.DEGREES, 0
        )  # rows: right, up, toward us
        eye = np.array([0.15, 1.3, 1.0]) / np.linalg.norm([0.15, 1.3, 1.0])
        up = np.eye(3)[1] - eye[1] * eye
        up /= np.linalg.norm(up)
        screen = np.array([cam[2], cam[1], np.cross(cam[2], cam[1])]).T
        display = screen @ np.array([eye, up, np.cross(eye, up)])  # body → world
        sphere, sphere_tris = surface(revolve(ball(1.0, 36), 72))
        parts = [(sphere @ display.T, sphere_tris, panel_colors(sphere, inertia, 0.4))]
        curves = polhodes(inertia)
        for k, curve in enumerate(curves):  # the last two: the separatrix
            wide, sides, color = (
                (0.016, 6, "#ffffff") if k > 7 else (0.008, 4, "#cfe0ff")
            )
            ring = tube(curve @ display.T, wide / radius, sides)
            parts.append((*surface(ring), rgba(color, 0.9 if k > 7 else 0.45)))
        for part in handle_parts(com):  # the handle at rest in its own frame
            small = part.points @ display.T * 0.6 / radius
            parts.append((small, part.triangles, part.paint.fill[0]))
        first = round((flips[1] + 1.2) * RATE)  # L's path from when the globe appears
        trail = surface(tube(seen[first::2] @ display.T * 1.012, 0.018 / radius, 6))
        parts.append((*trail, rgba(GOLD, 0.0)))
        trail_age = np.repeat(np.arange(first, len(seen), 2), 7) / RATE
        pointer = surface(revolve(arrow(1.0, 0.012, 0.09, 0.03), 12))
        parts.append((*pointer, rgba(GOLD, 1.0)))
        head = surface(revolve(ball(0.035, 10), 14))
        parts.append((*head, rgba("#fff6d5", 1.0)))
        globe = Globe(parts)
        appear = m.ValueTracker(0.0)

        def refresh(mob: m.Mobject) -> None:
            i = now()
            d = seen[i] @ display.T
            points = [
                *globe.base[:-2],
                pointer[0] @ toward_z(d, np.array([0.3, 0.5, 0.8])),
                head[0] + 1.012 * d,
            ]
            colors = [np.array(c) for c in globe.tint]
            age = i / RATE - trail_age  # a comet, fading to a lasting trace
            colors[-3][:, 3] = (age >= 0) * np.maximum(1 - age / 1.2, 0.3)
            for c in colors:
                c[:, 3] *= appear.get_value()
            grow = 0.85 + 0.15 * appear.get_value()
            globe.show([center + radius * grow * p for p in points], colors)

        globe.add_updater(refresh)
        refresh(globe)

        # heads-up display
        title = m.Text("Why a spinning handle flips", font_size=36).to_corner(m.UL)
        subtitle = m.Text(
            "one T-handle, spun about each of its three principal axes", font_size=22
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)
        subtitle2 = m.Text(
            "seen from the handle, L slides along curves of equal energy", font_size=22
        ).set_color(m.GREY_B)
        subtitle2.move_to(subtitle, aligned_edge=m.LEFT)
        labels, verdicts, ells = [], [], []
        words = [("steady", m.GREY_B), ("flips", CORAL), ("steady", m.GREY_B)]
        for k, spot in enumerate(spots):
            ratio = inertia[k] / inertia[1]
            label = m.MathTex(rf"I_{k + 1} = {ratio:.2f}", font_size=34)
            labels.append(label.move_to(project(self.camera, spot) + 2.3 * m.DOWN))
            verdict = m.Text(words[k][0], font_size=26).set_color(words[k][1])
            verdicts.append(verdict.next_to(label, m.DOWN, buff=0.18))
            tip = project(self.camera, spot + [0, 0, 1.75]) + [0.3, -0.1, 0]
            ells.append(m.MathTex("L", font_size=34, color=GOLD).move_to(tip))
        l_globe = m.MathTex("L", font_size=34, color=GOLD)

        def follow(mob: m.Mobject) -> None:
            d = seen[now()] @ display.T
            mob.move_to(project(self.camera, center + radius * d) + [0.28, 0.12, 0])
            mob.set_opacity(appear.get_value())

        l_globe.add_updater(follow)
        sphere_law = m.MathTex(r"L_1^2 + L_2^2 + L_3^2 = L^2", font_size=32)
        energy_law = m.MathTex(
            r"\frac{L_1^2}{I_1} + \frac{L_2^2}{I_2} + \frac{L_3^2}{I_3} = 2E",
            font_size=32,
        )
        laws = m.VGroup(sphere_law, energy_law).arrange(m.DOWN, aligned_edge=m.RIGHT)
        laws.to_corner(m.UR)
        closing = m.Text(
            "The middle axis is a saddle: the slightest wobble grows into a flip.",
            font_size=26,
        ).to_edge(m.DOWN, buff=0.3)
        saddle_at = project(self.camera, center + radius * (display @ np.eye(3)[1]))
        saddle = m.Text("saddle", font_size=26).move_to(saddle_at + [-1.9, 1.05, 0])
        pin = m.Line(
            saddle.get_right() + [0.08, -0.08, 0], saddle_at + [-0.12, 0.08, 0]
        )
        pin.set_stroke(m.WHITE, 2)
        hud = [subtitle, subtitle2, *labels, *verdicts, *ells, l_globe, laws, closing]
        hud += [saddle, pin]
        self.add_fixed_in_frame_mobjects(title, *hud)
        self.remove(*hud)

        # 0–9 s: three spins, one of which keeps turning over
        self.play(*[m.FadeIn(mob) for mob in [subtitle, *labels, *ells]], run_time=1.5)
        self.wait(flips[0] + 1.3 - self.time)
        self.play(*[m.FadeIn(v, shift=0.1 * m.UP) for v in verdicts], run_time=1)
        self.wait(flips[1] + 1.2 - self.time)

        # 9–12 s: the flipping one, next to the same motion seen from the handle itself
        steady: list[m.Mobject] = [handles[0], handles[2], subtitle]
        steady += [group[k] for group in (axes, labels, verdicts, ells) for k in (0, 2)]
        self.play(*[m.FadeOut(mob) for mob in steady], run_time=0.8)
        self.add(globe, l_globe)
        moved = project(self.camera, goal)[0] - project(self.camera, spots[1])[0]
        self.play(
            axes[1].animate.shift(goal - spots[1]),
            *[
                mob.animate.shift(moved * m.RIGHT)
                for mob in (labels[1], verdicts[1], ells[1])
            ],
            slide.animate.set_value(1.0),
            appear.animate.set_value(1.0),
            m.FadeIn(subtitle2),
            m.FadeIn(laws),
            run_time=1.8,
        )
        # 12–27 s: every flip is L running along the separatrix, from saddle to saddle
        self.wait(flips[3] + 0.8 - self.time)
        self.play(m.FadeIn(saddle), m.Create(pin), run_time=1)
        self.wait(flips[5] + 0.5 - self.time)
        self.play(
            m.FadeIn(closing, shift=0.15 * m.UP),
            m.FadeOut(labels[1]),
            m.FadeOut(verdicts[1]),
            run_time=1.2,
        )
        self.wait(1.8)


if __name__ == "__main__":
    TennisRacket().render("tennis_racket.mp4")

"""A magnetic bottle around the Earth: how the Van Allen belts trap particles.

A charged particle in the Earth's dipole field does three things at once. It gyrates around a
field line. It slides along the line toward a pole until the growing field turns it back: its
magnetic moment μ = m v⊥²/2B stays constant while its speed cannot change, so it runs out of
parallel speed exactly where B = B_eq / sin²α (α: its pitch angle at the equator) — and bounces
to the other hemisphere and back. And it drifts slowly around the planet: protons west, electrons
east. The drift paints a doughnut-shaped shell, a radiation belt. Particles whose pitch angle is
too small (the loss cone) reach the atmosphere before they can turn, and rain down near the poles.
The motion is integrated exactly (Boris pusher); the time scales are stretched for visibility.
"""

import functools
import math

import numpy as np

import manimgx as m

K = 1500.0  # the dipole's strength, charge-to-mass ratio folded in: gyrofrequency K / r³ at the equator
SPEED = 5.0  # every particle's speed, Earth radii per second
DT = 1 / 540  # integration step: 9 steps per tick of the 60 Hz simulation clock
STEPS = 9
MOMENT = np.array([0.0, 0.0, -1.0])  # the Earth's dipole points south
PITCH = 30.0  # the first proton's equatorial pitch angle, degrees
ORANGE, CYAN = np.array([1.0, 0.68, 0.25]), np.array([0.35, 0.85, 1.0])


def field(x: np.ndarray, sign: np.ndarray) -> np.ndarray:
    """(charge sign) × the dipole field at points x (rows): each particle's rotation vector Ω."""
    r2 = (x * x).sum(-1, keepdims=True)
    r = np.sqrt(r2)
    rhat = x / r
    return sign[:, None] * K * (3 * (rhat @ MOMENT)[:, None] * rhat - MOMENT) / (r2 * r)


def field_at(x: float, y: float, z: float, qk: float) -> tuple[float, float, float]:
    """`field` at one point for charge sign × K = qk, in plain floats and operation for
    operation (so to the bit): numpy's per-call overhead would dwarf the arithmetic of three
    numbers."""
    r2 = x * x + y * y + z * z
    r = math.sqrt(r2)
    x, y, z = x / r, y / r, z / r
    c = -3 * z  # 3 (r̂ · m), with m = MOMENT = −ẑ
    d = r2 * r
    return qk * (c * x) / d, qk * (c * y) / d, qk * (c * z + 1) / d


def boris(particles: list[list[float]]) -> None:
    """A step of DT in a pure magnetic field (the Boris rotation: speed is conserved exactly),
    split so that no particle turns more than 0.25 rad per substep — near the planet, where
    the field is hundreds of times stronger, the gyration stays resolved. Each particle is
    [x, y, z, vx, vy, vz, sign × K], stepped in place."""
    omegas = [field_at(p[0], p[1], p[2], p[6]) for p in particles]
    fastest = math.sqrt(max(a * a + b * b + c * c for a, b, c in omegas))
    parts = max(1, math.ceil(fastest * DT / 0.25))
    h = DT / parts
    for p, (o0, o1, o2) in zip(particles, omegas, strict=True):
        x0, x1, x2, v0, v1, v2, qk = p
        for part in range(parts):
            if part:  # the first substep's field is the one just measured
                o0, o1, o2 = field_at(x0, x1, x2, qk)
            t0, t1, t2 = 0.5 * h * o0, 0.5 * h * o1, 0.5 * h * o2
            q = 1 + (t0 * t0 + t1 * t1 + t2 * t2)
            s0, s1, s2 = 2 * t0 / q, 2 * t1 / q, 2 * t2 / q
            u0 = v0 + (v1 * t2 - v2 * t1)  # u = v + v × t, then v += u × s
            u1 = v1 + (v2 * t0 - v0 * t2)
            u2 = v2 + (v0 * t1 - v1 * t0)
            v0 += u1 * s2 - u2 * s1
            v1 += u2 * s0 - u0 * s2
            v2 += u0 * s1 - u1 * s0
            x0 += h * v0
            x1 += h * v1
            x2 += h * v2
        p[:6] = x0, x1, x2, v0, v1, v2


def fly(
    x: np.ndarray, v: np.ndarray, sign: np.ndarray, steps: int, every: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """`steps` Boris steps of the particles (rows): their final positions and velocities, and
    both after every `every`-th step from the first (a row per particle per sample)."""
    particles = [
        [*p, *u, s * K]
        for p, u, s in zip(x.tolist(), v.tolist(), sign.tolist(), strict=True)
    ]
    seen: list[list[float]] = []
    for step in range(steps):
        boris(particles)
        if step % every == 0:
            seen += [p[:6] for p in particles]
    final, states = np.array(particles)[:, :6], np.array(seen)
    return final[:, :3], final[:, 3:], states[:, :3], states[:, 3:]


def guiding_center(x: np.ndarray, v: np.ndarray, sign: np.ndarray) -> np.ndarray:
    """The center of each particle's gyration: x + (v × Ω) / Ω²."""
    omega = field(x, sign)
    return x + np.cross(v, omega) / (omega * omega).sum(-1, keepdims=True)


def launch(
    L: np.ndarray,
    pitch: np.ndarray,
    azimuth: np.ndarray,
    sign: np.ndarray,
    speed: np.ndarray | float = SPEED,
) -> tuple[np.ndarray, np.ndarray]:
    """Particles whose gyration centers sit at the equator of the field line L, with the given
    equatorial pitch angles (the field is vertical there)."""
    center = np.stack([L * np.cos(azimuth), L * np.sin(azimuth), np.zeros_like(L)], 1)
    around = np.stack([-np.sin(azimuth), np.cos(azimuth), np.zeros_like(L)], 1)
    direction = np.sin(pitch)[:, None] * around + np.cos(pitch)[:, None] * np.array(
        [0.0, 0.0, 1.0]
    )
    v = np.reshape(speed, (-1, 1)) * direction
    return center - (guiding_center(center, v, sign) - center), v


def field_line(L: float, azimuth: float, count: int = 160) -> np.ndarray:
    """The dipole field line r = L cos²λ in the meridian at `azimuth`, above the surface."""
    top = np.arccos(np.sqrt(1 / L))
    lat = np.linspace(-top, top, count)
    r = L * np.cos(lat) ** 2
    return np.stack(
        [
            r * np.cos(lat) * np.cos(azimuth),
            r * np.cos(lat) * np.sin(azimuth),
            r * np.sin(lat),
        ],
        1,
    )


def tube(
    points: np.ndarray, radius: np.ndarray, sides: int = 8
) -> tuple[np.ndarray, np.ndarray]:
    """A tube along a polyline with a radius per point (parallel-transport frames)."""
    tangent = np.gradient(points, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-12
    seed = np.cross(tangent[0], [0.3, 0.5, 0.8])
    n0, n1, n2 = (seed / np.linalg.norm(seed)).tolist()
    normals = [n0, n1, n2]
    for t0, t1, t2 in tangent[1:].tolist():  # plain floats: one short step per point
        d = n0 * t0 + n1 * t1 + n2 * t2
        n0, n1, n2 = n0 - d * t0, n1 - d * t1, n2 - d * t2
        norm = math.sqrt(n0 * n0 + n1 * n1 + n2 * n2) + 1e-12
        n0, n1, n2 = n0 / norm, n1 / norm, n2 / norm
        normals += n0, n1, n2
    n_ = np.array(normals).reshape(-1, 3)
    b_ = np.cross(tangent, n_)
    a = np.linspace(0, m.TAU, sides, endpoint=False)
    ring = (
        np.cos(a)[None, :, None] * n_[:, None] + np.sin(a)[None, :, None] * b_[:, None]
    )
    verts = (points[:, None] + radius[:, None, None] * ring).reshape(-1, 3)
    return verts, tube_triangles(len(points), sides)


@functools.lru_cache(maxsize=1)
def tube_triangles(rings: int, sides: int) -> np.ndarray:
    """A tube's triangles, two per side between neighboring rings: the same for every tube
    of its size (kept, read-only, while a trail's length holds)."""
    i = np.arange(rings - 1)[:, None]
    j = np.arange(sides)[None, :]
    k = (j + 1) % sides
    tris = np.stack(
        [
            np.stack([i * sides + j, (i + 1) * sides + j, (i + 1) * sides + k], -1),
            np.stack([i * sides + j, (i + 1) * sides + k, i * sides + k], -1),
        ],
        2,
    ).reshape(-1, 3)
    tris.flags.writeable = False
    return tris


@functools.lru_cache(maxsize=1)
def trail_look(samples: int) -> tuple[np.ndarray, np.ndarray]:
    """A trail's radius per sample and color per vertex, fading toward its oldest end: the
    same for every trail of its length (kept while the length holds)."""
    fade = np.linspace(0, 1, samples)
    rows = np.ones((samples * 8, 4))
    rows[:, :3] = ORANGE
    rows[:, 3] = np.repeat(0.15 + 0.85 * fade, 8)
    return 0.004 + 0.016 * fade, rows


def globe_colors(points: np.ndarray) -> np.ndarray:
    """A deep-blue planet, a little lighter toward the equator."""
    z = points[:, 2] / np.linalg.norm(points, axis=1)
    rows = np.ones((len(points), 4))
    rows[:, :3] = np.array([0.05, 0.16, 0.38]) + 0.12 * (1 - np.abs(z))[
        :, None
    ] * np.array([0.3, 0.6, 1.0])
    return rows


class Proton:
    """The first particle: its state, and the trail it leaves (its path, or in fast time its
    guiding center)."""

    def __init__(self) -> None:
        sign = np.ones(1)
        self.sign = sign
        self.x, self.v = launch(
            np.array([3.0]), np.radians([PITCH]), np.array([-0.35]), sign
        )
        self.samples: np.ndarray = self.x.copy()
        self.speedup = 1
        self.keep = 1400

    def advance(self) -> None:
        fast = self.speedup > 1
        self.x, self.v, xs, vs = fly(
            self.x, self.v, self.sign, STEPS * self.speedup, STEPS if fast else 1
        )
        new = guiding_center(xs, vs, self.sign.repeat(len(xs))) if fast else xs
        self.samples = np.concatenate([self.samples, new])[-self.keep :]


def unit_sphere(nu: int, nv: int) -> m.MeshMobject:
    """A smooth lit unit sphere over an (nu + 1) × (nv + 1) grid of longitude u ∈ [0, 2π] and
    colatitude v ∈ [0, π] (vertex i·(nv + 1) + j), each cell two triangles."""
    u, v = np.meshgrid(
        np.linspace(0, m.TAU, nu + 1), np.linspace(0, m.PI, nv + 1), indexing="ij"
    )
    points = np.stack([np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), np.cos(v)], -1)
    idx = np.arange((nu + 1) * (nv + 1)).reshape(nu + 1, nv + 1)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    cells = np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], 2)
    return m.MeshMobject(points.reshape(-1, 3), cells.reshape(-1, 3), shade_in_3d=True)


class VanAllen(m.ThreeDScene):
    def construct(self) -> None:
        rng = np.random.default_rng(1958)
        globe = unit_sphere(96, 48)
        globe.paint = globe.paint.but(fill=globe_colors(globe.points))
        lines = m.VGroup(
            *[
                m.VMobject(
                    stroke_color="#8fb8ff",
                    stroke_width=1.2,
                    stroke_opacity=0.3,
                    shade_in_3d=True,
                ).set_points_smoothly(field_line(L, a))
                for L in (2.0, 3.0, 4.4)
                for a in np.linspace(0, m.TAU, 8, endpoint=False)
            ]
        )

        proton = Proton()
        dot = m.Dot3D(proton.x[0], radius=0.06, color=m.WHITE)
        trail = m.MeshMobject(
            *tube(
                np.array([[3.0, 0, 0], [3.0, 0.001, 0], [3.0, 0.002, 0]]),
                np.full(3, 0.01),
            ),
            shade_in_3d=True,
        )

        def advance(_: m.Mobject, dt: float) -> None:
            proton.advance()

        def draw(_: m.Mobject) -> None:
            dot.move_to(proton.x[0])
            points = proton.samples
            if len(points) > 2:
                radius, rows = trail_look(len(points))
                trail.points, trail.triangles = tube(points, radius)
                trail.paint = trail.paint.but(fill=rows)

        driver = m.Mobject()
        driver.add_updater(advance)
        driver.add_updater(draw)

        b_eq = float(np.linalg.norm(field(np.array([[3.0, 0.0, 0.0]]), np.ones(1))))
        b_value = m.DecimalNumber(1.0, num_decimal_places=2, font_size=30)
        b_value.add_updater(
            lambda d: d.set_value(
                float(
                    np.linalg.norm(
                        field(
                            guiding_center(proton.x, proton.v, proton.sign), np.ones(1)
                        )
                    )
                )
                / b_eq
            )
        )
        mirror = 1 / np.sin(np.radians(PITCH)) ** 2
        readout = (
            m.VGroup(
                m.VGroup(
                    m.MathTex(r"B / B_{\text{eq}} =", font_size=30), b_value
                ).arrange(m.RIGHT, buff=0.15),
                m.MathTex(
                    rf"\text{{it turns back at }} 1/\sin^2\alpha = {mirror:.2f}",
                    font_size=28,
                ).set_color(m.GREY_A),
            )
            .arrange(m.DOWN, aligned_edge=m.LEFT)
            .to_corner(m.UR)
        )
        law = m.MathTex(
            r"\mu = \frac{m v_\perp^2}{2B} = \text{const},\quad v = \text{const}",
            font_size=30,
        ).to_corner(m.DL)

        title = m.Text("A magnetic bottle around the Earth", font_size=36).to_corner(
            m.UL
        )
        subtitle = m.Text(
            "gyrate, bounce, drift: how the radiation belts trap particles",
            font_size=22,
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )
        self.add_fixed_in_frame_mobjects(title, subtitle, readout, law)
        self.remove(readout, law)

        # 0–10 s: close to one proton: it gyrates, slides toward a pole, turns back, bounces
        self.set_camera_orientation(
            phi=76 * m.DEGREES,
            theta=-112 * m.DEGREES,
            zoom=1.55,
            frame_center=np.array([2.2, -1.0, 0.1]),
        )
        self.add(globe, lines, driver, trail, dot)
        self.play(m.FadeIn(readout), m.FadeIn(law), run_time=1.2)
        self.wait(5.3)
        self.move_camera(
            phi=64 * m.DEGREES,
            theta=-80 * m.DEGREES,
            zoom=1.0,
            frame_center=np.array([0.8, 0.0, 0.0]),
            run_time=3.5,
        )

        # 10–18 s: time × 12: the bounce and the slow drift wrap a shell around the planet
        fast = m.Text(
            "time × 12 (the trail follows the gyration's center)", font_size=24
        ).set_color(m.YELLOW)
        fast.next_to(subtitle, m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        self.add_fixed_in_frame_mobjects(fast)
        self.remove(fast)
        proton.speedup, proton.keep = 12, 4000
        proton.samples = guiding_center(proton.x, proton.v, proton.sign)
        self.play(m.FadeOut(readout), m.FadeOut(law), m.FadeIn(fast), run_time=1)
        self.begin_ambient_camera_rotation(rate=0.07)
        self.move_camera(
            phi=56 * m.DEGREES, zoom=0.92, frame_center=np.zeros(3), run_time=7
        )

        # 18–30 s: time × 30. An inner-belt proton and an outer-belt electron weave shells of their
        # own, drifting opposite ways; electrons knocked into the loss cone off the equator (as
        # waves do) stream down their field lines into the atmosphere, near the poles
        GREEN = np.array([0.45, 1.0, 0.55])
        proton.speedup, proton.keep = 30, 5000
        belts = [(2.0, 60.0, 1.2, 1.0, 5.0, ORANGE), (4.2, 55.0, 2.6, -1.0, 2.6, CYAN)]
        L = np.array([b_[0] for b_ in belts])
        xs, vs = launch(
            L,
            np.radians([b_[1] for b_ in belts]),
            np.array([b_[2] for b_ in belts]),
            np.array([b_[3] for b_ in belts]),
            np.array([b_[4] for b_ in belts]),
        )
        # the rain: a latitude of ±25° on lines L = 5 … 6, heading down the line, pitch 2° (inside
        # the local loss cone, ~5°), released one after another
        rain_count = 64
        rain_L = rng.uniform(5.0, 6.0, rain_count)
        hemisphere = np.where(np.arange(rain_count) % 2 == 0, 1.0, -1.0)
        lat0 = np.radians(25.0) * hemisphere
        azim = rng.uniform(0, m.TAU, rain_count)
        r0 = rain_L * np.cos(lat0) ** 2
        start = np.stack(
            [
                r0 * np.cos(lat0) * np.cos(azim),
                r0 * np.cos(lat0) * np.sin(azim),
                r0 * np.sin(lat0),
            ],
            1,
        )
        b_hat = field(start, np.ones(rain_count))
        b_hat /= np.linalg.norm(b_hat, axis=1, keepdims=True)
        b_hat *= -np.sign((b_hat * start).sum(1))[:, None]  # along the line, inward
        side = np.cross(b_hat, np.array([0.0, 0.0, 1.0]))
        side /= np.linalg.norm(side, axis=1, keepdims=True)
        tilt = np.radians(2.0)
        rain_v = 1.2 * (np.cos(tilt) * b_hat + np.sin(tilt) * side)
        swarm_x = np.concatenate([xs, start])
        swarm_v = np.concatenate([vs, rain_v])
        sign = np.array([b_[3] for b_ in belts] + [-1.0] * rain_count)
        count = len(sign)
        release = np.concatenate(
            [np.zeros(len(belts), int), np.sort(rng.integers(0, 480, rain_count))]
        )
        alive = np.ones(count, bool)
        landed_at = np.full(
            count, -1
        )  # the tick each rain electron reached the atmosphere
        clock = {"tick": 0}
        tracks: list[list[np.ndarray]] = [[swarm_x[k]] for k in range(count)]
        colors = [b_[5] for b_ in belts] + [GREEN] * rain_count
        strands = [
            m.VMobject(
                stroke_color=m.ManimColor(c),
                stroke_width=2.4 if k < len(belts) else 2.0,
                stroke_opacity=0.9,
                shade_in_3d=True,
            )
            for k, c in enumerate(colors)
        ]
        paths = m.VGroup(*strands)
        landed = m.Group()

        def weave(_: m.Mobject, dt: float) -> None:
            clock["tick"] += 1
            idx = np.flatnonzero(alive & (release <= clock["tick"]))
            if not len(idx):
                return
            x, v, xs, vs = fly(swarm_x[idx], swarm_v[idx], sign[idx], STEPS * 30, 15)
            centers = guiding_center(xs, vs, np.tile(sign[idx], len(xs) // len(idx)))
            for j, k in enumerate(idx):
                tracks[k].extend(centers[j :: len(idx)])
            swarm_x[idx], swarm_v[idx] = x, v
            for j, k in enumerate(idx):
                if np.linalg.norm(x[j]) < 1.03:  # it reached the atmosphere
                    alive[k] = False
                    landed_at[k] = clock["tick"]
                    spot = 1.012 * x[j] / np.linalg.norm(x[j])
                    landed.add(m.Dot3D(spot, radius=0.05, color=m.ManimColor(GREEN)))

        def redraw(_: m.Mobject) -> None:
            for k, (path, track) in enumerate(zip(strands, tracks, strict=True)):
                if k < len(belts):
                    if len(track) > 1:
                        path.set_points_as_corners(np.array(track[-3000:]))
                    continue
                # a rain electron: a bright streak down its line, fading once it has landed
                since = clock["tick"] - landed_at[k] if landed_at[k] >= 0 else 0
                if release[k] <= clock["tick"] and len(track) > 1 and since < 24:
                    path.set_points_as_corners(np.array(track[-160:]))
                    path.set_stroke(opacity=0.95 * (1 - since / 24))
                elif path.has_points():
                    path.set_stroke(opacity=0.0)

        weaver = m.Mobject()
        weaver.add_updater(weave)
        weaver.add_updater(redraw)
        outer_lines = m.VGroup(
            *[
                m.VMobject(
                    stroke_color="#8fb8ff",
                    stroke_width=1.0,
                    stroke_opacity=0.22,
                    shade_in_3d=True,
                ).set_points_smoothly(field_line(5.6, a_))
                for a_ in np.linspace(0, m.TAU, 8, endpoint=False)
            ]
        )
        legend = (
            m.VGroup(
                m.VGroup(
                    m.Dot(color=m.ManimColor(ORANGE)),
                    m.Text("protons drift west", font_size=22),
                ).arrange(m.RIGHT, buff=0.15),
                m.VGroup(
                    m.Dot(color=m.ManimColor(CYAN)),
                    m.Text("electrons drift east", font_size=22),
                ).arrange(m.RIGHT, buff=0.15),
                m.VGroup(
                    m.Dot(color=m.ManimColor(GREEN)),
                    m.Text("in the loss cone: down into the atmosphere", font_size=22),
                ).arrange(m.RIGHT, buff=0.15),
            )
            .arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.15)
            .to_corner(m.DL)
        )
        faster = (
            m.Text("time × 30", font_size=24)
            .set_color(m.YELLOW)
            .next_to(subtitle, m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        )
        self.add_fixed_in_frame_mobjects(legend, faster)
        self.remove(legend, faster)
        self.add(weaver, paths, landed)
        self.play(
            m.FadeOut(fast),
            m.FadeIn(faster),
            m.FadeIn(legend),
            m.FadeIn(outer_lines),
            dot.animate.set_opacity(0),
            run_time=1.5,
        )
        self.move_camera(phi=64 * m.DEGREES, zoom=0.8, run_time=5.5)
        self.move_camera(phi=46 * m.DEGREES, zoom=0.86, run_time=5)


if __name__ == "__main__":
    VanAllen().render("van_allen.mp4")

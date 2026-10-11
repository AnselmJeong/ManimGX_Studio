"""The dance of a spinning top: it does not fall, it precesses and nods.

A symmetric top pinned at its tip, L = ½I₁(θ̇² + φ̇² sin²θ) + ½I₃(ψ̇ + φ̇ cos θ)² − Mgl cos θ.
Its spin p_ψ = I₃ω₃, its vertical angular momentum p_φ and its energy are conserved, so θ
moves in the effective potential V(θ) = (p_φ − p_ψ cos θ)²/(2I₁ sin²θ) + Mgl cos θ and nods
between two turning points, while φ̇ = (p_φ − p_ψ cos θ)/(I₁ sin²θ) carries it around. Three
identical tops tilted 32° and spun alike are let go at rest, pushed backward and pushed
forward: the tip of each axis writes cusps, loops or waves on a glass sphere between its
two bounding circles. Integrated with RK4; moments computed from the drawn top.
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


TILT = 32 * m.DEGREES  # every top starts here, θ̇ = 0
SPIN = 2.2 * m.TAU  # ω₃, rad/s
MGL = 4.979  # gravity × height of the center of mass, per unit mass: tuned so the top
# let go at rest draws exactly four cusps a turn (and the one pushed back five loops)
PUSHES = (0.0, -1.362, 0.4)  # initial φ̇ in units of the steady precession rate
RATE, SUBSTEPS, DURATION = 60, 10, 31.0
CONE_H, CONE_R, DISK_Z, DISK_R, DISK_T = 0.75, 0.32, 0.9, 0.95, 0.22
PEN, SPINDLE_R, KNOB_R = 1.8, 0.05, 0.08  # the spindle's knob writes on the glass
GLASS_R, SKIRT = 1.9, 0.62  # a bell jar: a glass dome over the tip and a short wall
GOLD, CORAL, TEAL = "#f4c95d", "#ef6f6c", "#2ec4b6"


def moments() -> tuple[float, float]:
    """I₁ (about a transverse axis through the tip) and I₃ (about the spin axis), per unit
    density: a cone from the tip, a disk and a spindle."""
    cone = np.pi * CONE_R**2 * CONE_H / 3
    disk = np.pi * DISK_R**2 * DISK_T
    spindle = np.pi * SPINDLE_R**2 * (PEN - DISK_Z)
    knob = 4 / 3 * np.pi * KNOB_R**3
    i3 = 0.3 * cone * CONE_R**2 + 0.5 * disk * DISK_R**2 + 0.5 * spindle * SPINDLE_R**2
    i3 += 0.4 * knob * KNOB_R**2
    i1 = cone * (3 / 20 * CONE_R**2 + 3 / 5 * CONE_H**2)  # a cone about its apex
    i1 += disk * ((3 * DISK_R**2 + DISK_T**2) / 12 + DISK_Z**2)
    mid, length = (PEN + DISK_Z) / 2, PEN - DISK_Z
    i1 += spindle * ((3 * SPINDLE_R**2 + length**2) / 12 + mid**2)
    i1 += knob * (0.4 * KNOB_R**2 + PEN**2)
    mass = cone + disk + spindle + knob  # MGL = gravity × mass × height: one parameter
    return i1 / mass, i3 / mass


def simulate(i1: float, i3: float, push: float) -> tuple[np.ndarray, np.ndarray]:
    """Euler angles (θ, φ, ψ) at RATE samples a second after the release, and the effective
    potential's parameter p_φ, for a top let go at TILT with φ̇ = push."""
    p_psi = i3 * SPIN
    p_phi = i1 * push * np.sin(TILT) ** 2 + p_psi * np.cos(TILT)

    def deriv(s: np.ndarray) -> np.ndarray:
        th, thd = s[0], s[1]
        phd = (p_phi - p_psi * np.cos(th)) / (i1 * np.sin(th) ** 2)
        torque = phd * np.cos(th) * phd - p_psi / i1 * phd + MGL / i1
        return np.array([thd, torque * np.sin(th), phd, p_psi / i3 - phd * np.cos(th)])

    h = 1 / (RATE * SUBSTEPS)
    s = np.array([TILT, 0.0, 0.0, 0.0])
    samples = [s]
    for step in range(1, int(DURATION * RATE) * SUBSTEPS + 1):
        k1 = deriv(s)
        k2 = deriv(s + h / 2 * k1)
        k3 = deriv(s + h / 2 * k2)
        s = s + h / 6 * (k1 + 2 * k2 + 2 * k3 + deriv(s + h * k3))
        if step % SUBSTEPS == 0:
            samples.append(s)
    out = np.array(samples)
    return out[:, [0, 2, 3]], np.array([p_phi, p_psi])


def steady_rate(i1: float, i3: float) -> float:
    """The slow steady precession at TILT: I₁ cos θ φ̇² − p_ψ φ̇ + Mgl = 0."""
    a, b = i1 * np.cos(TILT), i3 * SPIN
    return (b - np.sqrt(b * b - 4 * a * MGL)) / (2 * a)


def euler(th: float, ph: float, ps: float) -> np.ndarray:
    """Body → world for Euler angles z-x-z: R = Rz(φ) Rx(θ) Rz(ψ)."""

    def rz(a: float) -> np.ndarray:
        return np.array(
            [[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]]
        )

    c, s = np.cos(th), np.sin(th)
    return rz(ph) @ np.array([[1, 0, 0], [0, c, -s], [0, s, c]]) @ rz(ps)


# ── smooth lit parts ────────────────────────────────────────────────────────────────────


def revolve(profile: np.ndarray, sides: int = 48) -> np.ndarray:
    """An (rows, sides + 1, 3) grid: profile rows (r, z) swept around the z axis."""
    a = np.linspace(0, m.TAU, sides + 1)
    r, z = profile[:, :1], profile[:, 1:]
    return np.stack([r * np.cos(a), r * np.sin(a), z + 0 * a], -1)


def surface(grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vertices and triangles of an (rows + 1, cols + 1, 3) grid of points."""
    rows, cols = grid.shape[0] - 1, grid.shape[1] - 1
    i, j = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    a = (i * (cols + 1) + j).ravel()
    b, c = a + cols + 1, a + cols + 2
    tris = np.vstack([np.stack([a, b, c], 1), np.stack([a, c, a + 1], 1)])
    return grid.reshape(-1, 3), tris


def tube(points: np.ndarray, radius: float, sides: int = 6) -> np.ndarray:
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


def arc(radius: float, rows: int, start: float, stop: float) -> np.ndarray:
    t = np.linspace(start, stop, rows + 1)[:, None]
    return radius * np.hstack([np.cos(t), np.sin(t)])


def lit(grid: np.ndarray, color: str) -> m.MeshMobject:
    return m.MeshMobject(*surface(grid), shade_in_3d=True, fill_color=color)


def top_parts() -> list[m.MeshMobject]:
    """The top along +z from its tip: a cone, a navy disk with one cream wedge (so the
    spin shows), a spindle and its knob, the pen."""
    bevel = arc(0.05, 4, -np.pi / 2, 0) + [DISK_R - 0.05, DISK_Z - DISK_T / 2 + 0.05]
    rim = np.vstack([bevel, (bevel * [1, -1] + [0, 2 * DISK_Z])[::-1]])
    disk = revolve(np.vstack([[0, rim[0, 1]], rim, [0, rim[-1, 1]]]), 96)
    navy, cream = m.ManimColor("#1d3557").to_rgb(), m.ManimColor("#f1e3c6").to_rgb()
    paint = np.where((np.arange(97) < 13)[:, None], cream, navy)
    rows = np.hstack([np.tile(paint, (len(disk), 1)), np.ones((disk.size // 3, 1))])
    knob = arc(KNOB_R, 10, -np.pi / 2, np.pi / 2) + [0, PEN]
    return [
        lit(revolve(np.array([[0, 0], [CONE_R, CONE_H], [0, CONE_H]])), "#c9ced6"),
        m.MeshMobject(*surface(disk), vertex_colors=rows, shade_in_3d=True),
        lit(revolve(np.array([[SPINDLE_R, DISK_Z], [SPINDLE_R, PEN]]), 24), "#c9ced6"),
        lit(revolve(knob, 24), "#ffffff"),
    ]


class Jar(m.Group):
    """A glass jar and all it holds — its stand, the circles where θ turns, the pen's trace,
    the top: a mesh a part, each shown with its points and colors of the moment (what shows
    through the glass is the engine's to composite). Part 0 is the glass."""

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


def rgba(color: str, alpha: float) -> np.ndarray:
    return np.array([*m.ManimColor(color).to_rgb(), alpha])


def project(camera: m.Camera, point: np.ndarray) -> np.ndarray:
    """Where a 3D point lands on the screen, in frame coordinates (for HUD labels)."""
    turn = camera_axes(camera.get_phi(), camera.get_theta(), camera.get_gamma())
    p = turn @ (point - camera.frame_center)
    depth = 1 - p[2] / camera.get_focal_distance()
    return np.array([*(camera.get_zoom() * p[:2] / depth), 0.0])


def axis_of(angles: np.ndarray) -> np.ndarray:
    """The unit spin axis for Euler angles (θ, φ, …): (sin θ sin φ, −sin θ cos φ, cos θ)."""
    th, ph = angles[..., 0], angles[..., 1]
    return np.stack([np.sin(th) * np.sin(ph), -np.sin(th) * np.cos(ph), np.cos(th)], -1)


class HeavyTop(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(
            phi=60 * m.DEGREES,
            theta=-90 * m.DEGREES,
            zoom=1.55,
            focal_distance=30,
            frame_center=[-2.8, 0, 0.5],
        )
        i1, i3 = moments()
        steady = steady_rate(i1, i3)
        spots = [np.array([x, 0.0, 0.0]) for x in (-4.7, 0.0, 4.7)]
        releases = [0.8, 13.6, 13.6]
        colors = [GOLD, CORAL, TEAL]
        facing = -90 * m.DEGREES  # each top first leans to the left
        motions = [simulate(i1, i3, k * steady) for k in PUSHES]
        clock = [0.0]

        def angles(k: int) -> np.ndarray:
            """(θ, φ, ψ) of top k now: spinning in place until it is let go."""
            after = clock[0] - releases[k]
            if after < 0:
                return np.array([TILT, facing, SPIN * clock[0]])
            th, ph, ps = motions[k][0][min(round(after * RATE), len(motions[k][0]) - 1)]
            return np.array([th, ph + facing, ps + SPIN * releases[k]])

        # each top under a bell jar, its pen writing on the glass between the two circles
        # where θ turns
        pieces = top_parts()
        body = np.vstack([p.points for p in pieces])
        cuts = np.cumsum([len(p.points) for p in pieces])[:-1]  # body → its pieces
        dome = np.vstack([[[GLASS_R, -SKIRT]], arc(GLASS_R, 24, 0, np.pi / 2)])
        glass, glass_tris = surface(revolve(dome, 72))
        rim, floor = GLASS_R + 0.12, -SKIRT
        plate = [[0, floor - 0.1], [rim, floor - 0.1], [rim, floor], [rim, floor]]
        plate += [[r, floor] for r in (1.4, 0.9, 0.45)]
        post = [[0.05, floor], [0.05, -0.06], [0.22, -0.06], [0.22, -0.02], [0, -0.02]]
        stand = np.array(plate + post)
        jars, ages, cycles = [], [], []
        for k, spot in enumerate(spots):
            path = motions[k][0][: round((DURATION - releases[k]) * RATE)]
            turned = np.unwrap(path[:, 1])
            cycles.append(np.argmax(np.abs(turned) >= m.TAU) / RATE)  # one precession
            parts = [(glass + spot, glass_tris, rgba("#9ec9ff", 0.09))]
            parts.append((*surface(revolve(stand, 72) + spot), rgba("#07080b", 1.0)))
            for bound in (path[:, 0].min(), path[:, 0].max()):
                ring = np.stack([np.full(121, bound), np.linspace(0, m.TAU, 121)], -1)
                circle = tube((GLASS_R + 0.016) * axis_of(ring) + spot, 0.012, 4)
                parts.append((*surface(circle), rgba("#aab2c0", 1.0)))
            pen = (GLASS_R + 0.034) * axis_of(path[::2] + [0, facing, 0]) + spot
            parts.append((*surface(tube(pen, 0.03, 8)), rgba(colors[k], 0.0)))
            ages.append(np.repeat(np.arange(len(pen)) * 2 / RATE + releases[k], 9))
            parts += [(p.points, p.triangles, p.paint.fill) for p in pieces]
            jars.append(Jar(parts))
        shown = [m.ValueTracker(1.0), m.ValueTracker(0.0), m.ValueTracker(0.0)]
        rings = m.ValueTracker(0.0)

        def refresh(k: int) -> None:
            jar = jars[k]
            top = np.split(body @ euler(*angles(k)).T + spots[k], cuts)
            points = [*jar.base[: -len(top)], *top]
            colors = [np.array(c) for c in jar.tint]
            trace = colors[-len(top) - 1]
            age = clock[0] - ages[k]
            live = (age >= 0) & (age < cycles[k])  # the last full turn of the pen
            trace[:, :3] *= 1 - 0.55 * np.clip(age / cycles[k], 0, 1)[:, None]
            trace[:, 3] = live
            for circle in colors[2:4]:
                circle[:, 3] *= rings.get_value()
            for c in colors:
                c[:, 3] *= shown[k].get_value()
            jar.show(points, colors)

        for k, jar in enumerate(jars):
            jar.add_updater(lambda mob, k=k: refresh(k))
            refresh(k)

        def advance(mob: m.Mobject, dt: float) -> None:
            clock[0] += dt

        driver = m.Mobject().add_updater(advance)
        self.add(driver, jars[0])

        # heads-up display: the effective potential of the first top, and θ in its well
        p_phi, p_psi = motions[0][1]

        def potential(th: float) -> float:
            well = (p_phi - p_psi * np.cos(th)) ** 2 / (2 * i1 * np.sin(th) ** 2)
            return float(well + MGL * np.cos(th))

        low, high = motions[0][0][:, 0].min(), motions[0][0][:, 0].max()
        level = potential(TILT)
        sweep = np.linspace(20, 70, 501)
        well = np.array([potential(np.radians(d)) for d in sweep])
        depth = level - well.min()
        base, ceiling = well.min() - 0.25 * depth, level + 0.9 * depth
        span = sweep[well <= ceiling]
        left, right = span[0] - 2, span[-1] + 2
        axes = m.Axes(
            x_range=[left, right, 5],
            y_range=[base, ceiling, 1],
            x_length=4.8,
            y_length=2.8,
            tips=False,
            axis_config={"include_ticks": False, "stroke_width": 2, "color": m.GREY_B},
        ).move_to([3.7, -0.9, 0])
        curve = axes.plot(
            lambda d: potential(np.radians(d)),
            x_range=[span[0], span[-1]],
            color=m.WHITE,
        )
        energy = m.DashedLine(axes.c2p(left, level), axes.c2p(right, level))
        energy.set_stroke(GOLD, 2.5)
        marks, names, tags = m.VGroup(), m.VGroup(), m.VGroup()
        for name, bound, off in ((r"\theta_1", low, -0.2), (r"\theta_2", high, 0.2)):
            x = np.degrees(bound)
            marks.add(
                m.DashedLine(axes.c2p(x, level), axes.c2p(x, base), stroke_width=1.5)
            )
            names.add(m.MathTex(name, font_size=30).next_to(axes.c2p(x, base), m.DOWN))
            side = spots[0] + GLASS_R * axis_of(np.array([bound + off, np.pi / 2]))
            tags.add(m.MathTex(name, font_size=30).move_to(project(self.camera, side)))
        v_label = m.MathTex(r"V(\theta)", font_size=30).next_to(axes.y_axis, m.UP, 0.1)
        t_label = m.MathTex(r"\theta", font_size=30).next_to(axes.x_axis, m.RIGHT, 0.1)
        formula = m.MathTex(
            r"V(\theta) = \frac{(p_\phi - p_\psi \cos\theta)^2}{2 I_1 \sin^2\theta}"
            r" + Mgl\cos\theta",
            font_size=30,
        )
        heading = m.VGroup(
            m.Text("effective potential", font_size=22).set_color(m.GREY_B), formula
        ).arrange(m.DOWN, buff=0.18)
        heading.next_to(axes, m.UP, buff=0.55)

        def ball() -> m.VGroup:
            th = angles(0)[0]
            at = axes.c2p(np.degrees(th), level)
            below = axes.c2p(np.degrees(th), potential(th))
            return m.VGroup(m.Line(at, below, color=GOLD), m.Dot(at, 0.07, color=GOLD))

        rider = m.always_redraw(ball)
        frame = [axes, heading, v_label, t_label]
        plot = [*frame, curve, energy, rider, marks, names, tags]

        title = m.Text("The dance of a spinning top", font_size=36).to_corner(m.UL)
        subtitle = m.Text(
            "pinned at its tip, it does not fall: it precesses and nods", font_size=22
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)
        subtitle2 = m.Text(
            "three identical tops, spun and tilted alike, let go three ways",
            font_size=22,
        ).set_color(m.GREY_B)
        subtitle2.move_to(subtitle, aligned_edge=m.LEFT)
        closing = m.Text(
            "None of them falls: each tip stays between its two circles.", font_size=26
        ).to_edge(m.DOWN, buff=0.25)
        captions = m.VGroup()
        for k, (what, how) in enumerate(
            [
                ("cusps", "let go at rest"),
                ("loops", "pushed back"),
                ("waves", "pushed forward"),
            ]
        ):
            word = m.Text(what, font_size=30).set_color(colors[k])
            note = m.Text(how, font_size=22).set_color(m.GREY_B)
            front = spots[k] + [
                0,
                -GLASS_R - 0.12,
                -SKIRT - 0.1,
            ]  # the plate's near edge
            pair = m.VGroup(word, note).arrange(m.DOWN, buff=0.12)
            pair.add_updater(
                lambda mob, at=front: mob.move_to(
                    project(self.camera, at) + 0.62 * m.DOWN
                )
            )
            captions.add(pair)
        hud = [subtitle, *plot, subtitle2, closing, captions]
        self.add_fixed_in_frame_mobjects(title, *hud)
        self.remove(*hud)

        # 0–10 s: one top, nodding between the turning points of its effective potential
        self.play(m.FadeIn(subtitle), run_time=1.2)
        self.play(*[m.FadeIn(mob) for mob in frame], run_time=1)
        self.play(m.Create(curve), m.FadeIn(energy), m.FadeIn(rider), run_time=1.2)
        turning = [m.FadeIn(mob) for mob in (marks, names, tags)]
        self.play(*turning, rings.animate.set_value(1.0), run_time=1)
        self.wait(10.4 - self.time)

        # 10–13 s: two more tops, let go with a push
        self.play(*[m.FadeOut(mob) for mob in plot], run_time=0.8)
        self.add(jars[1], jars[2])
        self.move_camera(
            phi=54 * m.DEGREES,
            theta=-97 * m.DEGREES,
            zoom=1.0,
            frame_center=[0, 0, -0.05],
            added_anims=[shown[k].animate.set_value(1.0) for k in (1, 2)],
            run_time=2.2,
        )
        self.begin_ambient_camera_rotation(rate=0.01)
        self.play(
            m.FadeOut(subtitle), m.FadeIn(subtitle2), m.FadeIn(captions), run_time=1.2
        )
        # 14–30 s: cusps, loops and waves, then all three from higher up
        self.wait(20.8 - self.time)
        self.stop_ambient_camera_rotation()
        self.move_camera(phi=40 * m.DEGREES, theta=-90 * m.DEGREES, run_time=3)
        self.wait(26.4 - self.time)
        self.play(m.FadeIn(closing, shift=0.15 * m.UP), run_time=1.2)
        self.wait(30.5 - self.time)  # ends as all three tops lean away from us


if __name__ == "__main__":
    HeavyTop().render("heavy_top.mp4")

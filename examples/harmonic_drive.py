"""Strain-wave gearing: 30:1 in one flat ring.

An elliptical plug (the wave generator) spins inside a thin ring of 60 teeth (the flexspline) and
flexes it into mesh with a rigid ring of 62 teeth (the circular spline) at the two ends of its long
axis. The thin ring cannot stretch, so where it bulges out by one module its teeth sit exactly one
gap apart and slide straight in and out of the gaps. Each turn of the plug carries the mesh past
all 62 gaps but only 60 teeth, so the flexspline walks back two teeth a turn:
β = −(N_c − N_f)/N_f · ψ = −ψ/30 (C. W. Musser, 1957). The circular spline's teeth are cut here as
the envelope of the flexspline's own moving teeth, so the two never collide.
"""

from collections.abc import Callable
from itertools import pairwise

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


NF, NC = 60, 62  # flexspline and circular spline teeth
MOD = 0.1  # module: the flexspline's pitch radius is NF · MOD / 2
RP, W0 = NF * MOD / 2, (NC - NF) * MOD / 2  # pitch radius; the bulge at the long axis
PITCH = np.pi * MOD  # tooth pitch along the pitch line
DELTA = m.TAU / NC  # the circular spline's pitch angle
HA, HF, RIM = 0.8 * MOD, 0.9 * MOD, 1.3 * MOD  # tooth tip and root; rim under the root
THICK = 0.5 * PITCH  # tooth thickness on the pitch line
FLANK = np.radians(25)  # flank angle
BALL, BALLS = 0.1, 36  # bearing balls between the plug and the flexspline
CAM = -HF - RIM - 2 * BALL  # the plug's rim, below the pitch line
CLEAR, R_OUT, HUB = 0.006, RP + 5.5 * MOD, 0.55  # tooth clearance; outer rim; shaft
STEEL, BRASS, RED = "#5d6879", "#d8b15e", "#e63946"
PLUG, PLUG_LIGHT = "#1d5a56", "#4fc1b5"
# plug speed (turns per second) at key times, eased between them
SPEED = [(0, 0), (8.6, 0), (10.2, 0.5), (19.2, 0.5), (21.2, 0.04), (25.2, 0.04)]
SPEED += [(27.0, 0.3), (31.0, 0.3)]
CLOSE_UP = 23.2  # the red tooth meets the long axis in the close-up
Face = tuple[np.ndarray, np.ndarray, list[np.ndarray]]  # points, triangles, loops


def pitch_line(
    theta: np.ndarray, w: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The flexspline's pitch line, bulged by w along the plug's long axis (angle 0), at material
    angles θ: an inextensible ring, radial shift w cos 2θ and tangential shift −(w/2) sin 2θ.
    Returns points, unit tangents and outward normals (each (n, 2))."""
    rho = RP + w * np.cos(2 * theta)
    phi = theta - w / (2 * RP) * np.sin(2 * theta)
    d_rho, d_phi = -2 * w * np.sin(2 * theta), 1 - w / RP * np.cos(2 * theta)
    radial = np.stack([np.cos(phi), np.sin(phi)], -1)
    across = np.stack([-np.sin(phi), np.cos(phi)], -1)
    tangent = d_rho[:, None] * radial + (rho * d_phi)[:, None] * across
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    normal = np.stack([tangent[:, 1], -tangent[:, 0]], -1)
    return rho[:, None] * radial, tangent, normal


def turn(points: np.ndarray, angle: float) -> np.ndarray:
    """Points (n, 2) turned counterclockwise by angle."""
    c, s = np.cos(angle), np.sin(angle)
    return points @ np.array([[c, s], [-s, c]])


def polar(r: np.ndarray, angle: np.ndarray) -> np.ndarray:
    return np.stack([r * np.cos(angle), r * np.sin(angle)], -1)


def tooth_cell() -> np.ndarray:
    """One flexspline pitch cell (x along the pitch line, y out of it), 14 points from x = −p/2 to
    x = p/2: root, a tooth with straight flanks and rounded tip corners, root."""
    half, slope = THICK / 2, np.tan(FLANK)
    fillet = 0.3 * (half - HA * slope)
    cy = HA - fillet  # the fillet touches the tip line and the flank
    cx = (half * np.cos(FLANK) - cy * np.sin(FLANK) - fillet) / np.cos(FLANK)
    arc = np.linspace(np.pi - FLANK, np.pi / 2, 5)
    corner = np.stack([-cx + fillet * np.cos(arc), cy + fillet * np.sin(arc)], -1)
    left = np.vstack([[-PITCH / 2, -HF], [-half - HF * slope, -HF], corner])
    return np.vstack([left, (left * [-1, 1])[::-1]])


def place_teeth(cell: np.ndarray, psi: float, w: float) -> np.ndarray:
    """Every tooth's copy of `cell` (NF, k, 2), each tooth rigid on its pitch-line spot, for the
    plug turned by ψ: the flexspline itself has turned by β = −ψ (NC − NF) / NF."""
    theta = m.TAU * np.arange(NF) / NF - psi * NC / NF  # material angles from the axis
    spot, tangent, normal = pitch_line(theta, w)
    pts = spot[:, None] + cell[:, :1] * tangent[:, None] + cell[:, 1:] * normal[:, None]
    return turn(pts.reshape(-1, 2), psi).reshape(NF, len(cell), 2)


def spline_tooth(cell: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The circular spline's tooth, cut as the envelope of the flexspline's teeth: the half-angle
    of the region they sweep through one gap, at each radius, subtracted from the pitch. The
    motion repeats, turned by one gap, every 1/62 turn of the plug, so that stretch covers all
    gaps. Returns the tooth's radii (tip → root) and half-angles."""
    deep = np.array([[PITCH / 2, -HF - RIM], [-PITCH / 2, -HF - RIM]])
    outline = np.vstack([cell, deep, cell[:1]])  # everything under the outline counts
    radii = np.linspace(RP - W0 - HF, RP + W0 + HA, 600)
    swept = np.zeros(len(radii))
    for psi in np.linspace(0, DELTA, 128, endpoint=False):
        pts = place_teeth(outline, psi, W0)
        middle = place_teeth(np.zeros((1, 2)), psi, W0)[:, 0]
        gap = np.round(np.arctan2(middle[:, 1], middle[:, 0]) / DELTA) * DELTA
        r = np.linalg.norm(pts, axis=-1)
        ang = np.arctan2(pts[..., 1], pts[..., 0]) - gap[:, None]
        ang = np.abs((ang + np.pi) % m.TAU - np.pi)[..., None]
        r = r[..., None]
        # where each edge of each outline crosses each radius, and at what angle
        f = (radii - r[:, :-1]) / np.where(
            r[:, 1:] == r[:, :-1], 1e-12, r[:, 1:] - r[:, :-1]
        )
        crossing = ang[:, :-1] + f * (ang[:, 1:] - ang[:, :-1])
        crossing = np.where((f >= 0) & (f <= 1), crossing, 0)
        swept = np.maximum(swept, crossing.max(axis=(0, 1)))
    half = DELTA / 2 - swept - CLEAR / radii
    solid = np.flatnonzero(half > 0)
    keep = np.linspace(solid[0], len(radii) - 1, 14).round().astype(int)
    return radii[keep], half[keep]


def prism(
    face: np.ndarray, tris: np.ndarray, loops: list[np.ndarray], z0: float, z1: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A flat part: its top face (points, triangles) at height z1 and a wall down to z0 along
    each closed boundary loop. Faces and walls share no vertices, so their edges stay crisp.
    Returns, per vertex, the face point it copies and its height, and the triangles."""
    source, height, faces = [np.arange(len(face))], [np.full(len(face), z1)], [tris]
    count = len(face)
    for loop in loops:
        n = len(loop)
        source.append(np.concatenate([loop, loop]))
        height.append(np.repeat([z0, z1], n))
        a = np.arange(n)
        b = (a + 1) % n
        wall = np.vstack([np.stack([a, b, n + b], 1), np.stack([a, n + b, n + a], 1)])
        faces.append(count + wall)
        count += 2 * n
    return np.concatenate(source), np.concatenate(height), np.vstack(faces)


def fan(center: int, rim: np.ndarray) -> np.ndarray:
    return np.stack([np.full(len(rim) - 1, center), rim[:-1], rim[1:]], 1)


def strip(inner: np.ndarray, outer: np.ndarray) -> np.ndarray:
    """Triangles between two closed rows of vertex indices of equal length."""
    a, b, c, d = inner, np.roll(inner, -1), np.roll(outer, -1), outer
    return np.vstack([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])


def facing_up(points: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """The triangles, each wound counterclockwise seen from above (so the shading's averaged
    normals agree)."""
    a, b, c = points[tris[:, 0]], points[tris[:, 1]], points[tris[:, 2]]
    area = (b - a)[:, 0] * (c - a)[:, 1] - (b - a)[:, 1] * (c - a)[:, 0]
    return np.where((area < 0)[:, None], tris[:, ::-1], tris)


def flexspline_face(cell: np.ndarray) -> Face:
    """The flexspline's top face in material terms, per vertex (tooth, x, y) in the tooth's own
    frame: per tooth its contour (13 points), the middle of its base and 4 points on the rim's
    inner edge. Returns them, the triangles and the boundary loops (toothed and inner).
    """
    contour = cell[:-1]  # the next tooth's first point closes this one's root
    inner = np.column_stack(
        [[contour[0, 0], contour[1, 0], 0.0, contour[12, 0]], [-HF - RIM] * 4]
    )
    local = np.vstack([contour, [[0.0, -HF]], inner])  # 13 + 1 + 4 = 18 per tooth
    first = len(local) * np.arange(NF)[:, None]
    teeth = np.vstack([fan(j + 13, j + np.arange(1, 13)) for j in first[:, 0]])
    rows = [
        (first + np.array(k)[None]).ravel() for k in ([14, 15, 16, 17], [0, 1, 13, 12])
    ]
    material = np.column_stack(
        [np.repeat(np.arange(NF), len(local)), np.tile(local, (NF, 1))]
    )
    loops = [(first + np.arange(13)[None]).ravel(), rows[0]]
    return material, np.vstack([teeth, strip(*rows)]), loops


def spline_face(radii: np.ndarray, half: np.ndarray) -> Face:
    """The circular spline's top face: 62 teeth pointing in (tooth k centred at (k + ½)·Δ) on a
    rim out to R_OUT. Returns points, triangles and boundary loops (toothed, outer)."""
    root = radii[-1] + CLEAR  # the root circle, just beyond the flexspline's reach
    # the tooth's edge: root → tip → root
    edge_r = np.concatenate([[root], radii[::-1], radii[1:], [root]])
    edge_a = np.concatenate([[-half[-1]], -half[::-1], half[1:], [half[-1]]])
    n = len(edge_r)
    pts = []
    for k in range(NC):
        c = (k + 0.5) * DELTA
        pts.append(polar(edge_r, c + edge_a))
        pts.append(polar(np.full(2, root), c + np.array([0, DELTA / 2])))  # base, gap
        outside = c + np.array([-half[-1], 0, half[-1], DELTA / 2])
        pts.append(polar(np.full(4, R_OUT), outside))
    first = (n + 6) * np.arange(NC)[:, None]
    teeth = np.vstack([fan(j + n, j + np.arange(n)) for j in first[:, 0]])
    inner = (first + np.array([0, n, n - 1, n + 1])[None]).ravel()
    outer = (first + np.arange(n + 2, n + 6)[None]).ravel()
    points = np.vstack(pts)
    toothed = (first + np.append(np.arange(n), n + 1)[None]).ravel()
    return (
        points,
        facing_up(points, np.vstack([teeth, strip(inner, outer)])),
        [toothed, outer],
    )


def plug_face(samples: int = 240) -> Face:
    """The wave generator's elliptical cam (in its own frame, long axis along x) around a hub."""
    spot, _, normal = pitch_line(np.linspace(0, m.TAU, samples, endpoint=False), W0)
    rim = spot + CAM * normal
    hub = HUB * rim / np.linalg.norm(rim, axis=1, keepdims=True)
    points = np.vstack([hub, rim])
    rows = np.arange(samples), samples + np.arange(samples)
    return points, facing_up(points, strip(*rows)), [rows[1], rows[0]]


def flat(outline: np.ndarray, center: tuple[float, float]) -> Face:
    """A flat polygon, fanned from a point that sees its whole outline."""
    points = np.vstack([outline, [center]])
    tris = fan(len(outline), np.append(np.arange(len(outline)), 0))
    return points, facing_up(points, tris), [np.arange(len(outline))]


def disk(radius: float) -> Face:
    return flat(
        polar(np.full(48, radius), np.linspace(0, m.TAU, 48, endpoint=False)), (0, 0)
    )


def arrow(start: float, stop: float, w: float) -> Face:
    """A flat arrow along +x."""
    neck = stop - 3 * w
    half = [[start, -w / 2], [neck, -w / 2], [neck, -1.5 * w], [stop, 0]]
    return flat(np.array(half + [[x, -y] for x, y in half[-2::-1]]), (neck, 0))


def ball() -> tuple[np.ndarray, np.ndarray]:
    """A bearing ball: a small sphere's vertices and triangles (a 6 × 10 grid)."""
    u, v = np.meshgrid(
        np.linspace(0, np.pi, 7), np.linspace(0, m.TAU, 11), indexing="ij"
    )
    grid = np.stack([np.sin(u) * np.cos(v), np.sin(u) * np.sin(v), np.cos(u)], -1)
    a = (np.arange(6)[:, None] * 11 + np.arange(10)[None]).ravel()
    tris = np.vstack(
        [np.stack([a, a + 11, a + 12], 1), np.stack([a, a + 12, a + 1], 1)]
    )
    return BALL * grid.reshape(-1, 3), tris


def speed_profile() -> tuple[np.ndarray, np.ndarray]:
    """Times, and the plug's angle (turns) by then: the integral of the eased SPEED profile."""
    fine = np.linspace(0, SPEED[-1][0], 60001)
    speed = np.zeros_like(fine)
    for (t0, s0), (t1, s1) in pairwise(SPEED):
        x = np.clip((fine - t0) / (t1 - t0), 0, 1)
        inside = (fine >= t0) & (fine <= t1)
        speed[inside] = s0 + (s1 - s0) * (x * x * (3 - 2 * x))[inside]
    steps = (speed[1:] + speed[:-1]) / 2 * np.diff(fine)
    return fine, np.concatenate([[0], np.cumsum(steps)])


PROFILE = speed_profile()


def plug_turns(times: np.ndarray) -> np.ndarray:
    return np.interp(times, *PROFILE)


def project(camera: m.Camera, point: np.ndarray) -> np.ndarray:
    """Where a 3D point lands on the screen, in frame coordinates (for HUD labels)."""
    turned = camera_axes(camera.get_phi(), camera.get_theta(), camera.get_gamma())
    p = turned @ (point - camera.frame_center)
    depth = 1 - p[2] / camera.get_focal_distance()
    return np.array([*(camera.get_zoom() * p[:2] / depth), 0.0])


def rgba(color: str) -> np.ndarray:
    return np.array([*m.ManimColor(color).to_rgb(), 1.0])


def live(
    value: Callable[[], float], places: int, shown: m.ValueTracker, right: np.ndarray
) -> m.DecimalNumber:
    """A number that follows `value` every frame, its right edge at `right`, faded by a tracker
    (it is rebuilt each frame, so it must not be faded by an animation)."""
    number = m.DecimalNumber(value(), num_decimal_places=places, font_size=30)

    def refresh(mob: m.DecimalNumber) -> None:
        mob.set_value(value()).set_opacity(shown.get_value())
        mob.move_to(right, aligned_edge=m.RIGHT)

    number.add_updater(refresh)
    refresh(number)
    return number


class HarmonicDrive(m.ThreeDScene):
    def construct(self) -> None:
        self.camera.background_color = "#0f1318"
        cell = tooth_cell()
        radii, half = spline_tooth(cell)
        # the red tooth is the one at the long axis in the middle of the close-up; the whole
        # drive is turned so that it starts at 12 o'clock
        close_up = plug_turns(np.array([CLOSE_UP]))[0] * m.TAU
        red = round(close_up * NC / m.TAU) % NF
        start = place_teeth(np.zeros((1, 2)), 0.0, W0)[red, 0]
        zero = np.pi / 2 - np.arctan2(start[1], start[0])
        clock = [0.0]
        bulge = m.ValueTracker(0.0)  # the flexspline's bulge, in units of W0
        lift = {"plug": m.ValueTracker(3.8), "flex": m.ValueTracker(1.9)}
        seen = {"psi": 0.0, "beta": 0.0}  # plug and ring angles, as drawn this frame

        def psi() -> float:
            return float(plug_turns(np.array([clock[0]]))[0] * m.TAU)

        def place(xy: np.ndarray, z: np.ndarray, angle: float = 0.0) -> np.ndarray:
            return np.column_stack([turn(xy, angle + zero), z])

        # circular spline: fixed
        face, tris, loops = spline_face(radii, half)
        source, height, faces = prism(face, tris, loops, 0.0, 0.5)
        spline = m.MeshMobject(
            place(face[source], height), faces, shade_in_3d=True, fill_color=STEEL
        )

        # flexspline: 60 rigid teeth riding the flexed pitch line, colored by how far the plug
        # pushes each out (bright) or pulls it in (dim): the strain wave
        material, tris, loops = flexspline_face(cell)
        f_source, f_height, f_faces = prism(material[:, 1:], tris, loops, 0.02, 0.56)
        tooth_of = material[f_source, 0].astype(int)
        local = material[f_source, 1:]
        dim, gold, bright = rgba("#5e4418"), rgba(BRASS), rgba("#fff6d0")
        rest = m.TAU * np.arange(NF) / NF

        def flex_update(mob: m.MeshMobject) -> None:
            a, w = psi(), bulge.get_value()
            theta = rest - a * NC / NF
            spot, tangent, normal = pitch_line(theta, W0 * w)
            xy = spot[tooth_of] + local[:, :1] * tangent[tooth_of]
            xy += local[:, 1:] * normal[tooth_of]
            mob.points = place(xy, f_height + lift["flex"].get_value(), a)
            # the ring's turn, measured from the drawn teeth: their mean angle from rest
            moved = turn(spot, a)
            angles = np.arctan2(moved[:, 1], moved[:, 0]) - rest
            seen["psi"], seen["beta"] = a, float(np.angle(np.exp(1j * angles).mean()))
            strain = w * np.cos(2 * theta)[tooth_of, None]
            rows = np.where(
                strain > 0,
                gold + strain * (bright - gold),
                gold - strain * (dim - gold),
            )
            rows[tooth_of == red] = rgba(RED)
            mob.paint = mob.paint.but(fill=rows)

        flex = m.MeshMobject(np.zeros((len(f_source), 3)), f_faces, shade_in_3d=True)
        flex_update(flex)
        flex.add_updater(flex_update)

        # wave generator: the cam, its hub and an arrow along its long axis, and the balls
        parts = [plug_face(), disk(HUB), arrow(HUB + 0.12, RP + W0 + CAM - 0.12, 0.07)]
        levels = [(0.08, 0.46), (0.0, 0.74), (0.46, 0.47)]
        tints = [PLUG, "#c9ced6", "#f1faee"]
        plug_parts = []
        for (face, tris, loops), (z0, z1), tint in zip(parts, levels, tints):
            source, height, faces = prism(face, tris, loops, z0, z1)
            mesh = m.MeshMobject(
                place(face[source], height), faces, shade_in_3d=True, fill_color=tint
            )

            def pose(
                mob: m.Mobject, xy: np.ndarray = face[source], z: np.ndarray = height
            ) -> None:
                mob.points = place(xy, z + lift["plug"].get_value(), psi())

            mesh.add_updater(pose)
            plug_parts.append(mesh)
        sphere, one = ball()
        tris = np.vstack([one + k * len(sphere) for k in range(BALLS)])
        balls = m.MeshMobject(
            np.zeros((BALLS * len(sphere), 3)),
            tris,
            shade_in_3d=True,
            fill_color="#e8ecf2",
        )

        def roll(mob: m.Mobject) -> None:
            a = psi()
            cage = (
                m.TAU * np.arange(BALLS) / BALLS - 0.52 * a
            )  # the cage: about half speed
            spot, _, normal = pitch_line(cage, W0)
            z = np.full(BALLS, 0.27 + lift["plug"].get_value())
            centers = place(spot + (CAM + BALL) * normal, z, a)
            mob.points = (centers[:, None] + sphere[None]).reshape(-1, 3)

        balls.add_updater(roll)
        roll(balls)

        # on the fixed ring, a tick grows where the ring has got to after each whole turn of
        # the plug: two teeth (12°) apart
        grid = np.linspace(0, SPEED[-1][0], 3101)
        turns = np.arange(int(plug_turns(grid)[-1]) + 1)
        when = np.interp(turns, plug_turns(grid), grid)
        when[0] = SPEED[1][0]  # where the red tooth starts
        root = radii[-1] + CLEAR
        across = np.array([-0.028, 0.028, 0.028, -0.028])
        quad = np.array([[0, 1, 2], [0, 2, 3]])
        tick_tris = np.vstack([quad + 4 * k for k in range(len(turns))])

        def tick_points() -> np.ndarray:
            grow = np.clip((clock[0] - when) / 0.5, 0, 1)
            out = []
            for k, g in zip(turns, grow):
                r = root + 0.07 + np.array([0, 0, 0.3, 0.3]) * max(g, 1e-3)
                out.append(
                    turn(np.column_stack([r, across]), np.pi / 2 - k * m.TAU / 30)
                )
            xy = np.vstack(out)
            return np.column_stack([xy, np.full(len(xy), 0.504)])

        ticks = m.MeshMobject(
            tick_points(), tick_tris, shade_in_3d=True, fill_color=m.WHITE
        )
        ticks.add_updater(lambda mob: setattr(mob, "points", tick_points()))

        def advance(mob: m.Mobject, dt: float) -> None:
            clock[0] += dt

        driver = m.Mobject().add_updater(advance)

        # heads-up display
        title = m.Text("Strain-wave gearing", font_size=38).to_corner(m.UL)
        notes = [
            "an elliptical plug flexes a 60-tooth ring inside a 62-tooth ring",
            "the ring meshes only where the plug pushes it out",
            (
                "where the ring bulges, its teeth sink into the gaps; a quarter turn"
                " on, they clear"
            ),
        ]
        subtitles = [m.Text(t, font_size=22).set_color(m.GREY_B) for t in notes]
        for sub in subtitles:
            sub.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)
        labels = m.VGroup()
        for name, note, color in [
            ("wave generator", "input: an elliptical plug", PLUG_LIGHT),
            ("flexspline", "60 teeth: output", BRASS),
            ("circular spline", "62 teeth: fixed", "#aab4c3"),
        ]:
            labels.add(
                m.VGroup(
                    m.Text(name, font_size=26).set_color(color),
                    m.Text(note, font_size=20).set_color(m.GREY_B),
                ).arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.1)
            )
        reaches = [RP + W0 + CAM + 2 * BALL, RP + HA, R_OUT]
        around = polar(np.ones(72), np.linspace(0, m.TAU, 72, endpoint=False))

        def follow(group: m.Mobject) -> None:
            """Each label just left of its part, never closer than 0.95 to the one below."""
            floor = -np.inf
            parts = zip(group[::-1], ["spline", "flex", "plug"], reaches[::-1])
            for label, part, reach in parts:
                z = 0.3 + (lift[part].get_value() if part in lift else 0.0)
                rim = [
                    project(self.camera, np.array([*(reach * p), z])) for p in around
                ]
                spot = min(rim, key=lambda q: q[0])
                y = max(spot[1], floor + 0.95)
                label.move_to([spot[0] - 0.3 - label.width / 2, y, 0])
                floor = y

        labels.add_updater(follow)

        formula = m.MathTex(
            r"\beta = -\frac{N_c - N_f}{N_f}\,\psi = -\frac{\psi}{30}", font_size=34
        )
        shown = m.ValueTracker(0.0)
        rows_y = [0.3 - 0.62 * k for k in range(3)]
        readings: list[tuple[Callable[[], float], int]] = [
            (lambda: seen["psi"] / m.TAU, 2),  # plug turns
            (lambda: seen["beta"] / m.TAU * NF, 1),  # ring teeth
            (lambda: seen["psi"] / seen["beta"] if seen["psi"] > 0.5 else -30.0, 1),
        ]
        numbers = [
            live(value, places, shown, np.array([-2.35, y, 0]))
            for (value, places), y in zip(readings, rows_y)
        ]
        names = [
            m.MathTex(r"\text{wave generator}\;\psi", font_size=30),
            m.MathTex(r"\text{flexspline}\;\beta", font_size=30),
            m.MathTex(r"\psi / \beta", font_size=30),
        ]
        units = [m.Text(u, font_size=24) for u in ("turns", "teeth", ": 1")]
        for name, unit, y in zip(names, units, rows_y):
            name.move_to([-6.75, y, 0], aligned_edge=m.LEFT)
            unit.move_to([-2.2, y - 0.02, 0], aligned_edge=m.LEFT)
        formula.move_to([-6.75, 1.55, 0], aligned_edge=m.LEFT)
        statics = m.VGroup(formula, *names, *units)
        closing = m.VGroup(
            m.Text("62 − 60 = 2 teeth:", font_size=28),
            m.Text("one turn in, two teeth back", font_size=28),
            m.Text("30 : 1 in one flat stage, without backlash", font_size=22),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.14)
        closing[2].set_color(m.GREY_B)
        closing.move_to([-6.75, -2.75, 0], aligned_edge=m.LEFT)
        self.add_fixed_in_frame_mobjects(
            title, *subtitles, labels, statics, *numbers, closing
        )
        self.remove(*subtitles, labels, statics, closing)

        def main_view(run_time: float) -> None:
            """Looking down at 32° on the drive, at the right of the frame (the HUD's left)."""
            self.move_camera(
                phi=32 * m.DEGREES,
                theta=-90 * m.DEGREES,
                zoom=0.92,
                frame_center=[-3.35, 0.2, 0],
                run_time=run_time,
            )

        # 0–6.5 s: the parts, apart; then assembled: the plug flexes the ring as it goes in
        self.add(driver, spline, flex, *plug_parts, balls, ticks)
        self.set_camera_orientation(
            phi=63 * m.DEGREES,
            theta=-78 * m.DEGREES,
            zoom=0.86,
            frame_center=[-0.6, 0, 2.25],
        )
        self.begin_ambient_camera_rotation(rate=0.05)
        self.play(m.FadeIn(subtitles[0]), m.FadeIn(labels), run_time=1.2)
        self.wait(1.6)
        self.play(
            lift["plug"].animate.set_value(1.9),
            bulge.animate.set_value(1.0),
            m.FadeOut(labels, run_time=0.8),
            run_time=1.9,
        )
        self.play(
            lift["plug"].animate.set_value(0.0),
            lift["flex"].animate.set_value(0.0),
            run_time=1.7,
        )
        self.stop_ambient_camera_rotation()
        # 6.5–19 s: the plug spins; the ring creeps back the other way, two teeth a turn
        self.play(m.FadeOut(subtitles[0]), run_time=0.4)
        main_view(2.0)
        self.play(
            m.FadeIn(subtitles[1]),
            m.FadeIn(statics),
            shown.animate.set_value(1.0),
            run_time=1.0,
        )
        self.wait(SPEED[3][0] - self.time)
        # 19–27 s: close up on the mesh where the long axis passes the red tooth
        axis = close_up + zero
        spot = np.array([3.2 * np.cos(axis), 3.2 * np.sin(axis), 0.5])
        view = (
            axis + np.pi / 2
        ) % m.TAU - 1.5 * np.pi  # axis − π, the turn nearest −π/2
        self.play(
            m.FadeOut(statics),
            shown.animate.set_value(0.0),
            m.FadeOut(subtitles[1]),
            run_time=0.5,
        )
        self.move_camera(
            phi=16 * m.DEGREES, theta=view, zoom=2.3, frame_center=spot, run_time=1.8
        )
        self.play(m.FadeIn(subtitles[2]), run_time=0.6)
        self.wait(SPEED[5][0] - self.time - 0.5)
        self.play(m.FadeOut(subtitles[2]), run_time=0.5)
        main_view(1.8)
        # 27–30.5 s: the poster
        self.play(
            m.FadeIn(statics),
            shown.animate.set_value(1.0),
            m.FadeIn(subtitles[1]),
            m.FadeIn(closing, shift=0.15 * m.UP),
            run_time=1.0,
        )
        self.wait(30.5 - self.time)


if __name__ == "__main__":
    HarmonicDrive().render("harmonic_drive.mp4")

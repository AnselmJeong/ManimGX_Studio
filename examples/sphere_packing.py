"""Two ways to stack oranges: ABAB... and ABCABC..., and the second one is a cube.

A hexagonal layer of spheres leaves two sets of hollows, B and C; the second layer fills one
set. The third layer then has a choice: over the first (ABAB..., hexagonal close packing) or
into the C hollows (ABCABC..., face-centred cubic). The ABC pile is the face-centred cubic
lattice seen along a body diagonal: trim it and a cube stands on its corner. Both fill
π/(3√2) ≈ 74.05% of space, and nothing fills more (Kepler's conjecture, 1611; proved by
Hales, 1998; formal proof 2014). The fill is measured by Cavalieri's principle: a knife
slices both piles, and the filled share of the cut, averaged down whole periods of the
lattice, is the filled share of space.
"""

import numpy as np

import manimgx as m

D = 0.5  # sphere diameter (scene units)
R = D / 2
H = D * np.sqrt(2 / 3)  # spacing of the layers
A1, A2 = np.array([1.0, 0.0]), np.array([0.5, np.sqrt(3) / 2])
HOLLOW = {"A": 0.0, "B": 1 / 3, "C": 2 / 3}  # layer offsets along a1 + a2
COLOR = {"A": "#f28a1e", "B": "#f2cf3c", "C": "#86c440"}  # orange, lemon, lime
STACKS = ("ABABABA", "ABCABCA")
BASE_Z = -1.2
APART = 2.3  # the towers' x offsets once they split
NT, NP = 10, 22  # a ball's mesh: rows from its cut to its bottom, columns around
UP = np.array([0.0, 0.0, 1.0])


def hexagon_norm(p: np.ndarray) -> np.ndarray:
    """Circumradius of the hexagon through p with vertices at 30°, 90°, ... (a crate)."""
    normals = np.array([[1.0, 0.0], [0.5, np.sqrt(3) / 2], [-0.5, np.sqrt(3) / 2]])
    return np.abs(p @ normals.T).max(axis=1) / np.cos(np.pi / 6)


def layer_sites(letter: str, radius: float) -> np.ndarray:
    """Centres (in diameters) of one hexagonal layer inside a crate of that radius."""
    i, j = np.meshgrid(np.arange(-8, 9), np.arange(-8, 9), indexing="ij")
    p = i.ravel()[:, None] * A1 + j.ravel()[:, None] * A2 + HOLLOW[letter] * (A1 + A2)
    return p[hexagon_norm(p) <= radius + 1e-9]


def drop_height(tau: np.ndarray, h0: float, g: float = 30.0) -> np.ndarray:
    """Height above its rest of a ball let go from h0 at tau = 0, bouncing to a stop."""
    out = np.where(tau < 0, h0, h0 - 0.5 * g * np.maximum(tau, 0) ** 2)
    start = np.sqrt(2 * h0 / g)
    speed = 0.3 * g * start  # restitution 0.3
    for _ in range(3):
        s = tau - start
        out = np.where((s >= 0) & (s < 2 * speed / g), speed * s - 0.5 * g * s**2, out)
        start, speed = start + 2 * speed / g, 0.3 * speed
    return np.where(tau >= start, 0.0, np.maximum(out, 0.0))


def turn(axis: np.ndarray, angle: float) -> np.ndarray:
    """Rotation matrix about a unit axis (Rodrigues)."""
    x, y, z = axis
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k


def ball_triangles(n: int) -> np.ndarray:
    """Triangles of n balls, each a polar grid (NT+1 x NP+1) and a cap disc (2 x NP+1)."""
    idx = np.arange((NT + 1) * (NP + 1)).reshape(NT + 1, NP + 1)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    shell = np.concatenate([np.stack([a, b, c], -1), np.stack([a, c, d], -1)])
    k, first = np.arange(NP), idx.size  # the cap: a centre ring, then a rim ring
    cap = np.stack([first + k, first + NP + 1 + k, first + NP + 2 + k], -1)
    one = np.concatenate([shell.reshape(-1, 3), cap])
    stride = idx.size + 2 * (NP + 1)
    return (one[None] + stride * np.arange(n)[:, None, None]).reshape(-1, 3)


def ball_points(c: np.ndarray, r: np.ndarray, knife: np.ndarray) -> np.ndarray:
    """Vertices of balls (centres c, radii r) cut by a horizontal knife at a height per
    ball: the part below the knife, and the flat cut face."""
    n = len(r)
    # the cut's polar angle: 0 keeps the whole ball, π keeps nothing
    cut = np.clip((knife - c[:, 2]) / r, -1, 1)
    top = np.arccos(cut)
    theta = top[:, None] + (np.pi - top)[:, None] * np.linspace(0, 1, NT + 1)
    theta = theta[..., None]
    phi = np.linspace(0, 2 * np.pi, NP + 1)
    unit = np.stack(
        [
            np.sin(theta) * np.cos(phi),
            np.sin(theta) * np.sin(phi),
            np.broadcast_to(np.cos(theta), (n, NT + 1, NP + 1)),
        ],
        -1,
    )
    shell = c[:, None, None] + r[:, None, None, None] * unit
    cap = np.zeros((n, 2, NP + 1, 3))  # a centre ring and a rim ring
    cap[:, 1, :, 0] = (r * np.sin(top))[:, None] * np.cos(phi)
    cap[:, 1, :, 1] = (r * np.sin(top))[:, None] * np.sin(phi)
    cap += np.column_stack([c[:, :2], c[:, 2] + r * cut])[:, None, None]
    out = np.concatenate([shell.reshape(n, -1, 3), cap.reshape(n, -1, 3)], 1)
    return out.reshape(-1, 3)


def covered(samples: np.ndarray, centres: np.ndarray, z: float) -> float:
    """Share of the sample points (x, y) inside the discs the balls cut at height z."""
    dz = z - centres[:, 2]
    near = np.abs(dz) < R
    d2 = ((samples[:, None, :] - centres[near][None, :, :2]) ** 2).sum(-1)
    return float((d2 < R**2 - dz[near] ** 2).any(axis=1).mean())


def grid_in(u: np.ndarray, v: np.ndarray, n: int) -> np.ndarray:
    """Midpoints of an n x n grid on the parallelogram spanned by u and v."""
    s = (np.arange(n) + 0.5) / n
    ss, tt = np.meshgrid(s, s)
    return ss.reshape(-1, 1) * u + tt.reshape(-1, 1) * v


def rgba(hex_color: str, whiten: float = 0.0) -> np.ndarray:
    c = np.array(m.ManimColor(hex_color).to_rgb())
    return np.array([*(c + (1 - c) * whiten), 1.0])


class SpherePacking(m.ThreeDScene):
    def construct(self) -> None:
        cam = self.camera
        self.set_camera_orientation(phi=58 * m.DEGREES, theta=-72 * m.DEGREES, zoom=1.7)
        cam.frame.move_to([0, 0, -0.75])

        # ── the two piles, ABABABA (left) and ABCABCA (right), in hexagonal crates ────────
        # each layer's start and how long its balls take to let go (roughly centre first)
        schedule = [(-1.0, 2.5), (2.1, 1.1)] + [(6.2 + 1.1 * k, 0.6) for k in range(5)]
        # one random order per layer: the two piles are one until they split
        jitter = np.random.default_rng(7).random((7, 64))
        side, home, letters, release = [], [], [], []
        for s, seq in enumerate(STACKS):
            for k, ch in enumerate(seq):
                sites = layer_sites(ch, 2.4)
                order = np.linalg.norm(sites, axis=1) + 2 * jitter[k, : len(sites)]
                side += [s] * len(sites)
                home += [np.column_stack([sites * D, np.full(len(sites), k * H)])]
                letters += [ch] * len(sites)
                release += list(schedule[k][0] + schedule[k][1] * order / order.max())
        tower, base, released = np.array(side), np.vstack(home), np.array(release)
        n_balls = len(base)

        # the FCC cube: 2 x 2 x 2 cells of side a = √2 D, standing on a corner in the ABC pile
        a = np.sqrt(2) * D
        g = np.arange(5) / 2
        grid = np.stack(np.meshgrid(g, g, g, indexing="ij"), -1).reshape(-1, 3)
        cube = grid[np.round(2 * grid).sum(axis=1) % 2 == 0] * a - a  # about its centre
        diagonal = np.ones(3) / np.sqrt(3)
        across = np.array([-1.0, 1.0, 0.0]) / np.sqrt(2)
        # cube frame → pile frame: the body diagonal points up
        on_corner = np.vstack([across, np.cross(diagonal, across), diagonal])
        standing = cube @ on_corner.T + 3 * H * UP
        gap = np.linalg.norm(base[:, None] - standing[None], axis=2)
        in_cube = (tower == 1) & (gap.min(axis=1) < 1e-6)
        cube_index = np.flatnonzero(in_cube)
        cube_coord = cube[gap[cube_index].argmin(axis=1)]
        assert len(cube_index) == 63
        # it tips onto a face, and turns about the vertical to show three faces
        face = on_corner[:, 2]
        tilt_axis = np.cross(face, UP) / np.linalg.norm(np.cross(face, UP))
        tilt = float(np.arccos(face[2]))
        side_face = turn(tilt_axis, tilt) @ on_corner[:, 0]
        spin = -27 * m.DEGREES - float(np.arctan2(side_face[1], side_face[0]))

        def cube_pose(s: float) -> tuple[np.ndarray, np.ndarray]:
            """Rotation and centre as it tips (s: 0 → 1), to rest level with the towers."""
            rot = turn(UP, s * spin) @ turn(tilt_axis, s * tilt) @ on_corner
            return rot, np.array([APART, 0, BASE_Z + 3 * H + s * (a - 3 * H)])

        clock = m.ValueTracker(0.0)  # the build's own clock, seconds
        split = m.ValueTracker(0.0)  # 1: two towers, APART each side
        trim = m.ValueTracker(0.0)  # 1: the FCC balls outside the cube are gone
        tip = m.ValueTracker(0.0)  # 1: the cube lies on a face
        knife = m.ValueTracker(0.0)  # 0: above everything, 1: region tops, 2: bottoms
        swept = m.ValueTracker(0.0)  # how much of the regions the knife has measured

        # the measured regions, whole periods of each lattice: the cube (FCC), and a
        # hexagonal prism of circumradius √3 D from layer 1 to layer 5 (HCP)
        cube_top, prism_top = BASE_Z + 2 * a, BASE_Z + 5 * H

        def knife_heights() -> tuple[float, float]:
            lead = min(knife.get_value(), 1.0)
            sweep = float(np.clip(knife.get_value() - 1, 0, 1))
            above = BASE_Z + 6 * H + R + 0.05
            left = above + lead * (prism_top - above) - sweep * 4 * H
            return left, above + lead * (cube_top - above) - sweep * 2 * a

        def pile_points() -> np.ndarray:
            sway = np.where(tower == 0, -APART, APART) * split.get_value()
            c = base + np.column_stack([sway, 0 * sway, np.full(n_balls, BASE_Z)])
            falling = clock.get_value() - released
            c[:, 2] += drop_height(falling, 3.4)
            # a ball grows in as it starts to fall
            r = R * np.clip(falling / 0.15, 1e-4, 1)
            # the trimmed balls shrink away, top first
            gone = (tower == 1) & ~in_cube
            lag = 0.35 * (1 - base[gone, 2] / (6 * H))
            x = np.clip((trim.get_value() - lag) / 0.65, 0, 1)
            r[gone] = np.maximum(r[gone] * (1 - x * x * (3 - 2 * x)), 1e-4)
            if tip.get_value() > 0:
                rot, centre = cube_pose(tip.get_value())
                c[cube_index] = centre + cube_coord @ rot.T
            left, right = knife_heights()
            return ball_points(c, r, np.where(tower == 0, left, right))

        skin = np.array([rgba(COLOR[ch]) for ch in letters])
        flesh = np.array([rgba(COLOR[ch], 0.45) for ch in letters])  # the cut faces
        paint = [np.repeat(skin[:, None], (NT + 1) * (NP + 1), 1)]
        paint += [np.repeat(flesh[:, None], 2 * (NP + 1), 1)]
        pile = m.MeshMobject(pile_points(), ball_triangles(n_balls), shade_in_3d=True)
        pile.paint = pile.paint.but(fill=np.concatenate(paint, 1).reshape(-1, 4))
        pile.add_updater(lambda mob: mob.set_points(pile_points()))

        # the C hollows of the second layer: lime beads resting in them (they ride right)
        # (a bead of radius 0.3 R touches the three balls around it, D/√3 away sideways)
        c_sites = layer_sites("C", 1.9) * D
        bead_z = BASE_Z + H + np.sqrt((1.3 * R) ** 2 - D**2 / 3)
        bead_size = m.ValueTracker(0.0)

        def bead_points() -> np.ndarray:
            c = np.column_stack([c_sites, np.full(len(c_sites), bead_z)])
            c[:, 0] += split.get_value() * APART
            r = np.full(len(c), 0.3 * R * bead_size.get_value() + 1e-4)
            return ball_points(c, r, np.full(len(c), 99.0))

        bead_tris = ball_triangles(len(c_sites))
        beads = m.MeshMobject(bead_points(), bead_tris, shade_in_3d=True)
        beads.set_fill(COLOR["C"], 1.0)
        beads.add_updater(lambda mob: mob.set_points(bead_points()))

        # a wooden tray under each pile (flat faces: each face has its own vertices)
        turn6 = np.radians(30 + 60 * np.arange(6))
        rim = 3.05 * D * np.column_stack([np.cos(turn6), np.sin(turn6), np.zeros(6)])
        drop = np.array([0, 0, 0.1])
        walls = [
            [rim[k], rim[k - 1], rim[k - 1] - drop, rim[k] - drop] for k in range(6)
        ]
        slab = np.vstack([[0, 0, 0], rim, *walls]) + [0, 0, BASE_Z - R - 0.004]
        k = np.arange(6)
        fan = np.stack([0 * k, 1 + k, 1 + (k + 1) % 6], 1)
        quads = 7 + 4 * k[:, None] + np.array([[0, 1, 2], [0, 2, 3]])[:, None]
        slab_tris = np.concatenate([fan, *quads])
        trays = m.Group()
        for sign in (-1, 1):
            tray = m.MeshMobject(slab, slab_tris, shade_in_3d=True)
            tray.paint = tray.paint.but(
                fill=np.repeat([rgba("#4a3524"), rgba("#241a12")], [7, 24], 0)
            )
            tray.add_updater(
                lambda mob, s=sign: mob.set_points(
                    slab + [s * APART * split.get_value(), 0, 0]
                )
            )
            trays.add(tray)

        # ── Cavalieri: the filled share of each cut, tabulated down each region ───────────
        square = grid_in(np.array([2 * a, 0]), np.array([0, 2 * a]), 150) - a
        corners = np.radians(30 + 60 * np.arange(7))
        rim = np.sqrt(3) * D * np.column_stack([np.cos(corners), np.sin(corners)])
        hexagon = np.vstack([grid_in(rim[k], rim[k + 2], 80) for k in (0, 2, 4)])
        depth = np.linspace(0, 1, 201)  # down each region, from its top
        fcc_share = np.array([covered(square, cube, a - 2 * a * t) for t in depth])
        hcp = base[tower == 0]
        hcp_share = np.array([covered(hexagon, hcp, 5 * H - 4 * H * t) for t in depth])

        def measured() -> int:
            return max(1, int(round(swept.get_value() * (len(depth) - 1))))

        def running_mean(share: np.ndarray) -> float:
            """The filled share (in percent) averaged down the part measured so far."""
            k = measured()
            return 100 * float(np.trapezoid(share[: k + 1], depth[: k + 1]) / depth[k])

        final = cube_pose(1.0)[0]

        def outlines() -> m.VGroup:
            """The knife's outline on each measured region."""
            left, right = knife_heights()
            hexa = np.column_stack([rim - [APART, 0], np.full(7, min(left, prism_top))])
            sq = np.array([[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0], [-1, -1, 0]])
            sq = a * sq @ final.T + [APART, 0, min(right, cube_top)]
            lines = [m.VMobject().set_points_as_corners(p) for p in (hexa, sq)]
            return m.VGroup(*lines).set_stroke(m.WHITE, 3, 0.95).shift(0.01 * UP)

        knife_lines = m.always_redraw(outlines)

        # ── heads-up display ──────────────────────────────────────────────────────────────
        title = m.Text("Two ways to stack oranges", font_size=36).to_corner(m.UL)

        def caption(text: str, size: float = 22) -> m.Text:
            c = m.Text(text, font_size=size).set_color(m.GREY_B)
            return c.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)

        captions = [
            caption("each layer settles into the hollows of the one below"),
            caption("layer B fills half the hollows: the other half, C, stay open"),
            caption("the third layer can go back over A, or into the C hollows"),
            caption("trim the ABC pile: it is a cube, balanced on its corner"),
            caption("slice both: a cut's average filled share is the share of space"),
            caption("Both fill 74.05% of space, and no stack of spheres fills more"),
        ]
        credit = "Kepler, 1611  ·  proved by Hales, 1998; by computer, 2014"
        history = m.Text(credit, font_size=18).set_color(m.GREY_C)
        history.next_to(captions[5], m.DOWN, aligned_edge=m.LEFT, buff=0.1)

        def name_tag(seq: str, name: str, x: float) -> m.VGroup:
            row = m.VGroup(*[m.Text(ch, font_size=28, weight=m.BOLD) for ch in seq])
            for letter, ch in zip(row, seq):
                letter.set_color(COLOR[ch])
            tag = m.VGroup(row.arrange(m.RIGHT, buff=0.12), m.Text(name, font_size=22))
            return tag.arrange(m.DOWN, buff=0.1).move_to([x, -3.07, 0])

        tags = [
            name_tag(STACKS[0], "hexagonal close packing", -APART - 0.9),
            name_tag(STACKS[1], "face-centred cubic", APART + 0.9),
        ]

        # the filled share of each cut as the knife goes down, and the running averages
        plot = m.Axes(
            x_range=[0, 1, 0.25],
            y_range=[0.5, 1.0, 0.1],
            x_length=2.6,
            y_length=1.5,
            tips=False,
            axis_config={"include_ticks": False, "stroke_width": 1.5},
        ).move_to([4.55, 2.45, 0])
        plot.set_color(m.GREY_B)
        level = np.pi / (3 * np.sqrt(2))
        mean_line = m.DashedLine(plot.c2p(0, level), plot.c2p(1, level))
        mean_line.set_stroke(m.WHITE, 1.5)
        mean_label = m.MathTex(r"\tfrac{\pi}{3\sqrt{2}}", font_size=30)
        mean_label.next_to(mean_line, m.RIGHT, 0.1)
        plot_label = m.Text("filled share of the cut", font_size=18).set_color(m.GREY_B)
        plot_label.next_to(plot, m.UP, buff=0.08)

        def trace(share: np.ndarray, color: str) -> m.VMobject:
            def draw() -> m.VMobject:
                k = measured()
                upto = zip(depth[: k + 1], share[: k + 1])
                pts = [plot.c2p(float(t), float(v)) for t, v in upto]
                return m.VMobject().set_points_as_corners(pts).set_stroke(color, 2.5)

            return m.always_redraw(draw)

        def readout(share: np.ndarray, color: str, x: float) -> m.VGroup:
            label = m.Text("filled", font_size=24).set_color(m.GREY_B)
            number = m.DecimalNumber(running_mean(share), unit=r"\%", font_size=32)
            row = m.VGroup(label, number.set_color(color)).arrange(m.RIGHT, buff=0.15)
            row.move_to([x, -3.68, 0])

            def update(d: m.DecimalNumber) -> None:
                d.set_value(running_mean(share))
                d.next_to(label, m.RIGHT, buff=0.15)

            number.add_updater(update)
            return row

        live = [
            trace(hcp_share, COLOR["B"]),
            trace(fcc_share, COLOR["C"]),
            readout(hcp_share, COLOR["B"], -APART - 0.9),
            readout(fcc_share, COLOR["C"], APART + 0.9),
        ]
        chart = [plot, mean_line, mean_label, plot_label]
        hud = [*captions[1:], history, *tags, *chart, *live]
        self.add_fixed_in_frame_mobjects(title, captions[0], *hud)
        self.remove(*hud)
        self.add(trays, pile, beads)

        def swap(k: int, *more: m.Mobject) -> list[m.Animation]:
            """Caption k replaces caption k - 1 (one fades out, then the other in)."""
            early = m.squish_rate_func(m.smooth, 0, 0.35)
            late = m.squish_rate_func(m.smooth, 0.35, 0.85)
            ins = [m.FadeIn(mob, rate_func=late) for mob in (captions[k], *more)]
            return [m.FadeOut(captions[k - 1], rate_func=early), *ins]

        def build(until: float, *also: m.Animation, run_time: float) -> None:
            """Let the build's clock run on (steadily), with other animations alongside."""
            steady = clock.animate(rate_func=m.linear).set_value(until)
            self.play(steady, *also, run_time=run_time)

        # 0–5 s: layer A drops; layer B settles into half its hollows; the other half shows
        build(2.2, cam.zoom_tracker.animate.set_value(2.0), run_time=2.2)
        build(3.5, *swap(1), run_time=1.3)
        build(4.8, bead_size.animate.set_value(1.0), run_time=1.3)
        # 5–6 s: the choice: the pile splits in two
        build(
            6.2,
            split.animate.set_value(1.0),
            cam.zoom_tracker.animate.set_value(1.07),  # (the piles clear of the text)
            cam.phi_tracker.animate.set_value(64 * m.DEGREES),
            cam.frame.animate.move_to([0, 0, -0.3]),
            *swap(2),
            run_time=1.4,
        )
        # 6–12 s: five more layers each: ABABABA on the left, ABCABCA on the right
        build(12.2, *[m.FadeIn(t, shift=0.2 * m.UP) for t in tags], run_time=6.0)
        self.remove(beads)
        # 12–16.5 s: trim the ABC pile: a cube on its corner; tip it onto a face
        self.play(trim.animate.set_value(1.0), *swap(3), run_time=1.8)
        self.wait(0.6)
        self.play(tip.animate.set_value(1.0), run_time=2.0)
        # 16.5–24.5 s: the knife measures both, down whole periods of each lattice
        self.add(knife_lines)
        self.play(
            knife.animate.set_value(1.0),
            cam.phi_tracker.animate.set_value(54 * m.DEGREES),
            *swap(4, *chart, *live),
            run_time=1.2,
        )
        self.play(
            knife.animate.set_value(2.0),
            swept.animate.set_value(1.0),
            cam.theta_tracker.animate.set_value(-66 * m.DEGREES),
            run_time=6.5,
            rate_func=m.linear,
        )
        # 24.5–30 s: the oranges come back
        self.remove(knife_lines)
        self.begin_ambient_camera_rotation(rate=0.035)
        self.play(
            knife.animate.set_value(0.0),
            cam.phi_tracker.animate.set_value(63 * m.DEGREES),
            cam.zoom_tracker.animate.set_value(0.9),
            cam.frame.animate.move_to([0, 0, 0.15]),
            *swap(5, history),
            run_time=1.8,
        )
        self.wait(3.0)


if __name__ == "__main__":
    SpherePacking().render("sphere_packing.mp4")

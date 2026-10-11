"""Miura-ori: one pull folds the whole sheet.

A sheet creased into identical parallelograms (sides a, b, angle γ) folds rigidly — no facet bends
or stretches — with a single degree of freedom, the fold angle θ. With Schenk & Guest's unit cell
(PNAS 2013): H = a sin θ sin γ, S = b cos θ tan γ / √(1 + cos²θ tan²γ),
L = a √(1 − sin²θ sin²γ), V = b / √(1 + cos²θ tan²γ), the vertex (i, j) sits at
(i S, j L + (i mod 2) V, (j mod 2) H): every edge keeps its length and every facet stays flat (checked
at build time). Width and length shrink together, a negative Poisson ratio ν = −tan²γ cos²θ, which is
why Koryo Miura's fold opens a satellite's solar array with one pull (Space Flyer Unit, 1995).
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


A, B, GAMMA = 1.0, 1.0, np.radians(60)  # facet sides and angle
COLS, ROWS = 14, 12  # facets across (b edges) and along (a edges)
SCALE = 0.44  # sheet units → scene units
PAPER, INK = "#d3c8ae", "#2f4b7c"  # the sheet, and alternate columns once it folds
MOUNTAIN, VALLEY = "#d62828", "#1d5fd8"


def cell(theta: float) -> tuple[float, float, float, float]:
    """Schenk & Guest's unit cell at fold angle θ: height H, zigzag step S, row pitch L, offset V."""
    s, c = np.sin(theta), np.cos(theta)
    k = np.sqrt(1 + (c * np.tan(GAMMA)) ** 2)
    return (
        A * s * np.sin(GAMMA),
        B * c * np.tan(GAMMA) / k,
        A * np.sqrt(1 - (s * np.sin(GAMMA)) ** 2),
        B / k,
    )


def sheet(theta: float) -> np.ndarray:
    """The folded sheet's vertices (COLS + 1, ROWS + 1, 3), in sheet units."""
    h, s, pitch, v = cell(theta)
    i, j = np.meshgrid(np.arange(COLS + 1), np.arange(ROWS + 1), indexing="ij")
    return np.stack([i * s, j * pitch + (i % 2) * v, (j % 2) * h], -1).astype(float)


def rigidity(theta: float) -> float:
    """The largest error, at fold angle θ, in any edge length or in any facet's flatness."""
    p = sheet(theta)
    across = np.linalg.norm(p[1:] - p[:-1], axis=-1) - B
    along = np.linalg.norm(p[:, 1:] - p[:, :-1], axis=-1) - A
    o, x, y, far = p[:-1, :-1], p[1:, :-1], p[:-1, 1:], p[1:, 1:]
    normal = np.cross(x - o, y - o)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    warp = np.einsum("ijk,ijk->ij", far - o, normal)
    return float(max(np.abs(across).max(), np.abs(along).max(), np.abs(warp).max()))


def facets(p: np.ndarray) -> np.ndarray:
    """Each facet's own four corners (COLS · ROWS · 4, 3): unshared, so every facet is flat-lit."""
    quads = np.stack([p[:-1, :-1], p[1:, :-1], p[1:, 1:], p[:-1, 1:]], 2)
    return quads.reshape(-1, 3)


def creases() -> tuple[np.ndarray, np.ndarray]:
    """Every interior crease as (vertex a, vertex b, facet 1, facet 2) index rows into the
    vertex grid and the facet list, and whether it is a mountain (seen from above)."""
    vid = np.arange((COLS + 1) * (ROWS + 1)).reshape(COLS + 1, ROWS + 1)
    fid = np.arange(COLS * ROWS).reshape(COLS, ROWS)
    rows = []
    for i in range(COLS):  # zigzag creases between facet rows j − 1 and j
        for j in range(1, ROWS):
            rows.append([vid[i, j], vid[i + 1, j], fid[i, j - 1], fid[i, j]])
    for i in range(1, COLS):  # creases between facet columns i − 1 and i
        for j in range(ROWS):
            rows.append([vid[i, j], vid[i, j + 1], fid[i - 1, j], fid[i, j]])
    index = np.array(rows)
    # a crease is a mountain where it stands above the midpoint of its two facets' centers
    p = sheet(np.radians(10)).reshape(-1, 3)
    centers = facets(sheet(np.radians(10))).reshape(-1, 4, 3).mean(axis=1)
    middle = (p[index[:, 0]] + p[index[:, 1]]) / 2
    return index, middle[:, 2] > (centers[index[:, 2], 2] + centers[index[:, 3], 2]) / 2


def ribbons(p: np.ndarray, index: np.ndarray, width: np.ndarray) -> np.ndarray:
    """Strips `width` wide (one per crease) along the creases, half on each of the two facets,
    lifted a hair off them: (creases · 8, 3) vertices, 4 per half."""
    grid = p.reshape(-1, 3)
    corners = facets(p).reshape(-1, 4, 3)
    a, b = grid[index[:, 0]], grid[index[:, 1]]
    halves = []
    for side in (2, 3):
        center = corners[index[:, side]].mean(axis=1)
        normal = np.cross(
            corners[index[:, side], 1] - corners[index[:, side], 0],
            corners[index[:, side], 3] - corners[index[:, side], 0],
        )
        normal /= np.linalg.norm(normal, axis=1, keepdims=True)
        along = (b - a) / np.linalg.norm(b - a, axis=1, keepdims=True)
        inward = center - a - ((center - a) * along).sum(axis=1, keepdims=True) * along
        inward /= np.linalg.norm(inward, axis=1, keepdims=True)
        lift = 0.012 * normal
        side_edge = width[:, None] * inward
        halves.append(np.stack([a, b, b + side_edge, a + side_edge], 1) + lift[:, None])
    return np.concatenate(halves, 1).reshape(-1, 3)


def project(camera: m.Camera, point: np.ndarray) -> np.ndarray:
    """Where a 3D point lands on the screen, in frame coordinates (for HUD labels)."""
    turned = camera_axes(camera.get_phi(), camera.get_theta(), camera.get_gamma())
    q = turned @ (point - camera.frame_center)
    depth = 1 - q[2] / camera.get_focal_distance()
    return np.array([*(camera.get_zoom() * q[:2] / depth), 0.0])


def rgba(color: str) -> np.ndarray:
    return np.array([*m.ManimColor(color).to_rgb(), 1.0])


class MiuraOri(m.ThreeDScene):
    def construct(self) -> None:
        self.camera.background_color = "#0b1020"
        self.camera.light_source.move_to([-6, -9, 7])
        error = max(rigidity(np.radians(d)) for d in np.linspace(0, 89, 90))
        fold = m.ValueTracker(0.0)  # the one degree of freedom, degrees
        crease_width = m.ValueTracker(0.03)
        sweep = m.ValueTracker(0.0)  # the creases are drawn in across the sheet

        def now(extra: float = 0.0) -> np.ndarray:
            """The sheet at the current fold (plus `extra` degrees), in scene units, centered."""
            p = sheet(np.radians(fold.get_value() + extra))
            middle = (p.reshape(-1, 3).max(axis=0) + p.reshape(-1, 3).min(axis=0)) / 2
            return SCALE * (p - middle)

        # the sheet, every facet lit flat; alternate columns ink over as it folds, so the two
        # ways the facets lean show
        odd = np.repeat(np.arange(COLS * ROWS) // ROWS % 2 == 1, 4)[:, None]
        quad = np.array([[0, 1, 2], [0, 2, 3]])
        paper = m.MeshMobject(
            facets(now()),
            (np.arange(COLS * ROWS)[:, None, None] * 4 + quad).reshape(-1, 3),
            shade_in_3d=True,
        )

        def refold(mob: m.MeshMobject) -> None:
            mob.points = facets(now())
            ink = np.clip((fold.get_value() - 8) / 30, 0, 1)
            ink = ink * ink * (3 - 2 * ink)
            tint = rgba(PAPER) + ink * (rgba(INK) - rgba(PAPER))
            mob.paint = mob.paint.but(fill=np.where(odd, tint, rgba(PAPER)))

        refold(paper)
        paper.add_updater(refold)

        # mountain and valley creases, drawn as strips that thin away as the fold deepens
        index, mountain = creases()
        colors = np.where(np.repeat(mountain, 2)[:, None], rgba(MOUNTAIN), rgba(VALLEY))
        flat = now().reshape(-1, 3)
        across = (flat[index[:, 0], :2] + flat[index[:, 1], :2]).sum(axis=1)
        across = (across - across.min()) / (across.max() - across.min())

        def widths() -> np.ndarray:
            drawn = np.clip((1.3 * sweep.get_value() - across) / 0.3, 0, 1)
            return crease_width.get_value() * drawn

        lines = m.MeshMobject(
            ribbons(now(), index, widths()),
            (np.arange(len(index) * 2)[:, None, None] * 4 + quad).reshape(-1, 3),
            vertex_colors=np.repeat(colors, 4, axis=0),
            shade_in_3d=True,
        )
        lines.add_updater(
            lambda mob: setattr(mob, "points", ribbons(now(), index, widths()))
        )

        # the camera keeps the sheet's middle at one spot on the screen, and zooms in as it
        # shrinks (by its measured diagonal)
        spot = np.array([2.5, -0.3])

        def span() -> float:
            p = now()
            return float(np.hypot(p[-1, 0, 0] - p[0, 0, 0], p[0, -1, 1] - p[0, 0, 1]))

        flat_span = span()

        def follow(mob: m.Mobject) -> None:
            cam = self.camera
            cam.zoom_tracker.set_value(0.95 * (flat_span / span()) ** 0.85)
            turned = camera_axes(cam.get_phi(), cam.get_theta(), cam.get_gamma())
            offset = (spot[0] * turned[0] + spot[1] * turned[1]) / cam.get_zoom()
            cam.frame.move_to(-offset)

        # measured from the drawn sheet: its width across the columns, its length along them,
        # and Poisson's ratio from the two a hair further folded
        def measure(extra: float = 0.0) -> tuple[float, float]:
            p = now(extra)
            return float(p[-1, 0, 0] - p[0, 0, 0]), float(p[0, -1, 1] - p[0, 0, 1])

        flat_w, flat_l = measure()  # the sheet starts flat

        def poisson() -> float:
            (w0, l0), (w1, l1) = measure(), measure(0.01)
            return -np.log(l1 / l0) / np.log(w1 / w0)

        # the pull: outward along the width (blue); the sheet answers along its length (gold)
        pulling = m.ValueTracker(0.0)

        def arrows() -> m.VGroup:
            p = now().reshape(-1, 3)
            low, high = p.min(axis=0), p.max(axis=0)
            mid = (low + high) / 2
            out = m.VGroup()
            for axis, color in ((0, "#8ecae6"), (1, "#ffb703")):
                for side, edge in ((-1, low), (1, high)):
                    start = mid.copy()
                    start[axis] = edge[axis] + side * 0.15
                    stop = start.copy()
                    stop[axis] += side * 0.9
                    a, b = project(self.camera, start), project(self.camera, stop)
                    out.add(m.Arrow(a, b, buff=0, stroke_width=6, color=color))
            return out.set_opacity(pulling.get_value())

        pull = m.always_redraw(arrows)

        # heads-up display
        title = m.Text("Miura-ori", font_size=40).to_corner(m.UL)
        notes = [
            "a sheet creased into identical parallelograms",
            "one angle folds every crease at once, rigidly",
            "pull it apart one way: it opens the other way too",
        ]
        subtitles = [m.Text(t, font_size=24).set_color(m.GREY_B) for t in notes]
        for sub in subtitles:
            sub.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)
        legend = m.VGroup()
        for name, color in (("mountain fold", MOUNTAIN), ("valley fold", VALLEY)):
            swatch = m.Line(m.ORIGIN, 0.5 * m.RIGHT, stroke_width=6, color=color)
            legend.add(
                m.VGroup(swatch, m.Text(name, font_size=22)).arrange(m.RIGHT, buff=0.2)
            )
        legend.arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        legend.move_to([-6.7, 2.15, 0], aligned_edge=m.LEFT)
        shown = m.ValueTracker(0.0)

        def dial() -> m.VGroup:
            """The fold angle on a slider, and width and length as bars, both measured."""
            fade = shown.get_value()
            track = m.Line(
                [-6.7, 1.2, 0], [-3.7, 1.2, 0], stroke_width=3, color=m.GREY_C
            )
            at = -6.7 + 3.0 * fold.get_value() / 90
            knob = m.Dot([at, 1.2, 0], 0.09, color=m.WHITE)
            angle = m.MathTex(rf"\theta = {fold.get_value():.0f}^\circ", font_size=30)
            angle.next_to(track, m.RIGHT, 0.3)
            width, length = measure()
            bars = m.VGroup()
            for k, (name, ratio, color) in enumerate(
                (
                    ("width", width / flat_w, "#8ecae6"),
                    ("length", length / flat_l, "#ffb703"),
                )
            ):
                y = 0.45 - 0.55 * k
                word = m.Text(name, font_size=22).move_to(
                    [-6.7, y, 0], aligned_edge=m.LEFT
                )
                box = m.Rectangle(width=2.2 * ratio, height=0.22).set_fill(color, 0.9)
                box.set_stroke(width=0).move_to([-5.45, y, 0], aligned_edge=m.LEFT)
                value = m.Text(f"{100 * ratio:.0f}%", font_size=22).next_to(
                    box, m.RIGHT, 0.15
                )
                bars.add(word, box, value)
            nu = m.MathTex(
                rf"\nu = -\frac{{d L / L}}{{d W / W}} = {poisson():.2f}", font_size=32
            ).move_to([-6.7, -0.95, 0], aligned_edge=m.LEFT)
            group = m.VGroup(track, knob, angle, bars, nu)
            return group.set_opacity(fade)

        panel = m.always_redraw(dial)
        law = m.MathTex(r"\nu = -\tan^2\gamma\,\cos^2\theta", font_size=32)
        law.move_to([-6.7, -1.8, 0], aligned_edge=m.LEFT)
        mantissa, power = f"{error:.0e}".split("e")
        note = m.MathTex(
            rf"\text{{rigid: edges and flatness exact to }} {mantissa} \times"
            rf" 10^{{{int(power)}}}",
            font_size=24,
        ).set_color(m.GREY_B)
        note.move_to([-6.7, -2.45, 0], aligned_edge=m.LEFT)
        closing = m.VGroup(
            m.Text("Koryo Miura's fold opens", font_size=28),
            m.Text("a solar array with one pull", font_size=28),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        closing.move_to([-6.7, -3.3, 0], aligned_edge=m.LEFT)
        self.add_fixed_in_frame_mobjects(
            title, *subtitles, legend, panel, law, note, closing, pull
        )
        self.remove(*subtitles, legend, law, note, closing)

        driver = m.Mobject().add_updater(follow)
        self.set_camera_orientation(phi=54 * m.DEGREES, theta=-104 * m.DEGREES)
        self.begin_ambient_camera_rotation(rate=0.03)
        follow(driver)
        self.add(paper, lines, driver)
        # 0–4.5 s: the flat sheet and its creases
        self.play(m.FadeIn(subtitles[0]), run_time=1.0)
        self.play(sweep.animate.set_value(1.0), m.FadeIn(legend), run_time=1.8)
        self.play(shown.animate.set_value(1.0), run_time=1.0)
        self.wait(0.8)
        # 4.5–14 s: it folds, every crease at once
        self.play(m.FadeOut(subtitles[0]), run_time=0.3)
        self.play(m.FadeIn(subtitles[1]), run_time=0.4)
        self.play(
            fold.animate.set_value(82),
            crease_width.animate(rate_func=lambda t: min(1.0, 3 * t)).set_value(0.0),
            m.FadeOut(legend),
            run_time=8.5,
        )
        self.wait(1.0)
        # 15–23 s: pulled apart along its width, it grows along its length too
        self.play(m.FadeOut(subtitles[1]), run_time=0.3)
        self.play(m.FadeIn(subtitles[2]), pulling.animate.set_value(1.0), run_time=0.6)
        self.play(fold.animate.set_value(28), m.FadeIn(law), run_time=6.5)
        self.play(pulling.animate.set_value(0.0), run_time=0.6)
        # 23–30.5 s: the poster
        self.play(
            m.FadeIn(note), m.FadeIn(closing), fold.animate.set_value(45), run_time=3
        )
        self.wait(30.5 - self.time)


if __name__ == "__main__":
    MiuraOri().render("miura_ori.mp4")

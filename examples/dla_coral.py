"""Diffusion-limited aggregation: random walkers build a coral.

Start with one particle. Release another far away and let it wander at random, one lattice step at
a time, until it touches the cluster, where it sticks. Repeat 18,000 times (Witten & Sander,
1981). The walkers almost never reach the fjords: the tips catch them first, so the tips grow and
branch while the inside stays empty. The cluster is a fractal: its mass grows like its radius to
a power D, measured here from the cluster itself (radius of gyration against particle count, on
log–log axes), close to the known D ≈ 2.5 for three dimensions, between a surface (2) and a solid (3).
Walkers far from the cluster take long jumps to the cluster's bounding sphere, which changes nothing
about where they land but saves most of the walking.
"""

import numpy as np

import manimgx as m

COUNT = 18000
SIZE = 200  # the lattice, SIZE³ cells
CELL = 0.052  # screen units per lattice cell
STOPS = ["#3c096c", "#7b2cbf", "#c9184a", "#ff5d8f", "#ff9e00", "#ffe066"]  # old → new
MOVES = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]])


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


class Cluster:
    """The growing cluster on a cubic lattice, and the walkers wandering toward it."""

    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng
        self.center = SIZE // 2
        self.taken = np.zeros((SIZE,) * 3, bool)
        # the cells next to the cluster: a walker that steps onto one sticks
        self.sticky = np.zeros((SIZE,) * 3, bool)
        self.cells: list[tuple[int, int, int]] = []
        self.radius = 1.0
        self.stick((self.center, self.center, self.center))

    def stick(self, cell: tuple[int, int, int]) -> None:
        self.taken[cell] = True
        for dx, dy, dz in MOVES.tolist():
            self.sticky[cell[0] + dx, cell[1] + dy, cell[2] + dz] = True
        self.cells.append(cell)
        self.radius = max(
            self.radius, float(np.linalg.norm(np.array(cell) - self.center))
        )

    def launch(self, n: int) -> np.ndarray:
        v = self.rng.normal(size=(n, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        return np.round(self.center + (self.radius + 8) * v).astype(np.int64)

    def step(self, walkers: np.ndarray) -> np.ndarray:
        """One move for every walker: a lattice step, or, when the cluster's bounding sphere is
        far, a jump straight toward it through the free room (its landing spot is uniform).
        """
        room = np.linalg.norm(walkers - self.center, axis=1) - self.radius - 3
        moves = MOVES[self.rng.integers(0, 6, len(walkers))]
        far = np.flatnonzero(room > 2)
        v = self.rng.normal(size=(len(far), 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        moves[far] = np.round(room[far, None] * v).astype(np.int64)
        walkers = walkers + moves
        lost = np.linalg.norm(walkers - self.center, axis=1) > min(
            2 * self.radius + 25, SIZE / 2 - 3
        )
        walkers[lost] = self.launch(int(lost.sum()))
        return walkers

    def grow(self, count: int) -> None:
        walkers = self.launch(20)
        while len(self.cells) < count:
            want = min(3000, 20 + len(self.cells) // 5)  # more walkers as it grows
            if len(walkers) < want:
                walkers = np.concatenate([walkers, self.launch(want - len(walkers))])
            walkers = self.step(walkers)
            x, y, z = walkers.T
            hit = np.flatnonzero(self.sticky[x, y, z] & ~self.taken[x, y, z])
            for i in hit:
                cell = (int(walkers[i, 0]), int(walkers[i, 1]), int(walkers[i, 2]))
                if not self.taken[cell] and len(self.cells) < count:
                    self.stick(cell)
            walkers[hit] = self.launch(len(hit))

    def wander(self) -> np.ndarray:
        """One more walker's whole path, from launch to where it would stick (lattice steps
        only; it is not stuck: see `stick`)."""
        walker = self.launch(1)
        path = [walker[0].copy()]
        while not self.sticky[tuple(walker[0])]:
            walker = walker + MOVES[self.rng.integers(0, 6, 1)]
            if np.linalg.norm(walker[0] - self.center) > self.radius + 12:
                walker = self.launch(1)
                path = []
            path.append(walker[0].copy())
        return np.array(path, float)


def beads(centers: np.ndarray, radius: float) -> tuple[np.ndarray, np.ndarray]:
    """A small octahedron at every center, in order (smooth-shaded, it reads as a bead):
    vertices and triangles, wound outward."""
    corners = np.concatenate([np.eye(3), -np.eye(3)])  # +x +y +z −x −y −z
    faces = []
    for sx, sy, sz in np.ndindex(2, 2, 2):
        a, b, c = 3 * sx, 1 + 3 * sy, 2 + 3 * sz
        faces.append([a, b, c] if (sx + sy + sz) % 2 == 0 else [a, c, b])
    verts = (centers[:, None, :] + radius * corners[None]).reshape(-1, 3)
    tris = (np.array(faces)[None] + 6 * np.arange(len(centers))[:, None, None]).reshape(
        -1, 3
    )
    return verts, tris


class DlaCoral(m.ThreeDScene):
    def construct(self) -> None:
        cluster = Cluster(np.random.default_rng(5))
        cluster.grow(COUNT)
        cells = np.array(cluster.cells, float) - cluster.center
        centers = CELL * cells
        verts, tris = beads(centers, 0.62 * CELL)
        coral = m.MeshMobject(verts, tris, shade_in_3d=True)
        coral.paint = coral.paint.but(
            fill=np.repeat(colormap(np.linspace(0, 1, COUNT), STOPS), 6, axis=0)
        )

        # the mass–radius law, measured: radius of gyration of the first n particles
        counts = np.unique(np.geomspace(50, COUNT, 24).astype(int))
        spread = np.array(
            [
                np.sqrt(((cells[:n] - cells[:n].mean(0)) ** 2).sum(1).mean())
                for n in counts
            ]
        )
        scaling = counts >= 300  # past the first few hundred, where the law has set in
        slope = 1 / np.polyfit(np.log(counts[scaling]), np.log(spread[scaling]), 1)[0]
        grown = m.ValueTracker(1.0)
        plot = (
            m.Axes(
                x_range=(0.8, 3.6, 1),
                y_range=(3.5, 10.0, 1),
                x_length=2.8,
                y_length=2.4,
                tips=False,
                axis_config={"stroke_width": 1.5, "include_ticks": False},
            )
            .to_corner(m.DR)
            .shift(0.4 * m.UP + 0.2 * m.LEFT)
        )
        plot_names = m.VGroup(
            m.MathTex(r"\log R_g", font_size=24).next_to(
                plot.x_axis, m.DOWN, buff=0.12
            ),
            m.MathTex(r"\log N", font_size=24).next_to(plot.y_axis, m.UP, buff=0.1),
        )

        hud = m.ValueTracker(
            1.0
        )  # the plot's opacity (it steps aside for the close-up)

        def measured() -> m.VGroup:
            shown = counts <= grown.get_value()
            return m.VGroup(
                *[
                    m.Dot(
                        plot.c2p(float(np.log(s)), float(np.log(n))),
                        radius=0.045,
                        color=m.GOLD,
                    )
                    for n, s in zip(counts[shown], spread[shown])
                ]
            ).set_opacity(hud.get_value())

        dots = m.always_redraw(measured)
        fit_value = m.DecimalNumber(slope, num_decimal_places=2, font_size=30)
        fit_row = m.VGroup(
            m.MathTex(r"N \propto R_g^{D},\ D =", font_size=30), fit_value
        )
        fit_row.arrange(m.RIGHT, buff=0.12).next_to(plot, m.UP, buff=0.45)
        unit = m.Text("particles", font_size=24).to_corner(m.UR)
        tally = m.Integer(1, font_size=30)

        def count_up(d: m.Mobject) -> None:
            assert isinstance(d, m.Integer)
            d.set_value(int(grown.get_value()))
            d.next_to(unit, m.LEFT, buff=0.15)  # (set_value re-centers the number)

        tally.add_updater(count_up)
        tally_row = m.VGroup(tally, unit)

        title = m.Text("Random walkers build a coral", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "each wanders until it touches the cluster, then sticks (Witten & Sander,"
            " 1981)",
            font_size=22,
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        self.add_fixed_in_frame_mobjects(
            title, subtitle, tally_row, plot, plot_names, dots, fit_row
        )
        self.remove(fit_row)

        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-60 * m.DEGREES, zoom=2.4)
        self.begin_ambient_camera_rotation(rate=0.1)
        self.add(coral)
        # grow: particles in the order they stuck, the camera pulling back with the cluster
        self.play(
            m.Create(coral, rate_func=lambda u: u**1.6),
            grown.animate(rate_func=lambda u: u**1.6).set_value(COUNT),
            self.camera.zoom_tracker.animate.set_value(0.95),
            run_time=19,
        )
        self.play(m.FadeIn(fit_row), run_time=1)
        # one more walker, followed all the way in, up close: of a dozen, the one that lands on
        # the tip that faces the camera
        phi, theta = self.camera.get_phi(), self.camera.get_theta()
        toward = np.array(
            [np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)]
        )
        paths = [cluster.wander() for _ in range(12)]
        chosen = max(paths, key=lambda p: float((p[-1] - cluster.center) @ toward))
        end = chosen[-1].astype(int)
        cluster.stick((int(end[0]), int(end[1]), int(end[2])))
        path = CELL * (chosen - cluster.center)
        trail = m.VMobject(stroke_color=m.WHITE, stroke_width=2, shade_in_3d=True)
        trail.set_points_as_corners(path[:: max(1, len(path) // 500)])
        bead_verts, bead_tris = beads(path[-1:], 0.75 * CELL)
        bead = m.MeshMobject(
            bead_verts, bead_tris, shade_in_3d=True, fill_color=m.WHITE
        )
        aside = m.VGroup(title, subtitle, plot, plot_names, fit_row)
        self.stop_ambient_camera_rotation()
        self.move_camera(
            frame_center=path[-1],
            zoom=3.0,
            added_anims=[aside.animate.set_opacity(0.0), hud.animate.set_value(0.0)],
            run_time=2,
        )
        self.play(m.Create(trail), run_time=3, rate_func=m.linear)
        self.add(bead)
        self.play(m.FadeOut(trail), run_time=0.6)
        self.move_camera(
            frame_center=m.ORIGIN,
            zoom=0.95,
            added_anims=[aside.animate.set_opacity(1.0), hud.animate.set_value(1.0)],
            run_time=2.4,
        )
        self.begin_ambient_camera_rotation(rate=0.1)
        closing = (
            m.Text(
                f"D = {slope:.2f}: more than a surface, less than a solid", font_size=26
            )
            .to_edge(m.DOWN, buff=0.35)
            .shift(1.5 * m.LEFT)
        )
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing), run_time=1)
        self.wait(2)


if __name__ == "__main__":
    DlaCoral().render("dla_coral.mp4")

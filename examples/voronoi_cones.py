"""Voronoi cells are crystals grown from seeds — and mountains of cones seen from above.

Plant sixteen seeds at once and let each grow a crystal at the same speed. A point belongs to
the grain that reaches it first, so the grains meet along the Voronoi diagram: every point goes
to its nearest seed. Draw arrival time as depth and each grain becomes a cone; the diagram is the
lower envelope of the cones, which the GPU's depth buffer computes exactly, pixel by pixel. A
dark plane marks the present moment and hides whatever has not been reached yet, so from above
you watch the grains grow. Then time runs back, and one seed gets a head start: its cone rises,
and its borders bend into hyperbolas (a Johnson–Mehl tessellation, as when metal crystallizes
from nuclei that appear at different times).
"""

import numpy as np

import manimgx as m

N_SEEDS = 16
TOP = 3.0  # the height of time zero
SLOPE = (
    1.6  # height lost per unit of growth: arrival time t is drawn at TOP − SLOPE · t
)
WIDTH, HEIGHT = 12.4, 6.6  # the dish the crystals grow in
GRID = (248, 132)
PALETTE = [
    "#ef476f",
    "#ffd166",
    "#06d6a0",
    "#118ab2",
    "#8338ec",
    "#ff9f1c",
    "#2ec4b6",
    "#e76f51",
    "#a7c957",
    "#f15bb5",
    "#00bbf9",
    "#fee440",
    "#9b5de5",
    "#00f5d4",
    "#f77f00",
    "#4cc9f0",
]
DARK = "#0b0f14"


def seeds(rng: np.random.Generator) -> np.ndarray:
    """Well-spread seeds: each the best of 30 random candidates (Mitchell's best candidate)."""
    low, high = (
        [-WIDTH / 2 + 0.7, -HEIGHT / 2 + 0.7],
        [WIDTH / 2 - 0.7, HEIGHT / 2 - 0.7],
    )
    points = [rng.uniform(low, high)]
    while len(points) < N_SEEDS:
        candidates = rng.uniform(low, high, (30, 2))
        distance = np.linalg.norm(
            candidates[:, None] - np.array(points)[None], axis=2
        ).min(axis=1)
        points.append(candidates[np.argmax(distance)])
    return np.array(points)


def grid_mesh(nu: int, nv: int, fill_color: str = "#ffffff") -> m.MeshMobject:
    """A smooth lit mesh over an (nu + 1) × (nv + 1) grid of vertices (vertex i·(nv + 1) + j),
    each cell two triangles; its points are set by whoever shapes it."""
    idx = np.arange((nu + 1) * (nv + 1)).reshape(nu + 1, nv + 1)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    cells = np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], 2)
    return m.MeshMobject(
        np.zeros(((nu + 1) * (nv + 1), 3)),
        cells.reshape(-1, 3),
        shade_in_3d=True,
        fill_color=fill_color,
    )


class Grains(m.Group):
    """The cones of all the grains, z = TOP − SLOPE · (tᵢ + |p − sᵢ|) over the dish, each cut down
    to the cell it wins (plus one triangle of margin, hidden under its neighbours) — so only the
    envelope exists, from any side. The cells are recomputed when a start changes.
    """

    def __init__(self, sites: np.ndarray, starts: list[m.ValueTracker]) -> None:
        xs = np.linspace(-WIDTH / 2, WIDTH / 2, GRID[0] + 1)
        ys = np.linspace(-HEIGHT / 2, HEIGHT / 2, GRID[1] + 1)
        self.gx, self.gy = np.meshgrid(xs, ys, indexing="ij")
        self.distance = np.hypot(
            self.gx[None] - sites[:, 0, None, None],
            self.gy[None] - sites[:, 1, None, None],
        )
        self.starts = starts
        self.drawn: list[float] = []  # the starts the cells were last made for
        self.cones = [
            grid_mesh(*GRID, fill_color=color) for color in PALETTE[: len(sites)]
        ]
        self.all_triangles = self.cones[0].triangles
        super().__init__(*self.cones)
        self.add_updater(lambda g: g.refresh())
        self.refresh()

    def refresh(self) -> None:
        starts = [s.get_value() for s in self.starts]
        if starts == self.drawn:
            return
        self.drawn = starts
        arrival = np.array(starts)[:, None, None] + self.distance
        owner = np.argmin(arrival, axis=0).ravel()[self.all_triangles]  # (triangles, 3)
        for k, mesh in enumerate(self.cones):
            z = TOP - SLOPE * arrival[k]
            mesh.points = np.stack([self.gx, self.gy, z], -1).reshape(-1, 3)
            mesh.triangles = self.all_triangles[(owner == k).any(axis=1)]


class VoronoiCones(m.ThreeDScene):
    def construct(self) -> None:
        rng = np.random.default_rng(1644)
        sites = seeds(rng)
        starts = [m.ValueTracker(0.0) for _ in sites]
        cones = Grains(sites, starts)
        dots = m.Group(
            *[m.Dot3D(np.array([*s, TOP]), radius=0.06, color=m.WHITE) for s in sites]
        )
        for dot, start, site in zip(dots, starts, sites, strict=True):
            dot.add_updater(
                lambda d, site=site, start=start: d.move_to(
                    np.array([*site, TOP - SLOPE * start.get_value() + 0.02])
                )
            )

        # the present moment: a dark plane at the height of time T hides every point not yet reached
        now = m.ValueTracker(0.0)
        shown = m.ValueTracker(
            1.0
        )  # the plane's opacity (it is hidden while the camera is tilted)
        present = m.Rectangle(
            width=WIDTH + 0.02,
            height=HEIGHT + 0.02,
            stroke_width=0,
            fill_color=DARK,
            fill_opacity=1,
        )

        def settle(plane: m.Mobject) -> None:
            plane.move_to(np.array([0.0, 0.0, TOP - SLOPE * now.get_value()]))
            plane.set_fill(opacity=shown.get_value())

        present.add_updater(settle)

        title = m.Text("Crystals grown from seeds", font_size=36).to_corner(m.UL)
        subtitle = m.Text(
            "every point joins the grain that reaches it first", font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )
        header = m.VGroup(title, subtitle)
        backing = m.BackgroundRectangle(header, color=DARK, fill_opacity=0.9, buff=0.12)
        self.add_fixed_in_frame_mobjects(backing, header)

        def note(tex: str) -> m.VGroup:
            label = m.MathTex(tex, font_size=32).to_corner(m.UR)
            group = m.VGroup(
                m.BackgroundRectangle(label, color=DARK, fill_opacity=0.9, buff=0.1),
                label,
            )
            self.add_fixed_in_frame_mobjects(group)
            self.remove(group)
            return group

        # 0–7 s: from above: the grains grow at equal speed and meet along the Voronoi diagram
        self.set_camera_orientation(
            phi=0,
            theta=-90 * m.DEGREES,
            focal_distance=40,
            zoom=1.08,
            frame_center=np.array([0, -0.25, 0]),
        )
        self.add(cones, present, dots)
        self.play(now.animate.set_value(3.2), run_time=6.5, rate_func=m.linear)
        self.wait(0.5)

        # 7–14 s: tilt: time is depth, and every grain is a cone
        equal = note(r"\text{arrival time} = |p - s_i|")
        self.move_camera(
            phi=55 * m.DEGREES,
            theta=-62 * m.DEGREES,
            focal_distance=24,
            zoom=0.8,
            frame_center=np.array([0, 0, 0.4]),
            added_anims=[shown.animate.set_value(0.0), m.FadeIn(equal)],
            run_time=4,
        )
        self.play(
            self.camera.theta_tracker.animate.set_value(-30 * m.DEGREES), run_time=3
        )

        # 14–18 s: back to the top; time runs back to zero; one seed gets a head start
        chosen = int(np.argmin(np.linalg.norm(sites - np.array([0.5, 0.3]), axis=1)))
        head = note(r"\text{arrival} = t_i + |p - s_i|")
        self.move_camera(
            phi=0,
            theta=-90 * m.DEGREES,
            focal_distance=40,
            zoom=1.08,
            frame_center=np.array([0, -0.25, 0]),
            added_anims=[
                now.animate.set_value(0.0),
                shown.animate.set_value(1.0),
                m.FadeOut(equal),
            ],
            run_time=3.5,
        )
        self.play(
            starts[chosen].animate.set_value(-1.15),
            m.FadeIn(head),
            m.Flash(dots[chosen], color=m.WHITE),
            run_time=1,
        )

        # 18–25 s: grow again: the early grain wins more ground, with curved borders
        self.play(now.animate.set_value(3.3), run_time=6.5, rate_func=m.linear)

        # 25–30 s: the poster
        closing = m.Text(
            "equal starts: straight borders · a head start: hyperbolas", font_size=26
        ).to_edge(m.DOWN, buff=0.3)
        self.add_fixed_in_frame_mobjects(
            m.BackgroundRectangle(closing, color=DARK, fill_opacity=0.9, buff=0.1),
            closing,
        )
        self.play(
            m.FadeIn(closing),
            self.camera.zoom_tracker.animate.set_value(1.12),
            run_time=4.5,
        )


if __name__ == "__main__":
    VoronoiCones().render("voronoi_cones.mp4")

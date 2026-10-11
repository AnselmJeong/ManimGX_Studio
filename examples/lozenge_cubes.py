"""Stacks of cubes and the arctic circle.

A tiling of a hexagon by three kinds of lozenges is secretly a stack of cubes in the corner of a
box, seen along the box's diagonal: each lozenge is a top, a left or a right face. Pick a stack
uniformly at random among all of them (here: by Glauber dynamics — add or remove a cube wherever
the stack stays a stack, at random, many times). For a big box something strange happens: near
the corners the tiling freezes into a single orientation, and all the disorder lives inside the
circle inscribed in the hexagon — the arctic circle (Cohn, Larsen & Propp, 1998). And whatever
the pile, each kind of lozenge appears exactly n² times: they are the tops, lefts and rights of
the cubes' faces seen along each axis (David & Tomei, 1989) — counted live from the faces drawn.
"""

import numpy as np

import manimgx as m

N = 30  # the big box is N × N × N
SMALL = 6  # the warm-up box
COLORS = ["#f4d35e", "#ee6352", "#3c91e6"]  # top, facing +x, facing +y
INSET = 0.07  # each face is drawn a little smaller, so the tiles' edges show
SIZE = 3.5  # the big box's side on screen


def glauber(heights: np.ndarray, rng: np.random.Generator, sweeps: int) -> None:
    """Heat-bath moves on a plane partition (heights non-increasing away from the corner, within
    0 … n): at every cell of one checkerboard color at once, try to add or remove a cube.
    """
    n = heights.shape[0]
    i, j = np.indices(heights.shape)
    for _ in range(sweeps):
        for parity in (0, 1):
            h = heights
            above = np.minimum(
                np.pad(h, ((1, 0), (0, 0)), constant_values=n)[:-1],
                np.pad(h, ((0, 0), (1, 0)), constant_values=n)[:, :-1],
            )
            below = np.maximum(
                np.pad(h, ((0, 1), (0, 0)))[1:], np.pad(h, ((0, 0), (0, 1)))[:, 1:]
            )
            ours = (i + j) % 2 == parity
            coin = rng.random(h.shape) < 0.5
            h[ours & coin & (h < above)] += 1
            h[ours & ~coin & (h > below)] -= 1


def unit_faces(corner: np.ndarray, du: np.ndarray, dv: np.ndarray) -> np.ndarray:
    """Quads (F, 4, 3) from their corners and edge vectors, shrunk by INSET toward their centers."""
    a, b = INSET, 1 - INSET
    return np.stack(
        [
            corner + a * du + a * dv,
            corner + b * du + a * dv,
            corner + b * du + b * dv,
            corner + a * du + b * dv,
        ],
        axis=1,
    )


def visible_faces(h: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Every unit face seen from the (1, 1, 1) direction — the lozenges: the tops of the columns
    (and of the bare floor), and the walls facing +x and +y at every plane x = i, y = j between a
    column and the one in front of it (behind the first column: the box's back wall, height n;
    in front of the last: nothing). (quads, which of the 3 kinds)."""
    n = h.shape[0]
    i, j = np.indices(h.shape)
    quads = [
        unit_faces(
            np.stack([i, j, h], -1).reshape(-1, 3).astype(float),
            np.array([1.0, 0, 0]),
            np.array([0, 1.0, 0]),
        )
    ]
    kinds = [np.zeros(n * n, int)]
    for kind, axis in ((1, 0), (2, 1)):
        behind = np.moveaxis(
            np.pad(np.moveaxis(h, axis, 0), ((1, 0), (0, 0)), constant_values=n),
            0,
            axis,
        )
        front = np.moveaxis(np.pad(np.moveaxis(h, axis, 0), ((0, 1), (0, 0))), 0, axis)
        lower, higher = (
            front.ravel(),
            behind.ravel(),
        )  # the wall at each plane spans lower … higher
        cells = np.repeat(np.arange(len(lower)), higher - lower)
        level = np.concatenate(
            [np.arange(lo, hi) for lo, hi in zip(lower, higher, strict=True)]
        )
        # the grid index (i, j) of each face's cell: the plane is i for +x walls, j for +y
        ci, cj = np.unravel_index(cells, front.shape)
        corner = np.stack([ci, cj, level], -1)
        du = np.array([0, 1.0, 0]) if axis == 0 else np.array([1.0, 0, 0])
        quads.append(unit_faces(corner.astype(float), du, np.array([0, 0, 1.0])))
        kinds.append(np.full(len(cells), kind))
    return np.concatenate(quads), np.concatenate(kinds)


def mesh_arrays(
    h: np.ndarray, colors: np.ndarray, size: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The visible faces of the pile in a box of side `size` on screen, centered at the origin."""
    quads, kinds = visible_faces(h)
    n = h.shape[0]
    verts = (quads.reshape(-1, 3) - n / 2) * size / n
    base = np.arange(len(quads))[:, None] * 4
    tris = np.concatenate([base + [0, 1, 2], base + [0, 2, 3]])
    rows = np.repeat(colors[kinds], 4, axis=0)
    return verts, tris, rows


class Pile(m.MeshMobject):
    """A pile of cubes in the corner of an n × n × n box, drawn `size` wide, shaken by Glauber
    dynamics at `rate` sweeps per tick of the simulation clock. It is rebuilt every tick, so it
    fades by its `shown` tracker (read at each rebuild), not by FadeIn/FadeOut."""

    def __init__(
        self, heights: np.ndarray, size: float, rng: np.random.Generator
    ) -> None:
        self.heights, self.size, self.rng, self.rate = heights, size, rng, 0
        self.shown = m.ValueTracker(1.0)
        self.palette = np.array([m.ManimColor(c).to_rgba() for c in COLORS])
        verts, tris, rows = mesh_arrays(heights, self.palette, size)
        super().__init__(verts, tris, vertex_colors=rows, shade_in_3d=True)
        self.add_updater(lambda mob, dt: self.evolve())

    def evolve(self) -> None:
        if self.rate:
            glauber(self.heights, self.rng, self.rate)
        self.points, self.triangles, rows = mesh_arrays(
            self.heights, self.palette, self.size
        )
        rows[:, 3] *= self.shown.get_value()
        self.paint = self.paint.but(fill=rows)

    def counts(self) -> list[int]:
        """How many lozenges of each kind the pile shows (its faces, 4 vertices each)."""
        rows = self.paint.fill[::4, :3]
        return [
            int(np.all(np.isclose(rows, c[:3]), axis=1).sum()) for c in self.palette
        ]


class LozengeCubes(m.ThreeDScene):
    def construct(self) -> None:
        rng = np.random.default_rng(1998)
        title = m.Text("Stacks of cubes and the arctic circle", font_size=36).to_corner(
            m.UL
        )
        subtitle = m.Text(
            "a lozenge tiling is a pile of cubes seen along the diagonal", font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )
        self.add_fixed_in_frame_mobjects(title, subtitle)

        # along the box's diagonal (1, 1, 1), nearly orthographic: the pile looks flat, a tiling
        # of a hexagon by three kinds of rhombi
        center = np.array([0.0, 0.0, 0.55])
        tilt = float(np.arccos(1 / np.sqrt(3)))
        self.set_camera_orientation(
            phi=tilt,
            theta=45 * m.DEGREES,
            gamma=0,
            focal_distance=120,
            zoom=1.0,
            frame_center=center,
        )

        def on_diagonal(seconds: float) -> None:
            self.move_camera(
                phi=tilt,
                theta=45 * m.DEGREES,
                gamma=0,
                focal_distance=120,
                zoom=1.0,
                run_time=seconds,
            )

        # 0–8 s: a small tiling … is a small pile of cubes
        small_heights = np.zeros((SMALL, SMALL), int)
        glauber(small_heights, rng, 400)
        small = Pile(small_heights, 3.3, rng)
        small.rate = 1  # the tiling flips here and there as cubes come and go
        self.add(small)
        self.wait(2.5)
        small.rate = 0
        self.move_camera(
            phi=64 * m.DEGREES,
            theta=5 * m.DEGREES,
            focal_distance=14,
            zoom=1.1,
            run_time=3,
        )
        small.rate = 1
        self.wait(1.5)
        small.rate = 0
        on_diagonal(2)

        # 8–19 s: a big box: cubes rain in at random until the pile is a typical one
        big = Pile(np.zeros((N, N), int), SIZE, rng)
        big.shown.set_value(0.0)
        self.add(big)
        self.play(
            small.shown.animate.set_value(0.0),
            big.shown.animate.set_value(1.0),
            run_time=0.8,
        )
        self.remove(small)
        big.rate = 16
        counters = m.VGroup()
        for kind, color in enumerate(COLORS):
            value = m.Integer(0, font_size=30, color=color)
            value.add_updater(lambda d, kind=kind: d.set_value(big.counts()[kind]))
            swatch = m.Square(0.22, fill_color=color, fill_opacity=1, stroke_width=0)
            counters.add(m.VGroup(swatch, value).arrange(m.RIGHT, buff=0.15))
        counters.arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        note = m.MathTex(r"= n^2 \text{ each}", font_size=30)
        note.next_to(counters, m.DOWN, aligned_edge=m.LEFT, buff=0.25)
        m.VGroup(counters, note).to_corner(m.UR).shift(0.25 * m.DOWN)
        self.add_fixed_in_frame_mobjects(counters, note)
        self.remove(note)
        self.wait(4)
        self.move_camera(
            phi=62 * m.DEGREES,
            theta=15 * m.DEGREES,
            focal_distance=16,
            zoom=1.0,
            run_time=3.5,
        )
        self.move_camera(theta=75 * m.DEGREES, added_anims=[m.FadeIn(note)], run_time=3)

        # 19–30 s: back on the diagonal: frozen corners, disorder inside the inscribed circle
        on_diagonal(3)
        big.rate = 2
        radius = SIZE / np.sqrt(2)  # the inradius of the hexagon the box projects to
        toward = np.array([1.0, 1.0, 1.0]) / np.sqrt(3)
        e1 = np.array([1.0, -1.0, 0.0]) / np.sqrt(2)
        e2 = np.cross(toward, e1)
        t = np.linspace(0, m.TAU, 241)
        circle = m.VMobject(stroke_color=m.WHITE, stroke_width=5).set_points_as_corners(
            3.0 * toward + radius * (np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2)
        )
        self.play(m.Create(circle), run_time=2)
        closing = m.Text(
            "Outside the inscribed circle, the tiling freezes (Cohn, Larsen & Propp,"
            " 1998)",
            font_size=24,
        )
        closing.to_edge(m.DOWN, buff=0.25)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing), run_time=1)
        self.wait(4.5)


if __name__ == "__main__":
    LozengeCubes().render("lozenge_cubes.mp4")

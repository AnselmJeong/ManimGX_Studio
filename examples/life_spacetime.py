"""The Game of Life in spacetime: stack the generations and gliders become staircases.

Conway's Game of Life: a live cell survives with two or three live neighbours, a dead one comes
alive with exactly three. Bill Gosper's glider gun (1970) is a pattern that fires a glider every
30 generations — the first proof that a finite pattern can grow forever. Stack each generation
on top of the one before, so height is time, and every cell becomes a column that lasts as long
as the cell does: the gun is a tower that repeats every 30 layers, the blocks that hold it in
place are pillars, and each glider is a staircase leaning away at one cell per four generations
in each direction — the speed of light of this universe is one cell per generation; gliders
travel at a quarter of it, diagonally.
"""

import numpy as np

import manimgx as m

GUN = [
    (5, 1),
    (5, 2),
    (6, 1),
    (6, 2),
    (5, 11),
    (6, 11),
    (7, 11),
    (4, 12),
    (8, 12),
    (3, 13),
    (9, 13),
    (3, 14),
    (9, 14),
    (6, 15),
    (4, 16),
    (8, 16),
    (5, 17),
    (6, 17),
    (7, 17),
    (6, 18),
    (3, 21),
    (4, 21),
    (5, 21),
    (3, 22),
    (4, 22),
    (5, 22),
    (2, 23),
    (6, 23),
    (1, 25),
    (2, 25),
    (6, 25),
    (7, 25),
    (3, 35),
    (4, 35),
    (3, 36),
    (4, 36),
]
SIZE = 64  # the board
GENERATIONS = 126
CELL = 0.105  # a cell's side on screen
LAYER = 0.042  # the height of one generation
STOPS = ["#9d4edd", "#4361ee", "#4cc9f0", "#80ffdb", "#ffd166", "#ff7b54"]
FOCUS = np.array([-0.2, 1.05, 0.0])  # the middle of the action: the gun and its gliders


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


def history() -> np.ndarray:
    """Every generation of the gun on the board: (GENERATIONS, SIZE, SIZE) booleans."""
    board = np.zeros((SIZE, SIZE), bool)
    for r, c in GUN:
        board[r + 3, c + 2] = True
    frames = []
    for _ in range(GENERATIONS):
        frames.append(board.copy())
        padded = np.pad(board, 1)
        neighbours = sum(
            padded[1 + dy : SIZE + 1 + dy, 1 + dx : SIZE + 1 + dx].astype(int)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if (dy, dx) != (0, 0)
        )
        board = (neighbours == 3) | (board & (neighbours == 2))
    return np.array(frames)


def runs(frames: np.ndarray) -> np.ndarray:
    """Every stretch of generations a cell stays alive: rows (row, column, first, last)."""
    alive = np.pad(frames, ((1, 1), (0, 0), (0, 0)))
    starts = np.argwhere(alive[1:-1] & ~alive[:-2])
    ends = np.argwhere(alive[1:-1] & ~alive[2:])
    starts = starts[np.lexsort((starts[:, 0], starts[:, 2], starts[:, 1]))]
    ends = ends[np.lexsort((ends[:, 0], ends[:, 2], ends[:, 1]))]
    return np.column_stack([starts[:, 1], starts[:, 2], starts[:, 0], ends[:, 0]])


# the six faces of a unit box, as corner indices (bit 0: x, bit 1: y, bit 2: z), outward
BOX_FACES = np.array(
    [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
)


def columns(
    spans: np.ndarray, now: float, depth: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The columns alive between generations now − depth and now, the oldest shown at height 0:
    vertices, triangles, colors (by generation)."""
    first = np.maximum(spans[:, 2], now - depth)
    last = np.minimum(spans[:, 3] + 1, now + 1)
    keep = last > first
    s, first, last = spans[keep], first[keep], last[keep]
    base = max(now - depth, 0.0)
    x0 = (s[:, 1] - SIZE / 2) * CELL
    y0 = (SIZE / 2 - s[:, 0]) * CELL
    inset = 0.08 * CELL
    lo = np.stack([x0 + inset, y0 - CELL + inset, (first - base) * LAYER], 1)
    hi = np.stack(
        [
            x0 + CELL - inset,
            y0 - inset,
            np.maximum((last - base) * LAYER, (first - base) * LAYER + 0.012),
        ],
        1,
    )
    bits = np.array([[(k >> 0) & 1, (k >> 1) & 1, (k >> 2) & 1] for k in range(8)])
    corners = lo[:, None, :] + bits[None] * (hi - lo)[:, None, :]  # (columns, 8, 3)
    quads = corners[:, BOX_FACES]  # (columns, 6, 4, 3)
    verts = quads.reshape(-1, 3)
    faces = np.arange(len(s) * 6)[:, None] * 4
    tris = np.concatenate([faces + [0, 1, 2], faces + [0, 2, 3]])
    generation = np.where(
        bits[BOX_FACES][..., 2] == 1, last[:, None, None] - 1, first[:, None, None]
    )
    rows = colormap((generation / GENERATIONS).reshape(-1), STOPS)
    return verts, tris, rows


class LifeSpacetime(m.ThreeDScene):
    def construct(self) -> None:
        spans = runs(history())
        now = m.ValueTracker(0.0)
        depth = m.ValueTracker(
            0.0
        )  # how many past generations stand below the present one
        stack = m.MeshMobject(*columns(spans, 0.0, 0.0)[:2], shade_in_3d=True)

        def rebuild(mob: m.Mobject) -> None:
            assert isinstance(mob, m.MeshMobject)
            g = float(np.floor(now.get_value()))
            verts, tris, rows = columns(spans, g, float(np.floor(depth.get_value())))
            mob.points, mob.triangles = verts, tris
            mob.paint = mob.paint.but(fill=rows)

        rebuild(stack)
        stack.add_updater(rebuild)
        board = m.Square(
            side_length=SIZE * CELL,
            stroke_color=m.GREY_D,
            stroke_width=1.5,
            fill_color="#0b0f1a",
            fill_opacity=1,
        )
        board.shift(0.001 * m.IN)

        title = m.Text("The Game of Life in spacetime", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "Gosper's glider gun: a glider every 30 generations", font_size=22
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        generation = m.Integer(0, font_size=30)
        generation.add_updater(lambda d: d.set_value(int(now.get_value())))
        counter = (
            m.VGroup(m.Text("generation", font_size=26), generation)
            .arrange(m.RIGHT, buff=0.15)
            .to_corner(m.UR)
        )
        self.add_fixed_in_frame_mobjects(title, subtitle, counter)

        # 0–6 s: from above: the gun, one generation at a time
        self.set_camera_orientation(
            phi=0,
            theta=-90 * m.DEGREES,
            focal_distance=60,
            zoom=1.9,
            frame_center=np.array([-1.3, 2.35, 0.0]),
        )
        self.add(board, stack)
        self.play(now.animate.set_value(34), run_time=5.5, rate_func=m.linear)

        # 6–11 s: keep every generation, each one on top of the last: height is time
        up = (
            m.Text("height = time", font_size=26)
            .set_color(m.YELLOW)
            .next_to(counter, m.DOWN, aligned_edge=m.RIGHT, buff=0.25)
        )
        self.add_fixed_in_frame_mobjects(up)
        self.remove(up)
        self.move_camera(
            phi=62 * m.DEGREES,
            theta=-65 * m.DEGREES,
            focal_distance=18,
            zoom=1.0,
            frame_center=FOCUS + np.array([0, 0, 1.2]),
            added_anims=[
                now.animate.set_value(54),
                depth.animate.set_value(54),
                m.FadeIn(up),
            ],
            run_time=5,
            rate_func=m.linear,
        )

        # 11–24 s: the tower grows; gliders lean away as staircases
        self.begin_ambient_camera_rotation(rate=0.12)
        self.play(
            now.animate.set_value(GENERATIONS - 1),
            depth.animate.set_value(GENERATIONS - 1),
            self.camera.frame.animate.move_to(FOCUS + np.array([0, 0, 2.7])),
            self.camera.zoom_tracker.animate.set_value(0.88),
            run_time=12,
            rate_func=m.linear,
        )

        # 24–30 s: the poster
        closing = m.Text(
            "each glider climbs one cell every four generations: c/4", font_size=26
        ).to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing), run_time=1)
        self.wait(5.8)


if __name__ == "__main__":
    LifeSpacetime().render("life_spacetime.mp4")

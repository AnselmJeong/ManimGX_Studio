"""The stars inside the Menger sponge: cut it through its center, perpendicular to a long
diagonal, and the cut face is a hexagon riddled with six-pointed stars.

The sponge keeps a cube of the 3 × 3 × 3 grid unless two of its three coordinates sit in the
middle third, and repeats that at every scale (level 3: 20³ = 8,000 cubes). Here it is cut by the
plane x + y + z = s. The cut is exact: every face of the sponge is clipped against the plane each
frame, and the cut face is painted from the same rule, so its holes are the sponge's tunnels. At
s = 3/2 the cut is a regular hexagon full of hexagrams; sweep s toward a corner and the pattern
morphs through Sierpinski-like triangles (a cut made famous by George Hart's 3D prints).
"""

import functools

import numpy as np

import manimgx as m

LEVEL = 3
SIZE = 4.3  # edge of the sponge on screen
NORMAL = np.ones(3) / np.sqrt(3)
E1 = np.array([1.0, -1.0, 0.0]) / np.sqrt(2)
E2 = np.array([1.0, 1.0, -2.0]) / np.sqrt(6)
CAP_PIXELS = 720
CAP_HALF = 0.74  # half the side of the cap's square, in unit-cube coordinates
BONE = "#e3dccb"
GOLD = np.array([1.0, 0.72, 0.18])
# the cap's pixel centers on the plane, a across the picture and b down it
CAP_A = ((np.arange(CAP_PIXELS) + 0.5) / CAP_PIXELS * 2 - 1) * CAP_HALF
CAP_B = -CAP_A  # rows go down the picture

# the six outward faces of a unit voxel: (axis, side) → its corners, counter-clockwise outside
FACES = {
    (0, -1): [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)],
    (0, 1): [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
    (1, -1): [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
    (1, 1): [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)],
    (2, -1): [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)],
    (2, 1): [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
}


def sponge(level: int) -> np.ndarray:
    """Occupancy of the level-`level` sponge on its 3^level grid."""
    n = 3**level
    x, y, z = np.meshgrid(*[np.arange(n)] * 3, indexing="ij")
    keep = np.ones((n, n, n), bool)
    for k in range(level):
        middles = sum(((c // 3**k) % 3 == 1).astype(int) for c in (x, y, z))
        keep &= middles < 2
    return keep


def in_sponge(x: np.ndarray, y: np.ndarray, z: np.ndarray, level: int) -> np.ndarray:
    """Is each point inside the sponge (in [0, 1)³)? The same rule, digit by digit, on
    coordinate arrays that broadcast (one constant along an axis is worked once)."""
    inside = (x >= 0) & (x < 1) & (y >= 0) & (y < 1) & (z >= 0) & (z < 1)
    q = [x * 3, y * 3, z * 3]  # at the next scale, worked in place (big arrays)
    digits = [np.empty_like(c) for c in q]
    for _ in range(level):
        for c, d in zip(q, digits, strict=True):
            np.floor(c, out=d)
            c -= d
            c *= 3
        mx, my, mz = (d == 1 for d in digits)
        inside &= ~((mx & my) | (mz & (mx | my)))  # fewer than two middle digits
    return inside


def boundary_quads(occupied: np.ndarray, all_faces: bool = False) -> np.ndarray:
    """(F, 4, 3) quads in unit coordinates: the faces between filled and empty voxels (or every
    face of every filled voxel)."""
    n = occupied.shape[0]
    padded = np.pad(occupied, 1)
    quads = []
    for (axis, side), corners in FACES.items():
        lo = [1, 1, 1]
        lo[axis] += side
        neighbor = padded[lo[0] : lo[0] + n, lo[1] : lo[1] + n, lo[2] : lo[2] + n]
        cells = np.argwhere(occupied if all_faces else occupied & ~neighbor)
        quads.append(cells[:, None, :] + np.array(corners)[None])
    return np.concatenate(quads).astype(float) / n


def clip_below(quads: np.ndarray, s: float) -> tuple[np.ndarray, np.ndarray]:
    """The part of every quad with x + y + z ≤ s, fan-triangulated: vertices, triangles.
    Each polygon keeps its own vertices, so faces stay flat-shaded."""
    d = quads.sum(axis=2) - s
    whole = quads[(d <= 0).all(axis=1)]
    cut = ~(d <= 0).all(axis=1) & (d <= 0).any(axis=1)
    q, dq = quads[cut], d[cut]
    nxt = [1, 2, 3, 0]
    a, b, da, db = q, q[:, nxt], dq, dq[:, nxt]
    t = da / np.where(da == db, 1.0, da - db)
    crossing = a + t[..., None] * (b - a)
    slots = np.stack([a, crossing], axis=2).reshape(len(q), 8, 3)
    valid = np.stack([da <= 0, (da <= 0) != (db <= 0)], axis=2).reshape(len(q), 8)
    order = np.argsort(~valid, axis=1, kind="stable")
    polygon = np.take_along_axis(slots, order[..., None], axis=1)[:, :5]
    count = valid.sum(axis=1)
    # whole quads: two triangles each; cut polygons (3–5 corners): a fan of count − 2
    verts = [whole.reshape(-1, 3), polygon.reshape(-1, 3)]
    tris = [
        (
            np.arange(len(whole))[:, None, None] * 4 + np.array([[0, 1, 2], [0, 2, 3]])
        ).reshape(-1, 3)
    ]
    base = len(whole) * 4 + np.arange(len(q)) * 5
    for k in (1, 2, 3):
        rows = count >= k + 2
        tris.append(np.stack([base[rows], base[rows] + k, base[rows] + k + 1], axis=1))
    return np.concatenate(verts), np.concatenate(tris)


def to_world(unit: np.ndarray) -> np.ndarray:
    return SIZE * (unit - 0.5)


@functools.cache
def cap_colors() -> np.ndarray:
    """The cap's picture before the cut, the same for every plane: gold, a little brighter in
    rings about its center, and transparent."""
    glow = 0.8 + 0.2 * np.cos(4 * np.hypot(CAP_A, CAP_B[:, None]))
    rgba = np.zeros((CAP_PIXELS, CAP_PIXELS, 4), np.uint8)
    rgba[..., :3] = GOLD * glow[..., None] * 255
    return rgba


def cap_pixels(s: float) -> np.ndarray:
    """The cut face as a picture on a square of the plane: the sponge's material where the
    plane meets it, transparent elsewhere (outside the cube and in the tunnels)."""
    # p = s/3 + a E1 + b E2, a coordinate at a time (E1 has no z: z varies only down)
    x = s / 3 + CAP_A * E1[0] + (CAP_B * E2[0])[:, None]
    y = s / 3 + CAP_A * E1[1] + (CAP_B * E2[1])[:, None]
    z = (s / 3 + CAP_B * E2[2])[:, None]
    rgba = cap_colors().copy()
    rgba[..., 3] = 255 * in_sponge(x, y, z, LEVEL).astype(np.uint8)
    return rgba


def cap_corners(s: float) -> np.ndarray:
    """Corners of the cap's square in the order of an ImageMobject: UL, UR, DL, DR."""
    center = np.full(3, s / 3)
    h = CAP_HALF
    unit = [
        center - h * E1 + h * E2,
        center + h * E1 + h * E2,
        center - h * E1 - h * E2,
        center + h * E1 - h * E2,
    ]
    return to_world(np.array(unit))


class MengerSlice(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(
            phi=64 * m.DEGREES, theta=-38 * m.DEGREES, zoom=0.95
        )
        cut = m.ValueTracker(3.0)  # s: x + y + z ≤ s is kept (3: the whole sponge)

        # the sponge, clipped by the plane as it moves
        occupied = sponge(LEVEL)
        faces = boundary_quads(occupied)

        def solid_mesh() -> tuple[np.ndarray, np.ndarray]:
            verts, tris = clip_below(faces, cut.get_value())
            return to_world(verts), tris

        body = m.MeshMobject(*solid_mesh(), shade_in_3d=True, fill_color=BONE)
        # where each was last cut: while the plane stands still, body and cap stay
        cut_at: dict[str, float] = {}

        def reclip(mob: m.Mobject) -> None:
            assert isinstance(mob, m.MeshMobject)
            s = cut.get_value()
            if cut_at.get("body") != s:
                cut_at["body"] = s
                mob.points, mob.triangles = solid_mesh()

        # the build: at each level the cubes it removes shrink away into their centers
        levels = [sponge(k) for k in range(LEVEL + 1)]
        quad_order = np.array([[0, 1, 2], [0, 2, 3]])

        def quad_triangles(count: int) -> np.ndarray:
            return (np.arange(count)[:, None, None] * 4 + quad_order).reshape(-1, 3)

        title = m.Text("The stars inside the Menger sponge", font_size=36).to_corner(
            m.UL
        )
        subtitle = m.Text(
            "cut through its center, perpendicular to a long diagonal", font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )

        def count_text(level: int) -> m.Text:
            label = m.Text(f"level {level}  ·  {20**level:,} cubes", font_size=26)
            return label.to_corner(m.UR)

        counter = count_text(0)
        plane_label = m.MathTex(r"x + y + z = s", font_size=34)
        s_value = m.DecimalNumber(1.5, num_decimal_places=2, font_size=34)
        s_row = m.VGroup(m.MathTex(r"s =", font_size=34), s_value).arrange(
            m.RIGHT, buff=0.15
        )
        plane_group = m.VGroup(plane_label, s_row).arrange(m.DOWN, aligned_edge=m.LEFT)
        plane_group.next_to(counter, m.DOWN, aligned_edge=m.RIGHT, buff=0.4)
        s_value.add_updater(lambda d: d.set_value(cut.get_value()))
        closing = m.Text("A hexagon full of six-pointed stars.", font_size=28)
        closing.to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(title, subtitle, counter, plane_group, closing)
        self.remove(plane_group, closing)

        # 0–5 s: cube → level 1 → 2 → 3, the removed cubes shrinking away
        cube = boundary_quads(levels[0])
        body.points, body.triangles = (
            to_world(cube.reshape(-1, 3)),
            quad_triangles(len(cube)),
        )
        self.add(body)
        self.begin_ambient_camera_rotation(rate=0.12)
        for k in range(LEVEL):
            n = 3 ** (k + 1)
            coarse = np.kron(levels[k], np.ones((3, 3, 3), bool))
            gone = np.argwhere(coarse & ~levels[k + 1])  # the cubes this level removes
            corners = np.array(list(FACES.values()))  # (6, 4, 3)
            quads = ((gone[:, None, None, :] + corners[None]) / n).reshape(-1, 4, 3)
            centers = np.repeat((gone + 0.5) / n, 6, axis=0)[:, None, :]
            shrink = m.ValueTracker(1.0)
            ghost = m.MeshMobject(
                to_world(quads.reshape(-1, 3)),
                quad_triangles(len(quads)),
                shade_in_3d=True,
                fill_color=BONE,
            )

            def squeeze(
                mob: m.Mobject,
                quads: np.ndarray = quads,
                centers: np.ndarray = centers,
                shrink: m.ValueTracker = shrink,
            ) -> None:
                f = shrink.get_value()
                mob.points = to_world((centers + f * (quads - centers)).reshape(-1, 3))

            ghost.add_updater(squeeze)
            holed = boundary_quads(levels[k + 1])
            body.points, body.triangles = (
                to_world(holed.reshape(-1, 3)),
                quad_triangles(len(holed)),
            )
            self.add(ghost)
            counter.become(count_text(k + 1))
            shrink.set_value(
                0.97
            )  # the cuts show as hairlines before the pieces fall in
            self.play(
                shrink.animate.set_value(0.0), run_time=1.5, rate_func=m.rush_into
            )
            self.remove(ghost)
        body.add_updater(reclip)

        # 5–9 s: the cutting plane arrives at the center; the top half slides away
        top_verts, top_tris = clip_below(
            faces * -1 + 1, 1.5
        )  # x+y+z ≥ 3/2, by symmetry
        top = m.MeshMobject(
            to_world(1 - top_verts), top_tris, shade_in_3d=True, fill_color=BONE
        )
        cap = m.ImageMobject(cap_pixels(1.5))
        cap.points = cap_corners(1.5)
        cut.set_value(1.5)
        self.add(top, cap)
        self.play(m.FadeIn(plane_group), run_time=1)
        self.play(top.animate.shift(13 * NORMAL), run_time=2.2, rate_func=m.rush_into)
        self.remove(top)
        self.stop_ambient_camera_rotation()

        def refresh_cap(mob: m.Mobject) -> None:
            s = cut.get_value()
            if cut_at.get("cap") != s:
                cut_at["cap"] = s
                mob.points = cap_corners(s)
                mob.paint = mob.paint.but(texture=cap_pixels(s))

        cap.add_updater(refresh_cap)
        # 9–14 s: look straight down the diagonal at the cut
        self.move_camera(
            phi=54.74 * m.DEGREES,
            theta=45 * m.DEGREES,
            gamma=0,
            zoom=0.95,
            frame_center=np.array([0.0, 0.0, 0.5]),
            run_time=3.5,
        )
        self.wait(1.5)
        # 14–26 s: sweep the plane toward a corner and back
        self.play(cut.animate.set_value(0.62), run_time=6)
        self.play(cut.animate.set_value(1.5), run_time=6)
        # 26–30 s: the stars, turning slowly about the diagonal
        self.play(
            m.FadeIn(closing),
            self.camera.gamma_tracker.animate.set_value(30 * m.DEGREES),
            run_time=5.3,
            rate_func=m.smooth,
        )


if __name__ == "__main__":
    MengerSlice().render("menger_slice.mp4")

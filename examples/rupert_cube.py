"""A cube through a hole in an identical cube (Prince Rupert's problem, 1693).

Seen straight along its long diagonal, a unit cube's outline is a regular hexagon of side √(2/3),
and a square of side √(2/3)·(3 − √3) ≈ 1.035 fits inside it. Bore a square tunnel of side just
over 1 along that diagonal and the cube stays in one piece — and a second unit cube slides right
through it. (Nieuwland found the best tilt: side 3√2/4 ≈ 1.061. In 2025 Steininger and
Yurkevich found the first convex polyhedron that cannot pass through a copy of itself.)
"""

import itertools

import numpy as np

import manimgx as m

SIZE = 2.4  # screen units per unit of length
DIAGONAL = np.ones(3) / np.sqrt(3)
E1 = np.array([1.0, -1.0, 0.0]) / np.sqrt(2)
E2 = np.cross(DIAGONAL, E1)
TUNNEL = 1.02  # side of the tunnel's square cross-section (the cube's side is 1)
WIDEST = np.sqrt(2 / 3) * (3 - np.sqrt(3))
FACES = [(axis, side) for axis in range(3) for side in (-0.5, 0.5)]


def box_faces(subdivide: int) -> tuple[np.ndarray, np.ndarray]:
    """A unit cube centered at the origin as one mesh, each face a subdivided grid (the light
    is reckoned at its vertices), each face with its own vertices (flat shading)."""
    verts, tris = [], []
    g = np.linspace(-0.5, 0.5, subdivide + 1)
    uu, vv = np.meshgrid(g, g, indexing="ij")
    for axis, side in FACES:
        others = [a for a in range(3) if a != axis]
        p = np.zeros((subdivide + 1, subdivide + 1, 3))
        p[..., axis] = side
        p[..., others[0]], p[..., others[1]] = uu, vv
        base = sum(len(v) for v in verts)
        verts.append(p.reshape(-1, 3))
        i, j = np.meshgrid(np.arange(subdivide), np.arange(subdivide), indexing="ij")
        a = (i * (subdivide + 1) + j).ravel() + base
        tris.append(
            np.concatenate(
                [
                    np.stack([a, a + subdivide + 1, a + subdivide + 2], 1),
                    np.stack([a, a + subdivide + 2, a + 1], 1),
                ]
            )
        )
    return np.concatenate(verts), np.concatenate(tris)


def through_cube(starts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Where lines p + t·DIAGONAL enter and leave the unit cube (slab method): two point sets."""
    with np.errstate(divide="ignore"):
        low = (-0.5 - starts) / DIAGONAL
        high = (0.5 - starts) / DIAGONAL
    enter = np.minimum(low, high).max(axis=1)
    leave = np.maximum(low, high).min(axis=1)
    return starts + enter[:, None] * DIAGONAL, starts + leave[:, None] * DIAGONAL


class RupertCube(m.ThreeDScene):
    def construct(self) -> None:
        # cube A: glass, with a square tunnel along its diagonal
        verts, tris = box_faces(14)
        shell = m.MeshMobject(
            SIZE * verts,
            tris,
            shade_in_3d=True,
            fill_color="#6fb6ff",
            fill_opacity=0.22,
        )
        edges = m.VGroup(
            *[
                m.Line(
                    SIZE * (a - 0.5),
                    SIZE * (b - 0.5),
                    stroke_width=2,
                    color="#cfe6ff",
                    shade_in_3d=True,
                )
                for a, b in itertools.combinations(
                    np.array(list(itertools.product((0.0, 1.0), repeat=3))), 2
                )
                if np.abs(a - b).sum() == 1
            ]
        )
        # the tunnel: lines along the diagonal through the edge of a square of side TUNNEL
        t = np.linspace(0, 4, 401)[:-1]
        side = np.floor(t).astype(int)
        f = t - side
        square = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]]) * TUNNEL / 2
        rim = square[side] + f[:, None] * (square[(side + 1) % 4] - square[side])
        starts = rim[:, :1] * E1 + rim[:, 1:] * E2
        entry, exit_ = through_cube(starts)
        walls_v = SIZE * np.concatenate([entry, exit_])
        n = len(entry)
        k = np.arange(n)
        walls_t = np.concatenate(
            [
                np.stack([k, (k + 1) % n, n + (k + 1) % n], 1),
                np.stack([k, n + (k + 1) % n, n + k], 1),
            ]
        )
        walls = m.MeshMobject(
            walls_v, walls_t, shade_in_3d=True, fill_color="#9ec9ff", fill_opacity=0.35
        )
        holes = m.VGroup(
            *[
                m.VMobject(
                    stroke_color=m.GOLD, stroke_width=4, shade_in_3d=True
                ).set_points_as_corners(SIZE * np.concatenate([ring, ring[:1]]))
                for ring in (entry, exit_)
            ]
        )

        # cube B: solid gold; it turns to line up with the tunnel, then slides through
        solid_v, solid_t = box_faces(1)
        turn = np.stack(
            [E1, E2, DIAGONAL], axis=1
        )  # columns: where B's x, y, z axes go
        rest = np.array([3.4, -1.2, 0.0])
        start = -2.6 * SIZE * DIAGONAL
        path = m.ValueTracker(
            0.0
        )  # 0: resting beside A; 1: lined up behind A; 2: through and out
        solid = m.MeshMobject(
            SIZE * solid_v + rest, solid_t, shade_in_3d=True, fill_color="#ffb52e"
        )

        def place(mob: m.Mobject) -> None:
            u = path.get_value()
            if u <= 1:
                w = u * u * (3 - 2 * u)
                # rotate from identity toward `turn` along the shortest path (via its axis–angle)
                angle = np.arccos(np.clip((np.trace(turn) - 1) / 2, -1, 1))
                axis = np.array(
                    [
                        turn[2, 1] - turn[1, 2],
                        turn[0, 2] - turn[2, 0],
                        turn[1, 0] - turn[0, 1],
                    ]
                )
                axis /= np.linalg.norm(axis)
                k_ = np.array(
                    [
                        [0, -axis[2], axis[1]],
                        [axis[2], 0, -axis[0]],
                        [-axis[1], axis[0], 0],
                    ]
                )
                r = (
                    np.eye(3)
                    + np.sin(w * angle) * k_
                    + (1 - np.cos(w * angle)) * k_ @ k_
                )
                mob.points = SIZE * solid_v @ r.T + (1 - w) * rest + w * start
            else:
                mob.points = (
                    SIZE * solid_v @ turn.T + start + (u - 1) * 4.5 * SIZE * DIAGONAL
                )

        solid.add_updater(place)

        title = m.Text("A cube through a hole in itself", font_size=36).to_corner(m.UL)
        subtitle = m.Text("Prince Rupert's problem (1693)", font_size=24).set_color(
            m.GREY_B
        )
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        fit = m.MathTex(
            r"\text{widest square} = \sqrt{\tfrac{2}{3}}\,(3-\sqrt3) \approx 1.035 > 1",
            font_size=32,
        )
        fit.to_corner(m.UR)
        closing = (
            m.VGroup(
                m.Text(
                    "Nieuwland's tilt fits a square of side 3√2/4 ≈ 1.061.",
                    font_size=24,
                ),
                m.Text(
                    "2025: the Noperthedron is the first convex solid that cannot do"
                    " this.",
                    font_size=24,
                ),
            )
            .arrange(m.DOWN, buff=0.12)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.add_fixed_in_frame_mobjects(title, subtitle, fit, closing)
        self.remove(fit, closing)

        self.set_camera_orientation(
            phi=66 * m.DEGREES,
            theta=-62 * m.DEGREES,
            zoom=0.82,
            frame_center=np.array([1.6, -0.6, 0.0]),
        )
        self.add(solid, edges, shell)
        self.wait(1.5)

        # 1.5–8 s: B lines up behind A; looking down A's long diagonal (nearly orthographic),
        # B's square shows through the glass, inside A's hexagonal outline
        widest = m.VMobject(
            stroke_color=m.YELLOW, stroke_width=4, shade_in_3d=True
        ).set_points_as_corners(
            SIZE
            * np.array(
                [
                    p[0] * E1 + p[1] * E2
                    for p in (
                        np.array([[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]])
                        * WIDEST
                        / 2
                    )
                ]
            )
        )
        self.move_camera(
            phi=54.74 * m.DEGREES,
            theta=45 * m.DEGREES,
            zoom=1.2,
            focal_distance=90,
            frame_center=np.zeros(3),
            added_anims=[path.animate.set_value(1.0)],
            run_time=4,
        )
        self.play(m.Create(widest), m.FadeIn(fit), run_time=1.5)
        self.wait(1)
        # 8–12 s: bore the tunnel
        self.add(walls, holes)
        self.play(m.FadeOut(widest), m.FadeIn(holes), run_time=1)
        # watch from the side, square to the tunnel: in one side, out the other
        self.move_camera(
            phi=74 * m.DEGREES,
            theta=-45 * m.DEGREES,
            zoom=0.7,
            focal_distance=20,
            frame_center=np.array([0.3, 0.3, 0.1]),
            run_time=3,
        )
        # 12–24 s: the second cube slides through
        self.play(
            path.animate.set_value(2.0),
            self.camera.theta_tracker.animate.set_value(-38 * m.DEGREES),
            run_time=11,
            rate_func=m.linear,
        )
        # 24–30 s: records
        self.play(
            m.FadeIn(closing),
            self.camera.theta_tracker.animate.set_value(-30 * m.DEGREES),
            run_time=4,
        )
        self.wait(2.3)


if __name__ == "__main__":
    RupertCube().render("rupert_cube.mp4")

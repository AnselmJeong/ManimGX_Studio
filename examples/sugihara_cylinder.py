"""Circle or square? Kokichi Sugihara's ambiguous cylinder, built from two projections.

Looked at from 40° above, the tube's rim is a perfect circle; its reflection in the mirror behind
it — the same tube seen from the back — is a square. Turn it around and they swap. The trick:
seen from the front, a rim point (x, y, z) sits at height v_f = y sin α + z cos α on the screen;
seen from the back it sits at v_b = −y sin α + z cos α. Ask for a circle in front
(x, v_f) = (cos t, sin t) and a rounded square behind (x, v_b) = (cos t, ±(1 − |cos t|⁶)^⅙), and
solve: y = (v_f − v_b)/(2 sin α), z = (v_f + v_b)/(2 cos α). The walls are vertical, so from
both sides they look like the sides of a cylinder. From anywhere else it is a wavy tube with a
bow-tie footprint (Sugihara, 2016).
"""

import math

import numpy as np

import manimgx as m

ALPHA = 40 * m.DEGREES  # the elevation of both views
SQUARENESS = 6.0
WALL = 1.1  # wall height
MIRROR_Y = 2.6  # the mirror is the plane y = MIRROR_Y
SAMPLES = 480


def rim() -> np.ndarray:
    """The rim, unturned: (SAMPLES + 1, 3)."""
    t = np.linspace(0, m.TAU, SAMPLES + 1)
    front = np.sin(t)
    back = np.sign(np.sin(t)) * (1 - np.abs(np.cos(t)) ** SQUARENESS) ** (
        1 / SQUARENESS
    )
    y = (front - back) / (2 * np.sin(ALPHA))
    z = (front + back) / (2 * np.cos(ALPHA))
    return np.stack([np.cos(t), y, z], axis=1)


def turned(points: np.ndarray, turn: float) -> np.ndarray:
    """The points, turned about the vertical axis by `turn`."""
    c, s = np.cos(turn), np.sin(turn)
    return points @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])


def mirrored(points: np.ndarray) -> np.ndarray:
    return points * np.array([1, -1, 1]) + np.array([0, 2 * MIRROR_Y, 0])


def wall(top: np.ndarray) -> np.ndarray:
    """A vertical wall hanging WALL below the rim: the rim's points, then its foot's."""
    return np.concatenate([top, top - np.array([0, 0, WALL])])


def wall_triangles(n: int) -> np.ndarray:
    """The wall's triangles, below a rim of n points: a strip of quads."""
    i = np.arange(n - 1)
    return np.concatenate(
        [np.stack([i, i + 1, n + i + 1], 1), np.stack([i, n + i + 1, n + i], 1)]
    )


def tube(points: np.ndarray, radius: float, sides: int = 10) -> np.ndarray:
    """A lit tube along a closed polyline (parallel-transport frames): a ring of
    `sides` vertices around each point."""
    tangent = np.gradient(points, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    seed = np.cross(tangent[0], [0.3, 0.5, 0.8])
    x, y, z = (seed / np.linalg.norm(seed)).tolist()
    normals = [(x, y, z)]
    # point by point, in floats: numpy's overhead would dwarf the work on 3-vectors
    for tx, ty, tz in tangent[1:].tolist():
        d = x * tx + y * ty + z * tz
        x, y, z = x - d * tx, y - d * ty, z - d * tz
        length = math.sqrt(x * x + y * y + z * z)
        x, y, z = x / length, y / length, z / length
        normals.append((x, y, z))
    n_ = np.array(normals)
    b_ = np.cross(tangent, n_)
    a = np.linspace(0, m.TAU, sides, endpoint=False)
    ring = (
        np.cos(a)[None, :, None] * n_[:, None] + np.sin(a)[None, :, None] * b_[:, None]
    )
    return (points[:, None] + radius * ring).reshape(-1, 3)


def tube_triangles(n: int, sides: int = 10) -> np.ndarray:
    """The tube's triangles, along a polyline of n points: quads between the rings."""
    i = np.arange(n - 1)[:, None]
    j = np.arange(sides)[None, :]
    k = (j + 1) % sides
    return np.stack(
        [
            np.stack([i * sides + j, (i + 1) * sides + j, (i + 1) * sides + k], -1),
            np.stack([i * sides + j, (i + 1) * sides + k, i * sides + k], -1),
        ],
        2,
    ).reshape(-1, 3)


class SugiharaCylinder(m.ThreeDScene):
    def construct(self) -> None:
        turn = m.ValueTracker(0.0)
        upright = rim()
        triangles = [
            wall_triangles(SAMPLES + 1),
            tube_triangles(SAMPLES + 1),
            tube_triangles(SAMPLES + 1),
        ]

        def object_parts(reflect: bool) -> list[np.ndarray]:
            top = turned(upright, turn.get_value())
            if reflect:
                top = mirrored(top)
            return [
                wall(top),
                tube(top, 0.045),
                tube(top - np.array([0, 0, WALL]), 0.02),
            ]

        def build(reflect: bool, colors: tuple[str, str, str]) -> m.Group:
            parts = m.Group(
                *(
                    m.MeshMobject(verts, tris, shade_in_3d=True, fill_color=color)
                    for verts, tris, color in zip(
                        object_parts(reflect), triangles, colors, strict=True
                    )
                )
            )
            shown = turn.get_value()

            # only a turn moves the parts: between turns they keep their points
            def follow(parts: m.Mobject) -> None:
                nonlocal shown
                if turn.get_value() != shown:
                    shown = turn.get_value()
                    for part, verts in zip(
                        parts.submobjects, object_parts(reflect), strict=True
                    ):
                        part.set_points(verts)

            parts.add_updater(follow)
            return parts

        tube_obj = build(False, ("#ff6b4a", "#ffe08a", "#ffd0b0"))
        reflection = build(True, ("#b8493a", "#c9ad63", "#b89a88"))
        mirror = m.Polygon(
            [-2.5, MIRROR_Y, -2.4],
            [2.5, MIRROR_Y, -2.4],
            [2.5, MIRROR_Y, 3.0],
            [-2.5, MIRROR_Y, 3.0],
            fill_color="#8fb8ff",
            fill_opacity=0.10,
            stroke_color="#dfe8ff",
            stroke_width=2,
            shade_in_3d=True,
        )

        # the magic view: 40° above, nearly orthographic
        self.set_camera_orientation(
            phi=90 * m.DEGREES - ALPHA,
            theta=-90 * m.DEGREES,
            zoom=0.9,
            focal_distance=120,
            frame_center=np.array([0.0, 1.6, 0.0]),
        )
        title = m.Text("Circle or square?", font_size=40).to_corner(m.UL)
        subtitle = m.Text("one tube in front of a mirror", font_size=24).set_color(
            m.GREY_B
        )
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        views = m.VGroup(
            m.MathTex(r"v_f = \phantom{-}y\sin\alpha + z\cos\alpha", font_size=32),
            m.MathTex(r"v_b = -y\sin\alpha + z\cos\alpha", font_size=32),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        solve = m.VGroup(
            m.MathTex(r"y = \frac{v_f - v_b}{2\sin\alpha}", font_size=32),
            m.MathTex(r"z = \frac{v_f + v_b}{2\cos\alpha}", font_size=32),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.25)
        m.VGroup(views, solve).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.45).to_edge(
            m.RIGHT, buff=0.5
        )
        in_front = (
            m.Text("the tube", font_size=24)
            .set_color(m.GREY_B)
            .move_to([-3.4, -2.2, 0])
        )
        behind = (
            m.Text("its reflection", font_size=24)
            .set_color(m.GREY_B)
            .move_to([-3.9, 1.6, 0])
        )
        truth = m.Text("neither: a wavy tube with a bow-tie footprint", font_size=28)
        truth.to_corner(m.DR)
        self.add_fixed_in_frame_mobjects(
            title, subtitle, solve, views, truth, in_front, behind
        )
        self.remove(solve, views, truth, in_front, behind)

        self.add(reflection, mirror, tube_obj)
        self.play(
            m.FadeIn(in_front),
            m.FadeIn(behind),
            self.camera.zoom_tracker.animate.set_value(0.94),
            run_time=3,
        )
        # 3–10 s: turn the tube half a turn: circle ↔ square
        self.play(turn.animate.set_value(np.pi), run_time=6, rate_func=m.smooth)
        self.wait(1)
        # 10–18 s: leave the magic view: the truth
        self.play(m.FadeOut(in_front), m.FadeOut(behind), run_time=0.5)
        self.move_camera(
            phi=62 * m.DEGREES,
            theta=-50 * m.DEGREES,
            focal_distance=16,
            zoom=1.15,
            frame_center=np.array([0.0, 0.6, -0.4]),
            run_time=3.5,
        )
        self.play(m.FadeIn(truth), turn.animate.set_value(2 * np.pi), run_time=4)
        # 18–22 s: from straight above: the footprint is a lens
        self.move_camera(
            phi=6 * m.DEGREES,
            theta=-90 * m.DEGREES,
            zoom=2.2,
            frame_center=np.array([0.0, 0.0, 0.0]),
            run_time=3.5,
        )
        self.play(m.FadeOut(truth), run_time=0.5)
        # 22–30 s: back to the magic view, and how it is made
        self.move_camera(
            phi=90 * m.DEGREES - ALPHA,
            theta=-90 * m.DEGREES,
            zoom=0.9,
            focal_distance=120,
            frame_center=np.array([0.0, 1.6, 0.0]),
            run_time=3.5,
        )
        self.play(m.Write(views), m.Write(solve), run_time=2)
        self.play(self.camera.zoom_tracker.animate.set_value(0.94), run_time=2.5)


if __name__ == "__main__":
    SugiharaCylinder().render("sugihara_cylinder.mp4")

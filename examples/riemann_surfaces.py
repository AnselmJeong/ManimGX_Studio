"""Where √z lives: two sheets — and log z, an endless staircase.

Walk once around 0 and √z comes back negated: √(r e^{iθ}) = √r e^{iθ/2}, and θ → θ + 2π flips
e^{iθ/2}. Walk around twice and it returns. So √z is not a function on the plane but on a
surface with two sheets over it (Riemann, 1851): here the height is Re √z and the color is the
angle of √z, and the walker's value — measured from the surface it stands on — flips sign after
one loop and comes back after two. The same plane grid then bends into log z = ln r + iθ, whose
height Im log z climbs 2π with every loop: an infinite spiral staircase.
"""

import numpy as np

import manimgx as m

R_MAX = 2.5
TURNS = 2  # the grid covers θ ∈ [0, 4π): both sheets of √z, two floors of log z
NR, NT = 40, 360
WALK = 1.8  # the walker's |z|
FLOOR = 1.6  # the staircase rises this much per turn (on screen)


def lifted(r: np.ndarray, theta: np.ndarray, blend: float) -> np.ndarray:
    """The surface: height Re √z (blend 0) bending into Im log z (blend 1), over z = r e^{iθ}."""
    root = np.sqrt(r) * np.cos(theta / 2)
    stairs = FLOOR * (theta / m.TAU - TURNS / 2)
    return np.stack(
        [r * np.cos(theta), r * np.sin(theta), (1 - blend) * root + blend * stairs], -1
    )


def hues(theta: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Color by the angle of the lifted point (θ/2 for √z: once around the rainbow over two
    turns), with soft rings in |z| for texture."""
    hue = (theta / (TURNS * m.TAU)) % 1.0
    k = np.arange(3)[None, :]
    rgb = 0.5 + 0.5 * np.cos(m.TAU * (hue[:, None] - k / 3))
    shade = 0.72 + 0.28 * np.cos(m.TAU * 2.5 * np.log(r + 0.05))[:, None]
    rows = np.ones((len(hue), 4))
    rows[:, :3] = np.clip(0.15 + 0.8 * rgb * shade, 0, 1)
    return rows


def tube(
    points: np.ndarray, radius: float, sides: int = 10
) -> tuple[np.ndarray, np.ndarray]:
    """A lit tube along a polyline (parallel-transport frames)."""
    tangent = np.gradient(points, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-12
    seed = np.cross(tangent[0], [0.3, 0.5, 0.8])
    normals = [seed / np.linalg.norm(seed)]
    for t in tangent[1:]:
        n = normals[-1] - np.dot(normals[-1], t) * t
        normals.append(n / (np.linalg.norm(n) + 1e-12))
    n_ = np.array(normals)
    b_ = np.cross(tangent, n_)
    a = np.linspace(0, m.TAU, sides, endpoint=False)
    ring = (
        np.cos(a)[None, :, None] * n_[:, None] + np.sin(a)[None, :, None] * b_[:, None]
    )
    verts = (points[:, None] + radius * ring).reshape(-1, 3)
    i = np.arange(len(points) - 1)[:, None]
    j = np.arange(sides)[None, :]
    k = (j + 1) % sides
    tris = np.stack(
        [
            np.stack([i * sides + j, (i + 1) * sides + j, (i + 1) * sides + k], -1),
            np.stack([i * sides + j, (i + 1) * sides + k, i * sides + k], -1),
        ],
        2,
    ).reshape(-1, 3)
    return verts, tris


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


class RiemannSurfaces(m.ThreeDScene):
    def construct(self) -> None:
        rr, tt = np.meshgrid(
            np.linspace(0.02, R_MAX, NR + 1),
            np.linspace(0, TURNS * m.TAU, NT + 1),
            indexing="ij",
        )
        blend = m.ValueTracker(0.0)
        sheet = grid_mesh(NR, NT)
        sheet.paint = sheet.paint.but(fill=hues(tt.ravel(), rr.ravel()))

        def bend(mob: m.Mobject) -> None:
            mob.points = lifted(rr, tt, blend.get_value()).reshape(-1, 3)

        bend(sheet)
        sheet.add_updater(bend)

        # the walker goes around 0 at |z| = WALK; its path on the surface is a glowing tube
        angle = m.ValueTracker(0.0)
        walker = m.Dot3D(radius=0.09, color=m.WHITE)

        def on_surface(theta: np.ndarray) -> np.ndarray:
            return lifted(
                np.full_like(theta, WALK), theta, blend.get_value()
            ) + np.array([0, 0, 0.03])

        def place(dot: m.Mobject) -> None:
            dot.move_to(on_surface(np.array([angle.get_value()]))[0])

        walker.add_updater(place)
        path = m.MeshMobject(
            *tube(on_surface(np.linspace(0, 0.01, 3)), 0.035),
            shade_in_3d=True,
            fill_color=m.WHITE,
        )

        def trace(mob: m.Mobject) -> None:
            span = max(angle.get_value(), 0.02)
            verts, tris = tube(
                on_surface(np.linspace(0, span, max(3, int(span * 40)))), 0.035
            )
            assert isinstance(mob, m.MeshMobject)
            mob.points, mob.triangles = verts, tris

        path.add_updater(trace)

        # the walker's value, read from where it stands (√z, then log z)
        title = m.Text("Where √z lives", font_size=40).to_corner(m.UL)
        subtitle = m.Text(
            "height: Re √z   ·   color: the angle of √z", font_size=22
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        real_part = m.DecimalNumber(
            np.sqrt(WALK), num_decimal_places=2, include_sign=True, font_size=32
        )
        imag_part = m.DecimalNumber(
            0, num_decimal_places=2, include_sign=True, font_size=32
        )
        real_part.add_updater(
            lambda d: d.set_value(np.sqrt(WALK) * np.cos(angle.get_value() / 2))
        )
        imag_part.add_updater(
            lambda d: d.set_value(np.sqrt(WALK) * np.sin(angle.get_value() / 2))
        )
        value_row = m.VGroup(
            m.MathTex(r"\sqrt z =", font_size=32),
            real_part,
            imag_part,
            m.MathTex("i", font_size=32),
        ).arrange(m.RIGHT, buff=0.12)
        loops = m.DecimalNumber(0, num_decimal_places=2, font_size=32)
        loops.add_updater(lambda d: d.set_value(angle.get_value() / m.TAU))
        loop_row = m.VGroup(m.Text("loops around 0:", font_size=26), loops).arrange(
            m.RIGHT, buff=0.15
        )
        hud = (
            m.VGroup(value_row, loop_row)
            .arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2)
            .to_corner(m.UR)
        )
        self.add_fixed_in_frame_mobjects(title, subtitle, hud)
        self.remove(hud)

        self.set_camera_orientation(
            phi=62 * m.DEGREES,
            theta=-60 * m.DEGREES,
            zoom=1.05,
            frame_center=np.array([0, 0, 0.2]),
        )
        self.begin_ambient_camera_rotation(rate=0.1)
        self.add(sheet)
        self.wait(1.5)
        self.add(path, walker)
        self.play(m.FadeIn(hud), m.FadeIn(walker), run_time=1)
        # one loop: the walker ends on the other sheet, and √z has flipped sign
        self.play(angle.animate.set_value(m.TAU), run_time=5, rate_func=m.linear)
        flipped = (
            m.Text("one loop: √z → −√z", font_size=26)
            .set_color(m.YELLOW)
            .next_to(hud, m.DOWN, aligned_edge=m.LEFT, buff=0.3)
        )
        self.add_fixed_in_frame_mobjects(flipped)
        self.remove(flipped)
        self.play(m.FadeIn(flipped), run_time=0.8)
        # a second loop brings it home
        self.play(
            angle.animate.set_value(2 * m.TAU - 0.02), run_time=5, rate_func=m.linear
        )
        home = (
            m.Text("two loops: home again", font_size=26)
            .set_color(m.YELLOW)
            .move_to(flipped, aligned_edge=m.LEFT)
        )
        self.play(m.Transform(flipped, home), run_time=0.8)
        self.wait(0.6)

        # log z: the same grid bends into an endless staircase
        log_title = m.Text("…and log z, an endless staircase", font_size=40).to_corner(
            m.UL
        )
        log_sub = m.Text(
            "height: Im log z   ·   every loop climbs 2π", font_size=22
        ).set_color(m.GREY_B)
        log_sub.next_to(log_title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        climb = m.DecimalNumber(0, num_decimal_places=2, font_size=32)
        climb.add_updater(lambda d: d.set_value(angle.get_value()))
        climb_row = m.VGroup(
            m.MathTex(r"\operatorname{Im}\log z =", font_size=32), climb
        ).arrange(m.RIGHT, buff=0.15)
        climb_row.move_to(value_row, aligned_edge=m.LEFT)
        self.add_fixed_in_frame_mobjects(log_title, log_sub, climb_row)
        self.remove(log_title, log_sub, climb_row)
        self.play(
            m.FadeOut(title),
            m.FadeOut(subtitle),
            m.FadeOut(value_row),
            m.FadeOut(flipped),
            run_time=0.8,
        )
        self.play(
            blend.animate.set_value(1.0),
            angle.animate.set_value(0.0),
            m.FadeIn(log_title),
            m.FadeIn(log_sub),
            m.FadeIn(climb_row),
            run_time=2.5,
        )
        self.play(
            angle.animate.set_value(2 * m.TAU - 0.02), run_time=7, rate_func=m.linear
        )
        closing = m.Text(
            "√z needs two sheets; log z needs infinitely many.", font_size=28
        ).to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing), run_time=1)
        self.wait(3.3)


if __name__ == "__main__":
    RiemannSurfaces().render("riemann_surfaces.mp4")

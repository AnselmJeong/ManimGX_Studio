"""Bending without stretching: the helicoid rolls up into the catenoid.

The associate family X_θ = cos θ · H + sin θ · C bends a helicoid H into a catenoid C through
minimal surfaces that all share one metric, ds² = cosh² v (du² + dv²). Gauss's Theorema
Egregium says curvature is intrinsic: the color, K = −sech⁴ v, stays painted on the same
material while the shape changes completely, and the two marked curves keep their lengths.
"""

import numpy as np

import manimgx as m

U = (-np.pi, np.pi)
V = (-1.25, 1.25)
RES = (120, 48)
SCALE = 0.9
STOPS = ["#1b2a6b", "#2f6fdb", "#39c5bb", "#f4d35e", "#f25c54"]


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    """RGBA rows for values in [0, 1], interpolated through color stops."""
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


def surface(theta: float, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """The associate family: θ = 0 is the helicoid, θ = π/2 the catenoid."""
    c, s = np.cos(theta), np.sin(theta)
    x = c * np.sinh(v) * np.sin(u) + s * np.cosh(v) * np.cos(u)
    y = -c * np.sinh(v) * np.cos(u) + s * np.cosh(v) * np.sin(u)
    z = u * c + v * s
    return SCALE * np.stack([x, y, z], axis=-1)


def tube(
    points: np.ndarray, radius: float, sides: int = 12
) -> tuple[np.ndarray, np.ndarray]:
    """Vertices and triangles of a tube along a polyline (parallel-transport frames)."""
    tangent = np.gradient(points, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    seed = np.cross(tangent[0], [0.3, 0.5, 0.8])
    normals = [seed / np.linalg.norm(seed)]
    for t in tangent[1:]:
        n = normals[-1] - np.dot(normals[-1], t) * t
        normals.append(n / np.linalg.norm(n))
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


def grid_mesh(points: np.ndarray) -> m.MeshMobject:
    """A smooth lit mesh over an (nu + 1, nv + 1, 3) grid of points (vertex i·(nv + 1) + j), its
    cells in order along u and both triangles of a cell together, so `Create` sweeps it along u.
    """
    nu, nv = points.shape[0] - 1, points.shape[1] - 1
    idx = np.arange((nu + 1) * (nv + 1)).reshape(nu + 1, nv + 1)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    cells = np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], 2)
    return m.MeshMobject(points.reshape(-1, 3), cells.reshape(-1, 3), shade_in_3d=True)


class CatenoidHelicoid(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(
            phi=72 * m.DEGREES, theta=-50 * m.DEGREES, zoom=0.78
        )
        theta = m.ValueTracker(0.0)

        us = np.linspace(*U, RES[0] + 1)
        vs = np.linspace(*V, RES[1] + 1)
        uu, vv = np.meshgrid(us, vs, indexing="ij")
        curvature = 1 / np.cosh(vv.ravel()) ** 4  # |K| = sech⁴ v, the same at every θ

        sheet = grid_mesh(surface(0.0, uu, vv))
        sheet.paint = sheet.paint.but(fill=colormap(curvature, STOPS))
        sheet.add_updater(
            lambda mob: mob.set_points(
                surface(theta.get_value(), uu, vv).reshape(-1, 3)
            )
        )

        # two material curves: a v-line (u = 0.9) and a u-line (v = 0.55)
        line_v = np.linspace(*V, 160)
        line_u = np.linspace(*U, 240)

        def curve_points(which: str) -> np.ndarray:
            t = theta.get_value()
            if which == "v":
                return surface(t, np.full_like(line_v, 0.9), line_v)
            return surface(t, line_u, np.full_like(line_u, 0.55))

        def make_tube(which: str, color: str) -> m.MeshMobject:
            verts, tris = tube(curve_points(which), 0.035)
            mob = m.MeshMobject(verts, tris, shade_in_3d=True, fill_color=color)

            def follow(mob: m.Mobject) -> None:
                mob.set_points(tube(curve_points(which), 0.035)[0])

            mob.add_updater(follow)
            return mob

        white_tube = make_tube("v", "#ffffff")
        black_tube = make_tube("u", "#111111")

        def length(which: str) -> float:
            p = curve_points(which)
            return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum() / SCALE)

        # heads-up display
        title = m.Text("Bending without stretching", font_size=34).to_corner(m.UL)
        subtitle = m.Text(
            "helicoid → catenoid, one family of minimal surfaces", font_size=22
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)
        family = m.MathTex(
            r"X_\theta = \cos\theta\,H + \sin\theta\,C", font_size=38
        ).to_corner(m.UR)
        theta_label = m.MathTex(r"\theta =", font_size=38)
        theta_value = m.DecimalNumber(0, num_decimal_places=2, font_size=38)
        theta_row = m.VGroup(theta_label, theta_value).arrange(m.RIGHT, buff=0.15)
        theta_row.next_to(family, m.DOWN, aligned_edge=m.LEFT, buff=0.3)
        theta_value.add_updater(lambda d: d.set_value(theta.get_value()))

        metric = m.MathTex(r"ds^2 = \cosh^2 v\,(du^2 + dv^2)", font_size=32).to_corner(
            m.DL
        )
        gauss = m.MathTex(r"K = -\operatorname{sech}^4 v", font_size=34)
        gauss.next_to(metric, m.UP, aligned_edge=m.LEFT, buff=0.3)

        bar = m.Rectangle(width=0.3, height=2.6, stroke_width=0, fill_opacity=1)
        bar.set_fill(color=STOPS, opacity=1)
        bar.set_sheen_direction(m.UP)
        bar.to_corner(m.DR).shift(0.6 * m.UP + 0.2 * m.LEFT)
        bar_top = m.MathTex(r"K=-1", font_size=28).next_to(bar, m.LEFT, buff=0.15)
        bar_top.align_to(bar, m.UP)
        bar_bottom = m.MathTex(r"K=-0.08", font_size=28).next_to(bar, m.LEFT, buff=0.15)
        bar_bottom.align_to(bar, m.DOWN)

        def length_row(color: str, which: str) -> m.VGroup:
            swatch = m.RoundedRectangle(
                corner_radius=0.05,
                width=0.5,
                height=0.1,
                fill_color=color,
                fill_opacity=1,
                stroke_color=m.WHITE,
                stroke_width=1,
            )
            label = m.MathTex(r"\ell =", font_size=32)
            value = m.DecimalNumber(length(which), num_decimal_places=3, font_size=32)
            value.add_updater(lambda d: d.set_value(length(which)))
            return m.VGroup(swatch, label, value).arrange(m.RIGHT, buff=0.15)

        lengths = m.VGroup(
            length_row("#ffffff", "v"), length_row("#111111", "u")
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        lengths.next_to(theta_row, m.DOWN, aligned_edge=m.LEFT, buff=0.35)

        hud = [family, theta_row, metric, gauss, bar, bar_top, bar_bottom]
        self.add_fixed_in_frame_mobjects(title, subtitle, *hud, lengths)
        self.remove(*hud, lengths)

        # 0–3 s: the helicoid sweeps in
        self.play(m.Create(sheet), run_time=3, rate_func=m.smooth)
        # 4–8 s: what stays: curvature and the metric
        self.play(
            m.FadeIn(bar),
            m.FadeIn(bar_top),
            m.FadeIn(bar_bottom),
            m.Write(gauss),
            m.Write(metric),
            run_time=2,
        )
        self.play(
            m.FadeIn(white_tube),
            m.FadeIn(black_tube),
            m.Write(family),
            m.FadeIn(theta_row),
            m.FadeIn(lengths),
            run_time=1.5,
        )
        self.begin_ambient_camera_rotation(rate=0.12)
        # 8–22 s: bend helicoid → catenoid
        self.play(theta.animate.set_value(np.pi / 2), run_time=9, rate_func=m.smooth)
        self.wait(1.0)
        self.move_camera(phi=60 * m.DEGREES, zoom=0.86, run_time=2.5)
        self.wait(0.5)
        # and on, to the mirror image of the helicoid
        self.play(theta.animate.set_value(np.pi), run_time=6, rate_func=m.smooth)
        closing = (
            m.Text("Same metric, same curvature, different shape.", font_size=28)
            .to_edge(m.DOWN, buff=0.3)
            .shift(1.2 * m.RIGHT)
        )
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing, shift=0.2 * m.UP), run_time=1.2)
        self.wait(2.6)


if __name__ == "__main__":
    CatenoidHelicoid().render("catenoid_helicoid.mp4")

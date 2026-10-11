"""Why the Taylor series of 1/(1 + x²) gives up at |x| = 1.

On the real line f(x) = 1/(1 + x²) is as smooth as a function can be, yet its Taylor series
1 − x² + x⁴ − x⁶ + ⋯ explodes as soon as |x| > 1. The reason is off the line: in the complex
plane f(z) = 1/(1 + z²) has poles at z = ±i, and a power series converges exactly in the largest
disk around its center that avoids every singularity. Seen from the side, the bell curve is a
slice of the landscape |f(z)|, colored by arg f(z); the disk |z| < 1 runs into the two towers. Move
the center to a and the radius becomes the distance to ±i, √(1 + a²).
"""

import numpy as np

import manimgx as m

UNIT = 1.45  # screen units per unit of x, y and |f|
X_RANGE = (-2.4, 2.4)
Y_RANGE = (-1.9, 1.9)
CLIP = 2.3  # |f| is cut off here (the poles go to infinity)


def f(z: np.ndarray) -> np.ndarray:
    return 1 / (1 + z * z)


def domain_colors(z: np.ndarray) -> np.ndarray:
    """RGBA rows: hue from arg f(z), a little brighter where |f| is large."""
    w = f(z)
    hue = (np.angle(w) / m.TAU) % 1.0
    k = np.arange(3)[None, :]
    rgb = 0.5 + 0.5 * np.cos(m.TAU * (hue[:, None] - k / 3))  # a smooth hue wheel
    light = np.clip(0.55 + 0.25 * np.tanh(np.log(np.abs(w) + 1e-9)), 0, 1)
    rows = np.ones((len(z), 4))
    rows[:, :3] = 0.25 + 0.75 * rgb * light[:, None]
    return rows


def partial_sum(x: np.ndarray, terms: int) -> np.ndarray:
    return sum((-1) ** k * x ** (2 * k) for k in range(terms))


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


def billboard(label: m.Mobject, camera: m.Camera, shown: m.ValueTracker) -> m.Mobject:
    """Keep `label` where it is, turned every frame to face the camera, at opacity `shown` (fade it
    by animating `shown`: a FadeIn would fight the turning)."""
    anchor = label.get_center()
    parts = [
        (part, part.points - anchor) for part in label.family_members_with_points()
    ]

    def face(_: m.Mobject) -> None:
        axes = camera_axes(camera.get_phi(), camera.get_theta(), camera.get_gamma())
        for part, flat in parts:
            part.points = anchor + flat[:, :1] * axes[0] + flat[:, 1:2] * axes[1]
        label.set_opacity(shown.get_value())

    label.add_updater(face)
    face(label)
    return label


class TaylorPoles(m.ThreeDScene):
    def construct(self) -> None:
        # the side view: the x–z plane seen face on, nearly orthographic (a 2D plot)
        self.set_camera_orientation(
            phi=90 * m.DEGREES,
            theta=-90 * m.DEGREES,
            focal_distance=60,
            zoom=1.0,
            frame_center=np.array([0.0, 0.0, 1.0]),
        )
        real_axis = m.Line(
            UNIT * X_RANGE[0] * m.RIGHT, UNIT * X_RANGE[1] * m.RIGHT, stroke_width=2
        )
        height_axis = m.Line(m.ORIGIN, UNIT * CLIP * m.OUT, stroke_width=2)
        ticks = m.VGroup(
            *[
                m.Line(
                    UNIT * x * m.RIGHT + 0.08 * m.IN,
                    UNIT * x * m.RIGHT + 0.08 * m.OUT,
                    stroke_width=2,
                )
                for x in (-2, -1, 1, 2)
            ]
        )
        tick_labels = m.VGroup(
            *[
                m.MathTex(str(x), font_size=28)
                .move_to(UNIT * x * m.RIGHT + 0.35 * m.IN)
                .rotate(m.PI / 2, m.RIGHT)
                for x in (-2, -1, 1, 2)
            ]
        )

        def graph(
            values: np.ndarray, xs: np.ndarray, color: str, width: float = 4
        ) -> m.VMobject:
            keep = np.abs(values) < CLIP + 0.4
            mob = m.VMobject(stroke_color=color, stroke_width=width)
            points = np.stack(
                [UNIT * xs, 0 * xs, UNIT * np.clip(values, -1.0, CLIP + 0.4)], 1
            )
            mob.set_points_smoothly(points[keep])
            return mob

        xs = np.linspace(*X_RANGE, 400)
        bell = graph(f(xs.astype(complex)).real, xs, m.WHITE, 5)
        edges = m.VGroup(
            *[
                m.DashedLine(
                    UNIT * x * m.RIGHT,
                    UNIT * x * m.RIGHT + UNIT * CLIP * m.OUT,
                    stroke_width=2,
                    color=m.GREY_B,
                )
                for x in (-1, 1)
            ]
        )

        title = m.Text(
            "Why does this Taylor series stop at 1?", font_size=34
        ).to_corner(m.UL)
        series = m.MathTex(
            r"\frac{1}{1+x^2} = 1 - x^2 + x^4 - x^6 + \cdots", font_size=34
        )
        series.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.25)
        terms_label = m.MathTex(r"n =", font_size=32)
        terms_value = m.Integer(1, font_size=32)
        terms_row = (
            m.VGroup(terms_label, terms_value)
            .arrange(m.RIGHT, buff=0.15)
            .to_corner(m.UR)
        )
        self.add_fixed_in_frame_mobjects(title, series, terms_row)
        self.remove(series, terms_row)

        self.add(real_axis, height_axis, ticks, tick_labels)
        self.play(m.Create(bell), m.FadeIn(series), run_time=2)
        # 2–9 s: partial sums hug the curve inside (−1, 1) and fly off outside
        partial = graph(partial_sum(xs, 1), xs, m.YELLOW, 3.5)
        self.play(m.FadeIn(partial), m.FadeIn(terms_row), m.Create(edges), run_time=1)
        for terms in range(2, 13):
            terms_value.set_value(terms)
            self.play(
                m.Transform(partial, graph(partial_sum(xs, terms), xs, m.YELLOW, 3.5)),
                run_time=0.5,
            )
        # 9–13 s: tilt the camera: the real line lies in the complex plane
        plane = m.NumberPlane(
            x_range=(*X_RANGE, 0.5),
            y_range=(*Y_RANGE, 0.5),
            x_length=UNIT * 4.8,
            y_length=UNIT * 3.8,
            background_line_style={
                "stroke_color": m.BLUE_E,
                "stroke_width": 1,
                "stroke_opacity": 0.6,
            },
            axis_config={"stroke_opacity": 0},
        )
        self.play(
            m.FadeOut(partial), m.FadeOut(edges), m.FadeOut(terms_row), run_time=1
        )
        self.add(plane)
        self.move_camera(
            phi=62 * m.DEGREES,
            theta=-62 * m.DEGREES,
            focal_distance=20,
            zoom=0.95,
            frame_center=np.array([-1.1, 0.4, 0.9]),
            added_anims=[m.FadeIn(plane)],
            run_time=3,
        )

        # 13–19 s: the landscape |f(z)| rises, colored by arg f
        nu, nv = 241, 191  # odd: no grid point lands exactly on a pole
        xg = np.linspace(*X_RANGE, nu + 1)
        yg = np.linspace(*Y_RANGE, nv + 1)
        zz = xg[:, None] + 1j * yg[None, :]
        height = np.minimum(np.abs(f(zz)), CLIP)
        base_colors = domain_colors(zz.ravel())
        rise = m.ValueTracker(0.0)
        center = m.ValueTracker(0.0)  # the center of the expansion
        spotlight = m.ValueTracker(
            0.0
        )  # 0: all lit; 1: only the disk of convergence lit
        land = grid_mesh(nu, nv)

        def lift(mob: m.Mobject) -> None:
            xx, yy = np.meshgrid(xg, yg, indexing="ij")
            mob.points = UNIT * np.stack(
                [xx, yy, rise.get_value() * height], -1
            ).reshape(-1, 3)
            a = center.get_value()
            inside = np.abs(zz.ravel() - a) < np.hypot(a, 1.0)
            shade = 1 - spotlight.get_value() * 0.6 * ~inside
            rows = base_colors.copy()
            rows[:, :3] *= shade[:, None]
            rows[:, 3] = min(1.0, 4 * rise.get_value())
            mob.paint = mob.paint.but(fill=rows)

        lift(land)
        land.add_updater(lift)
        poles = m.VGroup(
            *[
                m.MathTex(t, font_size=36).move_to(
                    UNIT * np.array([0.35, y, CLIP + 0.25])
                )
                for t, y in ((r"i", 1), (r"-i", -1))
            ]
        )
        poles_shown = m.ValueTracker(0.0)
        for pole in poles:
            billboard(pole, self.camera, poles_shown)
        complex_series = m.MathTex(
            r"f(z) = \frac{1}{1+z^2}\ \text{has poles at } z = \pm i", font_size=32
        )
        complex_series.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.25)
        self.add_fixed_in_frame_mobjects(complex_series)
        self.remove(complex_series)
        self.add(land)
        self.play(
            rise.animate.set_value(1.0),
            m.FadeOut(series),
            m.FadeIn(complex_series),
            run_time=3.5,
            rate_func=m.smooth,
        )
        self.add(poles)
        self.play(
            poles_shown.animate.set_value(1.0),
            self.camera.theta_tracker.animate.set_value(-40 * m.DEGREES),
            run_time=2,
        )

        # 19–30 s: the disk of convergence, drawn on the landscape, and moving its center
        def on_surface(z: np.ndarray, lift_by: float = 0.03) -> np.ndarray:
            h = np.minimum(np.abs(f(z)), CLIP) + lift_by
            return UNIT * np.stack([z.real, z.imag, h], 1)

        def ring_points() -> np.ndarray:
            a = center.get_value()
            t = np.linspace(0, m.TAU, 361)
            return on_surface(a + np.hypot(a, 1.0) * np.exp(1j * t) + 1e-4j)

        ring = m.VMobject(stroke_color=m.YELLOW, stroke_width=6, shade_in_3d=True)
        ring.set_points_as_corners(ring_points())
        ring.add_updater(lambda mob: mob.set_points_as_corners(ring_points()))

        def interval_points() -> np.ndarray:
            a = center.get_value()
            r = np.hypot(a, 1.0)
            x = np.linspace(max(a - r, X_RANGE[0]), min(a + r, X_RANGE[1]), 200)
            return on_surface(x + 0j, 0.04)

        interval = m.VMobject(stroke_color=m.YELLOW, stroke_width=9, shade_in_3d=True)
        interval.set_points_smoothly(interval_points())
        interval.add_updater(lambda mob: mob.set_points_smoothly(interval_points()))

        radius_value = m.DecimalNumber(1.0, num_decimal_places=2, font_size=32)
        center_value = m.DecimalNumber(0.0, num_decimal_places=2, font_size=32)
        readout = m.VGroup(
            m.VGroup(m.MathTex(r"a =", font_size=32), center_value).arrange(
                m.RIGHT, buff=0.15
            ),
            m.VGroup(
                m.MathTex(r"\text{radius} =", font_size=32),
                radius_value,
                m.MathTex(r"= |a \mp i| = \sqrt{1+a^2}", font_size=32),
            ).arrange(m.RIGHT, buff=0.15),
        ).arrange(m.DOWN, aligned_edge=m.LEFT)
        readout.next_to(complex_series, m.DOWN, aligned_edge=m.LEFT, buff=0.35)
        center_value.add_updater(lambda d: d.set_value(center.get_value()))
        # measured: the distance from the center to the nearest pole
        radius_value.add_updater(
            lambda d: d.set_value(
                float(min(abs(center.get_value() - p) for p in (1j, -1j)))
            )
        )
        closing = m.Text(
            "A power series converges out to the nearest singularity.", font_size=28
        )
        closing.to_edge(m.DOWN, buff=0.3)
        self.add_fixed_in_frame_mobjects(readout, closing)
        self.remove(readout, closing)
        self.play(
            m.Create(ring),
            m.FadeIn(interval),
            m.FadeIn(readout),
            spotlight.animate.set_value(1.0),
            run_time=2.5,
        )
        self.wait(0.5)
        self.play(center.animate.set_value(1.5), run_time=4)
        self.play(center.animate.set_value(0.0), m.FadeIn(closing), run_time=3.5)
        self.wait(1.5)


if __name__ == "__main__":
    TaylorPoles().render("taylor_poles.mp4")

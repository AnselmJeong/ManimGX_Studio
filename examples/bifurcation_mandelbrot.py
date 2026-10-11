"""The Mandelbrot set knows about period doubling.

The logistic map x → r x (1 − x) and z → z² + c are the same dynamics in different clothes:
c = r/2 − r²/4. So the logistic bifurcation diagram (the long-run values of x for each r) can be
stood up on the real axis of the Mandelbrot set, above the c that matches each r. Every
period-doubling lands on a pinch between two bulbs — period 2 at c = −3/4, period 4 at −5/4, the
cascade piling up at the Feigenbaum point −1.4012 — and the period-3 window sits exactly over the
little copy of the Mandelbrot set at c = −1.75.
"""

import numpy as np

import manimgx as m

UNIT = 2.6  # screen units per unit of c
HEIGHT = 3.0  # screen height of x ∈ [0, 1]
RE = (-2.15, 0.65)
IM = (-1.2, 1.2)
PIXELS = (1120, 960)  # (columns, rows) of the Mandelbrot picture
N_PARAMS = 2400
KEEP = 120  # iterates kept per parameter (after a transient)


def mandelbrot_pixels() -> np.ndarray:
    """The set in deep ink, its outside glowing by smooth escape time: (rows, cols, 4) uint8."""
    cols, rows = PIXELS
    re = np.linspace(*RE, cols)
    im = np.linspace(IM[1], IM[0], rows)  # the picture's rows go down
    c = re[None, :] + 1j * im[:, None]
    z = np.zeros_like(c)
    escape = np.full(c.shape, np.nan)
    for n in range(240):
        z = np.where(np.isnan(escape), z * z + c, z)
        out = np.isnan(escape) & (np.abs(z) > 4)
        escape[out] = n + 1 - np.log2(np.log2(np.abs(z[out])))
    t = np.nan_to_num(np.sqrt(np.nan_to_num(escape) / 40), nan=0)
    inside = np.isnan(escape)
    rgb = np.stack([0.10 + 0.9 * t**1.6, 0.18 + 0.6 * t, 0.45 + 0.55 * np.sqrt(t)], -1)
    rgb = np.clip(rgb * np.clip(t * 3, 0, 1)[..., None], 0, 1)
    rgb[inside] = [0.02, 0.02, 0.05]
    alpha = np.ones(t.shape)
    return (np.concatenate([rgb, alpha[..., None]], -1) * 255).astype(np.uint8)


def attractor() -> tuple[np.ndarray, np.ndarray]:
    """(c, x) of the logistic map's long-run values, r from 1 to 4, sorted by c from right to left."""
    r = np.linspace(1.0, 4.0, N_PARAMS)
    x = np.full(N_PARAMS, 0.5)
    for _ in range(600):
        x = r * x * (1 - x)
    xs = []
    for _ in range(KEEP):
        x = r * x * (1 - x)
        xs.append(x.copy())
    c = np.repeat(r / 2 - r * r / 4, KEEP).reshape(N_PARAMS, KEEP).T.ravel()
    values = np.array(xs).ravel()
    order = np.argsort(-c, kind="stable")
    return c[order], values[order]


def to_scene(c: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.stack([UNIT * (c + 0.75), 0 * c, HEIGHT * x], 1)


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


class BifurcationMandelbrot(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=0, theta=-90 * m.DEGREES, zoom=0.95)

        # the Mandelbrot set lying on the floor, the real axis along x
        floor = m.ImageMobject(mandelbrot_pixels())
        x0, x1 = UNIT * (RE[0] + 0.75), UNIT * (RE[1] + 0.75)
        y0, y1 = UNIT * IM[0], UNIT * IM[1]
        floor.points = np.array(
            [[x0, y1, 0], [x1, y1, 0], [x0, y0, 0], [x1, y0, 0]], dtype=float
        )

        # the logistic map's long-run values, revealed by a scan line moving in c at constant speed
        c, x = attractor()
        colors = np.ones((len(c), 4))
        colors[:, :3] = [1.0, 0.82, 0.35]
        diagram = m.PMobject(stroke_width=1.4)
        diagram.add_points(to_scene(c, x), rgbas=colors)
        scan = m.ValueTracker(0.3)

        def reveal(mob: m.Mobject) -> None:
            rows = colors.copy()
            rows[:, 3] = np.where(c >= scan.get_value(), 0.55, 0.0)
            mob.paint = mob.paint.but(fill=rows)

        reveal(diagram)
        diagram.add_updater(reveal)
        scanline = m.always_redraw(
            lambda: m.Line(
                to_scene(np.array([scan.get_value()]), np.array([0.0]))[0],
                to_scene(np.array([scan.get_value()]), np.array([1.05]))[0],
                stroke_width=3,
                color=m.WHITE,
                stroke_opacity=0.8 if -2.0 < scan.get_value() < 0.26 else 0.0,
            )
        )

        title = m.Text(
            "The Mandelbrot set knows about period doubling", font_size=30
        ).to_corner(m.UL)
        relation = m.MathTex(
            r"x \mapsto r x(1-x)\ \sim\ z \mapsto z^2 + c",
            r"\quad c = \tfrac{r}{2} - \tfrac{r^2}{4}",
            font_size=30,
        )
        relation.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        self.add_fixed_in_frame_mobjects(title, relation)
        self.remove(relation)

        # 0–3 s: the set from above
        self.add(floor)
        self.play(self.camera.zoom_tracker.animate.set_value(1.0), run_time=2.5)
        # 3–7 s: tilt; the real axis becomes a stage
        self.move_camera(
            phi=72 * m.DEGREES,
            theta=-90 * m.DEGREES,
            zoom=1.0,
            frame_center=np.array([-0.9, 0.0, 1.35]),
            added_anims=[m.FadeIn(relation)],
            run_time=4,
        )
        # 7–17 s: sweep c from 1/4 to −2; above each c its logistic attractor appears
        self.add(diagram, scanline)
        self.play(scan.animate.set_value(-2.02), run_time=10, rate_func=m.linear)
        diagram.clear_updaters()  # all revealed: nothing changes any more
        self.remove(scanline)

        # 17–25 s: the landmarks line up with the bulbs
        marks = [
            (-0.75, "period 2", 1.08),
            (-1.25, "period 4", 1.08),
            (-1.75, "period 3", 1.08),
        ]
        reveals = []
        for c_mark, name, reach in marks:
            top = to_scene(np.array([c_mark]), np.array([reach]))[0]
            drop = m.DashedLine(
                top,
                top * np.array([1, 1, 0]),
                stroke_width=2.5,
                color=m.WHITE,
                dash_length=0.1,
            )
            label = m.Text(name, font_size=20).move_to(top + 0.25 * m.OUT)
            shown = m.ValueTracker(0.0)
            self.add(billboard(label, self.camera, shown))
            reveals.append(
                m.AnimationGroup(
                    m.Create(drop), shown.animate.set_value(1.0), run_time=1.4
                )
            )
        # one at a time, while the camera swings round to look along the drops
        self.play(
            m.Succession(*reveals, m.Wait(3.8)),
            self.camera.phi_tracker.animate.set_value(66 * m.DEGREES),
            self.camera.theta_tracker.animate.set_value(-74 * m.DEGREES),
            run_time=8,
        )
        closing = m.Text(
            "Each doubling sits on a pinch between bulbs.", font_size=28
        ).to_edge(m.DOWN, buff=0.3)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(
            m.FadeIn(closing),
            self.camera.theta_tracker.animate.set_value(-84 * m.DEGREES),
            run_time=3.5,
        )
        self.wait(1)


if __name__ == "__main__":
    BifurcationMandelbrot().render("bifurcation_mandelbrot.mp4")

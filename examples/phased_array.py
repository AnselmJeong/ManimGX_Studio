"""Steering a beam with phase alone: a phased array.

Eight identical antennas that never move send out the same wave, each one a constant phase step
Δφ behind its neighbour. Their waves add up to a beam whose direction obeys sin θ = Δφ λ/(2π d),
the principle of every phased-array radar and 5G base station. The field is summed live from the
eight sources; the beam angle is measured from the array factor |Σ e^{ij(Δφ − kd sin θ)}| and set
beside the law. At twice the frequency (d = λ) a second, grating lobe appears. An 8×8 array steers
a 3D pencil beam the same way, with a phase step along each side.
"""

import numpy as np

import manimgx as m

N = 8  # antennas per row
WAVELENGTH = 0.6
PITCH = WAVELENGTH / 2  # d, fixed: the antennas never move
FREQUENCY = 1.1  # wave cycles per second
RADIUS = 5.0  # of the half-disc of field above the array
PIXELS = (800, 400)
ROW_Y = -PITCH / 2  # the field is drawn in the plane of one row of the planar array
LOBE = 3.6  # length of the 3D beam at full gain
FIELD = [
    (-1.0, "#c8f4ff"),
    (-0.55, "#2c93d8"),
    (-0.18, "#0a2240"),
    (0.0, "#04060b"),
    (0.18, "#3d1f06"),
    (0.55, "#e38a2b"),
    (1.0, "#fff2cc"),
]
GOLD = "#f0c05a"
GAIN = ["#0d2b52", "#1768ac", "#2fb5c9", "#f2d479", "#fff7e0"]


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    """(n, 4) RGBA rows for values in [0, 1], interpolated through color stops."""
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


def field_palette() -> np.ndarray:
    """A 256-entry RGBA lookup table for field values in [−1, 1]."""
    at = np.array([v for v, _ in FIELD])
    rgb = np.array([m.ManimColor(c).to_rgb() for _, c in FIELD])
    x = np.linspace(-1, 1, 256)
    table = np.stack([np.interp(x, at, rgb[:, c]) for c in range(3)], axis=1)
    return np.column_stack([table * 255, np.full(256, 255)]).astype(np.uint8)


def grid_mesh(points: np.ndarray, fill_color: str) -> m.MeshMobject:
    """A smooth lit mesh over an (nu+1, nv+1, 3) grid of points computed with numpy (vertex
    i·(nv + 1) + j), each cell two triangles."""
    nu, nv = points.shape[0] - 1, points.shape[1] - 1
    idx = np.arange((nu + 1) * (nv + 1)).reshape(nu + 1, nv + 1)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    cells = np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], 2)
    return m.MeshMobject(
        points.reshape(-1, 3),
        cells.reshape(-1, 3),
        shade_in_3d=True,
        fill_color=fill_color,
    )


def array_factor(u: np.ndarray, step: float, kd: float) -> np.ndarray:
    """|Σ_j e^{ij(step − kd u)}| / N for direction cosines u along a row of N antennas, summed
    in closed form: |sin(Nψ/2) / (N sin(ψ/2))| with ψ = step − kd u."""
    half = (step - kd * u) / 2
    below = np.sin(half)
    tiny = np.abs(below) < 1e-9
    return np.abs(
        np.where(tiny, 1.0, np.sin(N * half) / (N * np.where(tiny, 1.0, below)))
    )


SCAN = np.radians(np.linspace(-90, 90, 3601))
_found: dict[tuple[float, float], list[float]] = {}


def lobes(step: float, kd: float) -> list[float]:
    """Measured beam directions (degrees from broadside): the peaks of the array factor."""
    if (step, kd) not in _found:
        a = array_factor(np.sin(SCAN), step, kd)
        peak = (a > 0.8) & (a >= np.roll(a, 1)) & (a >= np.roll(a, -1))
        peak[[0, -1]] = a[[0, -1]] > 0.8
        _found.clear()
        _found[step, kd] = [float(np.degrees(t)) for t in SCAN[peak]]
    return _found[step, kd]


class Array:
    """The live state: phase step(s), frequency, time; the field over the half-disc."""

    def __init__(self) -> None:
        self.time = 0.0
        self.step = m.ValueTracker(0.0)  # Δφ along x (radians)
        self.step_y = m.ValueTracker(0.0)  # Δφ along y (the planar array)
        self.octave = m.ValueTracker(1.0)  # frequency multiplier
        w, h = PIXELS
        xs = np.linspace(-RADIUS, RADIUS, w)
        zs = np.linspace(RADIUS, 0, h)
        self.x, self.z = np.meshgrid(xs, zs)
        rim = np.hypot(self.x, self.z)
        edge = np.clip((RADIUS - rim) / (0.12 * RADIUS), 0, 1)
        self.edge = (edge**1.5).ravel()
        self.compensate = (np.sqrt(rim + 0.6) / N).astype(np.float32).ravel()
        self.sources = (np.arange(N) - (N - 1) / 2) * PITCH
        # each source's distance to every pixel, and its 1/√r fall-off
        r = np.hypot(self.x[None] - self.sources[:, None, None], self.z[None])
        self.r = r.reshape(N, -1).astype(np.float32)
        self.falloff = (1 / np.sqrt(self.r + 0.03)).astype(np.float32)
        self.palette = (
            field_palette().view(np.uint32).ravel()
        )  # one RGBA word per entry
        self.basis_octave = -1.0
        self.basis = np.zeros((N, w * h), np.complex64)

    @property
    def k(self) -> float:
        return 2 * np.pi * self.octave.get_value() / WAVELENGTH

    def phases(self) -> np.ndarray:
        """Each antenna's drive phase now: j Δφ − ωt."""
        omega = 2 * np.pi * FREQUENCY * self.octave.get_value()
        return np.arange(N) * self.step.get_value() - omega * self.time

    def picture(self, shown: float = 1.0) -> np.ndarray:
        """Re Σ_j e^{i(k r_j + jΔφ − ωt)} / √r_j over the half-disc, as RGBA pixels."""
        if self.basis_octave != self.octave.get_value():
            kr = np.float32(self.k) * self.r
            self.basis = (self.falloff * np.cos(kr)) + 1j * (self.falloff * np.sin(kr))
            self.basis = self.basis.astype(np.complex64)
            self.basis_octave = self.octave.get_value()
        drive = np.exp(1j * self.phases()).astype(np.complex64)
        value = (drive @ self.basis).real * self.compensate
        index = np.clip((value + 1) * 127.5, 0, 255).astype(np.uint8)
        rgba = self.palette[index].view(np.uint8).reshape(*self.x.shape, 4)
        rgba[..., 3] = (255 * shown * self.edge).astype(np.uint8).reshape(self.x.shape)
        return rgba


class PhasedArray(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(
            phi=90 * m.DEGREES,
            theta=-90 * m.DEGREES,
            zoom=0.92,
            frame_center=np.array([1.74, 0, 2.95]),
        )
        state = Array()
        clock = m.ValueTracker(0.0)

        def tick(_: m.Mobject, dt: float) -> None:
            state.time += dt

        clock.add_updater(tick)
        shown = m.ValueTracker(1.0)  # the field's visibility

        # ── the field, a textured half-disc standing in the plane of the array ──────────────
        field = m.ImageMobject(state.picture())
        field.scale_to_fit_width(2 * RADIUS)
        field.rotate(90 * m.DEGREES, axis=m.RIGHT)
        field.move_to(np.array([0, ROW_Y, RADIUS / 2]))

        def paint_field(mob: m.Mobject) -> None:
            mob.paint = mob.paint.but(texture=state.picture(shown.get_value()))

        field.add_updater(paint_field)

        # ── the antennas, pulsing with their own phase, and a phasor dial under each ────────
        xs = state.sources
        antennas = m.VGroup(
            *[m.Dot3D(np.array([x, ROW_Y, 0]), radius=0.07) for x in xs]
        )

        antennas_on = m.ValueTracker(1.0)

        def pulse(group: m.Mobject) -> None:
            glow = (1 + np.cos(state.phases())) / 2
            dim, bright = m.ManimColor("#6b4a1f"), m.ManimColor("#ffe7a8")
            for dot, g in zip(group.submobjects, glow, strict=True):
                dot.set_color(m.interpolate_color(dim, bright, g))
                dot.set_opacity(antennas_on.get_value())

        antennas.add_updater(pulse)
        dials_on = m.ValueTracker(1.0)

        def dials() -> m.VGroup:
            group = m.VGroup()
            for x, phase in zip(xs, state.phases(), strict=True):
                center = np.array([x, ROW_Y, -0.45])
                hand = 0.12 * np.array([np.cos(phase), 0, np.sin(phase)])
                group.add(
                    m.Circle(radius=0.13, stroke_width=1.5, color=m.GREY_B)
                    .rotate(90 * m.DEGREES, axis=m.RIGHT)
                    .move_to(center),
                    m.Line(center, center + hand, stroke_width=2.5, color="#ffe7a8"),
                )
            return group.set_stroke(opacity=dials_on.get_value())

        dial_group = m.always_redraw(dials)

        # ── heads-up display ─────────────────────────────────────────────────────────────────
        title = m.Text("Steering a beam with phase alone", font_size=36).to_corner(m.UL)
        subtitle = m.Text(
            "eight fixed antennas, each a phase step Δφ behind the last", font_size=22
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)
        law = m.MathTex(
            r"\sin\theta = \frac{\Delta\phi\,\lambda}{2\pi d}", font_size=38
        )
        law.to_corner(m.UR).shift(0.15 * m.LEFT)

        # polar plot of the array factor: angle from broadside, radius = |AF|
        hub = np.array([5.05, 0.35, 0])
        size = 1.55
        polar = m.VGroup(
            m.Arc(radius=size, start_angle=0, angle=np.pi, arc_center=hub),
            m.Arc(radius=size / 2, start_angle=0, angle=np.pi, arc_center=hub),
            m.Line(hub - size * m.RIGHT, hub + size * m.RIGHT),
            *[
                m.Line(hub, hub + size * np.array([np.sin(a), np.cos(a), 0]))
                for a in np.radians([-60, -30, 0, 30, 60])
            ],
        ).set_stroke(m.GREY_D, 1.2)
        ticks = m.VGroup(
            *[
                m.MathTex(rf"{a}^\circ", font_size=20)
                .set_color(m.GREY_B)
                .move_to(
                    hub
                    + (size + 0.25)
                    * np.array([np.sin(np.radians(a)), np.cos(np.radians(a)), 0])
                )
                for a in (-60, 0, 60)
            ]
        )
        angles = np.radians(np.linspace(-90, 90, 721))

        def pattern() -> m.VGroup:
            kd = state.k * PITCH
            a = array_factor(np.sin(angles), state.step.get_value(), kd)
            curve = m.VMobject(stroke_color=GOLD, stroke_width=2.5)
            curve.set_points_as_corners(
                hub
                + size
                * a[:, None]
                * np.stack([np.sin(angles), np.cos(angles), 0 * angles], 1)
            )
            beams = m.VGroup(
                *[
                    m.Line(
                        hub,
                        hub
                        + size
                        * np.array([np.sin(np.radians(b)), np.cos(np.radians(b)), 0]),
                        stroke_width=1.5,
                        color=m.WHITE,
                    )
                    for b in lobes(state.step.get_value(), kd)
                ]
            )
            return m.VGroup(curve, beams)

        pattern_on = m.ValueTracker(0.0)
        polar_curve = m.always_redraw(
            lambda: pattern().set_stroke(opacity=pattern_on.get_value())
        )

        def readout(tex: str, *values: m.Mobject) -> m.VGroup:
            return m.VGroup(m.MathTex(tex, font_size=30), *values).arrange(
                m.RIGHT, buff=0.15
            )

        def number(
            places: int, unit: str | None = None, color: str = "#ffffff"
        ) -> m.DecimalNumber:
            return m.DecimalNumber(
                0, num_decimal_places=places, font_size=30, unit=unit, color=color
            )

        step_value = number(2, r"\pi")
        step_value.add_updater(lambda d: d.set_value(state.step.get_value() / np.pi))
        spacing_value = number(2)
        spacing_value.add_updater(lambda d: d.set_value(PITCH * state.k / (2 * np.pi)))
        # the measured beams: the main one (nearest the law's) and a grating lobe, if any
        main_value = number(1, r"^\circ", color=GOLD)
        second_value = number(1, r"^\circ", color=GOLD)
        comma = m.MathTex(",", font_size=30, color=GOLD)
        law_value = number(1, r"^\circ")

        def principal() -> float:
            s = state.step.get_value() / (state.k * PITCH)
            return float(np.degrees(np.arcsin(np.clip(s, -1, 1))))

        def measure_beams(_: m.Mobject) -> None:
            found = sorted(
                lobes(state.step.get_value(), state.k * PITCH),
                key=lambda b: abs(b - principal()),
            )
            main_value.set_value(found[0])
            second_value.set_value(found[1] if len(found) > 1 else 0)
            second_value.set_opacity(1 if len(found) > 1 else 0)
            comma.set_opacity(1 if len(found) > 1 else 0)
            law_value.set_value(principal())

        law_value.add_updater(measure_beams)
        rows = m.VGroup(
            readout(r"\Delta\phi =", step_value),
            readout(r"d/\lambda =", spacing_value),
            readout(r"\theta_{\text{beam}} =", main_value, comma, second_value),
            readout(r"\arcsin\tfrac{\Delta\phi\,\lambda}{2\pi d} =", law_value),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        rows[2][2].shift(0.1 * m.LEFT + 0.08 * m.DOWN)
        rows.next_to(hub + size * m.DOWN, m.DOWN, buff=0.15).align_to(
            hub + (size + 0.25) * m.LEFT, m.LEFT
        )
        hud_1d = m.VGroup(polar, ticks, rows)

        # ── the planar array: 8×8 patches, each lit by its phase ─────────────────────────────
        grid = (np.arange(N) - (N - 1) / 2) * PITCH
        gx, gy = np.meshgrid(grid, grid, indexing="ij")
        centers = np.column_stack([gx.ravel(), gy.ravel(), np.full(N * N, 0.01)])
        half = 0.1
        corners = np.array(
            [[-half, -half, 0], [half, -half, 0], [half, half, 0], [-half, half, 0]]
        )
        verts = (centers[:, None, :] + corners[None]).reshape(-1, 3)
        base = 4 * np.arange(N * N)[:, None]
        tris = np.concatenate([base + [0, 1, 2], base + [0, 2, 3]])
        patches = m.MeshMobject(verts, tris, fill_color="#ffe7a8")
        board = m.Prism(
            dimensions=[N * PITCH + 0.3, N * PITCH + 0.3, 0.06], fill_color="#1a2230"
        )
        board.move_to(np.array([0, 0, -0.035]))
        planar_on = m.ValueTracker(0.0)

        def light_patches(mob: m.Mobject) -> None:
            omega = 2 * np.pi * FREQUENCY * state.octave.get_value()
            phase = (
                gx.ravel() / PITCH * state.step.get_value()
                + gy.ravel() / PITCH * state.step_y.get_value()
                - omega * state.time
            )
            rows_ = colormap((1 + np.cos(phase)) / 2, ["#3a2a12", "#ffe7a8"])
            rows_[:, 3] = planar_on.get_value()
            mob.paint = mob.paint.but(fill=np.repeat(rows_, 4, axis=0))

        patches.add_updater(light_patches)

        # ── the 3D beam: |AF_x · AF_y| over the upper hemisphere, as a lit surface ──────────
        th = np.linspace(0, np.pi / 2, 121)
        ph = np.linspace(0, 2 * np.pi, 181)
        tt, pp = np.meshgrid(th, ph, indexing="ij")
        dirs = np.stack(
            [np.sin(tt) * np.cos(pp), np.sin(tt) * np.sin(pp), np.cos(tt)], -1
        )
        grow = m.ValueTracker(0.0)

        def gain(d: np.ndarray) -> np.ndarray:
            kd = state.k * PITCH
            return array_factor(d[..., 0], state.step.get_value(), kd) * array_factor(
                d[..., 1], state.step_y.get_value(), kd
            )

        lobe = grid_mesh(dirs * 0.01, fill_color=GAIN[2])

        def shape_lobe(mob: m.Mobject) -> None:
            g = gain(dirs)
            mob.points = (
                LOBE * grow.get_value() * g[..., None] * dirs + 1e-3 * dirs
            ).reshape(-1, 3)
            mob.paint = mob.paint.but(fill=colormap(g.ravel(), GAIN))

        lobe.add_updater(shape_lobe)

        beam = np.zeros(
            2
        )  # the measured beam direction (θ, φ in degrees), once a frame

        def peak(_: m.Mobject) -> None:
            """The maximum of |AF| over the hemisphere, refined on a fine patch around it."""
            g = gain(dirs)
            i, j = np.unravel_index(int(np.argmax(g)), g.shape)
            fine_t = np.linspace(th[max(i - 1, 0)], th[min(i + 1, len(th) - 1)], 41)
            fine_p = np.linspace(ph[j] - 0.05, ph[j] + 0.05, 41)
            ft, fp = np.meshgrid(fine_t, fine_p, indexing="ij")
            fd = np.stack(
                [np.sin(ft) * np.cos(fp), np.sin(ft) * np.sin(fp), np.cos(ft)], -1
            )
            k = np.unravel_index(int(np.argmax(gain(fd))), ft.shape)
            beam[:] = np.degrees(ft[k]), np.degrees(fp[k]) % 360

        axis_line = m.Line3D(np.zeros(3), m.OUT, thickness=0.012, color=m.WHITE)

        def point_axis(mob: m.Mobject) -> None:
            t, p = np.radians(beam)
            d = np.array([np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)])
            mob.become(
                m.Line3D(
                    np.zeros(3),
                    (LOBE + 0.6) * grow.get_value() * d + 1e-3 * d,
                    thickness=0.012,
                    color=m.WHITE,
                )
            )

        axis_line.add_updater(peak)
        axis_line.add_updater(point_axis)

        beam_t, beam_p = (
            number(1, r"^\circ", color=GOLD),
            number(0, r"^\circ", color=GOLD),
        )
        law_t, law_p = number(1, r"^\circ"), number(0, r"^\circ")

        def planar_law(_: m.Mobject) -> None:
            kd = state.k * PITCH
            u, v = state.step.get_value() / kd, state.step_y.get_value() / kd
            beam_t.set_value(beam[0])
            beam_p.set_value(beam[1])
            law_t.set_value(np.degrees(np.arcsin(min(1.0, float(np.hypot(u, v))))))
            law_p.set_value(np.degrees(np.arctan2(v, u)) % 360)

        law_p.add_updater(planar_law)

        def pair(name: str, t: m.Mobject, p: m.Mobject, color: str) -> m.VGroup:
            row = m.VGroup(
                m.Text(name, font_size=24).set_color(color),
                m.MathTex(r"\theta =", font_size=30),
                t,
                m.MathTex(r"\varphi =", font_size=30),
                p,
            ).arrange(m.RIGHT, buff=0.15)
            row[3:].shift(0.25 * m.RIGHT)
            return row

        hud_2d = m.VGroup(
            pair("beam", beam_t, beam_p, GOLD), pair("law", law_t, law_p, "#ffffff")
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        hud_2d.to_corner(m.DR).shift(0.25 * m.UP)
        law_2d = (
            m.MathTex(
                r"\sin\theta\,(\cos\varphi,\ \sin\varphi) = \frac{\lambda}{2\pi"
                r" d}\,(\Delta\phi_x,\ \Delta\phi_y)",
                font_size=28,
            )
            .to_corner(m.UR)
            .shift(0.15 * m.LEFT + 0.1 * m.DOWN)
        )

        self.add(clock, field, antennas, dial_group)
        self.add_fixed_in_frame_mobjects(title, subtitle, law, hud_1d, polar_curve)
        self.remove(title, subtitle, law, hud_1d)

        # 0–3 s: in step, the waves add up straight ahead
        self.play(m.Write(title), m.FadeIn(subtitle), run_time=1.5)
        self.play(
            m.FadeIn(law),
            m.FadeIn(hud_1d),
            pattern_on.animate.set_value(1),
            run_time=1.2,
        )
        self.wait(0.4)
        # 3–11 s: a phase step between neighbours tilts the wavefronts and the beam
        self.play(state.step.animate.set_value(0.5 * np.pi), run_time=2.2)
        self.wait(0.5)
        self.play(state.step.animate.set_value(-0.7 * np.pi), run_time=3.0)
        self.wait(0.4)
        self.play(state.step.animate.set_value(0.25 * np.pi), run_time=1.5)
        # 11–15 s: the same antennas at twice the frequency: d = λ, and a second beam appears
        note = m.Text(
            "same antennas, twice the frequency: d = λ, and a second beam", font_size=22
        ).set_color(m.GREY_B)
        note.next_to(subtitle, m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        self.add_fixed_in_frame_mobjects(note)
        self.remove(note)
        self.play(
            state.octave.animate.set_value(2.0),
            m.FadeIn(note, shift=0.1 * m.DOWN),
            run_time=2.5,
        )
        self.wait(1.5)
        self.play(state.octave.animate.set_value(1.0), m.FadeOut(note), run_time=1.5)

        # 16–20 s: the full 8×8 panel steers a pencil beam in 3D
        def first(
            t: float,
        ) -> float:  # the old readouts leave in the first 40% of the move
            return m.smooth(min(1.0, t / 0.4))

        def last(t: float) -> float:  # the new ones arrive in the last half
            return m.smooth(max(0.0, 2 * t - 1))

        self.add(board, patches, lobe, axis_line)
        peak(
            axis_line
        )  # the readouts hold still while they fade in: give them their values
        planar_law(law_p)
        self.add_fixed_in_frame_mobjects(law_2d, hud_2d)
        self.remove(law_2d, hud_2d)
        self.move_camera(
            phi=62 * m.DEGREES,
            theta=-58 * m.DEGREES,
            zoom=1.2,
            frame_center=np.array([0.2, 0, 1.95]),
            run_time=3.5,
            added_anims=[
                planar_on.animate.set_value(1),
                dials_on.animate.set_value(0),
                antennas_on.animate(rate_func=first).set_value(0),
                grow.animate.set_value(1),
                shown.animate.set_value(0),
                m.FadeOut(hud_1d, rate_func=first),
                pattern_on.animate(rate_func=first).set_value(0),
                m.FadeOut(law, rate_func=first),
                m.FadeIn(law_2d, rate_func=last),
                m.FadeIn(hud_2d, rate_func=last),
            ],
        )
        # 20–28 s: a conical scan: the step turns around the panel, the beam sweeps a cone
        self.begin_ambient_camera_rotation(rate=0.1)
        sweep = m.ValueTracker(0.0)
        tilt = 0.55 * np.pi

        def steer(_: m.Mobject) -> None:
            a = sweep.get_value()
            state.step.set_value(tilt * np.cos(a) * min(1.0, a / 0.6 + 0.45))
            state.step_y.set_value(tilt * np.sin(a) * min(1.0, a / 0.6 + 0.45))

        sweep.add_updater(steer)
        self.add(sweep)
        self.play(
            sweep.animate.set_value(2 * np.pi),
            run_time=7.0,
            rate_func=m.linear,
        )
        closing = m.Text("No moving parts: the phase steers the beam.", font_size=28)
        closing.to_edge(m.DOWN, buff=0.35).to_edge(m.LEFT, buff=0.5)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(
            m.FadeIn(closing, shift=0.2 * m.UP),
            sweep.animate.set_value(2.6 * np.pi),
            run_time=2.0,
            rate_func=m.linear,
        )
        self.wait(1.0)


if __name__ == "__main__":
    PhasedArray().render("phased_array.mp4")

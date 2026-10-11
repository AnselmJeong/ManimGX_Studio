"""Outrunning light: a charge in water leaves a cone of blue light behind it.

Light in water travels at c/n (n = 1.33). Every point a charge passes sends out a wavelet growing
at c/n: below β = 1/n they nest; above it they pile up on a cone, the optical sonic boom, and
light leaves along its normal at the Cherenkov angle cos θ = 1/(nβ) (Cherenkov 1934; Frank & Tamm
1937), 41° in water as β → 1. On screen θ is fitted to the drawn wavefronts at three speeds;
photons leave the track at θ, as bright as Frank–Tamm says (∝ sin²θ). When the charge slows below
c/n the light goes out, and the shell already emitted lands on a wall of photomultipliers as a
ring: how Super-Kamiokande sees a muon.
"""

from collections.abc import Callable

import numpy as np

import manimgx as m

N_WATER = 1.33
WAVE = 1.15  # c/n: how fast every wavelet grows (scene units per second)
LIGHT = N_WATER * WAVE  # c
LIFE = 2.8  # seconds a wavelet is drawn behind the charge
# photons are absorbed at this age (the water's attenuation, shortened)
PHOTON_LIFE = 3.5
TICK = 1 / 60
RING_EVERY = 6  # simulation ticks between drawn wavelets (0.1 s)
# photons leave every tick at these azimuths: each azimuth traces one line of the cone
AZIMUTHS = 96
PHOTON_CAP = AZIMUTHS * 220
APEX_X = 2.0  # where the charge sits on screen while the camera follows it
FIT_AGES = (0.15, 0.8)  # the envelope is fitted to the wavelets just behind the charge
PMT_PITCH = 0.15
PMT_RADIUS = 3.4
BRAKE = 2.4  # the charge starts to slow down this far before the wall
WATER = "#020a17"
RING_BLUE = "#8fd3ff"
CHERENKOV = ["#ffffff", "#9ddcff", "#3fa9ff", "#1f5fd6"]
HIT_TIME = ["#fff3b0", "#ffb347", "#ff5e62", "#c84bff", "#4b6bff"]


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    """(n, 4) RGBA rows for values in [0, 1], interpolated through color stops."""
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


def cloud(count: int, size: float) -> m.PMobject:
    mob = m.PMobject(stroke_width=size)
    mob.add_points(np.zeros((count, 3)), rgbas=np.zeros((count, 4)))
    return mob


class Tank:
    """The charge, its wavelets and its photons, in the lab frame; the camera follows the charge
    (`shift` is the lab x drawn at the screen's x = 0) until `follow` is animated to 0.
    """

    def __init__(self, beta: m.ValueTracker, follow: m.ValueTracker) -> None:
        self.beta = beta
        self.follow = follow
        self.time = 0.0
        self.ticks = 0
        self.x = 0.0
        self.speed = beta.get_value()  # measured: distance per tick over c
        self.shift = -APEX_X
        self.wall = np.inf
        self.brake_time = np.inf  # when the charge began to slow down
        rings = int(LIFE / (RING_EVERY * TICK)) + 2
        self.ring_x = np.zeros(rings)
        self.ring_t = np.full(rings, -np.inf)
        self.photon_x = np.zeros(PHOTON_CAP)  # emission point on the track
        self.photon_dir = np.zeros((PHOTON_CAP, 3))
        self.photon_t = np.full(PHOTON_CAP, -np.inf)
        # brightness per photon: Frank–Tamm, ∝ sin²θ per unit length
        self.photon_w = np.zeros(PHOTON_CAP)
        self.alive = np.zeros(PHOTON_CAP, bool)
        self.next_photon = 0
        # the wall's photomultipliers: a square grid of tubes inside a disc, facing the track
        g = np.arange(-PMT_RADIUS, PMT_RADIUS + 1e-9, PMT_PITCH)
        yy, zz = np.meshgrid(g, g, indexing="ij")
        self.pmt_side = len(g)
        self.pmt_inside = (np.hypot(yy, zz) <= PMT_RADIUS).ravel()
        self.pmt_yz = np.stack([yy.ravel(), zz.ravel()], axis=1)
        self.pmt_flash = np.zeros(len(self.pmt_yz))
        self.pmt_charge = np.zeros(len(self.pmt_yz))
        self.pmt_first = np.full(len(self.pmt_yz), np.inf)

    # ── the simulation: one 60 Hz tick ──────────────────────────────────────────────────────
    def step(self, dt: float) -> None:
        if dt <= 0:
            return
        beta = self.beta.get_value()
        if beta < 0.985 and self.x > 0 and np.isfinite(self.wall):
            self.brake_time = min(self.brake_time, self.time)
        before = self.x
        self.x += beta * LIGHT * dt
        self.speed = (self.x - before) / dt / LIGHT
        self.shift += self.follow.get_value() * (self.x - before)
        self.time += dt
        self.ticks += 1
        if beta > 0.3 and self.ticks % RING_EVERY == 0:
            k = int(np.argmin(self.ring_t))  # reuse the oldest slot
            self.ring_x[k], self.ring_t[k] = self.x, self.time
        if N_WATER * beta > 1:  # faster than light in water: it shines
            self.emit(beta)
        self.alive &= self.time - self.photon_t < PHOTON_LIFE
        self.absorb()
        self.pmt_flash *= np.exp(-dt / 0.35)

    def emit(self, beta: float) -> None:
        """Photons leave the track at the Cherenkov angle, all around it."""
        cos_t = 1 / (N_WATER * beta)
        sin2 = 1 - cos_t**2
        count = AZIMUTHS
        idx = (self.next_photon + np.arange(count)) % PHOTON_CAP
        self.next_photon = (self.next_photon + count) % PHOTON_CAP
        az = np.linspace(0, 2 * np.pi, count, endpoint=False)
        sin_t = np.sqrt(sin2)
        self.photon_w[idx] = beta * sin2 / (1 - 1 / N_WATER**2)
        self.photon_dir[idx] = np.stack(
            [np.full(count, cos_t), sin_t * np.cos(az), sin_t * np.sin(az)], axis=1
        )
        self.photon_x[idx] = self.x
        self.photon_t[idx] = self.time
        self.alive[idx] = True

    def photons(self) -> np.ndarray:
        """Lab positions of all photon slots."""
        age = self.time - self.photon_t
        pos = WAVE * np.where(np.isfinite(age), age, 0)[:, None] * self.photon_dir
        pos[:, 0] += self.photon_x
        return pos

    def absorb(self) -> None:
        """Photons crossing the wall plane this tick are caught by the nearest tube."""
        if not np.isfinite(self.wall):
            return
        pos = self.photons()
        crossed = self.alive & (pos[:, 0] >= self.wall)
        if not crossed.any():
            return
        idx = np.nonzero(crossed)[0]
        # where each photon met the plane
        age = (self.wall - self.photon_x[idx]) / (WAVE * self.photon_dir[idx, 0])
        yz = WAVE * age[:, None] * self.photon_dir[idx, 1:]
        cell = np.round((yz + PMT_RADIUS) / PMT_PITCH).astype(int)
        cell = np.clip(cell, 0, self.pmt_side - 1)
        tube = cell[:, 0] * self.pmt_side + cell[:, 1]
        np.add.at(self.pmt_flash, tube, self.photon_w[idx])
        np.add.at(self.pmt_charge, tube, self.photon_w[idx])
        self.pmt_first[tube] = np.minimum(self.pmt_first[tube], self.time)
        self.alive[idx] = False

    # ── the measurement ─────────────────────────────────────────────────────────────────────
    def fitted_angle(self) -> float | None:
        """θ fitted to the drawn wavefronts: the least-squares line through the charge touching
        the wavelets emitted 0.15–0.8 s ago; the light leaves along its normal. None while the
        charge is still inside its own wavelets: then there is no cone."""
        age = self.time - self.ring_t
        chosen = (age > FIT_AGES[0]) & (age < FIT_AGES[1])
        if chosen.sum() < 3:
            return None
        behind = self.x - self.ring_x[chosen]
        radius = WAVE * age[chosen]
        s = radius / behind
        if np.any(s >= 1):
            return None
        # the point where the line from the charge touches each wavefront (charge at origin)
        tx = -behind + radius * s
        ty = radius * np.sqrt(1 - s * s)
        alpha = np.arctan(-(tx * ty).sum() / (tx * tx).sum())
        return float(np.pi / 2 - alpha)


class CherenkovCone(m.ThreeDScene):
    def construct(self) -> None:
        self.camera.background_color = WATER
        self.set_camera_orientation(phi=0, theta=-90 * m.DEGREES, zoom=0.92)
        beta = m.ValueTracker(0.60)
        follow = m.ValueTracker(1.0)  # 1: the camera rides with the charge
        glow = m.ValueTracker(0.0)  # the photons' visibility
        rings_on = m.ValueTracker(1.0)
        fit_on = m.ValueTracker(0.0)
        track_on = m.ValueTracker(1.0)
        wall_on = m.ValueTracker(0.0)
        charge_on = m.ValueTracker(1.0)
        tank = Tank(beta, follow)
        for _ in range(int(LIFE / TICK)):  # start with a full train of wavelets
            tank.step(TICK)

        def here(lab_x: float) -> np.ndarray:
            return np.array([lab_x - tank.shift, 0.0, 0.0])

        # ── wavelets: one circle per slot of the ring buffer ────────────────────────────────
        template = m.Circle(radius=1).points.copy()
        circles = [
            m.Circle(radius=1, stroke_width=1.7, color=RING_BLUE) for _ in tank.ring_t
        ]
        rings = m.VGroup(*circles)

        def draw_rings(_: m.Mobject) -> None:
            ages = tank.time - tank.ring_t
            for circle, age, x in zip(circles, ages, tank.ring_x, strict=True):
                if not 0 <= age < LIFE:
                    circle.set_stroke(opacity=0)
                    continue
                circle.points = template * max(WAVE * age, 0.01) + here(x)
                fade = (1 - age / LIFE) ** 1.4
                circle.set_stroke(opacity=0.9 * fade * rings_on.get_value())

        rings.add_updater(draw_rings)

        # ── photons on the cone ──────────────────────────────────────────────────────────────
        photons = cloud(PHOTON_CAP, 2.6)
        photon_halo = cloud(PHOTON_CAP, 8.0)  # a soft bloom around every photon

        def draw_photons(mob: m.Mobject) -> None:
            pos = tank.photons()
            pos[:, 0] -= tank.shift
            age = np.nan_to_num((tank.time - tank.photon_t) / PHOTON_LIFE, posinf=1)
            rows = colormap(age, CHERENKOV)
            # brighter bands (photons emitted together) slide down the cone: each is where one
            # wavelet touches it
            emitted = np.where(tank.alive, tank.photon_t, 0)
            pulse = 0.65 + 0.35 * np.cos(2 * np.pi * 2.5 * emitted)
            fade = np.clip((1 - age) / 0.3, 0, 1) * tank.photon_w * pulse
            shown = np.where(tank.alive, fade, 0) * glow.get_value()
            for layer, alpha in ((mob, 1.0), (photon_halo, 0.07)):
                rows[:, 3] = alpha * shown
                layer.points = pos
                layer.paint = layer.paint.but(fill=rows.copy())

        photons.add_updater(draw_photons)

        # ── water specks: they show the motion ──────────────────────────────────────────────
        rng = np.random.default_rng(3)
        speck_lab = rng.uniform([-12, -4.5, -4.5], [12, 4.5, 4.5], (420, 3))
        specks = cloud(len(speck_lab), 1.8)

        def draw_specks(mob: m.Mobject) -> None:
            pos = speck_lab.copy()
            pos[:, 0] = (pos[:, 0] - tank.shift + 12) % 24 - 12
            rows = np.tile([0.55, 0.7, 0.85, 0.0], (len(pos), 1))
            rows[:, 3] = 0.3 * np.clip((11.5 - np.abs(pos[:, 0])) / 2, 0, 1)
            mob.points = pos
            mob.paint = mob.paint.but(fill=rows)

        specks.add_updater(draw_specks)

        # ── the charge, its halo and its track ──────────────────────────────────────────────
        charge = m.Dot3D(radius=0.07, color=m.WHITE)
        halos = [cloud(1, w) for w in (12, 24, 44)]
        track = m.VMobject(stroke_color=m.WHITE, stroke_width=1.5)

        def draw_charge(mob: m.Mobject) -> None:
            p = here(tank.x)
            shown = charge_on.get_value()
            mob.move_to(p)
            mob.set_opacity(shown)
            for halo, a in zip(halos, (0.5, 0.18, 0.07), strict=True):
                halo.points = p[None, :]
                halo.paint = halo.paint.but(
                    fill=np.array([[0.62, 0.86, 1.0, a * shown]])
                )
            track.set_points_as_corners([p - np.array([7.5, 0, 0]), p])
            track.set_stroke(opacity=0.3 * track_on.get_value())

        charge.add_updater(draw_charge)

        # ── the fitted envelope, a light ray and its angle ──────────────────────────────────
        def fit_marks() -> m.VGroup:
            theta = tank.fitted_angle()
            show = fit_on.get_value()
            if theta is None or show < 0.01:
                return m.VGroup()
            alpha = np.pi / 2 - theta
            apex = here(tank.x)
            lines = m.VGroup(
                *[
                    m.DashedLine(
                        apex,
                        apex
                        + 3.4 * np.array([-np.cos(alpha), sign * np.sin(alpha), 0]),
                        dash_length=0.12,
                        stroke_width=2.4,
                        color=m.GOLD,
                    )
                    for sign in (1, -1)
                ]
            )
            # a ray from 2.6 behind the charge to the envelope, normal to it
            back = 2.6
            source = apex - np.array([back, 0, 0])
            foot = apex + back * np.cos(alpha) * np.array(
                [-np.cos(alpha), np.sin(alpha), 0]
            )
            ray = m.Arrow(
                source,
                foot,
                buff=0,
                stroke_width=3,
                color=m.GOLD,
                max_tip_length_to_length_ratio=0.12,
            )
            arc = m.Arc(radius=0.55, start_angle=0, angle=theta, arc_center=source)
            arc.set_stroke(m.GOLD, 2)
            label = m.MathTex(r"\theta", font_size=30, color=m.GOLD).move_to(
                source + 0.82 * np.array([np.cos(theta / 2), np.sin(theta / 2), 0])
            )
            marks = m.VGroup(lines, ray, arc, label)
            marks.set_opacity(show)
            return marks

        fit = m.always_redraw(fit_marks)

        # ── the wall of photomultipliers ─────────────────────────────────────────────────────
        inside = tank.pmt_inside
        pmts = cloud(int(inside.sum()), 8.0)

        def draw_wall(mob: m.Mobject) -> None:
            x = tank.wall - tank.shift if np.isfinite(tank.wall) else 40.0
            yz = tank.pmt_yz[inside]
            mob.points = np.column_stack([np.full(len(yz), x), yz])
            on = wall_on.get_value()
            first = tank.pmt_first[inside]
            hit = np.isfinite(first)
            # color by arrival time, across the half second in which the ring lands
            start = tank.brake_time + 2.55 if np.isfinite(tank.brake_time) else 0.0
            timed = colormap(np.where(hit, (first - start) / 0.55, 0), HIT_TIME)
            caught = tank.pmt_charge[inside]  # photons caught, Frank–Tamm weighted
            light = np.clip(caught / 4.0, 0, 1)[:, None]
            flash = np.clip(tank.pmt_flash[inside] / 2.0, 0, 1)[:, None]
            rows = np.tile([0.3, 0.36, 0.45, 0.0], (len(yz), 1))
            rows[:, :3] = rows[:, :3] * (1 - light) + timed[:, :3] * light
            rows[:, :3] = rows[:, :3] * (1 - flash) + flash
            lit = np.maximum(0.3 + 0.7 * light, flash)[:, 0]
            rows[:, 3] = on * np.where(hit, lit, 0.2)
            mob.paint = mob.paint.but(fill=rows)

        pmts.add_updater(draw_wall)

        driver = m.ValueTracker(0)
        driver.add_updater(lambda _, dt: tank.step(dt))

        # ── heads-up display ─────────────────────────────────────────────────────────────────
        title = m.Text("Outrunning light", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "a charge moving faster than light does in water", font_size=22
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)

        law = m.MathTex(r"\cos\theta = \frac{1}{n\beta}", font_size=40)
        medium = m.MathTex(r"n = 1.33\ \text{(water)}", font_size=26).set_color(
            m.GREY_B
        )
        law_block = m.VGroup(law, medium).arrange(m.DOWN, buff=0.15)
        law_block.to_corner(m.UR).shift(0.1 * m.LEFT)

        def readout(tex: str, value: m.DecimalNumber) -> m.VGroup:
            return m.VGroup(m.MathTex(tex, font_size=30), value).arrange(
                m.RIGHT, buff=0.15
            )

        beta_value = m.DecimalNumber(0.6, num_decimal_places=3, font_size=30)
        beta_value.add_updater(lambda d: d.set_value(tank.speed))
        fitted_value = m.DecimalNumber(
            0, num_decimal_places=1, font_size=30, unit=r"^\circ", color=m.GOLD
        )
        formula_value = m.DecimalNumber(
            0, num_decimal_places=1, font_size=30, unit=r"^\circ"
        )

        def fitted(d: m.DecimalNumber) -> None:
            theta = tank.fitted_angle()
            d.set_value(0 if theta is None else np.degrees(theta))
            d.set_opacity(0 if theta is None else 1)

        def formula(d: m.DecimalNumber) -> None:
            ok = N_WATER * tank.speed > 1
            d.set_value(np.degrees(np.arccos(1 / (N_WATER * tank.speed))) if ok else 0)
            d.set_opacity(1 if ok else 0)

        fitted_value.add_updater(fitted)
        formula_value.add_updater(formula)
        rows = m.VGroup(
            readout(r"\beta =", beta_value),
            readout(r"\theta_{\text{fit}} =", fitted_value),
            readout(r"\arccos\tfrac{1}{n\beta} =", formula_value),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.18)
        rows.next_to(law_block, m.DOWN, buff=0.4).align_to(law_block, m.LEFT)
        no_cone = m.Text("no cone", font_size=24).set_color(m.GREY_B)
        no_cone.next_to(rows[1][0], m.RIGHT, buff=0.15)
        no_cone.add_updater(
            lambda t: t.set_opacity(0 if tank.fitted_angle() is not None else 1)
        )
        no_angle = m.Text("none", font_size=24).set_color(m.GREY_B)
        no_angle.next_to(rows[2][0], m.RIGHT, buff=0.15)
        no_angle.add_updater(
            lambda t: t.set_opacity(0 if N_WATER * tank.speed > 1 else 1)
        )

        # θ(β): the law, the threshold, the live fit and the measured points
        axes = m.Axes(
            x_range=[0.6, 1.0, 0.1],
            y_range=[0, 45, 15],
            x_length=3.4,
            y_length=2.0,
            tips=False,
            axis_config={"stroke_width": 1.5, "color": m.GREY_B},
        )
        axes.to_corner(m.DR).shift(0.25 * m.UP + 0.35 * m.LEFT)
        threshold = 1 / N_WATER
        curve = axes.plot(
            lambda b: np.degrees(np.arccos(min(1.0, 1 / (N_WATER * b)))),
            x_range=[threshold, 1.0, 0.002],
            color=CHERENKOV[2],
            stroke_width=2.5,
        )
        cut = m.DashedLine(
            axes.c2p(threshold, 0), axes.c2p(threshold, 45), stroke_width=1.5
        ).set_color(m.GREY_B)
        labels = m.VGroup(
            m.MathTex(r"\beta", font_size=28).next_to(
                axes.c2p(1.0, 0), m.RIGHT, buff=0.15
            ),
            m.MathTex(r"1", font_size=24).next_to(axes.c2p(1.0, 0), m.DOWN, buff=0.12),
            m.MathTex(r"\tfrac{1}{n}", font_size=26).next_to(
                axes.c2p(threshold, 0), m.DOWN, buff=0.12
            ),
            m.MathTex(r"\theta", font_size=28).next_to(
                axes.c2p(0.6, 45), m.UP, buff=0.12
            ),
            m.MathTex(r"45^\circ", font_size=22).next_to(
                axes.c2p(0.6, 45), m.LEFT, buff=0.12
            ),
        )
        live = m.Dot(radius=0.06, color=m.GOLD)

        def track_live(d: m.Mobject) -> None:
            theta = tank.fitted_angle()
            b = float(np.clip(tank.speed, 0.6, 1.0))
            d.move_to(axes.c2p(b, 0 if theta is None else np.degrees(theta)))

        live.add_updater(track_live)
        plot = m.VGroup(axes, curve, cut, labels)

        # translucent points hide what is drawn after them behind them: add those last
        self.add(driver, specks, track, rings, pmts, charge, fit)
        self.add(photons, photon_halo, *halos)
        readouts = m.VGroup(rows, no_cone, no_angle, live)
        self.add_fixed_in_frame_mobjects(title, subtitle, law_block, readouts, plot)
        self.remove(title, subtitle, law_block, readouts, plot)

        def stamp() -> None:
            """Put the fitted angle at this speed on the plot."""
            theta = tank.fitted_angle()
            if theta is None:
                return
            dot = m.Dot(
                axes.c2p(tank.speed, np.degrees(theta)), radius=0.07, color=m.WHITE
            )
            ring = m.Circle(radius=0.13, stroke_width=2, color=m.WHITE).move_to(dot)
            self.add_fixed_in_frame_mobjects(dot, ring)
            self.remove(dot, ring)
            self.play(m.FadeIn(dot, scale=2), m.FadeIn(ring, scale=0.4), run_time=0.4)

        # 0–3 s: below the threshold the wavelets nest inside each other
        self.play(m.Write(title), m.FadeIn(subtitle), run_time=1.5)
        self.play(m.FadeIn(law_block), m.FadeIn(readouts), m.FadeIn(plot), run_time=1.2)
        self.wait(0.3)
        # 3–12 s: faster, through the threshold; the cone is fitted at three speeds
        self.play(beta.animate.set_value(0.80), run_time=1.8)
        self.play(fit_on.animate.set_value(1), run_time=0.8)
        self.wait(0.6)
        stamp()
        self.play(beta.animate.set_value(0.90), run_time=1.2)
        self.wait(0.9)
        stamp()
        self.play(beta.animate.set_value(0.99), run_time=1.2)
        self.wait(0.9)
        stamp()
        # 12–18 s: the cone in 3D, lit by its photons
        self.move_camera(
            phi=64 * m.DEGREES,
            theta=-118 * m.DEGREES,
            zoom=1.0,
            frame_center=np.array([0.7, -0.15, 0.3]),
            run_time=3.5,
            added_anims=[
                glow.animate.set_value(1),
                rings_on.animate.set_value(0.3),
                track_on.animate.set_value(0.5),
                fit_on.animate.set_value(0),
            ],
        )
        orbit = 4.5
        tank.wall = tank.x + BRAKE + beta.get_value() * LIGHT * orbit
        self.play(
            self.camera.theta_tracker.animate.set_value(-72 * m.DEGREES),
            self.camera.phi_tracker.animate.set_value(70 * m.DEGREES),
            run_time=orbit,
        )
        # 20–23 s: the charge slows below c/n: the cone closes and goes dark; the camera lets
        # it go and turns to the wall, where the light already emitted lands as a ring
        swing = 2.6
        wall_x = tank.wall - tank.shift - 0.15  # where it stops once the camera does

        def within(
            seconds: float, rate: Callable[[float], float] = m.smooth
        ) -> Callable[[float], float]:
            """A rate function that completes in the first `seconds` of the swing."""
            return lambda t: rate(min(1.0, t * swing / seconds))

        self.move_camera(
            phi=84 * m.DEGREES,
            theta=-10 * m.DEGREES,
            zoom=0.9,
            frame_center=np.array([wall_x, 1.33, 0.33]),
            run_time=swing,
            added_anims=[
                beta.animate(rate_func=within(1.6, m.rush_from)).set_value(0.0),
                follow.animate(rate_func=within(0.8, m.rush_from)).set_value(0.0),
                wall_on.animate(rate_func=within(1.2)).set_value(1),
                rings_on.animate.set_value(0),
                track_on.animate.set_value(0),
                charge_on.animate.set_value(0),
            ],
        )
        self.play(
            m.FadeOut(readouts),
            self.camera.theta_tracker.animate.set_value(-18 * m.DEGREES),
            run_time=3.0,
            rate_func=m.linear,
        )
        closing = m.Text(
            "Super-Kamiokande sees a stopping muon as a ring like this", font_size=26
        )
        closing.to_edge(m.DOWN, buff=0.3).to_edge(m.LEFT, buff=0.4)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(
            m.FadeIn(closing, shift=0.2 * m.UP),
            self.camera.theta_tracker.animate.set_value(-22 * m.DEGREES),
            run_time=1.4,
            rate_func=m.linear,
        )
        self.play(
            self.camera.theta_tracker.animate.set_value(-30 * m.DEGREES),
            run_time=3.2,
            rate_func=m.linear,
        )


if __name__ == "__main__":
    CherenkovCone().render("cherenkov_cone.mp4")

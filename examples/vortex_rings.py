"""Leapfrogging smoke rings: two vortex rings take turns passing through each other.

Two identical smoke rings travel one behind the other. The front ring's flow squeezes the rear
ring and pulls it forward: it shrinks, speeds up and slips through the front ring, which the rear
ring's flow pushes wider and slower. Then the roles swap, again and again (Helmholtz, 1858).

Each ring is a circular vortex filament with a smoothed core. Its velocity field is exact:
complete elliptic integrals, computed by the arithmetic–geometric mean. The two rings and 12,000
smoke particles are all carried by the same field. Kelvin's impulse, proportional to r₁² + r₂², is
conserved, so when one ring shrinks the other must grow.
"""

import numpy as np

import manimgx as m

GAMMA = 1.0  # circulation of each ring
CORE = 0.1  # smoothing length of the cores
TIME_SCALE = 0.8  # model time per second of video
SCALE = 1.75  # screen units per model unit (the rings start with radius 1)
SMOKE = 9000  # particles per ring
COLORS = ["#ff9f1c", "#3ddbd9"]


def elliptic(k2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The complete elliptic integrals K and E of parameter k², by the arithmetic–geometric mean."""
    a, b = np.ones_like(k2), np.sqrt(1 - k2)
    total, weight = 0.5 * k2, 0.5
    for _ in range(7):
        a, b, c = (a + b) / 2, np.sqrt(a * b), (a - b) / 2
        weight *= 2
        total = total + weight * c * c
    k = np.pi / (2 * a)
    return k, k * (1 - total)


def induced(
    r: np.ndarray, z: np.ndarray, ring_r: float, ring_z: float
) -> tuple[np.ndarray, np.ndarray]:
    """The velocity (u_r, u_z) at meridional points (r, z) of a vortex ring of radius ring_r at
    height ring_z, its core smoothed over CORE."""
    dz = z - ring_z
    far = dz**2 + (r + ring_r) ** 2 + CORE**2
    near = dz**2 + (r - ring_r) ** 2 + CORE**2
    k, e = elliptic(np.minimum(4 * r * ring_r / far, 1 - 1e-12))
    s = GAMMA / (2 * np.pi * np.sqrt(far))
    u_r = s * dz / np.maximum(r, 1e-9) * (-k + (r**2 + ring_r**2 + dz**2) / near * e)
    u_z = s * (k + (ring_r**2 - r**2 - dz**2) / near * e)
    return u_r, u_z


class Flow:
    """The two rings (entries 0 and 1) and the smoke, as meridional points (r, z), all carried by
    the rings' field; each smoke particle also keeps its angle around the axis."""

    def __init__(self) -> None:
        rng = np.random.default_rng(3)
        ring_r, ring_z = np.array([1.0, 1.0]), np.array([0.0, 0.7])
        owner = np.repeat([0, 1], SMOKE)
        swirl = rng.uniform(0, m.TAU, 2 * SMOKE)
        spread = 0.09 * np.sqrt(-2 * np.log(rng.uniform(1e-4, 1, 2 * SMOKE)))
        spread = np.minimum(spread, 0.3)
        self.r = np.concatenate([ring_r, ring_r[owner] + spread * np.cos(swirl)])
        self.z = np.concatenate([ring_z, ring_z[owner] + spread * np.sin(swirl)])
        self.angle = rng.uniform(0, m.TAU, 2 * SMOKE)
        self.owner = owner
        self.swirl = swirl  # where around its core each particle started
        self.t = 0.0

    def velocity(self, r: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        u_r, u_z = np.zeros_like(r), np.zeros_like(z)
        for i in (0, 1):
            a, b = induced(r, z, float(r[i]), float(z[i]))
            u_r, u_z = u_r + a, u_z + b
        return u_r, u_z

    def step(self, dt: float) -> None:
        """One RK4 step for rings and smoke together."""
        r, z = self.r, self.z
        k1 = self.velocity(r, z)
        k2 = self.velocity(r + dt / 2 * k1[0], z + dt / 2 * k1[1])
        k3 = self.velocity(r + dt / 2 * k2[0], z + dt / 2 * k2[1])
        k4 = self.velocity(r + dt * k3[0], z + dt * k3[1])
        self.r = r + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        self.z = z + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        self.t += dt

    def middle(self) -> float:
        return float(self.z[:2].mean())

    def smoke_points(self) -> np.ndarray:
        """The smoke on screen, in the frame moving with the pair (the axis along x)."""
        r, z = self.r[2:], self.z[2:] - self.middle()
        return SCALE * np.column_stack(
            [z, r * np.cos(self.angle), r * np.sin(self.angle)]
        )


class VortexRings(m.ThreeDScene):
    def construct(self) -> None:
        flow = Flow()

        def advance(_: m.Mobject, dt: float) -> None:
            flow.step(TIME_SCALE * dt)

        clock = m.Mobject()
        clock.add_updater(advance)

        rgba = np.ones((2 * SMOKE, 4))
        rgba[:, :3] = np.array([m.ManimColor(c).to_rgb() for c in COLORS])[flow.owner]
        # bands of denser smoke, so the rolling around each core shows
        rgba[:, 3] = np.where(np.cos(3 * flow.swirl) > 0, 0.55, 0.22)
        smoke = m.PMobject(stroke_width=3.6)
        smoke.add_points(flow.smoke_points(), rgbas=rgba)

        def carry(mob: m.Mobject) -> None:
            mob.points = flow.smoke_points()

        smoke.add_updater(carry)
        # a floor that scrolls back as the pair moves forward
        floor = m.VGroup(
            *[
                m.Line([-9, y, -2.4], [9, y, -2.4], stroke_width=1.2, color=m.GREY_D)
                for y in np.linspace(-4, 4, 9)
            ]
        )
        rungs = m.VGroup(
            *[
                m.Line([0, -4, -2.4], [0, 4, -2.4], stroke_width=1.2, color=m.GREY_D)
                for _ in range(19)
            ]
        )

        def scroll(group: m.Mobject) -> None:
            shift = (-SCALE * flow.middle()) % 1.0
            for k, rung in enumerate(group.submobjects):
                rung.move_to([k - 9 + shift, 0, -2.4])

        rungs.add_updater(scroll)

        # HUD: Kelvin's impulse as a bar split between the rings: the split moves, the total stays
        title = m.Text("Leapfrogging smoke rings", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "two vortex rings take turns passing through each other (Helmholtz, 1858)",
            font_size=22,
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        bar_height = 2.6
        frame = m.Rectangle(
            width=0.5, height=bar_height, stroke_width=1.5, color=m.GREY_B
        )
        frame.to_corner(m.UR).shift(0.55 * m.DOWN + 0.9 * m.LEFT)
        total0 = float(flow.r[0] ** 2 + flow.r[1] ** 2)

        def split() -> m.VGroup:
            share = float(flow.r[0] ** 2) / total0
            full = float(flow.r[0] ** 2 + flow.r[1] ** 2) / total0
            low = m.Rectangle(
                width=0.5, height=bar_height * share, stroke_width=0, fill_opacity=0.85
            ).set_fill(COLORS[0])
            high = m.Rectangle(
                width=0.5,
                height=bar_height * (full - share),
                stroke_width=0,
                fill_opacity=0.85,
            ).set_fill(COLORS[1])
            low.align_to(frame, m.DOWN).align_to(frame, m.LEFT)
            high.next_to(low, m.UP, buff=0).align_to(frame, m.LEFT)
            return m.VGroup(low, high)

        bar = m.always_redraw(split)
        total = m.DecimalNumber(total0, num_decimal_places=3, font_size=28)
        total.add_updater(lambda d: d.set_value(float(flow.r[0] ** 2 + flow.r[1] ** 2)))
        caption = m.VGroup(
            m.MathTex(
                r"r_1^2 + r_2^2 =",
                font_size=28,
                tex_to_color_map={"r_1^2": COLORS[0], "r_2^2": COLORS[1]},
            ),
            total,
        ).arrange(m.RIGHT, buff=0.1)
        caption.next_to(frame, m.DOWN, buff=0.2).align_to(frame, m.RIGHT).shift(
            0.2 * m.RIGHT
        )
        self.add_fixed_in_frame_mobjects(title, subtitle)

        self.set_camera_orientation(
            phi=64 * m.DEGREES,
            theta=-118 * m.DEGREES,
            zoom=1.15,
            focal_distance=16,
            frame_center=np.array([0.0, 0.0, 0.55]),
        )
        self.add(floor, rungs, clock, smoke)
        self.wait(3)
        self.add_fixed_in_frame_mobjects(frame, bar, caption)
        self.remove(frame, bar, caption)
        self.play(m.FadeIn(frame), m.FadeIn(caption), run_time=1)
        self.add(bar)
        self.wait(6)
        # swing round to look along the axis: one ring through the other
        self.move_camera(phi=72 * m.DEGREES, theta=-162 * m.DEGREES, run_time=6)
        self.wait(4)
        self.move_camera(phi=66 * m.DEGREES, theta=-100 * m.DEGREES, run_time=5)
        closing = m.Text(
            "Kelvin's impulse ∝ r₁² + r₂² is conserved: when one ring shrinks, the"
            " other grows.",
            font_size=24,
        ).to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing), run_time=1)
        self.wait(4)


if __name__ == "__main__":
    VortexRings().render("vortex_rings.mp4")

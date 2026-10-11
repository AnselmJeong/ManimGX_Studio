"""A quantum particle tunnels through a wall.

A free particle is a wave packet ψ(x, t). Drawn in 3D as the curve (x, Re ψ, Im ψ) it is a
corkscrew: its radius is |ψ| and its twist is the phase, whose crests move at half the packet's
speed. The packet meets a barrier higher than its energy, a wall a classical particle could never
cross, and splits: part reflects and part tunnels through. The Schrödinger equation
iψₜ = −½ψₓₓ + Vψ is solved as it plays, by split-step Fourier. The transmitted probability,
integrated from ψ, matches the square barrier's T = [1 + V₀² sinh²(κa) / 4E(V₀ − E)]⁻¹, averaged
over the packet's momenta.
"""

import numpy as np

import manimgx as m

N, LENGTH = 4096, 320.0  # the grid (periodic; far wider than the view)
DX = LENGTH / N
K0, SIGMA, X0 = 1.5, 5.0, -24.0  # the packet: momentum, width, start (ħ = m = 1)
V0 = 1.8  # the barrier's height, above the packet's energy K0²/2 = 1.125
WIDTH = 10 * DX  # the barrier's width, ten grid cells (0.78)
DT = 0.02
SHOWN = 36.0  # the view: |x| ≤ SHOWN
X_SCALE = 0.17  # screen units per unit of x
AMP = 3.4  # screen units per unit of |ψ|


class Packet:
    def __init__(self) -> None:
        self.x = (np.arange(N) - N // 2) * DX
        self.k = 2 * np.pi * np.fft.fftfreq(N, DX)
        self.potential = np.where(
            (self.x > -DX / 2) & (self.x < WIDTH - DX / 2), V0, 0.0
        )
        psi = np.exp(-((self.x - X0) ** 2) / (4 * SIGMA**2) + 1j * K0 * self.x)
        self.psi = psi / np.sqrt((np.abs(psi) ** 2).sum() * DX)
        self.t = 0.0

    def advance(self, until: float) -> None:
        """Split-step Fourier: half a step of the potential, a full step of the kinetic energy
        (exact in Fourier space), half a step of the potential."""
        while self.t < until - 1e-9:
            dt = min(DT, until - self.t)
            half = np.exp(-0.5j * self.potential * dt)
            kinetic = np.exp(-0.5j * self.k**2 * dt)
            self.psi = half * np.fft.ifft(kinetic * np.fft.fft(half * self.psi))
            self.t += dt

    def probability(self, where: np.ndarray) -> float:
        return float((np.abs(self.psi[where]) ** 2).sum() * DX)


def transmission_theory() -> float:
    """The square barrier's transmission T(k), averaged over the packet's momentum distribution
    |φ(k)|² ∝ exp(−2σ²(k − k₀)²) (complex κ covers the few momenta above the barrier).
    """
    k = np.linspace(K0 - 2.5 / SIGMA, K0 + 2.5 / SIGMA, 2000)
    weight = np.exp(-2 * SIGMA**2 * (k - K0) ** 2)
    energy = k**2 / 2
    kappa = np.sqrt(2 * (V0 - energy) + 0j)
    t = 1 / (1 + V0**2 * np.sinh(kappa * WIDTH) ** 2 / (4 * energy * (V0 - energy)))
    return float((weight * t.real).sum() / weight.sum())


def tube(
    points: np.ndarray, radius: float, sides: int = 8
) -> tuple[np.ndarray, np.ndarray]:
    """Vertices and triangles of a lit tube along a 3D polyline (parallel-transport frames)."""
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


def phase_colors(psi: np.ndarray, sides: int) -> np.ndarray:
    """Per-vertex colors: hue from the phase, fading to grey where |ψ| is negligible."""
    hue = np.angle(psi) / m.TAU
    k = np.arange(3)[None, :]
    rgb = 0.55 + 0.45 * np.cos(m.TAU * (hue[:, None] - k / 3))
    strength = np.clip(np.abs(psi) / 0.04, 0, 1)[:, None]
    rows = np.ones((len(psi), 4))
    rows[:, :3] = 0.35 * (1 - strength) + rgb * strength
    return np.repeat(rows, sides, axis=0)


class WavePacket(m.ThreeDScene):
    def construct(self) -> None:
        packet = Packet()
        clock = m.ValueTracker(0.0)  # the model time shown
        view = np.flatnonzero(np.abs(packet.x) <= SHOWN)[::2]

        def curve() -> np.ndarray:
            psi = packet.psi[view]
            return np.column_stack(
                [X_SCALE * packet.x[view], AMP * psi.real, AMP * psi.imag]
            )

        verts, tris = tube(curve(), 0.03)
        spiral = m.MeshMobject(verts, tris, shade_in_3d=True)
        spiral.paint = spiral.paint.but(fill=phase_colors(packet.psi[view], 8))

        def evolve(mob: m.Mobject) -> None:
            assert isinstance(mob, m.MeshMobject)
            packet.advance(clock.get_value())
            mob.points = tube(curve(), 0.03)[0]
            mob.paint = mob.paint.but(fill=phase_colors(packet.psi[view], 8))

        spiral.add_updater(evolve)
        axis = m.Line(
            [-X_SCALE * SHOWN, 0, 0],
            [X_SCALE * SHOWN, 0, 0],
            color=m.GREY_D,
            stroke_width=1.5,
        )
        wall = m.Prism(dimensions=[X_SCALE * WIDTH, 3.0, 3.0], fill_opacity=0.28)
        wall.set_fill(m.RED_C, opacity=0.28).set_stroke(width=0)
        wall.move_to([X_SCALE * WIDTH / 2, 0, 0])

        # HUD: the textbook picture: the barrier V(x), the energy E and |ψ|² sitting on it
        plot = m.Axes(
            x_range=(-SHOWN, SHOWN, 12),
            y_range=(0, 3.2, 0.8),
            x_length=10.5,
            y_length=1.7,
            tips=False,
            axis_config={"stroke_width": 1.5, "include_ticks": False},
        ).to_edge(m.DOWN, buff=0.35)
        barrier = m.Polygon(
            plot.c2p(0, 0),
            plot.c2p(0, V0),
            plot.c2p(WIDTH, V0),
            plot.c2p(WIDTH, 0),
            stroke_width=0,
            fill_color=m.RED_C,
            fill_opacity=0.85,
        )
        energy = float(K0**2 / 2 + 1 / (8 * SIGMA**2))  # ⟨E⟩ of the Gaussian packet
        level = m.DashedLine(
            plot.c2p(-SHOWN, energy), plot.c2p(SHOWN, energy), stroke_width=1.5
        ).set_color(m.GREY_B)
        labels = m.VGroup(
            m.MathTex("V_0", font_size=26).next_to(plot.c2p(WIDTH, V0), m.RIGHT, 0.1),
            m.MathTex("E", font_size=26).next_to(plot.c2p(-SHOWN, energy), m.LEFT, 0.1),
        )
        xs = packet.x[view]

        def density() -> m.VMobject:
            top = energy + 7.0 * np.abs(packet.psi[view]) ** 2
            outline = [plot.c2p(float(a), float(b)) for a, b in zip(xs, top)]
            base = [plot.c2p(float(xs[-1]), energy), plot.c2p(float(xs[0]), energy)]
            return m.Polygon(
                *outline, *base, stroke_width=1.5, stroke_color=m.BLUE_B
            ).set_fill(m.BLUE_D, opacity=0.6)

        cloud = m.always_redraw(density)

        # HUD: the probabilities, integrated from ψ, and the theory
        left, right = packet.x < 0, packet.x >= WIDTH
        reflected = m.DecimalNumber(1, num_decimal_places=3, font_size=30)
        reflected.add_updater(lambda d: d.set_value(packet.probability(left)))
        transmitted = m.DecimalNumber(0, num_decimal_places=3, font_size=30)
        transmitted.add_updater(lambda d: d.set_value(packet.probability(right)))
        table = m.VGroup(
            m.VGroup(m.Text("reflected", font_size=26), reflected).arrange(
                m.RIGHT, buff=0.2
            ),
            m.VGroup(m.Text("tunnelled", font_size=26), transmitted).arrange(
                m.RIGHT, buff=0.2
            ),
        ).arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.18)
        table.to_corner(m.UR)
        theory = m.MathTex(
            rf"T = \left[1 + \frac{{V_0^2 \sinh^2 \kappa a}}{{4E(V_0 -"
            rf" E)}}\right]^{{-1}}"
            rf" = {transmission_theory():.3f}",
            font_size=30,
        )

        title = m.Text("A particle tunnels through a wall", font_size=38).to_corner(
            m.UL
        )
        subtitle = m.MathTex(
            r"\psi(x) \text{ drawn as }"
            r" (x,\ \operatorname{Re}\psi,\ \operatorname{Im}\psi)"
            r":\quad i\psi_t = -\tfrac12 \psi_{xx} + V\psi",
            font_size=28,
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)
        theory.next_to(subtitle, m.DOWN, aligned_edge=m.LEFT, buff=0.35)
        self.add_fixed_in_frame_mobjects(
            title, subtitle, plot, barrier, level, labels, cloud, table, theory
        )
        self.remove(theory)

        self.set_camera_orientation(
            phi=68 * m.DEGREES,
            theta=-52 * m.DEGREES,
            zoom=0.92,
            frame_center=np.array([0.0, 0.0, -0.75]),
        )
        self.add(axis, wall, spiral)
        # the free packet: the corkscrew turns as it goes; its crests lag behind the packet
        self.play(
            clock.animate.set_value(10.0),
            self.camera.theta_tracker.animate.set_value(-62 * m.DEGREES),
            run_time=6,
            rate_func=m.linear,
        )
        # it meets the wall: part of it comes back, part of it comes through
        self.play(
            clock.animate.set_value(24.0),
            self.camera.theta_tracker.animate.set_value(-94 * m.DEGREES),
            self.camera.phi_tracker.animate.set_value(72 * m.DEGREES),
            run_time=13,
            rate_func=m.linear,
        )
        self.play(
            clock.animate.set_value(30.0),
            m.FadeIn(theory),
            self.camera.theta_tracker.animate.set_value(-124 * m.DEGREES),
            self.camera.phi_tracker.animate.set_value(66 * m.DEGREES),
            run_time=6,
            rate_func=m.linear,
        )
        self.play(clock.animate.set_value(32.5), run_time=5, rate_func=m.linear)


if __name__ == "__main__":
    WavePacket().render("wave_packet.mp4")

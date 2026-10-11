"""Turing patterns growing on a torus.

Two chemicals react and diffuse over the surface of a doughnut (the Gray–Scott model):
u̇ = D_u Δu − uv² + F(1 − u),  v̇ = D_v Δv + uv² − (F + k)v, with D_u = 2 D_v. The Laplacian Δ is
the torus's own (Laplace–Beltrami) operator,
Δf = f_φφ/ρ² + (1/(ρ r²)) ∂_θ(ρ f_θ),  ρ = R + r cos θ,
so spots come out round on the curved surface — smaller on the inside of the hole than they
would be on a flat map. From a few seeds, spots grow and divide until they tile the torus; then
F and k are changed and the same equations grow a labyrinth instead. Alan Turing (1952): diffusion,
which should smooth everything out, can create pattern.
"""

import numpy as np

import manimgx as m

R, r = 2.0, 0.95  # the torus's radii (screen units)
NU, NV = 288, 128  # the simulation grid: around the ring, around the tube
CELL = 0.045  # the classic Gray–Scott unit cell, in screen units
D_U, D_V = 0.16 * CELL**2, 0.08 * CELL**2
DT = 0.5
PHASES = {"spots": (0.0367, 0.0649), "labyrinth": (0.0545, 0.062)}
STOPS = ["#07213a", "#0f4c5c", "#2a9d8f", "#e9c46a", "#f4a261", "#fff3d6"]


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


class GrayScott:
    """The two concentrations on the torus's (φ, θ) grid, stepped by explicit Euler."""

    def __init__(self, rng: np.random.Generator) -> None:
        theta = np.linspace(0, m.TAU, NV, endpoint=False)
        self.dphi, self.dtheta = m.TAU / NU, m.TAU / NV
        self.rho = (R + r * np.cos(theta))[None, :]
        self.rho_half = (R + r * np.cos(theta + self.dtheta / 2))[
            None, :
        ]  # ρ between cells
        self.u = np.ones((NU, NV))
        self.v = np.zeros((NU, NV))
        for _ in range(7):  # a few seeds
            i, j = rng.integers(0, NU), rng.integers(0, NV)
            rows, cols = np.arange(i - 3, i + 3) % NU, np.arange(j - 3, j + 3) % NV
            self.u[np.ix_(rows, cols)] = 0.5
            self.v[np.ix_(rows, cols)] = 0.25
        self.v += 0.01 * rng.random((NU, NV))
        self.feed, self.kill = PHASES["spots"]

    def laplacian(self, f: np.ndarray) -> np.ndarray:
        along_ring = (np.roll(f, -1, 0) - 2 * f + np.roll(f, 1, 0)) / (
            self.dphi * self.rho
        ) ** 2
        flux = self.rho_half * (
            np.roll(f, -1, 1) - f
        )  # conservative: ρ f_θ between cells
        around_tube = (flux - np.roll(flux, 1, 1)) / (r * r * self.dtheta**2 * self.rho)
        return along_ring + around_tube

    def step(self, count: int) -> None:
        for _ in range(count):
            uvv = self.u * self.v * self.v
            self.u += DT * (
                D_U * self.laplacian(self.u) - uvv + self.feed * (1 - self.u)
            )
            self.v += DT * (
                D_V * self.laplacian(self.v) + uvv - (self.feed + self.kill) * self.v
            )


def torus_points(bump: np.ndarray) -> np.ndarray:
    """Vertices of the torus, pushed out along the normal by `bump` (grid-shaped)."""
    phi = np.linspace(0, m.TAU, NU, endpoint=False)[:, None]
    theta = np.linspace(0, m.TAU, NV, endpoint=False)[None, :]
    tube = r + bump
    rho = R + tube * np.cos(theta)
    return np.stack(
        [rho * np.cos(phi), rho * np.sin(phi), tube * np.sin(theta)], -1
    ).reshape(-1, 3)


def torus_triangles() -> np.ndarray:
    """A welded periodic grid: every vertex shared, so the surface has no seam."""
    i, j = np.meshgrid(np.arange(NU), np.arange(NV), indexing="ij")
    a = i * NV + j
    b = ((i + 1) % NU) * NV + j
    c = ((i + 1) % NU) * NV + (j + 1) % NV
    d = i * NV + (j + 1) % NV
    return np.concatenate(
        [np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)]
    )


class TuringTorus(m.ThreeDScene):
    def construct(self) -> None:
        chem = GrayScott(np.random.default_rng(1952))
        speed = {"steps": 16}  # simulation steps per tick of the 60 Hz simulation clock
        surface = m.MeshMobject(
            torus_points(np.zeros((NU, NV))),
            torus_triangles(),
            vertex_colors=colormap(np.zeros(NU * NV), STOPS),
            shade_in_3d=True,
        )

        def grow(mob: m.Mobject, dt: float) -> None:
            chem.step(speed["steps"])
            level = np.clip(chem.v * 3.2, 0, 1)
            mob.points = torus_points(0.035 * level)
            mob.paint = mob.paint.but(fill=colormap(level.ravel(), STOPS))

        surface.add_updater(grow)

        title = m.Text("Turing patterns on a torus", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "two chemicals reacting and diffusing (Gray–Scott)", font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )
        equations = (
            m.VGroup(
                m.MathTex(r"\dot u = D_u \Delta u - u v^2 + F(1 - u)", font_size=30),
                m.MathTex(r"\dot v = D_v \Delta v + u v^2 - (F + k)\,v", font_size=30),
            )
            .arrange(m.DOWN, aligned_edge=m.LEFT)
            .to_corner(m.DL)
        )
        feed_value = m.DecimalNumber(chem.feed, num_decimal_places=4, font_size=30)
        kill_value = m.DecimalNumber(chem.kill, num_decimal_places=4, font_size=30)
        feed_value.add_updater(lambda d: d.set_value(chem.feed))
        kill_value.add_updater(lambda d: d.set_value(chem.kill))
        knobs = (
            m.VGroup(
                m.VGroup(m.MathTex("F =", font_size=30), feed_value).arrange(
                    m.RIGHT, buff=0.15
                ),
                m.VGroup(m.MathTex("k =", font_size=30), kill_value).arrange(
                    m.RIGHT, buff=0.15
                ),
            )
            .arrange(m.DOWN, aligned_edge=m.LEFT)
            .to_corner(m.UR)
        )
        closing = m.Text(
            "Diffusion, which smooths, can also create pattern (Turing, 1952)",
            font_size=26,
        )
        closing.to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(title, subtitle, equations, knobs, closing)
        self.remove(equations, knobs, closing)

        self.set_camera_orientation(
            phi=62 * m.DEGREES, theta=-60 * m.DEGREES, zoom=1.05
        )
        self.begin_ambient_camera_rotation(rate=0.1)
        self.add(surface)
        # 0–16 s: seeds grow into spots that divide until they tile the torus
        self.play(m.FadeIn(equations), m.FadeIn(knobs), run_time=2)
        self.wait(6)
        self.move_camera(
            phi=40 * m.DEGREES,
            zoom=1.1,
            frame_center=np.array([0.0, 0.25, 0.0]),
            run_time=4,
        )
        self.wait(3.5)
        # 16–27 s: new F and k: the same equations grow a labyrinth
        chem.feed, chem.kill = PHASES["labyrinth"]
        speed["steps"] = 5  # slower: watch the spots stretch into worms
        self.play(m.Indicate(knobs, color=m.YELLOW, scale_factor=1.1), run_time=1.2)
        self.move_camera(
            phi=66 * m.DEGREES, zoom=1.05, frame_center=np.zeros(3), run_time=5
        )
        self.wait(3.3)
        self.play(m.FadeOut(equations), m.FadeIn(closing), run_time=1)
        speed["steps"] = 12
        self.wait(4)


if __name__ == "__main__":
    TuringTorus().render("turing_torus.mp4")

"""A traffic jam from nowhere, seen in spacetime.

Twenty-two cars drive around a ring road with no bottleneck, no merge, no accident — and within
a minute a jam appears out of nothing, just as it did in Sugiyama and colleagues' experiment on
a real track (New J. Phys., 2008). Each driver speeds toward the speed their gap allows and reacts
with a lag: the optimal-velocity model ẍₙ = a [V(xₙ₊₁ − xₙ) − ẋₙ], V(h) = tanh(h − 2) + tanh 2
(Bando et al., 1995). With the gap at 2 and a = 1, smooth flow is unstable: a tiny wobble grows
into a stop-and-go wave. Lift time into the third dimension (the last 70 time units, the present
on top) and each car's worldline winds up a cylinder; the jam is where worldlines flatten and
crowd — and that knot leans back, moving against the traffic while every car keeps going forward.
"""

import numpy as np

import manimgx as m

N = 22
LENGTH = 44.0  # the ring's length (gap 2 per car)
SENSITIVITY = 1.0
RADIUS = 2.6  # the ring on screen
TIME_SCALE = 12.5  # model time per second of video
RISE = 0.05  # height per unit of model time
WINDOW = 70.0  # how much of the past the cylinder shows (model time)
SPEED_STOPS = ["#e63946", "#f4a261", "#e9c46a", "#8ac926", "#2ec4b6"]  # stopped … fast
V_MAX = 1.0 + np.tanh(2.0)


def optimal_velocity(gap: np.ndarray) -> np.ndarray:
    return np.tanh(gap - 2) + np.tanh(2)


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


class Road:
    """The cars' positions and speeds, integrated with RK4; their histories for the worldlines."""

    def __init__(self) -> None:
        self.x = np.arange(N) * LENGTH / N
        self.x[0] += 0.1  # one driver a little out of place
        self.v = np.full(N, optimal_velocity(np.array(2.0)))
        self.t = 0.0
        self.times: list[float] = [0.0]
        self.xs: list[np.ndarray] = [self.x.copy()]
        self.vs: list[np.ndarray] = [self.v.copy()]

    def rates(self, x: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        gap = (np.roll(x, -1) - x) % LENGTH
        return v, SENSITIVITY * (optimal_velocity(gap) - v)

    def advance(self, duration: float, dt: float = 0.05) -> None:
        for _ in range(max(1, round(duration / dt))):
            k1 = self.rates(self.x, self.v)
            k2 = self.rates(self.x + dt / 2 * k1[0], self.v + dt / 2 * k1[1])
            k3 = self.rates(self.x + dt / 2 * k2[0], self.v + dt / 2 * k2[1])
            k4 = self.rates(self.x + dt * k3[0], self.v + dt * k3[1])
            self.x = self.x + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
            self.v = self.v + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
            self.t += dt
        self.times.append(self.t)
        self.xs.append(self.x.copy())
        self.vs.append(self.v.copy())


def on_ring(x: np.ndarray, height: np.ndarray, radius: float = RADIUS) -> np.ndarray:
    angle = m.TAU * x / LENGTH
    return np.stack([radius * np.cos(angle), radius * np.sin(angle), height], -1)


def worldlines(
    road: Road, lift: float, sides: int = 6
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Every car's worldline over the last WINDOW of model time, as a thin tube on the cylinder
    (the present on top), colored by the car's speed: vertices, triangles, colors. A curve on a
    cylinder has a natural frame — the outward radial direction and its cross with the tangent —
    so no transport along the curve is needed."""
    times = np.array(road.times)
    keep = times >= road.t - WINDOW
    xs, vs = np.array(road.xs)[keep], np.array(road.vs)[keep]  # (samples, cars)
    z = lift * RISE * (times[keep] - (road.t - WINDOW))[:, None] * np.ones((1, N))
    centers = on_ring(xs, z).transpose(1, 0, 2)  # (cars, samples, 3)
    angle = m.TAU * xs.T / LENGTH
    radial = np.stack([np.cos(angle), np.sin(angle), np.zeros_like(angle)], -1)
    tangent = np.gradient(centers, axis=1)
    tangent /= np.linalg.norm(tangent, axis=-1, keepdims=True) + 1e-12
    across = np.cross(tangent, radial)
    across /= np.linalg.norm(across, axis=-1, keepdims=True) + 1e-12
    out = np.cross(across, tangent)
    a = np.linspace(0, m.TAU, sides, endpoint=False)
    ring = (
        np.cos(a)[:, None] * out[:, :, None, :]
        + np.sin(a)[:, None] * across[:, :, None, :]
    )
    verts = (centers[:, :, None, :] + 0.028 * ring).reshape(-1, 3)
    cars, samples = centers.shape[:2]
    i = np.arange(samples - 1)[:, None]
    j = np.arange(sides)[None, :]
    k = (j + 1) % sides
    one = np.stack(
        [
            np.stack([i * sides + j, (i + 1) * sides + j, (i + 1) * sides + k], -1),
            np.stack([i * sides + j, (i + 1) * sides + k, i * sides + k], -1),
        ],
        2,
    ).reshape(-1, 3)
    tris = (one[None] + (np.arange(cars) * samples * sides)[:, None, None]).reshape(
        -1, 3
    )
    speed = np.repeat(vs.T.reshape(-1), sides)
    return verts, tris, colormap(speed / V_MAX, SPEED_STOPS)


class TrafficHelix(m.ThreeDScene):
    def construct(self) -> None:
        road = Road()
        lift = m.ValueTracker(0.0)  # 0: the present only (a flat ring); 1: time rises

        def step(_: m.Mobject, dt: float) -> None:
            road.advance(TIME_SCALE * dt)

        clock = m.Mobject()
        clock.add_updater(step)

        lines = m.MeshMobject(
            np.zeros((3, 3)), np.array([[0, 1, 2]]), shade_in_3d=True
        )  # drawn once time rises

        def redraw(mob: m.Mobject) -> None:
            assert isinstance(mob, m.MeshMobject)
            if lift.get_value() > 0 and len(road.times) > 2:
                verts, tris, rows = worldlines(road, lift.get_value())
                mob.points, mob.triangles = verts, tris
                mob.paint = mob.paint.but(fill=rows)

        lines.add_updater(redraw)
        cars = m.Group(*[m.Dot3D(radius=0.12, color=m.WHITE) for _ in range(N)])

        def drive(group: m.Mobject) -> None:
            height = lift.get_value() * RISE * WINDOW
            colors = colormap(road.v / V_MAX, SPEED_STOPS)
            for k, car in enumerate(group.submobjects):
                car.move_to(on_ring(road.x[k : k + 1], np.array([height]))[0])
                car.set_color(m.ManimColor(colors[k, :3]))

        cars.add_updater(drive)
        track = m.Circle(radius=RADIUS, color=m.GREY_D, stroke_width=10)

        title = m.Text("A traffic jam from nowhere", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "22 cars on a ring road; no bottleneck (Sugiyama et al., 2008)",
            font_size=22,
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        model = m.MathTex(
            r"\ddot x_n = a\,\bigl[V(x_{n+1} - x_n) - \dot x_n\bigr]", font_size=32
        ).to_corner(m.UR)
        bar = m.Rectangle(
            width=2.4, height=0.18, stroke_width=0, fill_opacity=1
        ).set_fill(color=SPEED_STOPS, opacity=1)
        bar.set_sheen_direction(m.RIGHT)
        legend = (
            m.VGroup(m.Text("stopped", font_size=20), bar, m.Text("fast", font_size=20))
            .arrange(m.RIGHT, buff=0.15)
            .next_to(model, m.DOWN, aligned_edge=m.RIGHT, buff=0.3)
        )
        self.add_fixed_in_frame_mobjects(title, subtitle, model, legend)

        # 0–8 s: from above: smooth flow, then a wobble grows into a jam
        self.set_camera_orientation(
            phi=0, theta=-90 * m.DEGREES, focal_distance=40, zoom=1.0
        )
        self.add(track, clock, lines, cars)
        self.wait(8)

        # 8–14 s: lift time into the third dimension: worldlines wind up a cylinder
        up = (
            m.Text("height = time", font_size=26)
            .set_color(m.YELLOW)
            .next_to(legend, m.DOWN, aligned_edge=m.RIGHT, buff=0.25)
        )
        self.add_fixed_in_frame_mobjects(up)
        self.remove(up)
        self.move_camera(
            phi=66 * m.DEGREES,
            theta=-70 * m.DEGREES,
            focal_distance=20,
            zoom=0.9,
            frame_center=np.array([0.0, 0.0, 1.75]),
            added_anims=[lift.animate.set_value(1.0), m.FadeIn(up)],
            run_time=6,
        )
        # 14–30 s: the jam is the band of flat, crowded, red worldlines — and it leans backward
        self.begin_ambient_camera_rotation(rate=0.08)
        self.wait(10)
        closing = m.Text(
            "The jam moves backward while every car moves forward.", font_size=28
        ).to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing), run_time=1)
        self.wait(5)


if __name__ == "__main__":
    TrafficHelix().render("traffic_helix.mp4")

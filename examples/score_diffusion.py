"""Noise into a word: a diffusion model, run with the exact score.

A diffusion model generates data by running noise backwards through time along the "score"
∇ₓ log p_t(x), the direction in which the noised data distribution p_t grows fastest. Here the
data is a mixture of narrow Gaussians sitting on the outlines of a word, so p_t (the data blurred
by the variance-preserving forward process, x_t = α_t x₀ + σ_t ε) is a mixture too, and its score
is exact — no neural network. 2,400 points of pure noise follow the probability-flow ODE
dx/dt = −½β(t)(x + ∇ₓ log p_t(x)) from t = 1 down to t ≈ 0 (Song et al., 2021), and land on the
letters. Height is the noise level σ_t; each point is colored by where it ends up, so the noise
at the top is visibly sorted into the letters on the way down.
"""

import itertools

import numpy as np

import manimgx as m

N_POINTS = 2400
N_CENTERS = 900
SPREAD = 0.012  # the width of each Gaussian on the outline
BETA = (0.1, 20.0)  # β(t) runs linearly between these
STEPS = 240
SCALE = 1.45  # screen units per data unit
HEIGHT = 4.2  # screen height of σ = 1
N_TRAILS = 110
BLOCK = 100  # points at a time in the score, so that its arrays stay in cache
RAINBOW = ["#ff595e", "#ff924c", "#ffca3a", "#8ac926", "#1982c4", "#6a4c93", "#c77dff"]


def colormap(values: np.ndarray, stops: list[str], opacity: float = 1.0) -> np.ndarray:
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.full((len(values), 4), opacity)
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


def word_centers(text: str, count: int) -> np.ndarray:
    """Points spread evenly along the outlines of a word, in data units (width 4.4)."""
    word = m.Text(text, font_size=96).scale_to_fit_width(4.4).move_to(m.ORIGIN)
    leaves = [
        leaf
        for leaf in word.family_members_with_points()
        if isinstance(leaf, m.VMobject)
    ]
    lengths = np.array([leaf.get_arc_length() for leaf in leaves])
    points = []
    for leaf, share in zip(
        leaves,
        np.maximum(3, np.round(count * lengths / lengths.sum())).astype(int),
        strict=True,
    ):
        points += [
            leaf.point_from_proportion(a)[:2]
            for a in np.linspace(0, 1, share, endpoint=False)
        ]
    return np.array(points)


def alpha(t: float) -> float:
    lo, hi = BETA
    return float(np.exp(-0.5 * (lo * t + 0.5 * (hi - lo) * t * t)))


def sigma(t: float) -> float:
    return float(np.sqrt(1 - alpha(t) ** 2))


def velocity(x: np.ndarray, t: float, centers: np.ndarray) -> np.ndarray:
    """The probability-flow ODE's velocity, with the mixture's exact score."""
    a = alpha(t)
    var = a * a * SPREAD**2 + 1 - a * a
    cx, cy = (a * centers).T[:, :, None]  # (centers, 1) each
    score = np.empty_like(x)
    for i in range(0, len(x), BLOCK):
        px, py = x[i : i + BLOCK].T.copy()
        dx, dy = cx - px, cy - py  # the offsets: (centers, points) each
        log_weight = -(dx * dx + dy * dy) / (2 * var)
        log_weight -= log_weight.max(axis=0)
        weight = np.exp(log_weight)
        weight /= weight.T.copy().sum(axis=1)  # each point's weights, summed pairwise
        score[i : i + BLOCK, 0] = (weight * dx).sum(axis=0)
        score[i : i + BLOCK, 1] = (weight * dy).sum(axis=0)
    score /= var
    beta = BETA[0] + t * (BETA[1] - BETA[0])
    return -0.5 * beta * (x + score)


def time_at_noise(level: np.ndarray) -> np.ndarray:
    """t with σ_t = level: −2 log α_t = β₀t + ½(β₁ − β₀)t² is a quadratic in t."""
    lo, hi = BETA
    c = -np.log(1 - level**2)  # = −2 log α
    half = 0.5 * (hi - lo)
    return (-lo + np.sqrt(lo * lo + 4 * half * c)) / (2 * half)


def flow(start: np.ndarray, centers: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Heun steps from t = 1 to t = 0.002, evenly spaced in the noise level σ_t (so the
    descent is steady, and the steps are fine near the data): (times, positions per time).
    """
    levels = np.linspace(sigma(1.0), sigma(0.002), STEPS + 1)
    times = np.concatenate([[1.0], time_at_noise(levels[1:])])
    x = start.copy()
    path = [x.copy()]
    for t, t_next in itertools.pairwise(times):
        h = t_next - t
        v1 = velocity(x, t, centers)
        v2 = velocity(x + h * v1, t_next, centers)
        x = x + 0.5 * h * (v1 + v2)
        path.append(x.copy())
    return times, np.array(path)


class ScoreDiffusion(m.ThreeDScene):
    def construct(self) -> None:
        rng = np.random.default_rng(2021)
        centers = word_centers("manimgx", N_CENTERS)
        times, path = flow(rng.standard_normal((N_POINTS, 2)), centers)
        heights = HEIGHT * np.array([sigma(t) for t in times])
        final = path[-1]
        colors = colormap(
            (final[:, 0] - final[:, 0].min()) / np.ptp(final[:, 0]), RAINBOW, 0.95
        )
        progress = m.ValueTracker(0.0)  # 0: t = 1 (noise) … 1: t ≈ 0 (data)

        def at(p: float) -> tuple[np.ndarray, float]:
            """Positions (screen units, xy) and height at progress p, interpolated between steps."""
            f = p * STEPS
            k = min(int(f), STEPS - 1)
            w = f - k
            xy = (1 - w) * path[k] + w * path[k + 1]
            return SCALE * xy, (1 - w) * heights[k] + w * heights[k + 1]

        cloud = m.PMobject(stroke_width=4.2)
        xy0, z0 = at(0.0)
        cloud.add_points(np.column_stack([xy0, np.full(N_POINTS, z0)]), rgbas=colors)

        def descend(mob: m.Mobject) -> None:
            xy, z = at(progress.get_value())
            mob.points = np.column_stack([xy, np.full(N_POINTS, z)])

        cloud.add_updater(descend)

        # the paths of a few points, all in one path object (a subpath each)
        chosen = rng.choice(N_POINTS, N_TRAILS, replace=False)
        trail_xyz = np.concatenate(
            [
                SCALE * path[:, chosen, :],
                np.broadcast_to(heights[:, None, None], (STEPS + 1, N_TRAILS, 1)),
            ],
            axis=2,
        )
        trails = m.VMobject(stroke_width=1.3)
        trail_colors = [
            m.ManimColor(c).to_hex() for c in colors[chosen, :3].tolist()
        ]  # by destination
        trails.set_stroke(color=trail_colors, opacity=0.6)

        # each step of each trail, a straight cubic Bézier: (trails, steps, 4, 3)
        start, end = trail_xyz[:-1].transpose(1, 0, 2), trail_xyz[1:].transpose(1, 0, 2)
        third = (end - start) / 3
        segments = np.stack([start, start + third, start + 2 * third, end], axis=2)
        shown = 0  # the steps the trails show

        def grow(mob: m.Mobject) -> None:
            nonlocal shown
            upto = max(1, int(progress.get_value() * STEPS))
            if upto != shown:
                shown = upto
                mob.set_points(segments[:, :upto].reshape(-1, 3))

        grow(trails)
        trails.add_updater(grow)

        title = m.Text(
            "Noise into a word, by following the score", font_size=34
        ).to_corner(m.UL)
        subtitle = m.Text(
            "a diffusion model with the exact score of the data (no neural network)",
            font_size=21,
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )
        ode = m.MathTex(
            r"\frac{dx}{dt} = -\tfrac12\,\beta(t)\,\bigl(x + \nabla_x \log"
            r" p_t(x)\bigr)",
            font_size=32,
        ).to_corner(m.DL)
        axis_note = (
            m.Text("height: noise level σ", font_size=22)
            .set_color(m.GREY_B)
            .to_corner(m.DR)
        )
        closing = m.Text(
            "2,400 points of noise, each carried down the score onto the data.",
            font_size=26,
        )
        closing.to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(title, subtitle, ode, axis_note, closing)
        self.remove(ode, closing)

        self.set_camera_orientation(
            phi=58 * m.DEGREES,
            theta=-72 * m.DEGREES,
            zoom=0.82,
            frame_center=np.array([0.0, 0.0, 2.3]),
        )
        self.add(trails, cloud)
        self.begin_ambient_camera_rotation(rate=0.05)
        self.wait(1.5)
        # 1.5–16 s: t from 1 down to 0: the noise is carried onto the letters
        self.play(
            progress.animate.set_value(1.0),
            m.FadeIn(ode, run_time=2),
            self.camera.frame.animate.move_to(np.array([0.0, 0.0, 1.4])),
            run_time=14,
            rate_func=m.smooth,
        )
        self.stop_ambient_camera_rotation()
        # 16–22 s: the whole bundle of paths
        self.move_camera(
            phi=76 * m.DEGREES,
            theta=-40 * m.DEGREES,
            zoom=0.9,
            frame_center=np.array([0.0, 0.0, 1.8]),
            run_time=5,
        )
        # 22–30 s: from above: the word
        self.move_camera(
            phi=0,
            theta=-90 * m.DEGREES,
            zoom=1.5,
            frame_center=np.zeros(3),
            run_time=4.5,
        )
        self.play(m.FadeIn(closing), m.FadeOut(axis_note), m.FadeOut(ode), run_time=1)
        self.play(self.camera.zoom_tracker.animate.set_value(1.6), run_time=4)


if __name__ == "__main__":
    ScoreDiffusion().render("score_diffusion.mp4")

"""How a neural network untangles two spirals.

No straight line separates two interleaved spirals, and no smooth deformation of the plane can pull
them apart: in 2D one arm would have to pass through the other. A small residual network lifts
the plane into 3D instead. Each of its four layers nudges every point, h ↦ h + V tanh(Uh + c), and
training pays for how far points move, so the network learns the cheapest way to untangle. Here
that means raising one arm above the other, until one flat plane cuts the two colors apart (after
Olah, "Neural Networks, Manifolds, and Topology", 2014). Carried back through the layers, that
flat cut becomes the winding boundary between the arms in the input plane.
"""

from dataclasses import dataclass

import numpy as np

import manimgx as m

LAYERS, HIDDEN = 4, 16
TURNS = 1.25  # of each spiral
ENERGY = 0.3  # the price of moving points: small, direct moves win
SEED = 0
SCALE = 2.4  # screen units per unit of the network's space
COLORS = ["#ff9f1c", "#2ec4b6"]


def two_spirals(count: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Two interleaved spirals of TURNS turns in the unit disk, and their labels (0, 1)."""
    turn = np.sqrt(rng.uniform(0.04, 1, count)) * TURNS * m.TAU
    arm = np.stack([np.cos(turn), np.sin(turn)], 1) * (turn / (TURNS * m.TAU))[:, None]
    arm += 0.02 * rng.normal(size=arm.shape)
    return np.concatenate([arm, -arm]), np.repeat([0.0, 1.0], count)


@dataclass
class Network:
    u: list[np.ndarray]  # (HIDDEN, 3) per layer
    c: list[np.ndarray]  # (HIDDEN,)
    v: list[np.ndarray]  # (3, HIDDEN)
    w: np.ndarray  # the classifier's normal
    b: np.ndarray  # and offset, shape (1,)

    def run(self, x: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray]]:
        """The points at every stage (the input in the plane z = 0, then after each layer) and
        each layer's hidden activations."""
        h = np.column_stack([x, np.zeros(len(x))])
        stages, hidden = [h], []
        for u, c, v in zip(self.u, self.c, self.v):
            a = np.tanh(h @ u.T + c)
            h = h + a @ v.T
            stages.append(h)
            hidden.append(a)
        return stages, hidden

    def stages(self, x: np.ndarray) -> list[np.ndarray]:
        return self.run(x)[0]

    def logit(self, x: np.ndarray) -> np.ndarray:
        return self.stages(x)[-1] @ self.w + self.b[0]


def train(
    x: np.ndarray, y: np.ndarray, rng: np.random.Generator, steps: int = 6000
) -> Network:
    """Logistic loss plus ENERGY × the mean squared move of each layer; full-batch Adam, with
    backpropagation written out."""
    net = Network(
        [0.5 * rng.normal(size=(HIDDEN, 3)) for _ in range(LAYERS)],
        [0.5 * rng.normal(size=HIDDEN) for _ in range(LAYERS)],
        [0.1 * rng.normal(size=(3, HIDDEN)) for _ in range(LAYERS)],
        rng.normal(size=3),
        np.zeros(1),
    )
    params = [*net.u, *net.c, *net.v, net.w, net.b]
    first = [np.zeros_like(p) for p in params]
    second = [np.zeros_like(p) for p in params]
    n = len(x)
    for step in range(1, steps + 1):
        stages, hidden = net.run(x)
        prob = 1 / (1 + np.exp(-(stages[-1] @ net.w + net.b[0])))
        g = (prob - y) / n  # d loss / d logit
        grad_u: list[np.ndarray] = [np.zeros(0)] * LAYERS
        grad_c: list[np.ndarray] = [np.zeros(0)] * LAYERS
        grad_v: list[np.ndarray] = [np.zeros(0)] * LAYERS
        grad_w, grad_b = stages[-1].T @ g, np.array([g.sum()])
        back = np.outer(g, net.w)  # d loss / d h, from the top down
        for k in reversed(range(LAYERS)):
            move = hidden[k] @ net.v[k].T
            through = back + 2 * ENERGY * move / n
            grad_v[k] = through.T @ hidden[k]
            pre = (through @ net.v[k]) * (1 - hidden[k] ** 2)
            grad_u[k], grad_c[k] = pre.T @ stages[k], pre.sum(0)
            back = (
                back + pre @ net.u[k]
            )  # h passes through each layer unchanged, plus its move
        for i, (p, grad) in enumerate(
            zip(params, [*grad_u, *grad_c, *grad_v, grad_w, grad_b])
        ):
            first[i] = 0.9 * first[i] + 0.1 * grad
            second[i] = 0.999 * second[i] + 0.001 * grad**2
            p -= (
                0.02
                * (first[i] / (1 - 0.9**step))
                / (np.sqrt(second[i] / (1 - 0.999**step)) + 1e-8)
            )
    return net


def boundary(net: Network, size: float = 1.15, n: int = 240) -> np.ndarray:
    """The network's decision boundary in the input plane (logit = 0), by marching squares:
    segments as (count, 2, 2)."""
    s = np.linspace(-size, size, n)
    gx, gy = np.meshgrid(s, s, indexing="ij")
    f = net.logit(np.column_stack([gx.ravel(), gy.ravel()])).reshape(n, n)
    segments = []
    corners = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for i in range(n - 1):
        for j in range(n - 1):
            values = [f[i + di, j + dj] for di, dj in corners]
            crossings = []
            for k in range(4):
                (ai, aj), (bi, bj) = corners[k], corners[(k + 1) % 4]
                fa, fb = values[k], values[(k + 1) % 4]
                if (fa < 0) != (fb < 0):
                    t = fa / (fa - fb)
                    crossings.append(
                        [
                            s[i + ai] + t * (s[i + bi] - s[i + ai]),
                            s[j + aj] + t * (s[j + bj] - s[j + aj]),
                        ]
                    )
            if len(crossings) == 2:
                segments.append(crossings)
    return np.array(segments)


class NeuralUntangle(m.ThreeDScene):
    def construct(self) -> None:
        rng = np.random.default_rng(SEED)
        x, y = two_spirals(300, rng)
        net = train(x, y, rng)
        accuracy = float(np.mean((net.logit(x) > 0) == (y == 1)))
        # 0: the input plane; k: after layer k (in between: a blend of the two)
        stage = m.ValueTracker(0.0)

        def at(stages: list[np.ndarray]) -> np.ndarray:
            s = stage.get_value()
            k = min(int(s), LAYERS - 1)
            f = s - k
            return SCALE * ((1 - f) * stages[k] + f * stages[k + 1])

        # the grid of the input plane, and the data, carried through every layer
        # (the grid's lines are cut off at radius 1.2: far from the data the layers are wild)
        grid_inputs = []
        for t in np.linspace(-1.1, 1.1, 13):
            half = np.sqrt(1.2**2 - t**2)
            along = np.linspace(-half, half, 90)
            grid_inputs += [
                np.column_stack([np.full(90, t), along]),
                np.column_stack([along, np.full(90, t)]),
            ]
        grid_stages = [net.stages(g) for g in grid_inputs]
        grid = m.VGroup(
            *[
                m.VMobject(stroke_color="#5c677d", stroke_width=1.4, shade_in_3d=True)
                for _ in grid_inputs
            ]
        )

        def bend_grid(group: m.Mobject) -> None:
            for line, stages in zip(group.submobjects, grid_stages):
                assert isinstance(line, m.VMobject)
                line.set_points_as_corners(at(stages))

        bend_grid(grid)
        grid.add_updater(bend_grid)
        data_stages = net.stages(x)
        rows = np.ones((len(x), 4))
        rows[:, :3] = np.array([m.ManimColor(c).to_rgb() for c in COLORS])[
            y.astype(int)
        ]
        data = m.PMobject(stroke_width=7)
        data.add_points(at(data_stages), rgbas=rows)

        def carry(mob: m.Mobject) -> None:
            mob.points = at(data_stages)

        data.add_updater(carry)

        # the classifier: a plane in the last layer's space, w·h + b = 0
        normal = net.w / np.linalg.norm(net.w)
        foot = -net.b[0] * net.w / float(net.w @ net.w)
        u = np.cross(normal, [0.3, 0.5, 0.8])
        u /= np.linalg.norm(u)
        v = np.cross(normal, u)
        cut = m.Polygon(
            *[
                SCALE * (foot + 1.3 * (a * u + b * v))
                for a, b in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
            ],
            stroke_width=1.5,
            stroke_color=m.WHITE,
            fill_color=m.WHITE,
            fill_opacity=0.18,
            shade_in_3d=True,
        )
        # the boundary it cuts: a curve on the sheet, drawn back to the input plane at the end
        pieces = boundary(net)
        piece_stages = net.stages(pieces.reshape(-1, 2))
        edge = m.VMobject(stroke_color=m.WHITE, stroke_width=3.5, shade_in_3d=True)

        def trace_edge(mob: m.Mobject) -> None:
            assert isinstance(mob, m.VMobject)
            ends = at(piece_stages).reshape(-1, 2, 3)
            mob.reset_points()
            for a, b in zip(ends[:, 0], ends[:, 1]):
                mob.start_new_path(a)
                mob.add_line_to(b)

        trace_edge(edge)
        edge.add_updater(trace_edge)

        # HUD
        title = m.Text("How a network untangles two spirals", font_size=38).to_corner(
            m.UL
        )
        subtitle = m.Text(
            "four residual layers, each nudging space: h ↦ h + V tanh(Uh + c)",
            font_size=22,
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        layer_value = m.Integer(0, font_size=30)
        layer_value.add_updater(lambda d: d.set_value(int(round(stage.get_value()))))
        layer_row = m.VGroup(m.Text("layer", font_size=28), layer_value).arrange(
            m.RIGHT, buff=0.15
        )
        layer_row.to_corner(m.UR)
        score = m.Text(
            f"one flat cut separates them: {100 * accuracy:.0f}% of points",
            font_size=24,
        ).to_edge(m.DOWN, buff=0.35)
        back = m.Text(
            "carried back to the input, the flat cut winds between the arms",
            font_size=24,
        ).to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(title, subtitle, layer_row, score, back)
        self.remove(score, back)

        self.set_camera_orientation(phi=35 * m.DEGREES, theta=-90 * m.DEGREES, zoom=1.0)
        self.add(grid, data)
        self.wait(1.5)
        self.begin_ambient_camera_rotation(rate=0.12)
        self.move_camera(phi=64 * m.DEGREES, run_time=2)
        for k in range(1, LAYERS + 1):
            self.play(stage.animate.set_value(k), run_time=3.2)
            self.wait(0.3)
        self.play(m.FadeIn(cut), m.FadeIn(score), m.Create(edge), run_time=1.5)
        self.wait(2.5)
        self.play(m.FadeOut(cut), m.FadeOut(score), run_time=0.6)
        self.play(
            stage.animate.set_value(0),
            m.FadeIn(back, rate_func=m.rush_from),
            run_time=4.4,
        )
        self.stop_ambient_camera_rotation()
        self.move_camera(phi=20 * m.DEGREES, theta=-90 * m.DEGREES, run_time=2)
        self.wait(1.5)


if __name__ == "__main__":
    NeuralUntangle().render("neural_untangle.mp4")

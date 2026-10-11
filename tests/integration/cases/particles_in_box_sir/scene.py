"""Show an SIR epidemic model: 25 dots wandering in a box, one starts red, infects neighbors on contact."""

import math
import random

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "Tests per-dot add_updater(lambda d, dt: ...) for position integration, "
    "wall bounce, and infection spread. Keeps per-dot state in side arrays so "
    "the scene stays type-checkable."
)


class TeacherScene(m.Scene):
    def construct(self):
        random.seed(0)

        # Containing box — inside the safe zone [-6.5, 6.5] x [-3.5, 3.5].
        box_w, box_h = 10.0, 6.0
        box = m.Rectangle(width=box_w, height=box_h).set_stroke(m.WHITE, 2.0)

        # Safe half-extents for wall-bounce clamping (account for the dot radius).
        dot_radius = 0.10
        x_half = box_w / 2.0 - dot_radius
        y_half = box_h / 2.0 - dot_radius

        # Build 25 dots at random positions, each with a random unit-ish velocity.
        n_dots = 25
        speed = 1.2
        dots: list[m.Dot] = []
        velocities: list[np.ndarray] = []
        infected: list[bool] = []
        for _i in range(n_dots):
            x = random.uniform(-x_half, x_half)
            y = random.uniform(-y_half, y_half)
            ang = random.uniform(0.0, 2.0 * math.pi)
            d = m.Dot(
                np.array([x, y, 0.0]),
                radius=dot_radius,
                color=m.BLUE,
            )
            velocities.append(speed * np.array([math.cos(ang), math.sin(ang), 0.0]))
            infected.append(False)
            dots.append(d)

        # Patient zero.
        dots[0].set_color(m.RED)
        infected[0] = True

        # Contagion radius: a blue dot within this distance of a red dot turns red.
        infection_radius = 0.30

        def make_updater(idx: int):
            def update(mob: m.Dot, dt: float) -> None:
                # 1) Integrate position.
                velocity = velocities[idx]
                mob.shift(velocity * dt)
                pos = mob.get_center()

                # 2) Wall bounce — flip the component that went past an edge.
                if pos[0] > x_half:
                    mob.shift((x_half - pos[0]) * m.RIGHT)
                    velocity[0] = -abs(velocity[0])
                elif pos[0] < -x_half:
                    mob.shift((-x_half - pos[0]) * m.RIGHT)
                    velocity[0] = abs(velocity[0])
                if pos[1] > y_half:
                    mob.shift((y_half - pos[1]) * m.UP)
                    velocity[1] = -abs(velocity[1])
                elif pos[1] < -y_half:
                    mob.shift((-y_half - pos[1]) * m.UP)
                    velocity[1] = abs(velocity[1])

                # 3) Infection: if uninfected, check distance to nearby red dots.
                if not infected[idx]:
                    my_pos = mob.get_center()
                    for other_idx, other in enumerate(dots):
                        if other is mob or not infected[other_idx]:
                            continue
                        delta = other.get_center() - my_pos
                        # Cheap AABB reject before the euclidean test.
                        if abs(delta[0]) > infection_radius:
                            continue
                        if abs(delta[1]) > infection_radius:
                            continue
                        if float(np.linalg.norm(delta)) < infection_radius:
                            mob.set_color(m.RED)
                            infected[idx] = True
                            break

            return update

        for i, d in enumerate(dots):
            d.add_updater(make_updater(i))

        # Intro.
        self.play(m.Create(box), run_time=1.0)
        self.play(
            m.LaggedStart(
                *[m.FadeIn(d) for d in dots],
                lag_ratio=0.02,
            ),
            run_time=1.2,
        )

        # Let the simulation run — updaters do the work frame-by-frame.
        self.wait(8.0)

        self.wait(0.5)

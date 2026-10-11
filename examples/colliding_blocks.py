"""Two blocks count the digits of π.

A small block rests between a wall and a big block sliding toward it. Every collision is
perfectly elastic and there is no friction: the small block bounces between the wall and the
big block until the big one turns back and nothing can catch it. Count the clacks. If the big
block is 100ᵈ times heavier, the count is the first d + 1 digits of π: 3, 31, 314, 3141, …
(Galperin, 2003). The reason is a circle: in the coordinates √m₁v₁ and √m₂v₂ the energy keeps
the state on a circle, and each collision steps it along by the same angle, arctan √(m₁/m₂).
Every clack here is simulated, and the counter counts them.
"""

import numpy as np

import manimgx as m

WALL = 11.8  # the README wall's 5 seconds start here
FLOOR = -1.6
WALL_X = -5.6
SPEED = 2.2  # the big block's starting speed, screen units a second
RUNS = [
    (1, 1.0, 1.4),
    (100, 1.4, 1.6),
    (10_000, 1.9, 1.6),
    (1_000_000, 2.3, 1.6),
]  # (ratio, its side, gap)


def simulate(
    ratio: float, small: float, big: float, gap: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """The collisions' times, and the blocks' left edges and velocities just after each
    (the start counted as one), small block first."""
    m1, m2 = 1.0, ratio
    x1, x2 = WALL_X + 1.2, WALL_X + 1.2 + small + gap
    v1, v2 = 0.0, -SPEED
    t = 0.0
    times, positions, velocities = [0.0], [(x1, x2)], [(v1, v2)]
    while True:
        # the next collision: the blocks meeting, or the small block reaching the wall
        meet = (x2 - x1 - small) / (v1 - v2) if v1 > v2 else np.inf
        wall = (x1 - WALL_X) / -v1 if v1 < 0 else np.inf
        dt = min(meet, wall)
        if not np.isfinite(dt):
            break
        t += dt
        x1, x2 = x1 + v1 * dt, x2 + v2 * dt
        if meet <= wall:
            v1, v2 = (
                ((m1 - m2) * v1 + 2 * m2 * v2) / (m1 + m2),
                ((m2 - m1) * v2 + 2 * m1 * v1) / (m1 + m2),
            )
        else:
            v1 = -v1
        times.append(t)
        positions.append((x1, x2))
        velocities.append((v1, v2))
    return np.array(times), np.array(positions), np.array(velocities), np.array([0])


class CollidingBlocks(m.Scene):
    def construct(self) -> None:
        floor = m.Line([WALL_X, FLOOR, 0], [7.2, FLOOR, 0], stroke_width=3)
        wall = m.Line([WALL_X, FLOOR, 0], [WALL_X, 3.0, 0], stroke_width=3)
        hatches = m.VGroup(
            *(
                m.Line([WALL_X, y, 0], [WALL_X - 0.3, y - 0.3, 0], stroke_width=2)
                for y in np.arange(FLOOR + 0.3, 3.0, 0.3)
            )
        )
        counter_label = m.Tex("collisions:", font_size=60)
        counter = m.Integer(0, font_size=72, color=m.YELLOW)
        readout = m.VGroup(counter_label, counter).arrange(m.RIGHT, buff=0.3)
        readout.move_to([0.8, 3.0, 0])
        counter_place = counter.get_left()
        self.play(
            m.Create(floor),
            m.Create(wall),
            m.Create(hatches),
            m.FadeIn(readout),
            run_time=1,
        )

        record = m.VGroup()  # the counts so far, under the counter
        for ratio, side, gap in RUNS:
            small_side = 0.7
            times, positions, velocities, _ = simulate(ratio, small_side, side, gap)
            clock = m.ValueTracker(0.0)
            small = m.Square(
                small_side,
                fill_color=m.BLUE_E,
                fill_opacity=1,
                stroke_color=m.BLUE_B,
                stroke_width=3,
            )
            big = m.Square(
                side,
                fill_color=m.BLUE_D,
                fill_opacity=1,
                stroke_color=m.BLUE_B,
                stroke_width=3,
            )
            small.add(m.MathTex("1", font_size=36).move_to(small))
            mass = f"{ratio:,}".replace(",", r"{,}")
            big.add(m.MathTex(mass, font_size=40 if ratio < 10**6 else 32).move_to(big))

            def place(
                _: m.Mobject,
                small: m.Mobject = small,
                big: m.Mobject = big,
                times: np.ndarray = times,
                positions: np.ndarray = positions,
                velocities: np.ndarray = velocities,
                clock: m.ValueTracker = clock,
            ) -> None:
                t = clock.get_value()
                k = int(np.searchsorted(times, t, side="right")) - 1
                x1, x2 = positions[k] + velocities[k] * (t - times[k])
                small.move_to([x1 + small.width / 2, FLOOR + small.height / 2, 0])
                big.move_to([x2 + big.width / 2, FLOOR + big.height / 2, 0])
                counter.set_value(k)
                counter.move_to(counter_place, aligned_edge=m.LEFT)

            blocks = m.VGroup(small, big)
            blocks.add_updater(place)
            place(blocks)
            self.play(m.FadeIn(blocks, shift=0.3 * m.DOWN), run_time=0.6)
            # until the big block has left the frame, or the last clack and a moment after
            last = times[-1]
            leave = (7.4 - positions[-1][1]) / max(velocities[-1][1], 1e-9) + last
            duration = min(leave, last + 1.6)
            self.play(
                clock.animate.set_value(duration), run_time=duration, rate_func=m.linear
            )
            blocks.clear_updaters()
            count = len(times) - 1
            entry = m.MathTex(rf"{mass} : {count}", font_size=40, color=m.GREY_A)
            record.add(entry)
            record.arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.22)
            record.move_to([WALL_X + 0.6, 2.75, 0], aligned_edge=m.UL)
            self.play(
                m.FadeOut(blocks), m.TransformFromCopy(counter, entry), run_time=0.8
            )
        digits = m.MathTex(r"\pi = 3.14159\ldots", font_size=64, color=m.YELLOW)
        digits.next_to(readout, m.DOWN, buff=0.5)
        self.play(m.Write(digits), run_time=1.2)
        self.wait(2)


if __name__ == "__main__":
    CollidingBlocks().render("colliding_blocks.mp4")

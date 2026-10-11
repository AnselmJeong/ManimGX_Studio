"""Show a Galton board: balls drop through pegs and accumulate into a bell curve in the buckets."""

import random

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "Tests MoveAlongPath through a polyline path + LaggedStart of 12 ball drops + "
    "histogram bars whose heights encode bucket counts. Paths are precomputed."
)


class TeacherScene(m.Scene):
    def construct(self):
        random.seed(0)

        # Geometry: 5 rows of pegs (rows 0..4), row k has k+1 pegs,
        # 6 buckets below. Horizontal peg spacing is `dx` per row half-step.
        n_rows = 5
        dx = 0.55
        dy = 0.55
        top_y = 2.6  # y of the ball's starting point
        peg_top_y = top_y - 0.5  # y of the top peg row

        # Build pegs.
        pegs = m.VGroup()
        peg_positions: list[list[np.ndarray]] = []
        for row in range(n_rows):
            row_positions: list[np.ndarray] = []
            for col in range(row + 1):
                x = (col - row / 2.0) * dx
                y = peg_top_y - row * dy
                pos = np.array([x, y, 0.0])
                pegs.add(m.Dot(pos, radius=0.05, color=m.GREY))
                row_positions.append(pos)
            peg_positions.append(row_positions)

        # Bucket floor: `n_rows + 1` columns, each width `dx`.
        n_buckets = n_rows + 1
        bucket_y = peg_top_y - n_rows * dy - 0.4
        floor = m.Line(
            np.array([-(n_buckets / 2.0) * dx, bucket_y, 0.0]),
            np.array([(n_buckets / 2.0) * dx, bucket_y, 0.0]),
            color=m.GREY_B,
            stroke_width=2.0,
        )
        # Bucket dividers.
        dividers = m.VGroup()
        for i in range(n_buckets + 1):
            x = (i - n_buckets / 2.0) * dx
            dividers.add(
                m.Line(
                    np.array([x, bucket_y, 0.0]),
                    np.array([x, bucket_y + 0.15, 0.0]),
                    color=m.GREY_B,
                    stroke_width=2.0,
                )
            )

        m.VGroup(pegs, floor, dividers)

        self.play(m.Create(pegs), run_time=1.0)
        self.play(m.Create(floor), m.Create(dividers), run_time=0.8)

        # For each ball, randomly choose left/right at each row; build the path.
        n_balls = 12
        balls: list[m.Dot] = []
        paths: list[m.VMobject] = []
        bucket_counts = [0] * n_buckets

        for _ in range(n_balls):
            # A ball's bucket index is the count of right-moves across n_rows trials.
            rights = 0
            corners: list[np.ndarray] = [np.array([0.0, top_y, 0.0])]
            x_offset = 0.0  # horizontal position of ball in "half-step units"

            for row in range(n_rows):
                # Peg it hits in this row (same horizontal offset as current x_offset).
                peg_x = x_offset * dx
                peg_y = peg_top_y - row * dy
                corners.append(np.array([peg_x, peg_y + 0.08, 0.0]))
                # Choose direction.
                go_right = random.random() < 0.5
                if go_right:
                    rights += 1
                    x_offset += 0.5
                else:
                    x_offset -= 0.5

            # Final fall into bucket (bucket index = rights).
            bucket_x = (rights - n_rows / 2.0) * dx
            corners.append(np.array([bucket_x, bucket_y + 0.08, 0.0]))

            path = m.VMobject()
            path.set_points_as_corners(corners)
            path.set_stroke(opacity=0.0)  # invisible, used only for MoveAlongPath
            paths.append(path)

            ball = m.Dot(corners[0], radius=0.08, color=m.YELLOW)
            balls.append(ball)
            bucket_counts[rights] += 1

        self.add(*balls)

        # Stagger-drop all balls along their paths.
        self.play(
            m.LaggedStart(
                *[
                    m.MoveAlongPath(ball, path, run_time=2.0)
                    for ball, path in zip(balls, paths, strict=False)
                ],
                lag_ratio=0.15,
            ),
            run_time=6.0,
        )

        # After the drop, convert the ball pile into histogram bars.
        max(bucket_counts)
        bar_unit = 0.18  # height per ball
        bars = m.VGroup()
        for i, count in enumerate(bucket_counts):
            if count == 0:
                continue
            bx = (i - (n_buckets - 1) / 2.0) * dx
            bar = (
                m.Rectangle(
                    width=dx * 0.85,
                    height=count * bar_unit,
                    color=m.BLUE,
                )
                .set_fill(m.BLUE, 0.6)
                .set_stroke(m.BLUE_E, 1.5)
            )
            bar.move_to(np.array([bx, bucket_y + 0.01 + count * bar_unit / 2.0, 0.0]))
            bars.add(bar)

        # Replace the stack of balls with clean histogram bars.
        self.play(
            m.FadeOut(m.VGroup(*balls)),
            m.LaggedStart(
                *[m.FadeIn(bar) for bar in bars],
                lag_ratio=0.1,
            ),
            run_time=1.5,
        )

        self.wait(0.5)

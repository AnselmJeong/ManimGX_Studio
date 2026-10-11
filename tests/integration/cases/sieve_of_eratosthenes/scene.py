"""Show me the Sieve of Eratosthenes on a 10x10 grid: cross out multiples of 2, then 3, then 5."""

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


class TeacherScene(m.Scene):
    def construct(self):
        # Build a 10x10 grid of Squares.
        cells = m.VGroup(
            *[
                m.Square(side_length=0.5).set_stroke(m.WHITE, width=1.0)
                for _ in range(100)
            ]
        ).arrange_in_grid(10, 10, buff=0.05)
        cells.move_to(m.ORIGIN)

        # One Integer per cell (1..100). Numbers go left-to-right, top-to-bottom.
        # arrange_in_grid(rows=10, cols=10) with default fills row-by-row,
        # so cells[k] corresponds to value k+1.
        numbers = m.VGroup()
        for k, cell in enumerate(cells):
            n = k + 1
            num = m.Integer(n).scale(0.45).move_to(cell.get_center())
            numbers.add(num)

        # Title label at the top.
        title = m.MathTex(R"\text{Sieve of Eratosthenes}").scale(0.9)
        title.to_edge(m.UP, buff=0.3)

        # Gray out the "1" (which is neither prime nor composite by convention).
        one_label = numbers[0]

        self.play(m.Write(title), run_time=0.8)
        self.play(m.Create(cells), run_time=1.2)
        self.play(
            m.LaggedStart(
                *[m.Write(n) for n in numbers],
                lag_ratio=0.01,
            ),
            run_time=1.5,
        )
        # Gray out 1 — not prime.
        self.play(one_label.animate.set_color(m.GREY), run_time=0.4)

        # --- Sweep through small primes: 2, 3, 5. For each, cross out its multiples
        #     (excluding the prime itself), then fade them out. ---
        crossed_out: set[int] = {1}

        def sweep_prime(p: int, color: str) -> None:
            # Highlight the prime itself.
            prime_label = numbers[p - 1]
            # Collect the multiples of p greater than p that are still live.
            multiples = [k for k in range(2 * p, 101, p) if k not in crossed_out]
            crosses = m.VGroup(
                *[
                    m.Cross(numbers[k - 1], color=color, stroke_width=4.0)
                    for k in multiples
                ]
            )

            # Emphasize the prime in its own color.
            self.play(prime_label.animate.set_color(color), run_time=0.4)

            # Draw crosses one by one (lagged) over each multiple.
            self.play(
                m.LaggedStart(
                    *[m.Create(c) for c in crosses],
                    lag_ratio=0.05,
                ),
                run_time=1.5,
            )

            # Fade out the numbers + crosses for those multiples, then mark them as crossed.
            fade_targets = m.VGroup(
                *[numbers[k - 1] for k in multiples],
                *list(crosses),
            )
            self.play(m.FadeOut(fade_targets), run_time=0.8)
            for k in multiples:
                crossed_out.add(k)

        sweep_prime(2, m.RED)
        sweep_prime(3, m.BLUE)
        sweep_prime(5, m.GREEN)

        self.wait(0.5)

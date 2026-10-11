"""Show why e^(i*pi) = -1 by chaining together Taylor series terms as vectors that spiral to -1."""

import numpy as np

import manimgx as m

EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = ""


N_TERMS = 7


def partial_sums(t: float) -> list[complex]:
    """Cumulative partial sums of sum_{k=0}^{N} (it)^k / k!."""
    z = 1.0 + 0.0j
    sums: list[complex] = [z]
    term = 1.0 + 0.0j  # (it)^0 / 0! = 1
    for k in range(1, N_TERMS + 1):
        term = term * (1j * t) / k
        z = z + term
        sums.append(z)
    return sums


class TeacherScene(m.Scene):
    def construct(self):
        plane = m.ComplexPlane(
            x_range=(-2.0, 2.0, 1.0),
            y_range=(-2.0, 2.0, 1.0),
            x_length=6.0,
            y_length=6.0,
        ).shift(0.3 * m.DOWN)

        title = (
            m.MathTex(R"e^{i\pi} = \sum_{k=0}^{\infty} \frac{(i\pi)^k}{k!}")
            .scale(0.95)
            .to_edge(m.UP)
        )

        self.play(m.Create(plane), run_time=1.2)
        self.play(m.Write(title), run_time=1.2)
        self.wait(0.3)

        t_tracker = m.ValueTracker(0.0)

        # Chain of arrows — each arrow k goes from partial_sum[k-1] to partial_sum[k].
        def build_chain() -> m.VGroup:
            t = t_tracker.get_value()
            sums = partial_sums(t)
            arrows = m.VGroup()
            palette = [
                m.YELLOW,
                m.ORANGE,
                m.RED,
                m.PINK,
                m.PURPLE,
                m.BLUE,
                m.GREEN,
            ]
            for k in range(1, len(sums)):
                start = plane.number_to_point(sums[k - 1])
                end = plane.number_to_point(sums[k])
                if np.linalg.norm(end - start) < 1e-4:
                    continue
                color = palette[(k - 1) % len(palette)]
                arrows.add(
                    m.Arrow(
                        start,
                        end,
                        color=color,
                        buff=0.0,
                        stroke_width=4.0,
                        max_tip_length_to_length_ratio=0.35,
                    )
                )
            return arrows

        chain = m.always_redraw(build_chain)

        # Green dot at the cumulative endpoint.
        endpoint_dot = m.always_redraw(
            lambda: m.Dot(
                plane.number_to_point(partial_sums(t_tracker.get_value())[-1]),
                color=m.GREEN,
                radius=0.1,
            )
        )

        # Reference mark at -1.
        target_dot = m.Dot(
            plane.number_to_point(-1.0 + 0.0j), color=m.WHITE, radius=0.08
        )
        target_label = (
            m.MathTex("-1", color=m.WHITE)
            .scale(0.7)
            .next_to(target_dot, m.DOWN, buff=0.1)
        )

        self.play(m.FadeIn(target_dot), m.Write(target_label), run_time=0.6)
        self.add(chain, endpoint_dot)

        self.play(
            t_tracker.animate.set_value(m.PI),
            run_time=5.0,
            rate_func=m.smooth,
        )
        self.wait(0.5)

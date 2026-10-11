"""Show how a chain of rotating vectors traces out a sine wave."""

import numpy as np

import manimgx as m

# Three-term Fourier-style chain. Each term has (frequency, radius, phase).
# The chain lives in 2D; the i-th vector's tail is the (i-1)-th vector's tip.
TERMS = (
    (1, 1.0 * 2, 0.0),
    (-1, 0.4 * 2, 0.0),
    (3, 0.25 * 2, 0.0),
)


def chain_tip(t: float, up_to: int | None = None) -> np.ndarray:
    """World-space offset of the tip of vector index `up_to` at time t (relative to anchor)."""
    tip = np.array([0.0, 0.0, 0.0])
    terms = TERMS if up_to is None else TERMS[: up_to + 1]
    for freq, radius, phase in terms:
        angle = freq * t + phase
        tip = tip + np.array([radius * np.cos(angle), radius * np.sin(angle), 0.0])
    return tip


class TeacherScene(m.Scene):
    def construct(self):
        # Anchor the chain on the left side so the traced path has room on the right.
        anchor = np.array([-3.5, 0.0, 0.0])

        # Time tracker shared across every vector's updater — this is the coupling.
        t = m.ValueTracker(0.0)

        # Circles visualize each rotation's orbit. Each circle is centered on the tip below.
        colors = [m.BLUE, m.YELLOW, m.RED]
        circles: list[m.Mobject] = []
        for i, (_, radius, _) in enumerate(TERMS):
            color = colors[i]

            def make_circle(
                i: int = i, radius: float = radius, color: str = color
            ) -> m.Circle:
                center = anchor + chain_tip(t.get_value(), up_to=i - 1)
                return (
                    m.Circle(radius=radius, color=color, stroke_width=1.5)
                    .set_stroke(opacity=0.35)
                    .move_to(center)
                )

            circles.append(m.always_redraw(make_circle))

        # Vectors: one per term. Each Vector constructs with its term's nominal direction at origin,
        # then its updater re-positions it every frame via put_start_and_end_on from the shared tracker.
        vectors: list[m.Vector] = []
        for i, (_, radius, _) in enumerate(TERMS):
            color = colors[i]
            # Initial direction is just the radius along +x; updater overrides it every frame.
            vec = m.Vector(direction=(radius, 0.0, 0.0), color=color)
            vec.set_stroke(width=4.0)

            def _updater(mob: m.Vector, i: int = i) -> None:
                start = anchor + chain_tip(t.get_value(), up_to=i - 1)
                end = anchor + chain_tip(t.get_value(), up_to=i)
                mob.put_start_and_end_on(start, end)

            vec.add_updater(_updater)
            vectors.append(vec)

        # TracedPath on the final tip. As t ramps, this sketches the sine-like curve.
        trace = m.TracedPath(
            lambda: anchor + chain_tip(t.get_value()),
            stroke_color=m.GREEN,
            stroke_width=3.0,
        )

        # A dot on the tip so the eye locks onto the trace.
        tip_dot = m.always_redraw(
            lambda: m.Dot(
                anchor + chain_tip(t.get_value()),
                radius=0.07,
                color=m.WHITE,
            )
        )

        # Reveal the chain one ring at a time.
        self.play(m.Create(circles[0]), m.Create(vectors[0]), run_time=0.8)
        self.play(m.Create(circles[1]), m.Create(vectors[1]), run_time=0.8)
        self.play(m.Create(circles[2]), m.Create(vectors[2]), run_time=0.8)

        self.add(tip_dot, trace)
        self.play(m.FadeIn(tip_dot), run_time=0.4)

        # Run the chain — linear so the frequency pattern reads cleanly.
        self.play(t.animate.set_value(4.0 * m.PI), run_time=6.0, rate_func=m.linear)

        self.wait(0.5)

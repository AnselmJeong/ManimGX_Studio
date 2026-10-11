"""e^{iπ} = −1, as a walk.

The exponential is a sum: eˣ = 1 + x + x²/2! + x³/3! + ⋯. Put x = iπ and draw the terms as
arrows, tip to tail. Each term is the last one times iπ/n, and multiplying by i turns an arrow a
quarter turn, so the walk turns a quarter turn at every step; the arrows grow while π/n > 1,
then n! wins and they shrink, and the walk spirals in on a single point: −1. Put x = it instead:
as t changes the walk reshapes, and its end runs around the unit circle, at angle t from 1, so
e^{it} = cos t + i sin t. Halfway round, at t = π, it is −1: e^{iπ} + 1 = 0.
"""

import numpy as np

import manimgx as m

UNIT = 1.0  # scene units per unit of the complex plane
ZERO = np.array([-1.3, -0.45, 0.0])  # where 0 is on screen
TERMS = 20  # enough for |t| ≤ π: the next term is below 10⁻⁷
COLORS = m.color_gradient(
    [m.BLUE, m.TEAL, m.GREEN, m.YELLOW, m.GOLD, m.RED, m.MAROON, m.PURPLE], 10
)
COLUMN = 4.35  # the x of the formulas' column
WALL = 11.25


def terms(x: complex, count: int = TERMS) -> np.ndarray:
    """The terms xⁿ/n! of the exponential series, n = 0 … count − 1: each the last times x/n."""
    out = np.empty(count, dtype=complex)
    out[0] = 1.0
    for n in range(1, count):
        out[n] = out[n - 1] * x / n
    return out


def point(z: complex) -> np.ndarray:
    """Where the complex number z is on screen."""
    return ZERO + UNIT * np.array([z.real, z.imag, 0.0])


def color(n: float) -> m.ManimColor:
    """The color of term n (between two terms, a blend of theirs)."""
    k = min(int(n), len(COLORS) - 1)
    following = COLORS[min(k + 1, len(COLORS) - 1)]
    return m.interpolate_color(COLORS[k], following, n - int(n))


def term_arrow(start: complex, end: complex, n: float) -> m.Arrow:
    return m.Arrow(
        point(start),
        point(end),
        buff=0,
        stroke_width=8,
        tip_length=0.3,
        color=color(n),
    )


def walk(x: complex) -> m.VGroup:
    """The terms of e^x as arrows tip to tail, leaving out those too short to see."""
    sums = np.concatenate([[0], np.cumsum(terms(x))])
    return m.VGroup(
        *(
            term_arrow(sums[n], sums[n + 1], n)
            for n in range(TERMS)
            if UNIT * abs(sums[n + 1] - sums[n]) > 0.02
        )
    )


def next_term(arrow: m.Arrow, n: int, x: complex) -> m.UpdateFromAlphaFunc:
    """Turn a copy of term n − 1 into term n: its tail slides to the walk's end while it turns
    and stretches by x/n, continuously (by the powers (x/n)^α, α from 0 to 1)."""
    values = terms(x, n + 1)
    tail_from = complex(np.sum(values[: n - 1]))

    def update(mob: m.Mobject, alpha: float) -> None:
        tail = tail_from + alpha * values[n - 1]
        vector = values[n - 1] * (x / n) ** alpha
        mob.become(term_arrow(tail, tail + vector, n - 1 + alpha))

    return m.UpdateFromAlphaFunc(arrow, update)


class EulerIdentity(m.Scene):
    def construct(self) -> None:
        plane = m.ComplexPlane(
            x_range=[-5, 2, 1],
            y_range=[-3.5, 3.5, 1],
            x_length=7 * UNIT,
            y_length=7 * UNIT,
            background_line_style={
                "stroke_color": m.BLUE_D,
                "stroke_width": 1.5,
                "stroke_opacity": 0.5,
            },
        )
        plane.shift(point(-1.5 + 0j) - plane.get_center())
        series = m.MathTex(r"e^{x} = \sum_{n=0}^{\infty} \frac{x^n}{n!}", font_size=56)
        series.move_to(np.array([COLUMN, 2.6, 0.0]))
        x_is = m.MathTex(r"{{x}} = {{i \pi}}", font_size=56)
        x_is.next_to(series, m.DOWN, buff=0.6)

        self.play(m.Create(plane, lag_ratio=0.1), m.Write(series), run_time=1.2)
        self.play(m.FadeIn(x_is), run_time=0.5)

        # the walk for x = iπ, term by term: each a quarter turn from the last
        x = 1j * np.pi
        values = terms(x)
        sums = np.concatenate([[0], np.cumsum(values)])
        names = [
            "1",
            r"i\pi",
            r"\frac{(i\pi)^2}{2!}",
            r"\frac{(i\pi)^3}{3!}",
            r"\frac{(i\pi)^4}{4!}",
        ]
        labels = m.VGroup()
        for n, name in enumerate(names):
            direction = values[n] / abs(values[n])
            outward = np.array([direction.imag, -direction.real, 0.0])  # its right side
            middle = point((sums[n] + sums[n + 1]) / 2)
            label = m.MathTex(name, font_size=44, color=COLORS[n])
            labels.add(label.next_to(middle, outward, buff=0.2))

        arrows = [term_arrow(0, 1, 0)]
        self.play(m.GrowArrow(arrows[0]), m.FadeIn(labels[0]), run_time=0.8)
        for n in range(1, 12):
            arrow = arrows[-1].copy()
            self.add(arrow)
            arrows.append(arrow)
            if n < len(names):
                self.play(next_term(arrow, n, x), m.FadeIn(labels[n]), run_time=1.0)
            else:
                self.play(next_term(arrow, n, x), run_time=0.45 if n < 8 else 0.25)
        rest = walk(x)[12:]
        self.add(rest)

        total = complex(sums[-1])  # the whole sum: −1, to the last digit drawn
        end = m.Dot(point(total), radius=0.09, color=m.WHITE)
        sign = "-" if total.real < 0 else "+"
        end_label = m.MathTex(
            "{{" + sign + "}}{{" + f"{abs(total.real):.0f}" + "}}", font_size=48
        )
        end_label.next_to(end, m.DL, buff=0.12)
        self.play(m.FadeIn(end, scale=0.5), m.Write(end_label), run_time=0.8)
        self.wait(0.6)

        # let the exponent vary: the walk for x = it, as t runs once round and back
        t = m.ValueTracker(np.pi)
        x_it = m.MathTex(r"{{x}} = {{i t}}", font_size=56).move_to(x_is)
        t_value = m.DecimalNumber(np.pi, num_decimal_places=2, font_size=56)
        t_row = m.VGroup(m.MathTex("t =", font_size=56), t_value)
        t_row.arrange(m.RIGHT, buff=0.2).next_to(x_it, m.DOWN, buff=0.45)
        t_value.add_updater(lambda d: d.set_value(t.get_value()))
        moving = m.always_redraw(lambda: walk(1j * t.get_value()))
        tip = m.always_redraw(
            lambda: m.Dot(point(np.exp(1j * t.get_value())), radius=0.09)
        )
        trace = m.TracedPath(tip.get_center, stroke_color=m.YELLOW, stroke_width=6)
        self.remove(*arrows, rest, end)
        self.add(trace, moving, tip)
        self.play(
            m.FadeOut(labels),
            m.FadeOut(end_label),
            m.TransformMatchingTex(x_is, x_it),
            m.FadeIn(t_row),
            run_time=1.0,
        )
        self.play(t.animate.set_value(-np.pi), run_time=5.5)
        circle_law = m.MathTex(r"e^{it} = \cos t + i \sin t", font_size=48)
        circle_law.next_to(t_row, m.DOWN, buff=0.75)
        self.play(
            t.animate(run_time=5.0).set_value(np.pi),
            m.Write(circle_law, run_time=1.5),
        )

        # halfway round
        minus_one = end_label.copy()
        self.play(m.FadeIn(minus_one), run_time=0.5)
        identity = m.MathTex(r"{{ e^{i\pi} }} {{=}} {{-}}{{1}}", font_size=80)
        identity.move_to(np.array([COLUMN, -2.75, 0.0]))
        self.play(
            m.FadeIn(identity[0]),
            m.FadeIn(identity[1]),
            m.TransformFromCopy(minus_one[0], identity[2]),
            m.TransformFromCopy(minus_one[1], identity[3]),
            run_time=1.3,
        )
        final = m.MathTex(r"{{ e^{i\pi} }} {{+}} {{1}} {{=}} {{0}}", font_size=80)
        final.move_to(identity)
        self.play(m.TransformMatchingTex(identity, final), run_time=1.6)
        self.wait(2.0)


if __name__ == "__main__":
    EulerIdentity().render("euler_identity.mp4")

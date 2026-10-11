"""Polynomials that turn into the sine.

Near 0, sin x looks like x. Subtract x³/3! and the cubic bends back down with the sine; add
x⁵/5! and it follows the next turn; every term fixes the error the one before it left. The
Taylor polynomial of degree 2n + 1 matches sin x and its first 2n + 1 derivatives at 0, and its
error is at most |x|^(2n+3)/(2n + 3)!: a factorial outruns any power, so each new term hugs the
wave over a wider stretch, and the whole infinite series is the sine everywhere.
"""

from math import factorial

import numpy as np

import manimgx as m

WALL = 9.4  # the polynomial chases the sine out to the edges

DEGREES = list(range(1, 41, 2))  # 1, 3, …, 39
# the terms written out one by one, to x¹⁹/19!; the rest rush in at the end
WRITTEN = 10
X_MAX = 11.0  # the axes run over |x| ≤ X_MAX
Y_MAX = 3.0  # and |y| ≤ Y_MAX; a polynomial is cut where it leaves them
COLORS = m.color_gradient([m.YELLOW, m.RED, m.PURPLE_A], WRITTEN)
XS = np.linspace(-X_MAX, X_MAX, 2201)


def term(degree: int, x: np.ndarray) -> np.ndarray:
    """The series' term of this (odd) degree: ±x^degree / degree!."""
    sign = -1 if degree % 4 == 3 else 1
    return sign * x**degree / factorial(degree)


def term_tex(degree: int) -> str:
    if degree == 1:
        return "x"
    sign = "-" if degree % 4 == 3 else "+"
    return sign + rf" \frac{{x^{{{degree}}}}}{{{degree}!}}"


def color(k: int) -> m.ManimColor:
    """The color of the polynomial with k + 1 terms, and of its last term."""
    return COLORS[min(k, WRITTEN - 1)]


def series_tex(count: int) -> m.MathTex:
    """sin x ≈ the first `count` terms; past seven, the middle ones go into ⋯."""
    shown = list(range(count))
    if count > 7:
        shown = [0, 1, 2, 3, -1, count - 1]
    parts = [r"\sin x", r"\approx"]
    parts += [r"+ \cdots" if k < 0 else term_tex(DEGREES[k]) for k in shown]
    tex = m.MathTex(*parts, font_size=50)
    tex[0].set_color(m.BLUE)
    for part, k in zip(tex[2:], shown, strict=True):
        if k >= 0:
            part.set_color(color(k))
    return tex.move_to(3.25 * m.UP)


class TaylorSeries(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(
            x_range=[-X_MAX, X_MAX, np.pi],
            y_range=[-Y_MAX, Y_MAX, 1],
            x_length=13.4,
            y_length=5.4,
            tips=False,
            axis_config={"stroke_width": 3, "color": m.GREY_B},
        ).move_to(0.7 * m.DOWN)
        sine = axes.plot(
            np.sin, x_range=[-X_MAX, X_MAX, 0.02], color=m.BLUE, stroke_width=6
        )

        # the polynomial: all the terms below `reach`, and the next one scaled by its fraction
        reach = m.ValueTracker(1.0)

        def polynomial() -> m.VMobject:
            done = int(reach.get_value())
            s = reach.get_value() - done
            ys = np.sum([term(d, XS) for d in DEGREES[:done]], axis=0)
            if s > 0 and done < len(DEGREES):
                ys = ys + s * term(DEGREES[done], XS)
            # keep the stretch around 0 inside the axes, cut where it leaves them
            inside = np.abs(ys) <= Y_MAX
            middle = len(XS) // 2
            left_out = np.nonzero(~inside[:middle])[0]
            right_out = np.nonzero(~inside[middle:])[0]
            lo = left_out[-1] + 1 if len(left_out) else 0
            hi = middle + right_out[0] if len(right_out) else len(XS)
            xs, ys_in = list(XS[lo:hi]), list(ys[lo:hi])
            if lo > 0:  # the exact point where it leaves, on each side
                a, b = lo, lo - 1
                bound = np.sign(ys[b]) * Y_MAX
                t = (bound - ys[a]) / (ys[b] - ys[a])
                xs.insert(0, XS[a] + t * (XS[b] - XS[a]))
                ys_in.insert(0, bound)
            if hi < len(XS):
                a, b = hi - 1, hi
                bound = np.sign(ys[b]) * Y_MAX
                t = (bound - ys[a]) / (ys[b] - ys[a])
                xs.append(XS[a] + t * (XS[b] - XS[a]))
                ys_in.append(bound)
            shade = color(done - 1)
            if s > 0 and done < len(DEGREES):
                shade = m.interpolate_color(color(done - 1), color(done), s)
            # thinner once past the written terms, so the sine shows around it
            width = 7 - 3 * min(1.0, max(0.0, (reach.get_value() - WRITTEN) / 4))
            curve = m.VMobject(stroke_color=shade, stroke_width=width)
            curve.set_points_as_corners(axes.c2p(np.array(xs), np.array(ys_in)).T)
            return curve

        poly = m.always_redraw(polynomial)
        series = series_tex(1)

        self.add(axes)
        self.play(m.Create(sine), run_time=1.6)
        self.play(m.Create(poly), m.Write(series), run_time=1.2)
        self.remove(poly)
        poly = m.always_redraw(polynomial)
        self.add(poly)
        # each new term bends the polynomial along one more turn of the wave
        for count in range(2, WRITTEN + 1):
            new_series = series_tex(count)
            self.play(
                reach.animate.set_value(float(count)),
                m.TransformMatchingTex(series, new_series),
                run_time=1.6,
            )
            series = new_series
        self.wait(0.8)

        # all the terms: the series is the sine
        whole = m.MathTex(
            r"\sin x",
            "=",
            r"\sum_{n=0}^{\infty} \frac{(-1)^n\, x^{2n+1}}{(2n+1)!}",
            font_size=56,
        )
        whole[0].set_color(m.BLUE)
        whole.move_to(3.2 * m.UP)
        # every term at once: the polynomial lies on the sine all the way across
        self.play(reach.animate.set_value(float(len(DEGREES))), run_time=2.5)
        name, approx, terms = series[0], series[1], m.VGroup(*series[2:])
        self.remove(series)
        self.add(name, approx, terms)
        self.play(m.FadeOut(terms, shift=0.4 * m.UP), run_time=0.8)
        self.play(
            m.ReplacementTransform(approx, whole[1]),
            name.animate.move_to(whole[0]),
            m.FadeIn(whole[2], shift=0.4 * m.UP),
            run_time=1.4,
        )
        self.wait(2)


if __name__ == "__main__":
    TaylorSeries().render("taylor_series.mp4")

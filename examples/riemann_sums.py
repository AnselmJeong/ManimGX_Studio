"""The area under a curve is the limit of sums of thin rectangles.

Cut the stretch from a to b into strips of width Δx and stand a rectangle in each, as tall as
the curve at the strip's left edge: the rectangles' areas add up to Σ f(xᵢ)Δx, close to the area
under the curve but not equal to it. Halve Δx and every rectangle splits in two, the new right
half rising or sinking to meet the curve; the sum creeps toward the true area. In the limit
Δx → 0 the sum becomes the integral ∫ₐᵇ f(x) dx, and the integral is the area.
"""

import numpy as np

import manimgx as m

WALL = 3.4  # the rectangles split, again and again

A, B = 0.5, 4.5  # the region
LEVELS = 6  # halvings: Δx from 1 down to 1/64
COLORS = (m.BLUE, m.GREEN)  # the rectangles' gradient, left to right


def F(x: np.ndarray) -> np.ndarray:
    """A wave on a slope, at every x of an array."""
    return 1 + 0.6 * x + 0.9 * np.sin(1.6 * x)


def f(x: float) -> float:
    return float(F(np.asarray(x)))


def exact_area(a: float, b: float, n: int = 20000) -> float:
    """∫ₐᵇ f(x) dx by Simpson's rule on n (even) strips."""
    xs = np.linspace(a, b, n + 1)
    ys = np.array([f(x) for x in xs])
    h = (b - a) / n
    return float(h / 3 * (ys[0] + ys[-1] + 4 * ys[1:-1:2].sum() + 2 * ys[2:-1:2].sum()))


def gap(width: float) -> float:
    """The gap between neighbouring rectangles `width` wide, in scene units: a sliver of
    page between wide ones, none between thin ones, which overlap a hair instead (two edges
    that merely touch would show a seam)."""
    return 0.06 * min(1.0, width / 0.5) ** 2 - 0.01 * (1 - min(1.0, width / 0.1))


class RiemannSums(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(
            x_range=[0, 5, 1],
            y_range=[0, 5, 1],
            x_length=10.5,
            y_length=5.2,
            tips=False,
            axis_config={"stroke_width": 3, "color": m.GREY_B},
        ).move_to(np.array([0.2, -0.75, 0]))
        curve = axes.plot(f, x_range=[0.05, 4.95], color=m.YELLOW, stroke_width=7)
        curve.set_z_index(1)  # over the rectangles
        f_label = m.MathTex("f(x)", color=m.YELLOW, font_size=52)
        f_label.next_to(axes.c2p(4.95, f(4.95)), m.RIGHT, buff=0.2)
        ends = m.VGroup(
            *[
                m.MathTex(name, font_size=48).next_to(axes.c2p(x, 0), m.DOWN, buff=0.25)
                for name, x in (("a", A), ("b", B))
            ]
        )
        x_unit = axes.get_x_unit_size()
        origin = axes.c2p(0, 0)
        y_unit = axes.c2p(0, 1)[1] - origin[1]
        gradient = np.array([c.to_rgb() for c in m.color_gradient(list(COLORS), 101)])

        def color_at(x: np.ndarray) -> np.ndarray:
            """The gradient's color (RGB rows) at each x, from a's to b's."""
            k = np.clip(np.round(100 * (x - A) / (B - A)), 0, 100).astype(int)
            return gradient[k]

        # the rectangles of level L (Δx = 1/2^L) splitting into those of level L + 1, at
        # progress s: each into a left half that keeps its height and a right half that
        # moves to the curve at its own left edge
        level = m.ValueTracker(0.0)  # L + s
        grown = m.ValueTracker(0.0)  # how far the first rectangles have risen
        memo: dict[tuple[float, float], tuple[np.ndarray, ...]] = {}

        def pair(a: np.ndarray, b: np.ndarray) -> np.ndarray:
            """Interleave two arrays row by row: a[0], b[0], a[1], b[1], …"""
            return np.stack([a, b], axis=1).reshape(-1, *a.shape[1:])

        def strips() -> tuple[np.ndarray, ...]:
            """The rectangles shown, as arrays: left and right x, height, the gaps at
            their left and right, and their colors (RGB rows)."""
            key = (level.get_value(), grown.get_value())
            if key in memo:
                return memo[key]
            whole = min(int(key[0]), LEVELS)
            s = key[0] - whole
            dx = 1 / 2**whole
            outer = (1 - s) * gap(dx * x_unit) + s * gap(dx / 2 * x_unit)
            inner = (1 - s) * -0.01 + s * gap(dx / 2 * x_unit)  # the split opens
            x = A + dx * np.arange(round((B - A) / dx))
            h = key[1] * F(x)
            n = len(x)
            if s == 0:
                shown = (
                    x,
                    x + dx,
                    h,
                    np.full(n, outer),
                    np.full(n, outer),
                    color_at(x + dx / 2),
                )
            else:
                mid = x + dx / 2
                parent = color_at(mid)
                shown = (
                    pair(x, mid),
                    pair(mid, x + dx),
                    pair(h, h + s * (key[1] * F(mid) - h)),
                    pair(np.full(n, outer), np.full(n, inner)),
                    pair(np.full(n, inner), np.full(n, outer)),
                    pair(
                        parent + s * (color_at(x + dx / 4) - parent),
                        parent + s * (color_at(x + 3 * dx / 4) - parent),
                    ),
                )
            memo.clear()
            memo[key] = shown
            return shown

        def area_shown() -> float:
            left, right, h, *_ = strips()
            return float(((right - left) * h).sum())

        pieces: list[m.VMobject] = []  # the rectangles' shapes, reshaped every frame

        def rectangles(group: m.Mobject) -> None:
            """Reshape the rectangles in place (one VMobject each, made anew only when
            their number changes)."""
            left, right, h, gap_left, gap_right, colors = strips()
            if len(pieces) != len(left):
                pieces[:] = [m.VMobject(stroke_width=0, fill_opacity=1) for _ in left]
                group.submobjects = list(pieces)
            x0 = origin[0] + left * x_unit + gap_left / 2
            x1 = origin[0] + right * x_unit - gap_right / 2
            y0, y1 = origin[1], origin[1] + h * y_unit
            for k, rect in enumerate(pieces):
                rect.set_points_as_corners(
                    [
                        [x0[k], y0, 0],
                        [x1[k], y0, 0],
                        [x1[k], y1[k], 0],
                        [x0[k], y1[k], 0],
                        [x0[k], y0, 0],
                    ]
                )
                rect.set_fill(m.ManimColor.from_rgb(colors[k]), 1)

        bars = m.VGroup()
        rectangles(bars)
        bars.add_updater(rectangles)

        # the readouts: Δx, the sum of the areas (live), and the true area it tends to
        dx_tex = m.MathTex(r"\Delta x =", font_size=52)
        dx_tex.move_to(np.array([-6.6, 3.3, 0]), aligned_edge=m.LEFT)

        def delta(dx: float) -> m.MathTex:
            """Δx's value, written out exactly: 1, 0.5, 0.25, …"""
            return m.MathTex(f"{dx:g}", font_size=52).next_to(dx_tex, m.RIGHT, buff=0.2)

        dx_value = delta(1)
        sum_tex = m.MathTex(
            r"{{ \sum_{i} }} {{f(}} {{x_i}} {{)}} \, {{\Delta x}} {{=}}", font_size=56
        )
        sum_tex.get_parts_by_tex("f(").set_color(m.YELLOW)
        sum_tex.get_parts_by_tex("x_i").set_color(m.YELLOW)
        sum_tex.get_parts_by_tex(")").set_color(m.YELLOW)
        sum_tex.move_to(np.array([-0.9, 3.2, 0]), aligned_edge=m.LEFT)
        truth = exact_area(A, B)
        # the number after the "=": the rectangles' total area, until it becomes the
        # integral's value, `settled` once Δx → 0 (−1 until then)
        settled = m.ValueTracker(-1.0)
        equals = [sum_tex[-1]]
        total = m.DecimalNumber(0, num_decimal_places=2, font_size=56)

        # its opacity: it fades in by this, not by an animation, which would hold its value
        written = m.ValueTracker(0.0)

        def show_total(mob: m.Mobject) -> None:
            value = settled.get_value()
            total.set_value(area_shown() if value < 0 else value)
            total.next_to(equals[0], m.RIGHT, buff=0.25)
            total.set_opacity(written.get_value())

        show_total(total)
        total.add_updater(show_total)
        self.add(total)
        target = m.MathTex(r"\to", font_size=56, color=m.GREY_B)
        target_value = m.DecimalNumber(
            truth, num_decimal_places=2, font_size=56, color=m.GREY_B
        )
        goal = m.VGroup(target, target_value).arrange(m.RIGHT, buff=0.25)
        widest = target_value.copy().move_to(total, aligned_edge=m.LEFT)  # 5 characters
        goal.next_to(widest, m.RIGHT, buff=0.35)

        self.add(axes)
        self.play(m.Create(curve), m.FadeIn(f_label), m.FadeIn(ends), run_time=1.4)
        self.add(bars)
        self.play(
            grown.animate.set_value(1.0),
            m.FadeIn(dx_tex),
            m.FadeIn(dx_value),
            m.Write(sum_tex),
            written.animate.set_value(1.0),
            run_time=1.5,
        )
        self.play(m.FadeIn(goal, shift=0.2 * m.LEFT), run_time=0.5)
        # Δx halves, again and again: the sum creeps toward the area
        # Δx's new value comes in as the split begins
        early = m.squish_rate_func(m.smooth, 0.0, 0.35)
        for k in range(LEVELS):
            new_value = delta(1 / 2 ** (k + 1))
            self.play(
                level.animate.set_value(k + 1.0),
                m.FadeOut(dx_value, shift=0.3 * m.UP, rate_func=early),
                m.FadeIn(new_value, shift=0.3 * m.UP, rate_func=early),
                run_time=1.8 if k < 3 else 1.4,
            )
            dx_value = new_value
            self.wait(0.15)
        self.wait(0.4)

        # Δx → 0: the sum becomes the integral, and the integral is the area
        integral_tex = m.MathTex(
            r"{{ \int_a^b }} {{f(}} {{x}} {{)}} \, {{dx}} {{=}}", font_size=56
        )
        integral_tex.get_parts_by_tex("f(").set_color(m.YELLOW)
        integral_tex.get_parts_by_tex("x", substring=False).set_color(m.YELLOW)
        integral_tex.get_parts_by_tex(")").set_color(m.YELLOW)
        width = integral_tex.width + 0.25 + total.width  # with its value, centered
        left = axes.get_center()[0] - width / 2
        integral_tex.move_to(np.array([left, 3.2, 0]), aligned_edge=m.LEFT)
        region = axes.get_area(axes.plot(f, x_range=[A, B, 0.01]), x_range=(A, B))
        region.set_stroke(width=0).set_fill(list(COLORS), opacity=1)
        region.set_sheen_direction(m.RIGHT)
        settled.set_value(area_shown())
        self.play(
            m.TransformMatchingTex(
                sum_tex,
                integral_tex,
                key_map={r"\sum_{i}": r"\int_a^b", "x_i": "x", r"\Delta x": "dx"},
            ),
            m.FadeOut(dx_tex),
            m.FadeOut(dx_value),
            m.FadeOut(goal),
            settled.animate.set_value(truth),
            m.FadeIn(region),  # over the thin rectangles, which it then replaces
            run_time=2,
        )
        equals[0] = integral_tex[-1]
        self.remove(bars)
        self.wait(2)


if __name__ == "__main__":
    RiemannSums().render("riemann_sums.mp4")

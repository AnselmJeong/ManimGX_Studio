"""Animate the convolution of two boxes f(x) and g(x): flip g, slide it across f, show the running area as the convolution result."""

import numpy as np

import manimgx as m


def f(x: float) -> float:
    """Box f(x) = 1 for x in [0, 1], else 0."""
    return 1.0 if 0.0 <= x <= 1.0 else 0.0


def g(x: float) -> float:
    """Box g(x) = 1 for x in [0, 1], else 0 — same width as f for a triangular convolution."""
    return 1.0 if 0.0 <= x <= 1.0 else 0.0


def convolution_at(s: float, num_samples: int = 201) -> float:
    """Numerical integral of f(x) * g(s - x) dx over a window wide enough to cover the support."""
    xs = np.linspace(-2.0, 3.0, num_samples)
    values = np.array([f(x) * g(s - x) for x in xs])
    return float(np.trapezoid(values, xs))


class TeacherScene(m.Scene):
    def construct(self):
        # Two stacked panels: top is the flip-and-slide, bottom is the cumulative convolution.
        top_axes = m.Axes(
            x_range=(-2.0, 3.0, 1.0),
            y_range=(0.0, 1.2, 1.0),
            x_length=8.0,
            y_length=1.8,
        ).shift(1.6 * m.UP)

        bot_axes = m.Axes(
            x_range=(-2.0, 3.0, 1.0),
            y_range=(0.0, 1.2, 1.0),
            x_length=8.0,
            y_length=1.8,
        ).shift(1.6 * m.DOWN)

        # Panel labels.
        top_label = m.MathTex(r"f(x) \cdot g(s - x)", font_size=30).next_to(
            top_axes, m.UP, buff=0.15
        )
        bot_label = m.MathTex(r"(f * g)(s)", font_size=30).next_to(
            bot_axes, m.UP, buff=0.15
        )

        self.play(
            m.Create(top_axes),
            m.Create(bot_axes),
            m.Write(top_label),
            m.Write(bot_label),
            run_time=1.4,
        )

        # Static f(x) curve on top panel — always visible.
        f_graph = top_axes.plot(
            f, x_range=(-2.0, 3.0, 0.005), color=m.BLUE, stroke_width=3.0
        )
        self.play(m.Create(f_graph), run_time=1.0)

        # The slider that drives everything.
        s_tracker = m.ValueTracker(-1.2)

        # Flipped-and-shifted g on top panel: g(s - x).
        g_graph = m.always_redraw(
            lambda: top_axes.plot(
                lambda x: g(s_tracker.get_value() - x),
                x_range=(-2.0, 3.0, 0.005),
                color=m.YELLOW,
                stroke_width=3.0,
            )
        )

        # Product curve f(x) * g(s - x) drawn as a filled polyline on top panel.
        def product_area() -> m.VMobject:
            s = s_tracker.get_value()
            xs = np.linspace(-2.0, 3.0, 241)
            shape_points = [top_axes.c2p(float(xs[0]), 0.0)]
            for x in xs:
                y = f(float(x)) * g(s - float(x))
                shape_points.append(top_axes.c2p(float(x), y))
            shape_points.append(top_axes.c2p(float(xs[-1]), 0.0))
            shape = m.Polygon(*shape_points).set_stroke(m.GREEN, 0)
            shape.set_fill(m.GREEN, 0.45)
            return shape

        product_shape = m.always_redraw(product_area)

        self.play(m.FadeIn(g_graph), m.FadeIn(product_shape), run_time=0.9)

        # Traced convolution dot on the bottom panel.
        conv_dot = m.always_redraw(
            lambda: m.Dot(
                bot_axes.c2p(
                    s_tracker.get_value(), convolution_at(s_tracker.get_value())
                ),
                radius=0.07,
                color=m.GREEN,
            )
        )

        # TracedPath follows the dot; its callable captures the tracker each frame.
        trace = m.TracedPath(
            lambda: bot_axes.c2p(
                s_tracker.get_value(), convolution_at(s_tracker.get_value())
            ),
            stroke_color=m.GREEN,
            stroke_width=3.0,
        )

        self.add(conv_dot, trace)

        # Sweep s across the support.
        self.play(s_tracker.animate.set_value(2.0), run_time=5.0, rate_func=m.linear)

        self.wait(0.5)

"""Show me the tangent line to y = x squared sliding along the curve, with the slope value updating live."""

import manimgx as m


class TeacherScene(m.Scene):
    def construct(self):
        # Axes sized to fit the safe zone with room for a slope readout at the bottom.
        axes = m.Axes(
            x_range=(-0.2, 3.2, 1.0),
            y_range=(-1.0, 10.0, 2.0),
            x_length=7.0,
            y_length=4.4,
        ).shift(0.3 * m.UP)

        curve = axes.plot(lambda x: x**2, x_range=(0.0, 3.0), color=m.BLUE)

        # Intro the stage.
        self.play(m.Create(axes), run_time=1.0)
        self.play(m.Create(curve), run_time=1.2)

        # One tracker drives everything — the canonical 3b1b live-coupling move.
        x0 = m.ValueTracker(0.3)

        # Moving point on the curve.
        dot = m.always_redraw(
            lambda: m.Dot(
                axes.c2p(x0.get_value(), x0.get_value() ** 2),
                radius=0.08,
                color=m.YELLOW,
            )
        )

        # Tangent line: y = 2*x0*(x - x0) + x0^2, drawn as a short segment near x0.
        def tangent_graph() -> m.ParametricFunction:
            x_val = x0.get_value()
            slope = 2.0 * x_val
            x_lo = max(0.0, x_val - 0.9)
            x_hi = min(3.0, x_val + 0.9)
            return axes.plot(
                lambda x: slope * (x - x_val) + x_val**2,
                x_range=(x_lo, x_hi),
                color=m.RED,
            )

        tangent = m.always_redraw(tangent_graph)

        # Live slope readout pinned below the axes.
        slope_text = m.always_redraw(
            lambda: m.MathTex(
                rf"\text{{slope}} = {2.0 * x0.get_value():.2f}",
                font_size=32,
            ).to_edge(m.DOWN, buff=0.4)
        )

        # Reveal the coupled trio.
        self.play(m.FadeIn(dot), m.Create(tangent), m.Write(slope_text), run_time=1.2)

        # The slide — linear rate so the slope reads as uniformly changing over x.
        self.play(x0.animate.set_value(2.8), run_time=4.0, rate_func=m.linear)

        # Settle.
        self.play(x0.animate.set_value(1.5), run_time=1.6, rate_func=m.linear)

        self.wait(0.5)

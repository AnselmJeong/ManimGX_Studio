import numpy as np

import manimgx as m


def f(x: float) -> float:
    return x * x


class TeacherScene(m.Scene):
    def construct(self) -> None:
        ax = m.Axes(
            x_range=[-0.5, 2.5, 0.5],
            y_range=[-0.5, 5, 1],
            x_length=9,
            y_length=6,
        )
        curve = ax.plot(f, color=m.BLUE)
        self.play(m.Create(ax), m.Create(curve))

        x0 = 1.0
        dx = m.ValueTracker(1.0)

        def secant() -> m.Line:
            x1 = x0 + dx.get_value()
            p0 = ax.c2p(x0, f(x0))
            p1 = ax.c2p(x1, f(x1))
            direction = p1 - p0
            norm = np.linalg.norm(direction)
            if norm > 1e-9:
                direction = direction / norm
            return m.Line(
                p0 - direction * 1.4,
                p1 + direction * 0.6,
                color=m.YELLOW,
                stroke_width=3,
            )

        def endpoints() -> m.VGroup:
            x1 = x0 + dx.get_value()
            return m.VGroup(
                m.Dot(ax.c2p(x0, f(x0)), color=m.RED, radius=0.08),
                m.Dot(ax.c2p(x1, f(x1)), color=m.RED, radius=0.08),
            )

        def slope_text() -> m.MathTex:
            slope = (f(x0 + dx.get_value()) - f(x0)) / dx.get_value()
            return m.MathTex(
                f"\\frac{{df}}{{dx}} \\approx {slope:.2f}",
                color=m.YELLOW,
            ).to_corner(m.UR, buff=0.5)

        self.add(
            m.always_redraw(secant),
            m.always_redraw(endpoints),
            m.always_redraw(slope_text),
        )
        self.wait(0.4)
        self.play(dx.animate.set_value(0.05), run_time=4.5)
        self.wait(1.5)

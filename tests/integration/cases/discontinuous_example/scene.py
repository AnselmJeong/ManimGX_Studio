# Source: manim/mobject/graphing/functions.py
import manimgx as m


class DiscontinuousExample(m.Scene):
    def construct(self):
        ax1 = m.NumberPlane((-3, 3), (-4, 4))
        ax2 = m.NumberPlane((-3, 3), (-4, 4))
        m.VGroup(ax1, ax2).arrange()

        def discontinuous_function(x):
            if abs(x + 2) < 1e-9:
                x = -2.01
            elif abs(x - 2) < 1e-9:
                x = 2.01
            return (x**2 - 2) / (x**2 - 4)

        incorrect = ax1.plot(discontinuous_function, color=m.RED)
        discontinuities = [-2, 2]  # discontinuous points
        dt = 0.1  # left and right tolerance of discontinuity
        correct = m.VGroup(
            ax2.plot(
                discontinuous_function,
                x_range=(-3, discontinuities[0] - dt),
                color=m.GREEN,
            ),
            ax2.plot(
                discontinuous_function,
                x_range=(discontinuities[0] + dt, discontinuities[1] - dt),
                color=m.GREEN,
            ),
            ax2.plot(
                discontinuous_function,
                x_range=(discontinuities[1] + dt, 3),
                color=m.GREEN,
            ),
        )
        self.add(ax1, ax2, incorrect, correct)
        self.wait()

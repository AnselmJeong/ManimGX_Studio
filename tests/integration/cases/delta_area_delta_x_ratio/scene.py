import math

import manimgx as m


def f(x: float) -> float:
    return 0.5 + 0.3 * math.sin(x) + 0.12 * x


class TeacherScene(m.Scene):
    def construct(self) -> None:
        ax = m.Axes(
            x_range=[0, 5, 1],
            y_range=[0, 2, 0.5],
            x_length=10,
            y_length=5,
        ).shift(m.DOWN * 0.5)
        curve = ax.plot(f, color=m.BLUE, x_range=[0, 5])
        self.play(m.Create(ax), m.Create(curve))

        title = m.MathTex(
            "\\frac{\\Delta A}{\\Delta x} \\approx f(x)",
            color=m.YELLOW,
        ).to_edge(m.UP, buff=0.4)
        self.play(m.Write(title))

        x = m.ValueTracker(2.0)
        dx = 0.5

        def area_region() -> m.Polygon:
            return ax.get_area(
                curve,
                x_range=[0, x.get_value()],
                color=m.YELLOW,
                opacity=0.45,
            )

        def delta_region() -> m.Polygon:
            return ax.get_area(
                curve,
                x_range=[x.get_value(), x.get_value() + dx],
                color=m.GREEN,
                opacity=0.7,
            )

        self.add(m.always_redraw(area_region), m.always_redraw(delta_region))
        self.play(x.animate.set_value(3.6), run_time=3.0)
        self.wait(1.5)

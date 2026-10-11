# Regression: a complete Printery scene rendered under Manim CE 0.20.1 but
# failed under manimgx when it called Axes.get_width().
import manimgx as m


class AxesGetWidthMethod(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(
            x_range=[-2, 2, 1],
            y_range=[-1, 1, 1],
            x_length=6,
            y_length=3,
        )
        width = axes.get_width()
        span = m.Line(m.LEFT * width / 2, m.RIGHT * width / 2, color=m.YELLOW)
        span.next_to(axes, m.DOWN)
        self.add(axes, span)
        self.wait(0.2)

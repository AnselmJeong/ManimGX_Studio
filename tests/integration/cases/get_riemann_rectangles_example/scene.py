# Source: manim/mobject/graphing/coordinate_systems.py
import manimgx as m


class GetRiemannRectanglesExample(m.Scene):
    def construct(self):
        ax = m.Axes(y_range=[-2, 10])
        quadratic = ax.plot(lambda x: 0.5 * x**2 - 0.5)

        # the rectangles are constructed from their top right corner.
        # passing an iterable to `color` produces a gradient
        rects_right = ax.get_riemann_rectangles(
            quadratic,
            x_range=[-4, -3],
            dx=0.25,
            color=(m.TEAL, m.BLUE_B, m.DARK_BLUE),
            input_sample_type="right",
        )

        # the colour of rectangles below the x-axis is inverted
        # due to show_signed_area
        rects_left = ax.get_riemann_rectangles(
            quadratic, x_range=[-1.5, 1.5], dx=0.15, color=m.YELLOW
        )

        bounding_line = ax.plot(lambda x: 1.5 * x, color=m.BLUE_B, x_range=[3.3, 6])
        bounded_rects = ax.get_riemann_rectangles(
            bounding_line,
            bounded_graph=quadratic,
            dx=0.15,
            x_range=[4, 5],
            show_signed_area=False,
            color=(m.MAROON_A, m.RED_B, m.PURPLE_D),
        )

        self.add(ax, bounding_line, quadratic, rects_right, rects_left, bounded_rects)
        self.wait()
